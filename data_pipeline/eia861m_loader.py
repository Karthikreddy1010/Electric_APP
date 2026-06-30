"""
EIA-861M Monthly Data Loader — CSV ingestion + EIA API incremental sync.

CSV Source: data/raw/EIA_861M_sales_revenue.xlsx (Monthly-States sheet)
API Source: EIA API v2 electricity/retail-sales

The CSV has a 3-row multi-header:
  Row 0: Sector group labels (RESIDENTIAL, COMMERCIAL, etc.)
  Row 1: Metric labels (Revenue, Sales, Customers, Price)
  Row 2: Unit labels (Thousand Dollars, Megawatthours, Count, Cents/kWh)
  Row 3+: Actual data

Each data row has 24 columns:
  [0] Year, [1] Month, [2] State, [3] Data Status
  [4-7] RESIDENTIAL: Revenue, Sales, Customers, Price
  [8-11] COMMERCIAL: Revenue, Sales, Customers, Price
  [12-15] INDUSTRIAL: Revenue, Sales, Customers, Price
  [16-19] TRANSPORTATION: Revenue, Sales, Customers, Price
  [20-23] TOTAL: Revenue, Sales, Customers, Price
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Sector column offsets (each sector has 4 columns: Revenue, Sales, Customers, Price)
SECTOR_MAP = {
    "residential":    (4, 5, 6, 7),
    "commercial":     (8, 9, 10, 11),
    "industrial":     (12, 13, 14, 15),
    "transportation": (16, 17, 18, 19),
    "total":          (20, 21, 22, 23),
}


def load_eia861m_from_csv(
    path: Optional[Path] = None,
    sheet_name: str = "Monthly-States",
) -> pd.DataFrame:
    """
    Load EIA-861M monthly state-level data from the Excel file.

    Returns a long-format DataFrame with columns:
        year, month, state, sector, period, data_status,
        revenue_k_dollars, sales_mwh, customers, price_cents_kwh
    """
    path = path or RAW_DIR / "EIA_861M_sales_revenue.xlsx"
    if not path.exists():
        logger.warning(f"EIA-861M file not found: {path}")
        return pd.DataFrame()

    logger.info(f"Loading EIA-861M from {path.name} (sheet: {sheet_name})")

    # Read without header — we'll parse the multi-row header manually
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)

    # Skip 3 header rows; data starts at row index 3
    data = raw.iloc[3:].copy()
    data = data.reset_index(drop=True)

    records = []
    for _, row in data.iterrows():
        year_val = row.iloc[0]
        month_val = row.iloc[1]
        state_val = row.iloc[2]
        status_val = row.iloc[3]

        # Skip rows with missing year/month/state
        if pd.isna(year_val) or pd.isna(month_val) or pd.isna(state_val):
            continue

        try:
            year = int(year_val)
            month = int(month_val)
        except (ValueError, TypeError):
            continue

        state = str(state_val).strip().upper()
        if len(state) != 2:
            continue

        data_status = str(status_val).strip() if pd.notna(status_val) else None
        period = f"{year}-{month:02d}"

        for sector, (rev_idx, sales_idx, cust_idx, price_idx) in SECTOR_MAP.items():
            rev = _safe_float(row.iloc[rev_idx])
            sales = _safe_float(row.iloc[sales_idx])
            cust = _safe_int(row.iloc[cust_idx])
            price = _safe_float(row.iloc[price_idx])

            records.append({
                "year": year,
                "month": month,
                "state": state,
                "sector": sector,
                "period": period,
                "data_status": data_status,
                "revenue_k_dollars": rev,
                "sales_mwh": sales,
                "customers": cust,
                "price_cents_kwh": price,
            })

    df = pd.DataFrame(records)
    if df.empty:
        logger.warning("No records parsed from EIA-861M CSV")
        return df

    # Drop rows where all numeric values are null
    numeric_cols = ["revenue_k_dollars", "sales_mwh", "customers", "price_cents_kwh"]
    df = df.dropna(subset=numeric_cols, how="all")
    df = df.drop_duplicates(subset=["year", "month", "state", "sector"])
    df = df.sort_values(["year", "month", "state", "sector"]).reset_index(drop=True)

    logger.info(
        f"Loaded EIA-861M: {len(df)} records, "
        f"{df['state'].nunique()} states, "
        f"{df['year'].min()}-{df['year'].max()}"
    )
    return df


def sync_eia861m_from_api(
    latest_period: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch incremental EIA-861M data from EIA API v2 (electricity/retail-sales).

    Only fetches records after `latest_period` (YYYY-MM format).
    Returns a DataFrame in the same format as load_eia861m_from_csv().
    """
    if api_key is None:
        from data_pipeline.config import get_eia_api_key
        api_key = get_eia_api_key()

    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA-861M API sync.")
        return pd.DataFrame()

    base_url = "https://api.eia.gov/v2/electricity/retail-sales/data"

    sector_map_api = {
        "RES": "residential",
        "COM": "commercial",
        "IND": "industrial",
        "TRA": "transportation",
        "ALL": "total",
    }

    all_records = []

    for api_sector, db_sector in sector_map_api.items():
        params = {
            "api_key": api_key,
            "frequency": "monthly",
            "data[0]": "price",
            "data[1]": "revenue",
            "data[2]": "sales",
            "data[3]": "customers",
            "facets[sectorid][]": api_sector,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }

        if latest_period:
            params["start"] = latest_period

        try:
            logger.info(f"EIA API: fetching {api_sector} data after {latest_period or 'beginning'}")
            resp = requests.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("response", {}).get("data", [])

            for record in data:
                period = record.get("period", "")
                if not period or len(period) < 7:
                    continue

                parts = period.split("-")
                year = int(parts[0])
                month = int(parts[1])
                state = record.get("stateid", "").strip().upper()

                if len(state) != 2:
                    continue

                all_records.append({
                    "year": year,
                    "month": month,
                    "state": state,
                    "sector": db_sector,
                    "period": period,
                    "data_status": "API",
                    "revenue_k_dollars": _safe_float(record.get("revenue")),
                    "sales_mwh": _safe_float(record.get("sales")),
                    "customers": _safe_int(record.get("customers")),
                    "price_cents_kwh": _safe_float(record.get("price")),
                })

            logger.info(f"EIA API: fetched {len(data)} {api_sector} records")

        except Exception as e:
            logger.error(f"EIA API error for sector {api_sector}: {e}")
            continue

    df = pd.DataFrame(all_records)
    if not df.empty:
        df = df.drop_duplicates(subset=["year", "month", "state", "sector"])
        df = df.sort_values(["year", "month", "state", "sector"]).reset_index(drop=True)
        logger.info(f"EIA API sync: {len(df)} total new records")

    return df


def _safe_float(val) -> Optional[float]:
    """Convert to float, returning None on failure."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    """Convert to int, returning None on failure."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
