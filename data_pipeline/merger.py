"""
Merger — Combines datasets and applies inflation adjustments.

Builds the final master dataset based on the monthly NJ retail prices spine,
joining CPI, weather, and computing real (inflation-adjusted) values.
"""
import logging
import pandas as pd

from data_pipeline.config import CPI_BASE_YEAR

logger = logging.getLogger(__name__)


def adjust_for_inflation(
    df: pd.DataFrame, 
    price_col: str, 
    cpi_col: str, 
    base_cpi: float
) -> pd.DataFrame:
    """
    Compute real (inflation-adjusted) price.
    Formula: real_value = nominal_value * (base_cpi / current_cpi)
    """
    df = df.copy()
    real_col = f"real_{price_col}"
    df[real_col] = df[price_col] * (base_cpi / df[cpi_col])
    return df


def build_master_dataset(datasets: dict) -> pd.DataFrame:
    """
    Takes processed datasets and joins them into a unified monthly master table.
    Spine: NJ retail prices (monthly).
    Left joins: CPI (monthly), Weather (monthly).
    """
    logger.info("=" * 70)
    logger.info("STAGE 5: Merging Datasets")
    logger.info("=" * 70)

    # 1. Base Spine: NJ Retail Prices
    nj_prices = datasets.get("nj_retail_prices")
    if nj_prices is None or nj_prices.empty:
        logger.error("NJ retail prices missing. Cannot build master spine.")
        return pd.DataFrame()
    
    master = nj_prices.copy()
    logger.info(f"Spine initialized with {len(master)} rows (NJ retail prices)")

    # 2. Join CPI (monthly)
    cpi_df = datasets.get("cpi_monthly")
    if cpi_df is not None and not cpi_df.empty:
        master = pd.merge(
            master, 
            cpi_df[["year", "month", "cpi"]], 
            on=["year", "month"], 
            how="left"
        )
        logger.info(f"Joined CPI: {len(master)} rows")
    else:
        logger.warning("CPI data missing. Inflation adjustment will be skipped.")

    # 3. Join Weather (monthly)
    weather_df = datasets.get("weather_monthly")
    if weather_df is not None and not weather_df.empty:
        master = pd.merge(
            master,
            weather_df,
            on=["year", "month"],
            how="left"
        )
        logger.info(f"Joined Weather: {len(master)} rows")

    # 4. Inflation Adjustment
    if "cpi" in master.columns and "price_cents_kwh" in master.columns:
        # Determine base CPI for CPI_BASE_YEAR (e.g. annual average of that year)
        # Fallback to the latest available if base year not found
        base_year_data = cpi_df[cpi_df["year"] == CPI_BASE_YEAR]
        if not base_year_data.empty:
            base_cpi = base_year_data["cpi"].mean()
        else:
            base_cpi = cpi_df["cpi"].iloc[-1]
            logger.warning(f"CPI_BASE_YEAR {CPI_BASE_YEAR} not found. Using {base_cpi} as base.")

        master = adjust_for_inflation(
            master, 
            price_col="price_cents_kwh", 
            cpi_col="cpi", 
            base_cpi=base_cpi
        )
        logger.info(f"Computed real_price_cents_kwh (base year: {CPI_BASE_YEAR}, base CPI: {base_cpi:.2f})")

    # Final cleanup
    master = master.sort_values(["year", "month"]).reset_index(drop=True)
    logger.info(f"Master dataset built successfully: {len(master)} rows, {len(master.columns)} columns")
    
    return master
