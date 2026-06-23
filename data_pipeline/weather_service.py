"""
Open-Meteo Weather Service for NJ Demand Forecasting
─────────────────────────────────────────────────────
Provides three clean functions:
    1. fetch_historical_weather()  — Gap-free archive data (2019 → yesterday)
    2. update_daily_weather()      — Incremental append of yesterday's weather
    3. fetch_forecast_weather()    — Real 7-day forecast for prediction

Uses Open-Meteo (free, no API key required).
NJ coordinates: lat=40.0583, lon=-74.4057 (central New Jersey).
Base temperature: 18°C (≈ 65°F) for HDD/CDD.

Storage: All historical weather data is persisted to the `weather_openmeteo`
database table.  CSV is retained as a secondary backup only.
"""

import logging
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

NJ_LAT = 40.0583
NJ_LON = -74.4057
BASE_TEMP_C = 18.0  # 18°C ≈ 65°F — standard base for HDD/CDD

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEATHER_CSV = PROJECT_ROOT / "data" / "raw" / "weather_openmeteo.csv"

# Maximum gap size (days) to interpolate; larger gaps are left as NaN
MAX_INTERP_GAP = 3


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compute_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute temp_avg, HDD, CDD from tmax/tmin columns (Celsius)."""
    df["temp_avg"] = (df["temp_max"] + df["temp_min"]) / 2.0
    df["hdd"] = (BASE_TEMP_C - df["temp_avg"]).clip(lower=0).round(2)
    df["cdd"] = (df["temp_avg"] - BASE_TEMP_C).clip(lower=0).round(2)
    return df


def _fetch_archive_chunk(start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Fetch one chunk from Open-Meteo Archive API."""
    params = {
        "latitude": NJ_LAT,
        "longitude": NJ_LON,
        "daily": "temperature_2m_max,temperature_2m_min",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "America/New_York",
    }
    try:
        resp = requests.get(ARCHIVE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        if not daily.get("time"):
            return None

        df = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "temp_max": daily["temperature_2m_max"],
            "temp_min": daily["temperature_2m_min"],
        })
        return _compute_weather_features(df)
    except Exception as e:
        logger.error(f"Open-Meteo archive fetch failed ({start_date} to {end_date}): {e}")
        return None


def _upsert_weather_to_db(df: pd.DataFrame) -> int:
    """Insert or update weather records into the weather_openmeteo table.

    Uses merge (upsert) semantics: if a date already exists, update it;
    otherwise insert a new row.  Returns the number of rows written.
    """
    from database.connection import get_sync_session
    from database.models import WeatherOpenMeteo

    if df is None or df.empty:
        return 0

    rows_written = 0
    with get_sync_session() as session:
        for _, row in df.iterrows():
            row_date = pd.to_datetime(row["date"]).date()
            existing = session.query(WeatherOpenMeteo).filter(
                WeatherOpenMeteo.date == row_date
            ).first()

            if existing:
                existing.temp_max = float(row["temp_max"]) if pd.notna(row["temp_max"]) else None
                existing.temp_min = float(row["temp_min"]) if pd.notna(row["temp_min"]) else None
                existing.temp_avg = float(row["temp_avg"]) if pd.notna(row["temp_avg"]) else None
                existing.hdd = float(row["hdd"]) if pd.notna(row["hdd"]) else None
                existing.cdd = float(row["cdd"]) if pd.notna(row["cdd"]) else None
            else:
                record = WeatherOpenMeteo(
                    date=row_date,
                    temp_max=float(row["temp_max"]) if pd.notna(row["temp_max"]) else None,
                    temp_min=float(row["temp_min"]) if pd.notna(row["temp_min"]) else None,
                    temp_avg=float(row["temp_avg"]) if pd.notna(row["temp_avg"]) else None,
                    hdd=float(row["hdd"]) if pd.notna(row["hdd"]) else None,
                    cdd=float(row["cdd"]) if pd.notna(row["cdd"]) else None,
                )
                session.add(record)
            rows_written += 1
        session.commit()
    logger.info(f"Upserted {rows_written} weather records to database")
    return rows_written


