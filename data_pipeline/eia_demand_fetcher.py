"""
EIA PJM Daily Demand Data Fetcher
─────────────────────────────────
Fetches PJM sub-BA daily demand data (AE, JC, PS, RECO) from the EIA API.
Supports both full download and incremental append modes.

Storage: All demand data is persisted to the `daily_subba_demand` database
table.  CSV is retained as a secondary backup only.

Usage:
    # As a module (called by scheduler):
    from data_pipeline.eia_demand_fetcher import fetch_and_update_daily_demand
    fetch_and_update_daily_demand()

    # Standalone:
    python -m data_pipeline.eia_demand_fetcher
"""

import os
import csv
import time
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

API_KEY = os.environ.get("EIA_API_KEY", "MPXiO8mjvmZc9fgNWkeZhhKP9SYaBbQDxodAswcg")

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-sub-ba-data/data/"

SUBBAS = ["AE", "JC", "PS", "RECO"]   # PJM sub-balancing authorities

FULL_START_DATE = "2019-01-01"          # earliest date for full downloads
PAGE_SIZE       = 5000                  # max records per API request
REQUEST_DELAY   = 0.5                   # seconds between pages

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "eia_pjm_daily_demand.csv"


# ── API helpers ───────────────────────────────────────────────────────────────

def _build_params(start_date: str, end_date: str, offset: int) -> list:
    """
    Build request params as a list of tuples so repeated keys
    (facets[subba][]) are handled correctly by the requests library.
    """
    params = [
        ("api_key",            API_KEY),
        ("frequency",          "daily"),
        ("data[0]",            "value"),
        ("facets[parent][]",   "PJM"),
        ("start",              start_date),
        ("end",                end_date),
        ("sort[0][column]",    "period"),
        ("sort[0][direction]", "asc"),
        ("length",             PAGE_SIZE),
        ("offset",             offset),
    ]
    for subba in SUBBAS:
        params.append(("facets[subba][]", subba))
    return params


def _fetch_page(session: requests.Session, start_date: str, end_date: str, offset: int) -> dict:
    """GET one page of results from the EIA API."""
    resp = session.get(BASE_URL, params=_build_params(start_date, end_date, offset), timeout=30)

    if resp.status_code == 403:
        raise RuntimeError(
            "403 Forbidden — EIA API key may be invalid or missing. "
            "Register at: https://www.eia.gov/opendata/"
        )
    if resp.status_code == 429:
        raise RuntimeError(
            "429 Too Many Requests — EIA rate limit hit. "
            "Wait a few minutes and try again."
        )

    resp.raise_for_status()
    return resp.json()


