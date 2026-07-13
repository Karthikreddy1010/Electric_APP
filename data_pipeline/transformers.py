"""
Transformers — preprocess, standardize, and aggregate datasets.

Takes raw DataFrames loaded by loaders.py and applies cleaning rules:
- Standardize column names
- Convert dates to datetime
- Handle missing values
- Remove duplicates
- Aggregate monthly data to yearly if needed
"""
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ── Generic Aggregation ──────────────────────────────────────────────────────

def aggregate_to_yearly(
    df: pd.DataFrame,
    value_col: str,
    agg_func: str = "mean",
    year_col: str = "year"
) -> pd.DataFrame:
    """
    Generic helper to convert monthly (or daily) to yearly data.
    """
    if year_col not in df.columns:
        if "date" in df.columns:
            df[year_col] = df["date"].dt.year
        else:
            raise ValueError(f"No {year_col} or date column found to aggregate.")

    agg_dict = {value_col: agg_func}
    yearly = df.groupby(year_col).agg(agg_dict).reset_index()
    return yearly


# ── Dataset Specific Transformers ────────────────────────────────────────────

def preprocess_bgs_auction(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess BGS Auction historical rates."""
    if df.empty:
        return df

    # Example: BGS file has 'sheet' (e.g. 2024, 2023) and columns
    # We want a unified view: year, rate, etc.
    # The actual columns depend on raw format. We'll ensure year is present
    df = df.copy()

    # Extract year from sheet name only if 'year' is not in columns or all are null
    if "year" not in df.columns or df["year"].isna().all():
        if "sheet" in df.columns:
            df["year"] = df["sheet"].astype(str).str.extract(r'(\d{4})')[0]
            df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.drop_duplicates()
    return df


def preprocess_municipal_energy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess Historic Municipal Energy Use.
    Filters to Electricity and selects key columns.
    """
    if df.empty:
        return df

    df = df.copy()

    # Filter to Electricity
    if "energy_type" in df.columns:
        df = df[df["energy_type"].str.lower() == "electricity"]

    # Select standard columns if available (standardize names)
    if "electricity_k_wh" in df.columns:
        df = df.rename(columns={"electricity_k_wh": "electricity_kwh"})
    if "natural_gas_therms" in df.columns:
        df["natural_gas_therms"] = pd.to_numeric(df["natural_gas_therms"], errors="coerce").fillna(0)

    expected_cols = ["municipality", "county", "utility", "year", "sector", "electricity_kwh", "natural_gas_therms"]
    available_cols = [c for c in expected_cols if c in df.columns]

    if "electricity_kwh" in df.columns:
        df["electricity_kwh"] = pd.to_numeric(df["electricity_kwh"], errors="coerce").fillna(0)

    if available_cols:
        df = df[available_cols]

    df = df.drop_duplicates()
    return df


def preprocess_community_energy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess Aggregated Community Scale Utility Energy Data.
    Cleans up the municipality dataset, removes unnamed columns, and standardizes numbers.
    """
    if df.empty:
        return df
    df = df.copy()

    # Rename total columns if needed
    if "total_electricity_k_wh" in df.columns:
        df = df.rename(columns={"total_electricity_k_wh": "total_electricity_kwh"})

    # Select standard columns
    expected_cols = [
        "municipality", "county", "muni_county", "year", "electric_utility",
        "residential_electricity", "commercial_electricity", "industrial_electricity",
        "street_lighting_electricity", "total_electricity_kwh", "natural_gas_utility",
        "residential_natural_gas", "commercial_natural_gas", "industrial_natural_gas",
        "street_lighting_natural_gas", "total_natural_gas_therms"
    ]
    available_cols = [c for c in expected_cols if c in df.columns]
    
    if available_cols:
        df = df[available_cols]

    # Convert non-numeric values like 'NDA' and 'CWC' to NaN or 0
    numeric_cols = [
        "residential_electricity", "commercial_electricity", "industrial_electricity",
        "street_lighting_electricity", "total_electricity_kwh",
        "residential_natural_gas", "commercial_natural_gas", "industrial_natural_gas",
        "street_lighting_natural_gas", "total_natural_gas_therms"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df = df.dropna(subset=["municipality", "year"])
    df["year"] = df["year"].astype(int)
    df = df.drop_duplicates()
    return df


def preprocess_nj_retail_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess NJ Residential Retail Prices.
    Outputs: date, year, month, price_cents_kwh.
    """
    if df.empty:
        return df
    
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

    # Ensure price is numeric
    if "price_cents_kwh" in df.columns:
        df["price_cents_kwh"] = pd.to_numeric(df["price_cents_kwh"], errors="coerce")

    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    return df


def preprocess_eia_residential_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess EIA multi-state residential prices."""
    if df.empty:
        return df
    
    df = df.copy()
    if "price_cents_per_k_wh" in df.columns:
        df = df.rename(columns={"price_cents_per_k_wh": "price_cents_kwh"})
    elif "price_cents_per_kwh" in df.columns:
        df = df.rename(columns={"price_cents_per_kwh": "price_cents_kwh"})

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

    # Ensure clean price column
    if "price_cents_kwh" in df.columns:
        df["price_cents_kwh"] = pd.to_numeric(df["price_cents_kwh"], errors="coerce")
        df = df.dropna(subset=["price_cents_kwh"])

    df = df.drop_duplicates()
    return df


def preprocess_weather(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess Weather Data.
    Aggregates daily weather to monthly (year, month).
    """
    if df.empty:
        return df

    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

    # Forward fill missing temps
    if "avg_temp_f" in df.columns:
        df["avg_temp_f"] = df["avg_temp_f"].interpolate(method="linear")
        df["avg_temp_f"] = df["avg_temp_f"].clip(-30, 120)

    # Recompute HDD/CDD for consistency if not present or to sanitize
    if "avg_temp_f" in df.columns:
        df["hdd"] = np.maximum(65 - df["avg_temp_f"], 0).round(1)
        df["cdd"] = np.maximum(df["avg_temp_f"] - 65, 0).round(1)

    # Aggregate to monthly
    monthly = df.groupby(["year", "month"]).agg(
        avg_temp_f=("avg_temp_f", "mean"),
        total_hdd=("hdd", "sum"),
        total_cdd=("cdd", "sum"),
        avg_humidity=("humidity_pct", "mean") if "humidity_pct" in df.columns else ("hdd", "count")
    ).reset_index()

    # Drop dummy humidity if it was used as fallback
    if "humidity_pct" not in df.columns and "avg_humidity" in monthly.columns:
        monthly = monthly.drop(columns=["avg_humidity"])

    return monthly


def preprocess_cpi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess CPI monthly.
    Ensures year, month, cpi are present.
    """
    if df.empty:
        return df
    
    df = df.copy()
    df["cpi"] = pd.to_numeric(df["cpi"], errors="coerce")
    df = df.dropna(subset=["cpi"])
    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    return df


def preprocess_pseg_distribution_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess PSEG Component Distribution Rates.
    Extracts tariff numbers and splits component labels.
    """
    if df.empty:
        return df

    df = df.copy()
    
    # Extract tariff number (e.g., 'Tariff 13' -> 13)
    if "tariff_version" in df.columns:
        df["tariff_number"] = df["tariff_version"].str.extract(r'(\d+)')[0]
        df["tariff_number"] = pd.to_numeric(df["tariff_number"], errors="coerce")
        
    # Split component_label by colon
    if "component_label" in df.columns:
        df["component_type"] = df["component_label"].str.split(":").str[0].str.strip()
        df["component_detail"] = df["component_label"].str.split(":", n=1).str[1].str.strip()
        
    # Ensure rates are numeric
    if "base_rate" in df.columns:
        df["base_rate"] = pd.to_numeric(df["base_rate"], errors="coerce")
    if "with_sut" in df.columns:
        df["with_sut"] = pd.to_numeric(df["with_sut"], errors="coerce")
        
    df = df.drop_duplicates()
    return df
