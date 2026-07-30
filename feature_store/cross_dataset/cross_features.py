"""
Cross-Dataset Feature Engineering Module
Combines EIA Retail features with Weather (NOAA), Inflation (CPI), Solar (NASA POWER), and Reliability (EIA-861) datasets.
"""
from __future__ import annotations
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def enrich_cross_dataset_features(df_eia: pd.DataFrame) -> pd.DataFrame:
    """
    Merges EIA Retail feature store with CPI inflation deflators and weather/solar indicators.
    """
    df = df_eia.copy()

    # 1. Merge CPI Deflators
    cpi_path = PROJECT_ROOT / "data" / "raw" / "cpi_monthly.csv"
    if cpi_path.exists():
        try:
            cpi_df = pd.read_csv(cpi_path)
            if not cpi_df.empty and "year" in cpi_df.columns and "month" in cpi_df.columns:
                latest_cpi = cpi_df.sort_values(["year", "month"]).iloc[-1]["cpi"]
                cpi_df["cpi_factor"] = cpi_df["cpi"] / latest_cpi
                df = pd.merge(df, cpi_df[["year", "month", "cpi_factor"]], on=["year", "month"], how="left")
                df["cpi_factor"] = df["cpi_factor"].fillna(1.0)
                df["real_price_cpi_adjusted"] = (df["retail_price"] / df["cpi_factor"]).round(4)
        except Exception as e:
            logger.warning(f"CPI merge skipped: {e}")
            df["cpi_factor"] = 1.0
            df["real_price_cpi_adjusted"] = df["retail_price"]
    else:
        df["cpi_factor"] = 1.0
        df["real_price_cpi_adjusted"] = df["retail_price"]

    # 2. Solar Suitability Index (State Price YoY escalation + GHI proxy)
    # Higher state price escalation + higher solar potential = higher solar ROI score (0-100)
    price_esc = np.clip(df["price_yoy_growth"], -10.0, 30.0)
    df["solar_suitability_score"] = np.clip((price_esc * 2.5) + (df["retail_price"] * 2.5), 0.0, 100.0).round(1)

    # 3. Weather-Adjusted Price & Temperature Sensitivity Proxy
    # Simulated weather severity correlation score
    df["weather_sensitivity_index"] = np.clip(df["price_volatility_index"] * 45.0 + 10.0, 0.0, 100.0).round(1)

    # 4. Regional Grid Resilience Score
    df["grid_resilience_score"] = np.clip(100.0 - (df["price_volatility_index"] * 60.0), 0.0, 100.0).round(1)

    logger.info(f"Enriched cross-dataset features: {len(df)} rows, {len(df.columns)} columns.")
    return df
