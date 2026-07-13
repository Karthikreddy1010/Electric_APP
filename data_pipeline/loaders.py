"""
Dataset Loaders — read all local CSV/XLSX files from data/raw/.

Each loader returns a pandas DataFrame with standardised column names.
The `load_all_local()` function orchestrates everything and returns a
named dictionary of DataFrames.
"""
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from data_pipeline.config import RAW_DIR, DATASET_REGISTRY, EIA861_DIR, EIA861_TABLES

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _snake_case(name: str) -> str:
    """Convert a column name to snake_case."""
    s = re.sub(r"[^\w\s]", "", str(name))
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower().strip("_")


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename all columns to snake_case."""
    df = df.copy()
    df.columns = [_snake_case(c) for c in df.columns]
    return df


def _log_loaded(name: str, df: pd.DataFrame) -> None:
    logger.info(
        f"Loaded {name}: {df.shape[0]:,} rows × {df.shape[1]} cols "
        f"| columns: {list(df.columns[:8])}{'...' if df.shape[1] > 8 else ''}"
    )


# ── Individual Loaders ───────────────────────────────────────────────────────

def load_bgs_auction() -> pd.DataFrame:
    """Load BGS Auction historical rates (xlsx, possibly multi-sheet)."""
    path = RAW_DIR / DATASET_REGISTRY["bgs_auction"]
    if not path.exists():
        logger.warning(f"BGS Auction file not found: {path}")
        return pd.DataFrame()

    xls = pd.ExcelFile(path)
    frames = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df = _standardise_columns(df)
        df["sheet"] = sheet
        frames.append(df)

    result = pd.concat(frames, ignore_index=True)
    _log_loaded("bgs_auction", result)
    return result


def load_community_energy() -> pd.DataFrame:
    """Load Aggregated Community-Scale Utility Energy Data (xlsx)."""
    path = RAW_DIR / DATASET_REGISTRY["community_energy"]
    if not path.exists():
        logger.warning(f"Community energy file not found: {path}")
        return pd.DataFrame()

    xls = pd.ExcelFile(path)
    frames = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df = _standardise_columns(df)
        df["sheet"] = sheet
        frames.append(df)

    result = pd.concat(frames, ignore_index=True)
    _log_loaded("community_energy", result)
    return result


def load_municipal_energy() -> pd.DataFrame:
    """Load Historic Municipal Energy Use in NJ (CSV)."""
    path = RAW_DIR / DATASET_REGISTRY["municipal_energy"]
    if not path.exists():
        logger.warning(f"Municipal energy file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path, low_memory=False)
    df = _standardise_columns(df)
    _log_loaded("municipal_energy", df)
    return df


def load_nj_retail_prices() -> pd.DataFrame:
    """
    Load NJ Residential Average Retail Price of Electricity (monthly).
    Parses the Mon-YY date format (e.g. 'Mar-26').
    """
    path = RAW_DIR / DATASET_REGISTRY["nj_retail_prices"]
    if not path.exists():
        logger.warning(f"NJ retail prices file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)

    # Rename to predictable names
    cols = list(df.columns)
    if len(cols) >= 2:
        df = df.rename(columns={
            cols[0]: "month_str",
            cols[1]: "price_cents_kwh",
        })

    # Parse Mon-YY format → datetime
    df["date"] = pd.to_datetime(df["month_str"], format="%b-%y", errors="coerce")
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["price_cents_kwh"] = pd.to_numeric(df["price_cents_kwh"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    _log_loaded("nj_retail_prices", df)
    return df


def load_avg_electricity_prices() -> pd.DataFrame:
    """Load Avg_price_Electricity.xlsx (Table 5.3 national prices)."""
    path = RAW_DIR / DATASET_REGISTRY["avg_price_electricity"]
    if not path.exists():
        logger.warning(f"Avg electricity prices file not found: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, header=None)
    _log_loaded("avg_price_electricity (raw)", df)
    return df


def load_sales_of_electricity() -> pd.DataFrame:
    """Load salesofelectricity.xlsx (Table 5.4.A state-level sales)."""
    path = RAW_DIR / DATASET_REGISTRY["sales_of_electricity"]
    if not path.exists():
        logger.warning(f"Sales of electricity file not found: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, header=None)
    _log_loaded("sales_of_electricity (raw)", df)
    return df


def load_eia_residential_prices() -> pd.DataFrame:
    """Load EIA Residential Average Electricity Prices (CSV, all states)."""
    path = RAW_DIR / DATASET_REGISTRY["eia_residential_prices"]
    if not path.exists():
        logger.warning(f"EIA residential prices file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)

    # Ensure date parsing
    date_col = [c for c in df.columns if "date" in c]
    if date_col:
        df[date_col[0]] = pd.to_datetime(df[date_col[0]], errors="coerce")
        if date_col[0] != "date":
            df = df.rename(columns={date_col[0]: "date"})
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

    _log_loaded("eia_residential_prices", df)
    return df


def load_weather() -> pd.DataFrame:
    """Load daily weather data (CSV)."""
    path = RAW_DIR / DATASET_REGISTRY["weather"]
    if not path.exists():
        logger.warning(f"Weather file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    _log_loaded("weather", df)
    return df


def load_air_temp() -> pd.DataFrame:
    """Load NOAA daily air temperature observations (CSV)."""
    path = RAW_DIR / DATASET_REGISTRY["air_temp"]
    if not path.exists():
        logger.warning(f"Air temp file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    _log_loaded("air_temp", df)
    return df


def load_cpi_cached() -> Optional[pd.DataFrame]:
    """Load existing CPI monthly data if cached locally."""
    path = RAW_DIR / DATASET_REGISTRY["cpi_monthly"]
    if not path.exists():
        logger.info("No cached CPI data found.")
        return None

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    _log_loaded("cpi_monthly (cached)", df)
    return df


def load_cpi_yearly_cached() -> Optional[pd.DataFrame]:
    """Load existing CPI yearly data if cached locally."""
    path = RAW_DIR / DATASET_REGISTRY["cpi_yearly"]
    if not path.exists():
        return None

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    _log_loaded("cpi_yearly (cached)", df)
    return df


def load_eia861_dataset(filename: str) -> pd.DataFrame:
    """Load a specific EIA-861 master CSV from data/raw/eia861_master_data/."""
    path = EIA861_DIR / filename
    if not path.exists():
        logger.warning(f"EIA-861 table not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path, low_memory=False)
    df = _standardise_columns(df)
    _log_loaded(f"eia861/{filename}", df)
    return df


def load_pseg_rate_history() -> pd.DataFrame:
    """Load PSEG rate history (CSV)."""
    path = RAW_DIR / DATASET_REGISTRY["pseg_rate_history"]
    if not path.exists():
        logger.warning(f"PSEG rate history file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    _log_loaded("pseg_rate_history", df)
    return df


def load_pseg_distribution_rates() -> pd.DataFrame:
    """Load PSEG Component Distribution Rates (CSV)."""
    path = RAW_DIR / DATASET_REGISTRY.get("pseg_distribution_rates", "PSEG_Component_Distribution_Rates.csv")
    if not path.exists():
        logger.warning(f"PSEG distribution rates file not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = _standardise_columns(df)
    _log_loaded("pseg_distribution_rates", df)
    return df


# ── Master Loader ────────────────────────────────────────────────────────────

def load_all_local() -> dict[str, pd.DataFrame]:
    """
    Load all local datasets. Returns a dict mapping logical names
    to DataFrames.
    """
    logger.info("=" * 70)
    logger.info("STAGE 1: Loading all local datasets from data/raw/")
    logger.info("=" * 70)

    datasets: dict[str, pd.DataFrame] = {}

    # Core datasets
    datasets["bgs_auction"] = load_bgs_auction()
    datasets["community_energy"] = load_community_energy()
    datasets["municipal_energy"] = load_municipal_energy()
    datasets["nj_retail_prices"] = load_nj_retail_prices()
    datasets["avg_price_electricity"] = load_avg_electricity_prices()
    datasets["sales_of_electricity"] = load_sales_of_electricity()
    datasets["eia_residential_prices"] = load_eia_residential_prices()
    datasets["weather"] = load_weather()
    datasets["air_temp"] = load_air_temp()
    datasets["cpi_monthly"] = load_cpi_cached()
    datasets["cpi_yearly"] = load_cpi_yearly_cached()
    datasets["pseg_rate_history"] = load_pseg_rate_history()
    datasets["pseg_distribution_rates"] = load_pseg_distribution_rates()

    # EIA-861 tables (selected subset)
    for table_file in EIA861_TABLES:
        key = f"eia861_{Path(table_file).stem}"
        datasets[key] = load_eia861_dataset(table_file)

    # Remove None entries (missing cached files)
    datasets = {k: v for k, v in datasets.items() if v is not None}

    loaded_count = sum(1 for v in datasets.values() if not v.empty)
    total_rows = sum(len(v) for v in datasets.values())
    logger.info(
        f"Loading complete: {loaded_count} datasets loaded, "
        f"{total_rows:,} total rows"
    )
    return datasets
