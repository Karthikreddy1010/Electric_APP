"""
Feature engineering pipeline for ML models.
Builds lag features, rolling averages, seasonal encodings, 
weather-billing joins, and market-derived features.
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def add_temporal_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Add time-based features from date column."""
    df = df.copy()
    dt = pd.to_datetime(df[date_col])
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month
    df["quarter"] = dt.dt.quarter
    df["day_of_year"] = dt.dt.dayofyear
    # Cyclical encoding for month (captures Jan-Dec continuity)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    # Season flag
    df["season"] = pd.cut(df["month"], bins=[0,3,6,9,12],
                          labels=["winter","spring","summer","fall"])
    df["is_summer_peak"] = df["month"].isin([6,7,8]).astype(int)
    df["is_winter_peak"] = df["month"].isin([12,1,2]).astype(int)
    return df


def add_lag_features(df: pd.DataFrame, col: str, lags: list[int] = None) -> pd.DataFrame:
    """Add lagged values for a target column."""
    if lags is None:
        lags = [1, 2, 3, 6, 12]
    df = df.copy()
    for lag in lags:
        df[f"{col}_lag_{lag}"] = df[col].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, col: str,
                         windows: list[int] = None) -> pd.DataFrame:
    """Add rolling mean and std for a target column."""
    if windows is None:
        windows = [3, 6, 12]
    df = df.copy()
    for w in windows:
        df[f"{col}_rolling_mean_{w}"] = df[col].rolling(window=w, min_periods=1).mean()
        df[f"{col}_rolling_std_{w}"] = df[col].rolling(window=w, min_periods=1).std()
    return df


def add_pct_change_features(df: pd.DataFrame, col: str,
                            periods: list[int] = None) -> pd.DataFrame:
    """Add percentage change features."""
    if periods is None:
        periods = [1, 3, 12]
    df = df.copy()
    for p in periods:
        df[f"{col}_pct_change_{p}"] = df[col].pct_change(periods=p)
    return df


def merge_weather_monthly(billing_df: pd.DataFrame,
                          weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily weather to monthly and merge with billing.
    Key features: monthly HDD, CDD, avg temp, temp variance.
    """
    weather = weather_df.copy()
    weather["date"] = pd.to_datetime(weather["date"])
    weather["year_month"] = weather["date"].dt.to_period("M")
    
    monthly_weather = weather.groupby("year_month").agg(
        monthly_hdd=("hdd", "sum"),
        monthly_cdd=("cdd", "sum"),
        avg_temp=("avg_temp_f", "mean"),
        temp_std=("avg_temp_f", "std"),
        max_temp=("avg_temp_f", "max"),
        min_temp=("avg_temp_f", "min"),
        precip_total=("precip_in", "sum"),
        humidity_avg=("humidity_pct", "mean"),
    ).reset_index()
    
    billing = billing_df.copy()
    billing["date"] = pd.to_datetime(billing["date"])
    billing["year_month"] = billing["date"].dt.to_period("M")
    
    merged = billing.merge(monthly_weather, on="year_month", how="left")
    merged = merged.drop(columns=["year_month"])
    
    # Derived: degree-day adjusted usage
    merged["hdd_per_kwh"] = merged["monthly_hdd"] / merged["usage_kwh"]
    merged["cdd_per_kwh"] = merged["monthly_cdd"] / merged["usage_kwh"]
    
    return merged


def merge_market_monthly(billing_df: pd.DataFrame,
                         market_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily market data to monthly and merge with billing."""
    market = market_df.copy()
    market["date"] = pd.to_datetime(market["date"])
    market["year_month"] = market["date"].dt.to_period("M")
    
    monthly_market = market.groupby("year_month").agg(
        avg_lmp=("lmp_da", "mean"),
        max_lmp=("lmp_da", "max"),
        lmp_volatility=("lmp_da", "std"),
        avg_capacity_price=("capacity_price", "mean"),
        avg_congestion=("congestion", "mean"),
    ).reset_index()
    
    billing = billing_df.copy()
    billing["date"] = pd.to_datetime(billing["date"])
    billing["year_month"] = billing["date"].dt.to_period("M")
    
    merged = billing.merge(monthly_market, on="year_month", how="left")
    return merged.drop(columns=["year_month"])


def build_feature_matrix(billing_df, weather_df, market_df,
                         target_col="total_bill"):
    """
    Full feature engineering pipeline.
    Returns feature matrix X and target y, with feature names.
    """
    logger.info("Building feature matrix...")
    
    # 1. Merge weather
    df = merge_weather_monthly(billing_df, weather_df)
    
    # 2. Merge market
    df = merge_market_monthly(df, market_df)
    
    # 3. Temporal features
    df = add_temporal_features(df)
    
    # 4. Lag features on target
    df = add_lag_features(df, target_col, lags=[1, 2, 3, 6, 12])
    
    # 5. Rolling features on target
    df = add_rolling_features(df, target_col, windows=[3, 6, 12])
    
    # 6. Lag features on usage
    df = add_lag_features(df, "usage_kwh", lags=[1, 3, 12])
    
    # 7. Pct change
    df = add_pct_change_features(df, target_col, periods=[1, 12])
    
    # 8. Rate component shares
    cost_cols = [c for c in df.columns if c.endswith("_cost") and c != "total_bill"]
    for c in cost_cols:
        df[f"{c}_share"] = df[c] / df["subtotal"].clip(lower=1)
    
    # 9. Drop rows with NaN from lagging (first 12 months)
    df = df.dropna().reset_index(drop=True)
    
    # 10. Select features
    exclude = ["date", "utility", "state", "customer_class", "season",
               target_col, "year_month"]
    feature_cols = [c for c in df.columns 
                    if c not in exclude and df[c].dtype in [np.float64, np.int64, np.int32, np.float32]]
    
    logger.info(f"Feature matrix: {df.shape[0]} rows, {len(feature_cols)} features")
    
    return df, feature_cols, target_col