def _load_weather_from_db() -> pd.DataFrame:
    """Load all weather records from the database into a DataFrame."""
    from database.connection import get_sync_session
    from database.models import WeatherOpenMeteo

    with get_sync_session() as session:
        rows = session.query(WeatherOpenMeteo).order_by(WeatherOpenMeteo.date.asc()).all()
        records = []
        for r in rows:
            records.append({
                "date": pd.Timestamp(r.date),
                "temp_max": r.temp_max,
                "temp_min": r.temp_min,
                "temp_avg": r.temp_avg,
                "hdd": r.hdd,
                "cdd": r.cdd,
            })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def _get_last_db_date() -> Optional[date]:
    """Return the latest date in the weather_openmeteo table, or None."""
    from database.connection import get_sync_session
    from database.models import WeatherOpenMeteo

    with get_sync_session() as session:
        result = session.query(func.max(WeatherOpenMeteo.date)).scalar()
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_historical_weather(
    start_date: str = "2019-01-01",
    end_date: str | None = None,
    output_path: Path | str | None = None,
) -> pd.DataFrame:
    """
    Fetch gap-free historical weather from Open-Meteo Archive API.

    Fetches in yearly chunks (API limit), concatenates, deduplicates,
    persists to the database, and optionally saves a CSV backup.
    Returns a clean DataFrame indexed by date.
    """
    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    output_path = Path(output_path) if output_path else DEFAULT_WEATHER_CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    logger.info(f"Fetching Open-Meteo historical weather: {start_date} to {end_date}")

    frames = []
    current_start = start_dt

    while current_start <= end_dt:
        # Chunk by year (Open-Meteo handles multi-year but yearly is safer)
        chunk_end = min(
            datetime(current_start.year, 12, 31),
            end_dt,
        )
        chunk_start_str = current_start.strftime("%Y-%m-%d")
        chunk_end_str = chunk_end.strftime("%Y-%m-%d")

        logger.info(f"  Fetching {chunk_start_str} to {chunk_end_str}...")
        chunk_df = _fetch_archive_chunk(chunk_start_str, chunk_end_str)

        if chunk_df is not None and len(chunk_df) > 0:
            frames.append(chunk_df)
            logger.info(f"    Got {len(chunk_df)} days")
        else:
            logger.warning(f"    No data returned for {chunk_start_str} to {chunk_end_str}")

        # Move to next year
        current_start = datetime(current_start.year + 1, 1, 1)
        time.sleep(0.3)  # Rate limiting

    if not frames:
        logger.error("No weather data fetched from Open-Meteo.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Interpolate small gaps only (≤ MAX_INTERP_GAP days)
    for col in ["temp_max", "temp_min", "temp_avg", "hdd", "cdd"]:
        df[col] = df[col].interpolate(method="linear", limit=MAX_INTERP_GAP)

    # ── Persist to database (primary storage) ─────────────────────────────
    _upsert_weather_to_db(df)

    # ── Save CSV backup (secondary) ───────────────────────────────────────
    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df)} days of weather to {output_path}")
    logger.info(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    gaps = df[["temp_avg"]].isnull().sum().values[0]
    if gaps > 0:
        logger.warning(f"  {gaps} days still have missing temperature data (gaps > {MAX_INTERP_GAP} days)")

    return df


def update_daily_weather(output_path: Path | str | None = None) -> pd.DataFrame:
    """
    Incremental update: check the database for the latest date, fetch
    only new days from the API, and insert them into the database.

    Also updates the CSV backup.  Should be called daily by the scheduler.
    """
    output_path = Path(output_path) if output_path else DEFAULT_WEATHER_CSV

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # ── Try database first ────────────────────────────────────────────────
    last_db_date = _get_last_db_date()

    if last_db_date is not None:
        start_date = (last_db_date + timedelta(days=1)).strftime("%Y-%m-%d")

        if start_date > yesterday:
            logger.info("Weather data is already up to date (checked database).")
            return _load_weather_from_db()

        logger.info(f"Updating weather from DB: {start_date} to {yesterday}")
        new_df = _fetch_archive_chunk(start_date, yesterday)

        if new_df is not None and len(new_df) > 0:
            _upsert_weather_to_db(new_df)
            logger.info(f"Appended {len(new_df)} new days to database.")
        else:
            logger.warning("No new weather data returned from Open-Meteo.")

        # Reload full dataset from DB and update CSV backup
        full_df = _load_weather_from_db()
        if not full_df.empty:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            full_df.to_csv(output_path, index=False)
        return full_df

    # ── Fallback: check CSV (migration path) ──────────────────────────────
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("No DB weather data found. Migrating from CSV to database...")
        existing_df = pd.read_csv(output_path)
        existing_df["date"] = pd.to_datetime(existing_df["date"])
        _upsert_weather_to_db(existing_df)

        last_date = existing_df["date"].max()
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

        if start_date <= yesterday:
            new_df = _fetch_archive_chunk(start_date, yesterday)
            if new_df is not None and len(new_df) > 0:
                _upsert_weather_to_db(new_df)

        return _load_weather_from_db()

    # ── No existing data — do full backfill ───────────────────────────────
    logger.info("No existing weather data found. Running full historical backfill.")
    return fetch_historical_weather(output_path=output_path)


def fetch_forecast_weather(days: int = 7) -> pd.DataFrame:
    """
    Fetch real weather forecast from Open-Meteo Forecast API.

    Returns a DataFrame with columns: date, temp_max, temp_min, temp_avg, hdd, cdd.
    This is called at prediction time — NOT stored to disk.

    FAIL-LOUD: If the API call fails or returns empty data, a RuntimeError
    is raised.  No silent fallback to climatology or historical averages.
    """
    # Open-Meteo forecast API supports up to 16 days
    forecast_days = min(days, 16)

    params = {
        "latitude": NJ_LAT,
        "longitude": NJ_LON,
        "daily": "temperature_2m_max,temperature_2m_min",
        "forecast_days": forecast_days,
        "timezone": "America/New_York",
    }

    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})

        if not daily.get("time"):
            raise RuntimeError(
                "Open-Meteo forecast API returned empty data. "
                "Cannot generate demand forecast without real weather."
            )

        df = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "temp_max": daily["temperature_2m_max"],
            "temp_min": daily["temperature_2m_min"],
        })
        df = _compute_weather_features(df)

        # If user requested more than 16 days, extend with climatology
        # from the DATABASE (not CSV)
        if days > 16:
            logger.info(
                f"Forecast API provides {forecast_days} days; "
                f"extending remaining {days - forecast_days} with climatology."
            )
            last_forecast_date = df["date"].max()
            extra_dates = pd.date_range(
                last_forecast_date + timedelta(days=1),
                periods=days - forecast_days,
                freq="D",
            )

            # Load historical from database for climatology
            hist_df = _load_weather_from_db()
            if hist_df.empty:
                # Fallback to CSV if DB is empty (migration not yet run)
                if DEFAULT_WEATHER_CSV.exists():
                    hist_df = pd.read_csv(DEFAULT_WEATHER_CSV)
                    hist_df["date"] = pd.to_datetime(hist_df["date"])

            if not hist_df.empty:
                hist_df["month"] = hist_df["date"].dt.month
                hist_df["day"] = hist_df["date"].dt.day
                clim = hist_df.groupby(["month", "day"])[
                    ["temp_max", "temp_min", "temp_avg", "hdd", "cdd"]
                ].mean()

                extra_rows = []
                for d in extra_dates:
                    try:
                        row = clim.loc[(d.month, d.day)]
                        extra_rows.append({
                            "date": d,
                            "temp_max": row["temp_max"],
                            "temp_min": row["temp_min"],
                            "temp_avg": row["temp_avg"],
                            "hdd": row["hdd"],
                            "cdd": row["cdd"],
                        })
                    except KeyError:
                        extra_rows.append({
                            "date": d, "temp_max": 20, "temp_min": 10,
                            "temp_avg": 15, "hdd": 3, "cdd": 0,
                        })
                df = pd.concat([df, pd.DataFrame(extra_rows)], ignore_index=True)

        logger.info(f"Fetched {len(df)}-day weather forecast from Open-Meteo")
        return df

    except RuntimeError:
        # Re-raise RuntimeErrors (our own fail-loud errors)
        raise
    except Exception as e:
        raise RuntimeError(
            f"Open-Meteo forecast API failed: {e}. "
            f"Cannot generate demand forecast without real weather."
        ) from e


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("  Open-Meteo Weather Service for NJ")
    print(f"  Coordinates: {NJ_LAT}, {NJ_LON}")
    print("=" * 60)

    # Step 1: Full historical backfill
    hist = fetch_historical_weather()
    print(f"\nHistorical: {len(hist)} days")
    print(hist.tail())

    # Step 2: Forecast
    fc = fetch_forecast_weather(days=7)
    print(f"\n7-day Forecast:")
    print(fc)
