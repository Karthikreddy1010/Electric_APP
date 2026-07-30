"""
EIA Retail Loader
Ingests the 4 raw parquet datasets, merges them on (period, stateid, sectorid),
normalizes base columns, extracts temporal fields, and saves immutable eia_retail_raw_v1.parquet.
"""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_and_merge_eia_raw(raw_dir: Path | str | None = None) -> pd.DataFrame:
    """
    Ingests and merges the 4 EIA Retail parquets:
    - eia_retail_price.parquet
    - eia_retail_sales.parquet
    - eia_retail_revenue.parquet
    - eia_retail_customers.parquet
    
    Returns normalized, immutable raw DataFrame and saves to data/processed/eia_retail_raw_v1.parquet.
    """
    if raw_dir is None:
        raw_dir = PROJECT_ROOT / "data" / "raw" / "eia_retail"
    else:
        raw_dir = Path(raw_dir)

    price_path = raw_dir / "eia_retail_price.parquet"
    sales_path = raw_dir / "eia_retail_sales.parquet"
    revenue_path = raw_dir / "eia_retail_revenue.parquet"
    customers_path = raw_dir / "eia_retail_customers.parquet"

    if not price_path.exists():
        raise FileNotFoundError(f"Missing required dataset file: {price_path}")

    logger.info("Loading raw EIA Retail parquet files...")
    df_price = pd.read_parquet(price_path)
    df_sales = pd.read_parquet(sales_path)
    df_revenue = pd.read_parquet(revenue_path)
    df_cust = pd.read_parquet(customers_path)

    # Rename metric columns to standard schema
    df_price = df_price.rename(columns={"price": "retail_price", "price-units": "price_units"})
    df_sales = df_sales.rename(columns={"sales": "retail_sales", "sales-units": "sales_units"})
    df_revenue = df_revenue.rename(columns={"revenue": "retail_revenue", "revenue-units": "revenue_units"})
    df_cust = df_cust.rename(columns={"customers": "retail_customers", "customers-units": "customers_units"})

    # Merge on Primary Keys: period, stateid, sectorid
    pk = ["period", "stateid", "sectorid"]
    
    # Merge price + sales
    merged = pd.merge(
        df_price[pk + ["stateDescription", "sectorName", "retail_price"]],
        df_sales[pk + ["retail_sales"]],
        on=pk,
        how="outer"
    )

    # Merge revenue
    merged = pd.merge(
        merged,
        df_revenue[pk + ["retail_revenue"]],
        on=pk,
        how="outer"
    )

    # Merge customers
    merged = pd.merge(
        merged,
        df_cust[pk + ["retail_customers"]],
        on=pk,
        how="outer"
    )

    # Ensure temporal features: year, month, quarter, date
    dt = pd.to_datetime(merged["period"], format="%Y-%m", errors="coerce")
    merged["year"] = dt.dt.year
    merged["month"] = dt.dt.month
    merged["quarter"] = dt.dt.quarter
    merged["date"] = dt.dt.strftime("%Y-%m-%01")

    # Clean numeric types
    num_cols = ["retail_price", "retail_sales", "retail_revenue", "retail_customers"]
    for c in num_cols:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0.0)

    # Sort deterministically
    merged = merged.sort_values(["stateid", "sectorid", "period"]).reset_index(drop=True)

    # Save immutable raw merged dataset
    processed_dir = PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    raw_out = processed_dir / "eia_retail_raw_v1.parquet"
    merged.to_parquet(raw_out, index=False)
    logger.info(f"Saved merged raw dataset: {raw_out} ({len(merged)} rows)")

    return merged
