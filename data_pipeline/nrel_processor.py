"""
NREL NASA POWER Weather & Solar Data Processor
───────────────────────────────────────────────
Ingests the NASA POWER NJ hourly dataset (21 counties, 2015-2025),
validates data quality, computes daily/monthly aggregates with
engineered features, and persists results to:

  1. Parquet file (primary time-series store for hourly data)
  2. SQLite database (daily & monthly county aggregates only)

Storage design:
  - Raw hourly data → Parquet (~230 MB compressed)
  - Daily county aggregates → SQLite `weather_nrel_daily`
  - Monthly county aggregates → SQLite `weather_nrel_monthly`
  - Hourly data is NOT written to SQLite (avoids 2M+ row bloat)

Usage:
    from data_pipeline.nrel_processor import NRELProcessor
    processor = NRELProcessor()
    report = processor.run()
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "nrel data-20260730T125144Z-1-001" / "nrel data"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

# NASA POWER missing value sentinel
NASA_MISSING_VALUE = -999.0

# Base temperature for HDD/CDD in Celsius (18°C ≈ 65°F)
BASE_TEMP_C = 18.0

# Physical bounds for validation
VARIABLE_BOUNDS = {
    "T2M": (-60.0, 60.0),        # Air temperature at 2m (°C)
    "T2MDEW": (-80.0, 40.0),     # Dew point temperature (°C)
    "RH2M": (0.0, 100.0),        # Relative humidity (%)
    "WS2M": (0.0, 50.0),         # Wind speed at 2m (m/s)
    "WS10M": (0.0, 75.0),        # Wind speed at 10m (m/s)
    "WD10M": (0.0, 360.0),       # Wind direction at 10m (degrees)
    "PS": (80.0, 110.0),         # Surface pressure (kPa)
    "ALLSKY_SFC_SW_DWN": (0.0, 1400.0),   # Solar irradiance (W/m²)
    "ALLSKY_SFC_SW_DNI": (0.0, 1400.0),   # Direct normal irradiance (W/m²)
    "ALLSKY_SFC_SW_DIFF": (0.0, 800.0),   # Diffuse irradiance (W/m²)
    "ALLSKY_KT": (0.0, 1.0),     # Clearness index
    "PRECTOTCORR": (0.0, 200.0), # Precipitation (mm/h)
}

# Variables to use (excluding ALLSKY_SFC_PAR_TOT per plan)
WEATHER_VARIABLES = [
    "ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF",
    "T2M", "T2MDEW", "RH2M", "WS2M", "WS10M", "WD10M", "PS",
    "ALLSKY_KT", "PRECTOTCORR",
]


class NRELProcessor:
    """End-to-end NREL NASA POWER dataset processor."""

    def __init__(self, raw_dir: Path | str | None = None):
        self.raw_dir = Path(raw_dir) if raw_dir else RAW_DATA_DIR
        self.processed_dir = PROCESSED_DIR
        self.reports_dir = REPORTS_DIR
        self.parquet_path = self.processed_dir / "nrel_weather_hourly.parquet"
        self._cache: Optional[pd.DataFrame] = None
        self._daily_cache: Optional[pd.DataFrame] = None
        self._monthly_cache: Optional[pd.DataFrame] = None

    # ── 1. Dataset Discovery ─────────────────────────────────────────────

    def discover(self) -> Dict[str, Any]:
        """Scan the raw data directory and produce a dataset summary report."""
        logger.info("═" * 70)
        logger.info("NREL NASA POWER Dataset Discovery")
        logger.info("═" * 70)

        report: Dict[str, Any] = {
            "source": "NASA POWER / NREL",
            "scan_timestamp": datetime.now().isoformat(),
            "raw_directory": str(self.raw_dir),
            "files": [],
        }

        if not self.raw_dir.exists():
            report["error"] = f"Directory not found: {self.raw_dir}"
            logger.error(report["error"])
            return report

        # Scan for CSV files
        csv_files = list(self.raw_dir.glob("*.csv"))
        metadata_files = list(self.raw_dir.glob("*.json")) + list(self.raw_dir.glob("*.txt"))

        for f in csv_files:
            report["files"].append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "type": "csv",
            })

        for f in metadata_files:
            report["files"].append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "type": f.suffix.lstrip("."),
            })

        if not csv_files:
            report["error"] = "No CSV files found in dataset directory"
            logger.error(report["error"])
            return report

        # Quick scan of primary CSV
        primary_csv = csv_files[0]
        logger.info(f"Primary CSV: {primary_csv.name} ({report['files'][0]['size_mb']} MB)")

        # Read a sample to detect schema
        sample = pd.read_csv(primary_csv, nrows=1000)
        report["columns"] = sample.columns.tolist()
        report["dtypes"] = {col: str(dtype) for col, dtype in sample.dtypes.items()}
        report["total_columns"] = len(sample.columns)

        # Full read for comprehensive stats (chunked for memory efficiency)
        t0 = time.time()
        df = self._load_raw()
        load_time = time.time() - t0

        report["total_rows"] = len(df)
        report["load_time_seconds"] = round(load_time, 2)

        # Date range
        report["date_range"] = {
            "start": str(df["datetime"].min()),
            "end": str(df["datetime"].max()),
        }

        # Temporal resolution
        if len(df) > 1:
            dt_diff = df["datetime"].diff().dropna()
            median_gap = dt_diff.median()
            report["temporal_resolution"] = str(median_gap)

        # Locations
        locations = df[["location", "lat", "lon"]].drop_duplicates()
        report["locations"] = locations.to_dict("records")
        report["num_locations"] = len(locations)

        # Weather variables
        report["weather_variables"] = [
            col for col in df.columns
            if col not in ["datetime", "location", "lat", "lon"]
        ]

        # Missing values
        missing_counts = {}
        for col in report["weather_variables"]:
            nasa_missing = int((df[col] == NASA_MISSING_VALUE).sum())
            nan_missing = int(df[col].isna().sum())
            total_missing = nasa_missing + nan_missing
            if total_missing > 0:
                missing_counts[col] = {
                    "nasa_sentinel": nasa_missing,
                    "nan": nan_missing,
                    "total": total_missing,
                    "pct": round(total_missing / len(df) * 100, 3),
                }
        report["missing_values"] = missing_counts

        # Duplicate timestamps
        dupes = df.duplicated(subset=["datetime", "location"]).sum()
        report["duplicate_timestamps"] = int(dupes)

        # Invalid records (out-of-bounds)
        invalid_counts = {}
        for var, (lo, hi) in VARIABLE_BOUNDS.items():
            if var in df.columns:
                mask = (df[var] != NASA_MISSING_VALUE) & ((df[var] < lo) | (df[var] > hi))
                count = int(mask.sum())
                if count > 0:
                    invalid_counts[var] = count
        report["invalid_records"] = invalid_counts

        logger.info(f"  Rows: {report['total_rows']:,}")
        logger.info(f"  Locations: {report['num_locations']}")
        logger.info(f"  Date range: {report['date_range']['start']} → {report['date_range']['end']}")
        logger.info(f"  Duplicate timestamps: {report['duplicate_timestamps']}")
        logger.info(f"  Load time: {report['load_time_seconds']}s")

        return report

    # ── 2. Raw Loading ───────────────────────────────────────────────────

    def _load_raw(self) -> pd.DataFrame:
        """Load raw CSV with proper dtypes and datetime parsing."""
        csv_files = list(self.raw_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.raw_dir}")

        df = pd.read_csv(csv_files[0], parse_dates=["datetime"])
        return df

    # ── 3. Preprocessing & Validation ────────────────────────────────────

    def preprocess(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Clean and validate the raw dataset:
          - Replace NASA -999.0 sentinel with NaN
          - Validate physical bounds
          - Remove duplicate timestamps
          - Interpolate missing values (linear, max gap = 6 hours)
          - Ensure timezone consistency (UTC → America/New_York)
          - Drop ALLSKY_SFC_PAR_TOT (agricultural, not relevant)
        """
        if df is None:
            df = self._load_raw()

        t0 = time.time()
        initial_rows = len(df)
        logger.info(f"Preprocessing {initial_rows:,} NREL records...")

        df = df.copy()

        # Drop ALLSKY_SFC_PAR_TOT (photosynthetically active radiation — agricultural use only)
        if "ALLSKY_SFC_PAR_TOT" in df.columns:
            df = df.drop(columns=["ALLSKY_SFC_PAR_TOT"])
            logger.info("  Dropped ALLSKY_SFC_PAR_TOT (not relevant for electricity demand)")

        # Replace NASA sentinel value with NaN
        for col in WEATHER_VARIABLES:
            if col in df.columns:
                sentinel_count = (df[col] == NASA_MISSING_VALUE).sum()
                if sentinel_count > 0:
                    df.loc[df[col] == NASA_MISSING_VALUE, col] = np.nan
                    logger.info(f"  Replaced {sentinel_count:,} sentinel values in {col}")

        # Validate physical bounds — clip to valid ranges
        for var, (lo, hi) in VARIABLE_BOUNDS.items():
            if var in df.columns:
                out_of_bounds = ((df[var] < lo) | (df[var] > hi)) & df[var].notna()
                count = out_of_bounds.sum()
                if count > 0:
                    df.loc[out_of_bounds, var] = np.clip(df.loc[out_of_bounds, var], lo, hi)
                    logger.info(f"  Clipped {count:,} out-of-bounds values in {var}")

        # Remove duplicate timestamps per location
        before_dedup = len(df)
        df = df.drop_duplicates(subset=["datetime", "location"], keep="first")
        dedup_removed = before_dedup - len(df)
        if dedup_removed > 0:
            logger.info(f"  Removed {dedup_removed:,} duplicate timestamp-location rows")

        # Sort by location then datetime for proper interpolation
        df = df.sort_values(["location", "datetime"]).reset_index(drop=True)

        # Interpolate missing values within each location (linear, max gap = 6 hours)
        numeric_cols = [c for c in WEATHER_VARIABLES if c in df.columns]
        for col in numeric_cols:
            df[col] = df.groupby("location")[col].transform(
                lambda s: s.interpolate(method="linear", limit=6)
            )

        # Ensure datetime is timezone-aware (America/New_York)
        # Handle DST transitions: spring-forward (nonexistent) and fall-back (ambiguous)
        if df["datetime"].dt.tz is None:
            df["datetime"] = pd.to_datetime(df["datetime"]).dt.tz_localize(
                "America/New_York", ambiguous="NaT", nonexistent="shift_forward"
            )
            # Drop rows where ambiguous DST times resulted in NaT
            nat_count = df["datetime"].isna().sum()
            if nat_count > 0:
                df = df.dropna(subset=["datetime"])
                logger.info(f"  Dropped {nat_count} ambiguous DST timestamp rows")

        elapsed = time.time() - t0
        logger.info(f"  Preprocessing complete: {len(df):,} rows in {elapsed:.1f}s")

        return df

    # ── 4. Feature Engineering (Hourly) ──────────────────────────────────

    def engineer_hourly_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add engineered features to hourly data. These are computed at the
        hourly level and then aggregated in daily/monthly rollups.
        """
        df = df.copy()

        # ── Temporal features ────────────────────────────────────────────
        df["hour"] = df["datetime"].dt.hour
        df["day_of_week"] = df["datetime"].dt.dayofweek
        df["day_of_year"] = df["datetime"].dt.dayofyear
        df["month"] = df["datetime"].dt.month
        df["quarter"] = df["datetime"].dt.quarter
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["season"] = pd.cut(
            df["month"], bins=[0, 3, 6, 9, 12],
            labels=["winter", "spring", "summer", "fall"]
        )

        # ── Temperature features ─────────────────────────────────────────
        if "T2M" in df.columns:
            df["hdd_hourly"] = np.maximum(BASE_TEMP_C - df["T2M"], 0.0)
            df["cdd_hourly"] = np.maximum(df["T2M"] - BASE_TEMP_C, 0.0)

            # Heat Index (simplified Steadman formula)
            if "RH2M" in df.columns:
                t_f = df["T2M"] * 9 / 5 + 32  # Convert to °F for heat index calc
                rh = df["RH2M"]
                # Heat index only meaningful above 80°F
                hi_f = (
                    -42.379 + 2.04901523 * t_f + 10.14333127 * rh
                    - 0.22475541 * t_f * rh - 0.00683783 * t_f ** 2
                    - 0.05481717 * rh ** 2 + 0.00122874 * t_f ** 2 * rh
                    + 0.00085282 * t_f * rh ** 2 - 0.00000199 * t_f ** 2 * rh ** 2
                )
                df["heat_index_c"] = np.where(t_f >= 80, (hi_f - 32) * 5 / 9, df["T2M"])

            # Wind Chill (only below 10°C and wind > 1.3 m/s)
            if "WS10M" in df.columns:
                ws_kmh = df["WS10M"] * 3.6  # m/s to km/h
                wc = (
                    13.12 + 0.6215 * df["T2M"]
                    - 11.37 * ws_kmh ** 0.16
                    + 0.3965 * df["T2M"] * ws_kmh ** 0.16
                )
                df["wind_chill_c"] = np.where(
                    (df["T2M"] <= 10) & (df["WS10M"] > 1.3), wc, df["T2M"]
                )

            # Apparent Temperature (composite perceived temperature)
            if "heat_index_c" in df.columns and "wind_chill_c" in df.columns:
                df["apparent_temp_c"] = np.where(
                    df["T2M"] >= 27, df["heat_index_c"],
                    np.where(df["T2M"] <= 10, df["wind_chill_c"], df["T2M"])
                )

        # ── Humidity categories ──────────────────────────────────────────
        if "RH2M" in df.columns:
            df["humidity_category"] = pd.cut(
                df["RH2M"], bins=[0, 40, 70, 100],
                labels=["Low", "Moderate", "High"]
            )

        # ── Solar features ───────────────────────────────────────────────
        if "ALLSKY_SFC_SW_DWN" in df.columns:
            df["solar_intensity_wm2"] = df["ALLSKY_SFC_SW_DWN"]

        if "ALLSKY_KT" in df.columns:
            df["cloudiness_indicator"] = 1.0 - df["ALLSKY_KT"].clip(0, 1)

        # ── Wind features ────────────────────────────────────────────────
        if "WS10M" in df.columns:
            df["wind_category"] = pd.cut(
                df["WS10M"], bins=[-1, 2, 6, 11, 100],
                labels=["Calm", "Breeze", "Strong", "High"]
            )

        if "WD10M" in df.columns:
            rad = np.deg2rad(df["WD10M"])
            df["wind_dir_sin"] = np.sin(rad)
            df["wind_dir_cos"] = np.cos(rad)

        # ── Precipitation flags ──────────────────────────────────────────
        if "PRECTOTCORR" in df.columns:
            df["rain_flag"] = (df["PRECTOTCORR"] > 0).astype(int)
            df["heavy_rain_flag"] = (df["PRECTOTCORR"] > 5.0).astype(int)

        # ── Interaction features ─────────────────────────────────────────
        if "T2M" in df.columns and "RH2M" in df.columns:
            df["temp_x_humidity"] = df["T2M"] * df["RH2M"]
        if "T2M" in df.columns and "ALLSKY_SFC_SW_DWN" in df.columns:
            df["temp_x_solar"] = df["T2M"] * df["ALLSKY_SFC_SW_DWN"]
        if "T2M" in df.columns and "PRECTOTCORR" in df.columns:
            df["temp_x_rain"] = df["T2M"] * df["PRECTOTCORR"]

        return df

    # ── 5. Daily Aggregation ─────────────────────────────────────────────

    def compute_daily_aggregates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate hourly data to daily county-level summaries."""
        df = df.copy()
        df["date"] = df["datetime"].dt.date

        agg_dict = {
            "lat": ("lat", "first"),
            "lon": ("lon", "first"),
        }

        # Temperature
        if "T2M" in df.columns:
            agg_dict["temp_avg_c"] = ("T2M", "mean")
            agg_dict["temp_max_c"] = ("T2M", "max")
            agg_dict["temp_min_c"] = ("T2M", "min")
            agg_dict["temp_std_c"] = ("T2M", "std")

        if "apparent_temp_c" in df.columns:
            agg_dict["apparent_temp_avg_c"] = ("apparent_temp_c", "mean")

        # Degree days
        if "hdd_hourly" in df.columns:
            agg_dict["hdd"] = ("hdd_hourly", lambda x: x.sum() / 24.0)
        if "cdd_hourly" in df.columns:
            agg_dict["cdd"] = ("cdd_hourly", lambda x: x.sum() / 24.0)

        # Humidity
        if "RH2M" in df.columns:
            agg_dict["humidity_avg_pct"] = ("RH2M", "mean")
            agg_dict["humidity_max_pct"] = ("RH2M", "max")

        # Solar
        if "ALLSKY_SFC_SW_DWN" in df.columns:
            # Daily solar energy: sum of hourly W/m² → Wh/m² → kWh/m²
            agg_dict["daily_solar_kwh_m2"] = ("ALLSKY_SFC_SW_DWN", lambda x: x.sum() / 1000.0)
            agg_dict["solar_max_wm2"] = ("ALLSKY_SFC_SW_DWN", "max")

        if "ALLSKY_KT" in df.columns:
            agg_dict["clearness_index_avg"] = ("ALLSKY_KT", "mean")

        # Wind
        if "WS10M" in df.columns:
            agg_dict["wind_speed_avg_ms"] = ("WS10M", "mean")
            agg_dict["wind_speed_max_ms"] = ("WS10M", "max")

        # Precipitation
        if "PRECTOTCORR" in df.columns:
            agg_dict["precip_total_mm"] = ("PRECTOTCORR", "sum")
            agg_dict["rain_hours"] = ("rain_flag", "sum")
            agg_dict["heavy_rain_hours"] = ("heavy_rain_flag", "sum")

        # Pressure
        if "PS" in df.columns:
            agg_dict["pressure_avg_kpa"] = ("PS", "mean")

        daily = df.groupby(["location", "date"]).agg(**agg_dict).reset_index()

        # Convert to Fahrenheit for compatibility with existing pipeline
        if "temp_avg_c" in daily.columns:
            daily["temp_avg_f"] = daily["temp_avg_c"] * 9 / 5 + 32
            daily["temp_max_f"] = daily["temp_max_c"] * 9 / 5 + 32
            daily["temp_min_f"] = daily["temp_min_c"] * 9 / 5 + 32

        # ── Advanced daily features ──────────────────────────────────────
        # Heatwave flag: temp_max > 32°C (90°F)
        if "temp_max_c" in daily.columns:
            daily["is_extreme_heat"] = (daily["temp_max_c"] > 32).astype(int)
            daily["is_extreme_cold"] = (daily["temp_min_c"] < -5).astype(int)

        # Solar potential index (0-100)
        if "daily_solar_kwh_m2" in daily.columns and "clearness_index_avg" in daily.columns:
            max_solar = daily["daily_solar_kwh_m2"].quantile(0.99) if len(daily) > 10 else 8.0
            daily["solar_potential_index"] = np.clip(
                (daily["daily_solar_kwh_m2"] / max(max_solar, 0.1)) * 50
                + daily["clearness_index_avg"] * 50,
                0, 100
            ).round(1)

        # Weather severity score (0-100)
        severity = pd.Series(0.0, index=daily.index)
        if "temp_max_c" in daily.columns:
            severity += np.clip(np.abs(daily["temp_avg_c"] - 20) * 2, 0, 30)
        if "precip_total_mm" in daily.columns:
            severity += np.clip(daily["precip_total_mm"] * 2, 0, 25)
        if "wind_speed_max_ms" in daily.columns:
            severity += np.clip(daily["wind_speed_max_ms"] * 1.5, 0, 20)
        if "humidity_avg_pct" in daily.columns:
            severity += np.clip(np.abs(daily["humidity_avg_pct"] - 50) * 0.4, 0, 15)
        if "clearness_index_avg" in daily.columns:
            severity += np.clip((1 - daily["clearness_index_avg"]) * 10, 0, 10)
        daily["weather_severity_score"] = np.clip(severity, 0, 100).round(1)

        # Consecutive hot/cold/rain day counts (per location)
        for loc in daily["location"].unique():
            loc_mask = daily["location"] == loc
            loc_idx = daily.loc[loc_mask].index

            if "is_extreme_heat" in daily.columns:
                daily.loc[loc_idx, "consec_hot_days"] = (
                    daily.loc[loc_idx, "is_extreme_heat"]
                    .groupby((daily.loc[loc_idx, "is_extreme_heat"] != 1).cumsum())
                    .cumsum()
                )

            if "precip_total_mm" in daily.columns:
                rain_day = (daily.loc[loc_idx, "precip_total_mm"] > 1).astype(int)
                daily.loc[loc_idx, "consec_rain_days"] = (
                    rain_day.groupby((rain_day != 1).cumsum()).cumsum()
                )

        daily["date"] = pd.to_datetime(daily["date"])
        return daily

    # ── 6. Monthly Aggregation ───────────────────────────────────────────

    def compute_monthly_aggregates(self, daily: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily data to monthly county-level summaries."""
        daily = daily.copy()
        daily["year"] = daily["date"].dt.year
        daily["month"] = daily["date"].dt.month

        agg_dict = {
            "lat": ("lat", "first"),
            "lon": ("lon", "first"),
        }

        # Temperature
        if "temp_avg_c" in daily.columns:
            agg_dict["temp_avg_c"] = ("temp_avg_c", "mean")
            agg_dict["temp_max_c"] = ("temp_max_c", "max")
            agg_dict["temp_min_c"] = ("temp_min_c", "min")
            agg_dict["temp_avg_f"] = ("temp_avg_f", "mean")
            agg_dict["temp_max_f"] = ("temp_max_f", "max")
            agg_dict["temp_min_f"] = ("temp_min_f", "min")

        # Degree days
        if "hdd" in daily.columns:
            agg_dict["monthly_hdd"] = ("hdd", "sum")
        if "cdd" in daily.columns:
            agg_dict["monthly_cdd"] = ("cdd", "sum")

        # Humidity
        if "humidity_avg_pct" in daily.columns:
            agg_dict["humidity_avg_pct"] = ("humidity_avg_pct", "mean")

        # Solar
        if "daily_solar_kwh_m2" in daily.columns:
            agg_dict["monthly_solar_kwh_m2"] = ("daily_solar_kwh_m2", "sum")
            agg_dict["avg_daily_solar_kwh_m2"] = ("daily_solar_kwh_m2", "mean")
        if "solar_potential_index" in daily.columns:
            agg_dict["solar_potential_index"] = ("solar_potential_index", "mean")

        # Wind
        if "wind_speed_avg_ms" in daily.columns:
            agg_dict["wind_speed_avg_ms"] = ("wind_speed_avg_ms", "mean")

        # Precipitation
        if "precip_total_mm" in daily.columns:
            agg_dict["monthly_precip_mm"] = ("precip_total_mm", "sum")
            agg_dict["rain_days"] = ("rain_hours", lambda x: (x > 0).sum())

        # Extreme weather counts
        if "is_extreme_heat" in daily.columns:
            agg_dict["extreme_heat_days"] = ("is_extreme_heat", "sum")
        if "is_extreme_cold" in daily.columns:
            agg_dict["extreme_cold_days"] = ("is_extreme_cold", "sum")

        # Severity
        if "weather_severity_score" in daily.columns:
            agg_dict["avg_weather_severity"] = ("weather_severity_score", "mean")

        # Consecutive extremes (max streak per month)
        if "consec_hot_days" in daily.columns:
            agg_dict["max_consec_hot_days"] = ("consec_hot_days", "max")
        if "consec_rain_days" in daily.columns:
            agg_dict["max_consec_rain_days"] = ("consec_rain_days", "max")

        monthly = daily.groupby(["location", "year", "month"]).agg(**agg_dict).reset_index()

        return monthly

    # ── 7. Parquet & DB Persistence ──────────────────────────────────────

    def save_to_parquet(self, df: pd.DataFrame) -> Path:
        """Save hourly data to compressed Parquet file."""
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # Strip timezone info for Parquet compatibility
        df_out = df.copy()
        if hasattr(df_out["datetime"].dt, "tz") and df_out["datetime"].dt.tz is not None:
            df_out["datetime"] = df_out["datetime"].dt.tz_localize(None)

        df_out.to_parquet(self.parquet_path, index=False, compression="snappy")
        size_mb = self.parquet_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved hourly Parquet: {self.parquet_path} ({size_mb:.1f} MB)")
        return self.parquet_path

    def save_aggregates_to_db(
        self, daily: pd.DataFrame, monthly: pd.DataFrame
    ) -> Dict[str, int]:
        """Persist daily and monthly aggregates to SQLite tables."""
        try:
            from database.connection import get_sync_engine
            engine = get_sync_engine()

            # Ensure tables exist
            from database.models import Base
            Base.metadata.create_all(engine, checkfirst=True)

            # Daily aggregates — upsert
            daily_out = daily.copy()
            if hasattr(daily_out["date"].dt, "tz") and daily_out["date"].dt.tz is not None:
                daily_out["date"] = daily_out["date"].dt.tz_localize(None)
            daily_out["date"] = daily_out["date"].dt.date

            daily_count = daily_out.to_sql(
                "weather_nrel_daily", engine, if_exists="replace", index=False
            )

            # Monthly aggregates — upsert
            monthly_count = monthly.to_sql(
                "weather_nrel_monthly", engine, if_exists="replace", index=False
            )

            logger.info(
                f"Saved to DB: {len(daily_out):,} daily rows, {len(monthly):,} monthly rows"
            )
            return {"daily": len(daily_out), "monthly": len(monthly)}

        except Exception as e:
            logger.error(f"Failed to save aggregates to database: {e}")
            return {"daily": 0, "monthly": 0, "error": str(e)}

    # ── 8. Save Ingestion Report ─────────────────────────────────────────

    def save_report(self, report: Dict[str, Any]) -> Path:
        """Save ingestion report to JSON."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.reports_dir / "nrel_dataset_summary.json"

        # Convert non-serializable types
        def _serialize(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            return str(obj)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=_serialize)

        logger.info(f"Saved ingestion report: {report_path}")
        return report_path

    # ── 9. Public API: Load cached data ──────────────────────────────────

    def load_hourly(self) -> pd.DataFrame:
        """Load hourly data from Parquet cache (lazy loading)."""
        if self._cache is not None:
            return self._cache

        if self.parquet_path.exists():
            self._cache = pd.read_parquet(self.parquet_path)
            logger.info(f"Loaded {len(self._cache):,} hourly records from Parquet cache")
            return self._cache

        logger.warning("No Parquet cache found. Run processor.run() first.")
        return pd.DataFrame()

    def load_daily(self, location: Optional[str] = None) -> pd.DataFrame:
        """Load daily aggregates from DB (lazy loading)."""
        if self._daily_cache is not None:
            df = self._daily_cache
        else:
            try:
                from database.connection import get_sync_engine
                engine = get_sync_engine()
                df = pd.read_sql("SELECT * FROM weather_nrel_daily", engine)
                df["date"] = pd.to_datetime(df["date"])
                self._daily_cache = df
                logger.info(f"Loaded {len(df):,} daily NREL records from database")
            except Exception as e:
                logger.warning(f"Failed to load NREL daily from DB: {e}")
                return pd.DataFrame()

        if location and not df.empty:
            df = df[df["location"] == location]

        return df

    def load_monthly(self, location: Optional[str] = None) -> pd.DataFrame:
        """Load monthly aggregates from DB (lazy loading)."""
        if self._monthly_cache is not None:
            df = self._monthly_cache
        else:
            try:
                from database.connection import get_sync_engine
                engine = get_sync_engine()
                df = pd.read_sql("SELECT * FROM weather_nrel_monthly", engine)
                self._monthly_cache = df
                logger.info(f"Loaded {len(df):,} monthly NREL records from database")
            except Exception as e:
                logger.warning(f"Failed to load NREL monthly from DB: {e}")
                return pd.DataFrame()

        if location and not df.empty:
            df = df[df["location"] == location]

        return df

    # ── 10. Master Pipeline Runner ───────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """
        Execute the full NREL ingestion pipeline:
          1. Discover & validate dataset
          2. Preprocess (clean, deduplicate, interpolate)
          3. Engineer hourly features
          4. Compute daily & monthly aggregates
          5. Save Parquet + DB
          6. Generate ingestion report
        """
        logger.info("═" * 70)
        logger.info("NREL NASA POWER — Full Ingestion Pipeline")
        logger.info("═" * 70)

        t0 = time.time()

        # Step 1: Discovery
        report = self.discover()
        if "error" in report:
            return report

        # Step 2: Preprocess
        df = self.preprocess()

        # Step 3: Feature engineering
        df = self.engineer_hourly_features(df)

        # Step 4: Parquet (hourly)
        self.save_to_parquet(df)

        # Step 5: Daily aggregates
        daily = self.compute_daily_aggregates(df)
        self._daily_cache = daily

        # Step 6: Monthly aggregates
        monthly = self.compute_monthly_aggregates(daily)
        self._monthly_cache = monthly

        # Step 7: DB persistence (daily + monthly only)
        db_result = self.save_aggregates_to_db(daily, monthly)

        # Step 8: Report
        report["processing"] = {
            "total_time_seconds": round(time.time() - t0, 2),
            "parquet_path": str(self.parquet_path),
            "parquet_size_mb": round(self.parquet_path.stat().st_size / (1024 * 1024), 2),
            "daily_rows": len(daily),
            "monthly_rows": len(monthly),
            "db_result": db_result,
            "hourly_features": [c for c in df.columns if c not in report.get("columns", [])],
        }
        self.save_report(report)

        logger.info("═" * 70)
        logger.info(f"NREL pipeline complete in {report['processing']['total_time_seconds']}s")
        logger.info(f"  Parquet: {report['processing']['parquet_size_mb']} MB")
        logger.info(f"  Daily DB rows: {len(daily):,}")
        logger.info(f"  Monthly DB rows: {len(monthly):,}")
        logger.info("═" * 70)

        return report


# ── Module-level singleton for lazy access ────────────────────────────────

_processor: Optional[NRELProcessor] = None


def get_nrel_processor() -> NRELProcessor:
    """Get or create the singleton NRELProcessor instance."""
    global _processor
    if _processor is None:
        _processor = NRELProcessor()
    return _processor


# ── Standalone execution ──────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    processor = NRELProcessor()
    result = processor.run()
    print(json.dumps(result.get("processing", {}), indent=2))
