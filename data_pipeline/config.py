"""
Pipeline Configuration — centralized paths, API keys, dataset registry.

All API keys are read from environment variables (never hardcoded).
Set them in a .env file at the project root or export them in your shell.
"""
import logging
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Project Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EIA861_DIR = RAW_DIR / "eia861_master_data"

# Ensure output dirs exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── API Keys (from environment) ─────────────────────────────────────────────

def get_api_key(name: str) -> Optional[str]:
    """Retrieve an API key from environment variables."""
    value = os.environ.get(name)
    if not value:
        logging.getLogger(__name__).warning(
            f"Environment variable {name} not set. "
            f"API calls requiring this key will fail."
        )
    return value


def get_eia_api_key() -> Optional[str]:
    return get_api_key("EIA_API_KEY")


def get_bls_api_key() -> Optional[str]:
    return get_api_key("BLS_API_KEY")


def get_noaa_token() -> Optional[str]:
    return get_api_key("NOAA_TOKEN")


def get_census_api_key() -> Optional[str]:
    return get_api_key("CENSUS_API_KEY")


def get_pjm_api_key() -> Optional[str]:
    return get_api_key("PJM_API_KEY")


# ── CPI Configuration ───────────────────────────────────────────────────────
CPI_BASE_YEAR = 2024
CPI_SERIES_ID = "CUSR0000SA0"  # CPI-U All Items, Seasonally Adjusted
CPI_START_YEAR = 2015
CPI_END_YEAR = 2025

# ── Dataset Registry ────────────────────────────────────────────────────────
# Maps logical dataset name → filename in data/raw/
DATASET_REGISTRY = {
    "bgs_auction": "BGS Auction historical rates.xlsx",
    "community_energy": "Aggregated_Community-Scale_Utility_Energy_Data.xlsx",
    "municipal_energy": (
        "Historic_Municipal_Energy_Use_in_New_Jersey__Table__"
        "-772512291409682993.csv"
    ),
    "nj_retail_prices": (
        "nj-rs-Average_retail_price_of_electricity_monthly.csv"
    ),
    "avg_price_electricity": "Avg_price_Electricity.xlsx",
    "sales_of_electricity": "salesofelectricity.xlsx",
    "eia_residential_prices": "eia_residential_Avg_electricity_prices.csv",
    "weather": "weather.csv",
    "air_temp": "air_temp.csv",
    "cpi_monthly": "cpi_monthly.csv",
    "cpi_yearly": "cpi_yearly.csv",
    "pjm_market": "pjm_market.csv",
    "billing": "billing.csv",
    "pseg_rate_history": "pseg_rate_history.csv",
    "eia_pjm_daily_demand": "eia_pjm_daily_demand.csv",
    "state_benchmark": "state_benchmark.csv",
    "retail_plans": "retail_plans.csv",
    "eia861m_monthly": "EIA_861M_sales_revenue.xlsx",
    "openei_iou_mapping": "OpenEI_IOU_Utility_ZIP_Mapping_2024.csv",
    "openei_noniou_mapping": "OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv",
}

# EIA-930 Default Balancing Authorities (PJM is primary)
EIA930_BA_CODES = ["PJM"]
EIA930_SUB_BA_PARENT = "PJM"


# EIA-861 tables to process (subset of the full 23-file directory)
EIA861_TABLES = [
    "Sales_Ult_Cust_master.csv",
    "Operational_Data_master.csv",
    "Utility_Data_master.csv",
]

# ── Processed Output Names ───────────────────────────────────────────────────
OUTPUT_FILES = {
    "bgs_auction": "bgs_auction.csv",
    "community_energy": "community_energy.csv",
    "municipal_energy": "municipal_energy.csv",
    "nj_retail_prices": "nj_retail_prices.csv",
    "eia_residential_prices": "eia_residential_prices.csv",
    "weather_monthly": "weather_monthly.csv",
    "cpi": "cpi.csv",
    "cpi_yearly": "cpi_yearly.csv",
    "master": "final_master_dataset.csv",
}


# ── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    """Configure pipeline-wide logging to console and file."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    log_file = PROJECT_ROOT / "data" / "pipeline.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicates on re-run
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(log_format))
    root.addHandler(console)

    # File handler
    fh = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(log_format))
    root.addHandler(fh)

    logging.getLogger(__name__).info(
        f"Logging initialized. Log file: {log_file}"
    )