def _download_records(start_date: str, end_date: str) -> list[dict]:
    """Page through every result page and return a flat list of records."""
    all_records = []
    offset = 0

    with requests.Session() as session:
        # Page 1 — also discovers the total record count
        logger.info(f"EIA fetch page 1 (offset=0, {start_date} → {end_date})...")
        payload = _fetch_page(session, start_date, end_date, offset)
        body    = payload.get("response", {})
        total   = int(body.get("total", 0))
        records = body.get("data", [])

        if total == 0:
            logger.info("EIA API returned 0 records for the given date range.")
            return []

        all_records.extend(records)
        pages_needed = -(-total // PAGE_SIZE)  # ceiling division
        logger.info(f"  {len(records):,} records fetched | total: {total:,} | pages: {pages_needed}")

        # Remaining pages
        offset += PAGE_SIZE
        page = 2
        while offset < total:
            time.sleep(REQUEST_DELAY)
            logger.info(f"EIA fetch page {page} (offset={offset})...")
            payload = _fetch_page(session, start_date, end_date, offset)
            records = payload.get("response", {}).get("data", [])
            if not records:
                break
            all_records.extend(records)
            logger.info(f"  {len(records):,} records fetched | total so far: {len(all_records):,}")
            offset += PAGE_SIZE
            page += 1

    logger.info(f"EIA download complete — {len(all_records):,} records total")
    return all_records


# ── Database helpers ──────────────────────────────────────────────────────────

def _upsert_demand_to_db(df: pd.DataFrame) -> int:
    """Insert or update demand records into the daily_subba_demand table.

    Uses merge semantics: if a (period, subba) pair already exists, update;
    otherwise insert.  Returns the number of rows written.
    """
    from database.connection import get_sync_session
    from database.models import DailySubBaDemand

    if df is None or df.empty:
        return 0

    rows_written = 0
    with get_sync_session() as session:
        for _, row in df.iterrows():
            row_date = pd.to_datetime(row["period"]).date()
            subba = str(row.get("subba", ""))
            value = float(row["value"]) if pd.notna(row.get("value")) else None
            parent = str(row.get("parent", row.get("parent-name", "PJM")))

            existing = session.query(DailySubBaDemand).filter(
                DailySubBaDemand.period == row_date,
                DailySubBaDemand.subba == subba,
            ).first()

            if existing:
                existing.value = value
                existing.parent = parent
            else:
                record = DailySubBaDemand(
                    period=row_date,
                    subba=subba,
                    value=value,
                    parent=parent,
                )
                session.add(record)
            rows_written += 1
        session.commit()
    logger.info(f"Upserted {rows_written} demand records to database")
    return rows_written


def _load_demand_from_db() -> pd.DataFrame:
    """Load all demand records from the database into a DataFrame."""
    from database.connection import get_sync_session
    from database.models import DailySubBaDemand

    with get_sync_session() as session:
        rows = (
            session.query(DailySubBaDemand)
            .order_by(DailySubBaDemand.period.asc(), DailySubBaDemand.subba.asc())
            .all()
        )
        records = []
        for r in rows:
            records.append({
                "period": str(r.period),
                "subba": r.subba,
                "value": r.value,
                "parent": r.parent,
            })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def _get_last_db_demand_date() -> Optional[date]:
    """Return the latest period in the daily_subba_demand table, or None."""
    from database.connection import get_sync_session
    from database.models import DailySubBaDemand

    with get_sync_session() as session:
        result = session.query(func.max(DailySubBaDemand.period)).scalar()
    return result


# ── Core public API ───────────────────────────────────────────────────────────

def fetch_and_update_daily_demand(output_path: str | Path | None = None) -> Path:
    """
    Fetch the latest PJM daily demand data from EIA and persist to the database.

    - If the DB has data: reads the last date, fetches only newer data, and upserts.
    - If the DB is empty but a CSV exists: migrates CSV to DB first, then fetches new.
    - If neither exists: downloads the full history from 2019-01-01.

    Also writes a CSV backup.  Returns the path to the CSV file.
    """
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── Try database first ────────────────────────────────────────────────
    last_db_date = _get_last_db_demand_date()

    if last_db_date is not None:
        start_date = (last_db_date + timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(
            f"Incremental mode (DB): existing data through {last_db_date}, "
            f"fetching from {start_date}"
        )

        if start_date > today_str:
            logger.info("Data is already up to date — nothing to fetch.")
            return output_path

        new_records = _download_records(start_date, today_str)
        if new_records:
            new_df = pd.DataFrame(new_records)
            _upsert_demand_to_db(new_df)
            logger.info(f"Appended {len(new_records):,} new records to database.")
        else:
            logger.info("No new records returned by EIA API.")

        # Update CSV backup
        full_df = _load_demand_from_db()
        if not full_df.empty:
            full_df.to_csv(output_path, index=False)
        return output_path

    # ── Fallback: check CSV (migration path) ──────────────────────────────
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("No DB demand data found. Migrating from CSV to database...")
        try:
            existing_df = pd.read_csv(output_path)
            _upsert_demand_to_db(existing_df)

            last_date = pd.to_datetime(existing_df["period"]).max()
            start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

            if start_date <= today_str:
                new_records = _download_records(start_date, today_str)
                if new_records:
                    _upsert_demand_to_db(pd.DataFrame(new_records))

        except Exception as e:
            logger.warning(f"CSV migration failed ({e}), doing full download")
            return _full_download(output_path, today_str)

        return output_path

    # ── No existing data — full download ──────────────────────────────────
    return _full_download(output_path, today_str)


def _full_download(output_path: Path, today_str: str) -> Path:
    """Perform a full download from FULL_START_DATE."""
    logger.info("No existing data found — performing full download")

    new_records = _download_records(FULL_START_DATE, today_str)

    if not new_records:
        logger.info("No records returned by EIA API.")
        return output_path

    new_df = pd.DataFrame(new_records)

    # Persist to database
    _upsert_demand_to_db(new_df)

    # Sort and save CSV backup
    new_df = new_df.sort_values(["period", "subba"]).reset_index(drop=True)
    new_df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(new_df):,} total records to {output_path}")
    logger.info(f"  Date range: {new_df['period'].min()} → {new_df['period'].max()}")

    return output_path


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    masked = ("*" * (len(API_KEY) - 4) + API_KEY[-4:]) if len(API_KEY) > 8 else "(not set)"
    print("=" * 60)
    print("  EIA PJM Sub-BA Daily Demand Fetcher")
    print(f"  Sub-BAs : {', '.join(SUBBAS)}")
    print(f"  API key : {masked}")
    print(f"  Output  : {DEFAULT_OUTPUT}")
    print("=" * 60)

    result_path = fetch_and_update_daily_demand()
    print(f"\n  Done → {result_path}")
