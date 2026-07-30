"""
EIA Retail Feature Engineering Engine
Computes Price, Sales, Revenue, Customer, and Derived features per (stateid, sectorid) group.
Exports enriched dataset and saves to data/processed/eia_retail_features_v1.parquet.
"""
from __future__ import annotations
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def build_eia_retail_features(df_raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Computes all engineered EIA Retail features on normalized raw DataFrame.
    """
    if df_raw is None or df_raw.empty:
        from feature_store.eia_retail.loader import load_and_merge_eia_raw
        df_raw = load_and_merge_eia_raw()

    df = df_raw.copy()
    df = df.sort_values(["stateid", "sectorid", "period"]).reset_index(drop=True)

    logger.info("Computing engineered EIA Retail features...")

    # Groupby state and sector for time-series computations
    g = df.groupby(["stateid", "sectorid"])

    # 1. Effective Price (cents/kWh) = Revenue (million $) * 100 / Sales (million kWh)
    # Note: 1 million $ = 100,000,000 cents. 1 million kWh = 1,000,000 kWh.
    # Revenue * 1e8 / (Sales * 1e6) = Revenue * 100 / Sales
    sales_safe = np.where(df["retail_sales"] > 0, df["retail_sales"], np.nan)
    df["effective_price"] = np.where(
        np.isnan(sales_safe),
        df["retail_price"],
        (df["retail_revenue"] * 100.0 / sales_safe)
    )

    # 2. Price Features
    df["price_mom_growth"] = g["retail_price"].pct_change(1) * 100.0
    df["price_yoy_growth"] = g["retail_price"].pct_change(12) * 100.0
    df["price_rolling_3m"] = g["retail_price"].transform(lambda x: x.rolling(3, min_periods=1).mean())
    df["price_rolling_6m"] = g["retail_price"].transform(lambda x: x.rolling(6, min_periods=1).mean())
    df["price_rolling_12m"] = g["retail_price"].transform(lambda x: x.rolling(12, min_periods=1).mean())
    df["price_rolling_std_12m"] = g["retail_price"].transform(lambda x: x.rolling(12, min_periods=1).std()).fillna(0.0)
    
    mean_12m = np.where(df["price_rolling_12m"] > 0, df["price_rolling_12m"], np.nan)
    df["price_volatility_index"] = np.where(np.isnan(mean_12m), 0.0, df["price_rolling_std_12m"] / mean_12m)

    # 3. Sales Features
    df["sales_mom_growth"] = g["retail_sales"].pct_change(1) * 100.0
    df["sales_yoy_growth"] = g["retail_sales"].pct_change(12) * 100.0
    df["sales_annual_mwh"] = g["retail_sales"].transform(lambda x: x.rolling(12, min_periods=1).sum()) * 1000.0  # million kWh -> MWh

    # Seasonal sales index (month sales / 12m rolling avg sales)
    sales_avg_12m = g["retail_sales"].transform(lambda x: x.rolling(12, min_periods=1).mean())
    df["sales_seasonal_index"] = np.where(sales_avg_12m > 0, df["retail_sales"] / sales_avg_12m, 1.0)

    # 4. Revenue Features
    df["revenue_mom_growth"] = g["retail_revenue"].pct_change(1) * 100.0
    df["revenue_yoy_growth"] = g["retail_revenue"].pct_change(12) * 100.0

    # Revenue per customer ($ / customer / month)
    # retail_revenue is in million dollars. million dollars * 1e6 / customers = dollars / customer
    cust_safe = np.where(df["retail_customers"] > 0, df["retail_customers"], np.nan)
    df["revenue_per_customer"] = np.where(np.isnan(cust_safe), 0.0, df["retail_revenue"] * 1e6 / cust_safe)

    # 5. Customer Features
    df["customer_mom_growth"] = g["retail_customers"].pct_change(1) * 100.0
    df["customer_yoy_growth"] = g["retail_customers"].pct_change(12) * 100.0
    
    # Avg monthly usage per customer (kWh / customer / month)
    # retail_sales is in million kWh. million kWh * 1e6 / customers = kWh / customer
    df["avg_usage_per_customer_kwh"] = np.where(np.isnan(cust_safe), 0.0, df["retail_sales"] * 1e6 / cust_safe)

    # 6. Sector Spreads (Res vs Com, Res vs Ind per state & period)
    # Res price minus Com price for same state & period
    res_df = df[df["sectorid"] == "RES"][["period", "stateid", "retail_price"]].rename(columns={"retail_price": "res_price"})
    com_df = df[df["sectorid"] == "COM"][["period", "stateid", "retail_price"]].rename(columns={"retail_price": "com_price"})
    ind_df = df[df["sectorid"] == "IND"][["period", "stateid", "retail_price"]].rename(columns={"retail_price": "ind_price"})

    spreads = pd.merge(res_df, com_df, on=["period", "stateid"], how="left")
    spreads = pd.merge(spreads, ind_df, on=["period", "stateid"], how="left")
    spreads["res_com_spread"] = spreads["res_price"] - spreads["com_price"]
    spreads["res_ind_spread"] = spreads["res_price"] - spreads["ind_price"]

    df = pd.merge(df, spreads[["period", "stateid", "res_com_spread", "res_ind_spread"]], on=["period", "stateid"], how="left")

    # Fill remaining NaNs for numeric columns safely
    growth_cols = [c for c in df.columns if "growth" in c]
    for c in growth_cols:
        df[c] = df[c].fillna(0.0)

    # Clean infinity / overflow
    df = df.replace([np.inf, -np.inf], 0.0)

    # Add Version & Metadata Attributes
    df["dataset_version"] = "v1"
    df["feature_version"] = "v1"
    df["build_timestamp"] = pd.Timestamp.now().isoformat()

    # Save to data/processed/eia_retail_features_v1.parquet
    processed_dir = PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "eia_retail_features_v1.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved engineered features dataset: {out_path} ({len(df)} rows, {len(df.columns)} cols)")

    return df
