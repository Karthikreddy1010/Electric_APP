"""
Data cleaning and validation pipeline.
Handles missing values, unit normalization, outlier detection, and schema validation.
"""
import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BillingCleaner:
    """Clean and validate billing data."""
    
    REQUIRED_COLS = ["date", "usage_kwh", "total_bill"]
    RATE_COLS = ["bgs_rate", "transmission_rate", "distribution_rate", "sbc_rate", "nug_rate"]
    COST_COLS = ["bgs_cost", "transmission_cost", "distribution_cost", "sbc_cost", "nug_cost"]
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Parse dates
        df["date"] = pd.to_datetime(df["date"])
        
        # 2. Validate required columns
        missing = [c for c in self.REQUIRED_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # 3. Handle missing values
        for col in self.RATE_COLS:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())
        
        for col in self.COST_COLS:
            if col in df.columns:
                df[col] = df[col].interpolate(method="linear").fillna(0)
        
        df["usage_kwh"] = df["usage_kwh"].fillna(df["usage_kwh"].median())
        df["total_bill"] = df["total_bill"].interpolate(method="linear").fillna(df["total_bill"].median())
        
        # 4. Remove negative usage
        df.loc[df["usage_kwh"] < 0, "usage_kwh"] = np.nan
        df["usage_kwh"] = df["usage_kwh"].interpolate()
        
        # 5. Outlier capping (IQR method on total_bill)
        q1 = df["total_bill"].quantile(0.05)
        q3 = df["total_bill"].quantile(0.95)
        iqr = q3 - q1
        lower, upper = q1 - 2*iqr, q3 + 2*iqr
        n_outliers = ((df["total_bill"] < lower) | (df["total_bill"] > upper)).sum()
        if n_outliers > 0:
            logger.warning(f"Capping {n_outliers} outlier bills to [{lower:.2f}, {upper:.2f}]")
        df["total_bill"] = df["total_bill"].clip(lower, upper)
        
        # 6. Ensure chronological order, no duplicates
        df = df.sort_values("date").drop_duplicates(subset=["date"])
        
        # 7. Compute effective rate
        df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
        
        return df.reset_index(drop=True)


class WeatherCleaner:
    """Clean and validate weather data."""
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        
        # Forward-fill missing temps (weather stations may have gaps)
        df["avg_temp_f"] = df["avg_temp_f"].interpolate(method="linear")
        
        # Recompute HDD/CDD to ensure consistency
        df["hdd"] = np.maximum(65 - df["avg_temp_f"], 0).round(1)
        df["cdd"] = np.maximum(df["avg_temp_f"] - 65, 0).round(1)
        
        # Cap unreasonable temperatures
        df["avg_temp_f"] = df["avg_temp_f"].clip(-30, 120)
        
        df = df.sort_values("date").drop_duplicates(subset=["date"])
        return df.reset_index(drop=True)


class MarketCleaner:
    """Clean and validate PJM market data."""
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        
        # LMP can spike; log extreme values but don't remove
        p99 = df["lmp_da"].quantile(0.99) if "lmp_da" in df.columns else 200
        n_spikes = (df.get("lmp_da", pd.Series()) > p99*2).sum()
        if n_spikes > 0:
            logger.info(f"Detected {n_spikes} LMP price spikes above ${p99*2:.2f}")
        
        # Fill missing with forward fill (markets close on weekends/holidays)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].ffill()
        
        df = df.sort_values("date").drop_duplicates(subset=["date"])
        return df.reset_index(drop=True)


def run_cleaning_pipeline(billing_df, weather_df, market_df):
    """Run full cleaning pipeline on all datasets."""
    logger.info("Running cleaning pipeline...")
    billing = BillingCleaner().clean(billing_df)
    weather = WeatherCleaner().clean(weather_df)
    market = MarketCleaner().clean(market_df)
    logger.info(f"Cleaned: billing={len(billing)}, weather={len(weather)}, market={len(market)}")
    return billing, weather, market
