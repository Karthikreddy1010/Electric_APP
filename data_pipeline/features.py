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
    Hybrid loading strategy:
      1. Processed CSV (weather_monthly.csv)
      2. Open-Meteo DB (weather_openmeteo)
      3. Fallback to NOAA air_temp.csv or synthetic weather_df
    """
    import os
    import numpy as np
    from pathlib import Path
    
    billing = billing_df.copy()
    billing["date"] = pd.to_datetime(billing["date"])
    billing["year_month"] = billing["date"].dt.to_period("M")
    billing_months = set(billing["year_month"].unique())

    # --- 1. Try Processed CSV ---
    project_root = Path(__file__).resolve().parent.parent
    processed_csv_path = project_root / "data" / "processed" / "weather_monthly.csv"
    
    csv_weather = None
    if processed_csv_path.exists():
        try:
            temp_df = pd.read_csv(processed_csv_path)
            # Create year_month from year and month
            temp_df["year_month"] = pd.to_datetime(
                temp_df["year"].astype(str) + "-" + temp_df["month"].astype(str).str.zfill(2) + "-01"
            ).dt.to_period("M")
            
            csv_months = set(temp_df["year_month"].unique())
            if billing_months.issubset(csv_months):
                logger.info("Using complete processed weather from weather_monthly.csv")
                csv_weather = temp_df
                # Standardize csv_weather columns
                csv_weather = csv_weather.rename(columns={
                    "total_hdd": "monthly_HDD",
                    "total_cdd": "monthly_CDD",
                    "avg_temp_f": "avg_temp",
                })
                # Add dummy columns for min/max/std if missing to be filled later
                for col in ["temp_std", "max_temp", "min_temp"]:
                    if col not in csv_weather.columns:
                        csv_weather[col] = np.nan
            else:
                logger.info("Processed weather_monthly.csv is incomplete/outdated. Will fallback to Open-Meteo DB.")
        except Exception as e:
            logger.error(f"Error reading weather_monthly.csv: {e}")

    # --- 2. Try Open-Meteo DB ---
    db_weather = None
    if csv_weather is None:
        try:
            from database.connection import get_sync_session
            from database.models import WeatherOpenMeteo
            with get_sync_session() as session:
                rows = session.query(WeatherOpenMeteo).order_by(WeatherOpenMeteo.date.asc()).all()
                if rows:
                    records = []
                    for r in rows:
                        records.append({
                            "date": pd.Timestamp(r.date),
                            "temp_avg": r.temp_avg,
                            "temp_max": r.temp_max,
                            "temp_min": r.temp_min
                        })
                    db_df = pd.DataFrame(records)
                    
                    # Convert from Celsius to Fahrenheit
                    for col in ["temp_avg", "temp_max", "temp_min"]:
                        db_df[col] = (db_df[col] * 9/5) + 32.0
                        
                    # Calculate CDD and HDD base 65F
                    db_df["cdd"] = np.maximum(db_df["temp_avg"] - 65.0, 0)
                    db_df["hdd"] = np.maximum(65.0 - db_df["temp_avg"], 0)
                    
                    db_df["year_month"] = db_df["date"].dt.to_period("M")
                    db_monthly = db_df.groupby("year_month").agg(
                        monthly_CDD=("cdd", "sum"),
                        monthly_HDD=("hdd", "sum"),
                        avg_temp=("temp_avg", "mean"),
                        temp_std=("temp_avg", "std"),
                        max_temp=("temp_max", "max"),
                        min_temp=("temp_min", "min")
                    ).reset_index()
                    
                    db_months = set(db_monthly["year_month"].unique())
                    if billing_months.issubset(db_months):
                        logger.info("Using complete weather from Open-Meteo DB")
                        db_weather = db_monthly
                    else:
                        logger.info("Open-Meteo DB is incomplete. Will use standard fallback.")
        except Exception as e:
            logger.error(f"Error reading from Open-Meteo DB: {e}")

    # --- 3. Fallback (NOAA CSV or Synthetic) ---
    fallback_weather = None
    if csv_weather is None and db_weather is None:
        raw_dir = project_root / "data" / "raw"
        csv_path = raw_dir / "air_temp.csv"
        
        if csv_path.exists():
            try:
                logger.info("Reading NOAA daily temperature observations from air_temp.csv...")
                noaa_df = pd.read_csv(csv_path)
                noaa_df["DATE"] = pd.to_datetime(noaa_df["DATE"])
                
                # Fill missing TAVG using (TMAX + TMIN)/2
                if "TAVG" not in noaa_df.columns:
                    noaa_df["TAVG"] = np.nan
                tavg_calc = (noaa_df["TMAX"].astype(float) + noaa_df["TMIN"].astype(float)) / 2.0
                noaa_df["TAVG"] = noaa_df["TAVG"].fillna(tavg_calc)
                
                # Clip outlier temperatures
                noaa_df["TAVG"] = noaa_df["TAVG"].clip(-30, 120)
                
                # Compute CDD / HDD with 65°F base
                noaa_df["cdd_calc"] = np.maximum(noaa_df["TAVG"] - 65.0, 0)
                noaa_df["hdd_calc"] = np.maximum(65.0 - noaa_df["TAVG"], 0)
                
                # Group monthly
                noaa_df["year_month"] = noaa_df["DATE"].dt.to_period("M")
                fallback_weather = noaa_df.groupby("year_month").agg(
                    monthly_CDD=("cdd_calc", "sum"),
                    monthly_HDD=("hdd_calc", "sum"),
                    avg_temp=("TAVG", "mean"),
                    temp_std=("TAVG", "std"),
                    max_temp=("TMAX", "max"),
                    min_temp=("TMIN", "min")
                ).reset_index()
            except Exception as e:
                logger.error(f"Error parsing NOAA daily air_temp.csv: {e}. Falling back to standard weather.")

    # Always compute a baseline from synthetic weather_df to fill any missing features
    weather = weather_df.copy()
    weather["date"] = pd.to_datetime(weather["date"])
    weather["year_month"] = weather["date"].dt.to_period("M")
    synthetic_fallback = weather.groupby("year_month").agg(
        fallback_hdd=("hdd", "sum"),
        fallback_cdd=("cdd", "sum"),
        fallback_avg_temp=("avg_temp_f", "mean"),
        fallback_temp_std=("avg_temp_f", "std"),
        fallback_max_temp=("avg_temp_f", "max"),
        fallback_min_temp=("avg_temp_f", "min"),
    ).reset_index()

    # --- Merge Logic ---
    if csv_weather is not None:
        merged = billing.merge(csv_weather, on="year_month", how="left")
    elif db_weather is not None:
        merged = billing.merge(db_weather, on="year_month", how="left")
    elif fallback_weather is not None:
        merged = billing.merge(fallback_weather, on="year_month", how="left")
    else:
        # If all else failed, just use synthetic directly
        synthetic_mapped = synthetic_fallback.rename(columns={
            "fallback_hdd": "monthly_HDD",
            "fallback_cdd": "monthly_CDD",
            "fallback_avg_temp": "avg_temp",
            "fallback_temp_std": "temp_std",
            "fallback_max_temp": "max_temp",
            "fallback_min_temp": "min_temp",
        })
        merged = billing.merge(synthetic_mapped, on="year_month", how="left")

    # Fill missing values from synthetic fallback
    merged = merged.merge(synthetic_fallback, on="year_month", how="left")
    
    # Use fallback where primary is missing
    if "monthly_CDD" not in merged.columns:
        merged["monthly_CDD"] = merged["fallback_cdd"]
    else:
        merged["monthly_CDD"] = merged["monthly_CDD"].fillna(merged["fallback_cdd"])
        
    if "monthly_HDD" not in merged.columns:
        merged["monthly_HDD"] = merged["fallback_hdd"]
    else:
        merged["monthly_HDD"] = merged["monthly_HDD"].fillna(merged["fallback_hdd"])
        
    if "avg_temp" not in merged.columns:
        merged["avg_temp"] = merged["fallback_avg_temp"]
    else:
        merged["avg_temp"] = merged["avg_temp"].fillna(merged["fallback_avg_temp"])
        
    if "temp_std" not in merged.columns:
        merged["temp_std"] = merged["fallback_temp_std"]
    else:
        merged["temp_std"] = merged["temp_std"].fillna(merged["fallback_temp_std"])
        
    if "max_temp" not in merged.columns:
        merged["max_temp"] = merged["fallback_max_temp"]
    else:
        merged["max_temp"] = merged["max_temp"].fillna(merged["fallback_max_temp"])
        
    if "min_temp" not in merged.columns:
        merged["min_temp"] = merged["fallback_min_temp"]
    else:
        merged["min_temp"] = merged["min_temp"].fillna(merged["fallback_min_temp"])
    
    # Cleanup extra columns
    cols_to_drop = ["year_month", "year", "month", "avg_humidity"] + [c for c in merged.columns if c.startswith("fallback_")]
    merged = merged.drop(columns=cols_to_drop, errors="ignore")
    
    # Add backward compatible lowercase columns
    merged["monthly_cdd"] = merged["monthly_CDD"]
    merged["monthly_hdd"] = merged["monthly_HDD"]
    
    # Derived: degree-day adjusted usage
    merged["hdd_per_kwh"] = merged["monthly_HDD"] / merged["usage_kwh"]
    merged["cdd_per_kwh"] = merged["monthly_CDD"] / merged["usage_kwh"]
    
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
        avg_lmp_rt=("lmp_rt", "mean"),
    ).reset_index()
    
    billing = billing_df.copy()
    billing["date"] = pd.to_datetime(billing["date"])
    billing["year_month"] = billing["date"].dt.to_period("M")
    
    merged = billing.merge(monthly_market, on="year_month", how="left")
    
    # Add PJM Market Physics features
    from models.pjm_market_physics import (
        DEFAULT_PJM,
        decompose_lmp,
        compute_effective_kwh,
        compute_energy_charge_two_settlement,
    )
    
    loss_factor = DEFAULT_PJM.total_loss_factor
    merged["loss_factor"] = loss_factor
    merged["effective_kwh"] = compute_effective_kwh(merged["usage_kwh"], loss_factor)
    
    # Decompose avg_lmp
    decomposed = decompose_lmp(
        merged["avg_lmp"].values,
        merged["avg_congestion"].values,
        loss_factor
    )
    merged["lmp_energy"] = decomposed["energy"]
    merged["lmp_congestion"] = decomposed["congestion"]
    merged["lmp_loss"] = decomposed["loss"]
    
    # Marginal cost matches energy price in PJM energy market
    merged["marginal_cost"] = merged["lmp_energy"]
    
    # Compute two-settlement components
    settlement = compute_energy_charge_two_settlement(
        effective_kwh=merged["effective_kwh"].values,
        da_price_mwh=merged["avg_lmp"].values,
        rt_price_mwh=merged["avg_lmp_rt"].values,
        da_fraction=DEFAULT_PJM.da_settlement_fraction
    )
    merged["da_energy_charge"] = settlement["da_charge"]
    merged["rt_deviation_charge"] = settlement["rt_charge"]
    
    return merged.drop(columns=["year_month"])


def add_unified_store_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich feature matrix with CPI deflators, utility profile indicators, 
    and advanced operational/environmental metrics (Unified Feature Store).
    
    Includes:
      - Scope 2 Emissions & Carbon Intensity
      - Demand Response Readiness
      - Peak & Base Load Analytics
      - Energy Intensity (per sqft)
      - Portfolio Benchmarking vs regional averages
      - Weather Normalization
    """
    df = df.copy()
    
    # 1. Parse dates if not already done
    dt = pd.to_datetime(df["date"])
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month
    
    # 2. Integrate CPI deflators (inflation deflator)
    try:
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        cpi_path = project_root / "data" / "raw" / "cpi_monthly.csv"
        if cpi_path.exists():
            cpi_df = pd.read_csv(cpi_path)
            # Find base CPI (the latest one)
            latest_row = cpi_df.sort_values(["year", "month"]).iloc[-1]
            base_cpi = float(latest_row["cpi"])
            
            cpi_df["cpi_factor"] = cpi_df["cpi"] / base_cpi
            df = df.merge(cpi_df[["year", "month", "cpi_factor"]], on=["year", "month"], how="left")
            df["cpi_factor"] = df["cpi_factor"].fillna(1.0)
            
            # Apply deflator to rates if they exist in df
            for rate_col in ["bgs_rate", "distribution_rate", "transmission_rate", "sbc_rate"]:
                if rate_col in df.columns:
                    df[f"{rate_col}_real"] = df[rate_col] / df["cpi_factor"]
    except Exception as e:
        logger.warning(f"Failed to integrate CPI deflator: {e}")
        df["cpi_factor"] = 1.0
        
    # 3. Query SQLite for Utility and Operational Metrics
    try:
        from database.connection import get_sync_engine
        engine = get_sync_engine()
        
        # Load EIA-861 Master table
        eia_df = pd.read_sql("SELECT * FROM eia861_master", con=engine)
        if not eia_df.empty:
            # Map utility names
            if "utility_name" not in df.columns:
                df["utility_name"] = "Public Service Elec & Gas Co"
                
            eia_subset = eia_df[[
                "year", "utility_name", "state", "peak_demand", "total_load", 
                "demand_response_flag", "dynamic_pricing_flag", "total_customers", 
                "total_sales_mwh", "avg_price"
            ]].copy()
            
            eia_subset["grid_loss_pct"] = 0.05
            
            df = df.merge(eia_subset, on=["year", "utility_name"], how="left")
            
            df["peak_demand"] = df["peak_demand"].fillna(0.0)
            df["total_load"] = df["total_load"].fillna(0.0)
            df["demand_response_flag"] = df["demand_response_flag"].fillna(0).astype(int)
            df["dynamic_pricing_flag"] = df["dynamic_pricing_flag"].fillna(0).astype(int)
            df["grid_loss_pct"] = df["grid_loss_pct"].fillna(0.05)
    except Exception as e:
        logger.warning(f"Failed to integrate Utility & Operational metrics from SQLite: {e}")
        
    # 4. Integrate Community/Municipal baseline indicators
    try:
        from database.connection import get_sync_engine
        engine = get_sync_engine()
        comm_df = pd.read_sql("SELECT * FROM community_energy", con=engine)
        if not comm_df.empty:
            # Aggregate to county average as regional benchmark feature
            county_df = comm_df.groupby(["year", "county"]).agg(
                county_avg_elec_kwh=("total_electricity_kwh", "mean"),
                county_avg_gas_therms=("total_natural_gas_therms", "mean")
            ).reset_index()
            
            if "county" not in df.columns:
                df["county"] = "Essex"
                
            df = df.merge(county_df, on=["year", "county"], how="left")
            df["county_avg_elec_kwh"] = df["county_avg_elec_kwh"].fillna(1000000.0)
            df["county_avg_gas_therms"] = df["county_avg_gas_therms"].fillna(50000.0)
    except Exception as e:
        logger.warning(f"Failed to integrate Community Energy metrics: {e}")

    # 5. Advanced Unified Feature Store Calculations (Carbon, DR, Normalization)
    usage = df["usage_kwh"] if "usage_kwh" in df.columns else pd.Series(750, index=df.index)
    
    # 5a. Carbon Intensity & Scope 2 Emissions
    # Seasonality in PJM marginal fuel mix: higher in Summer (6,7,8) & Winter (12,1,2)
    # Average PJM carbon intensity: 380 lbs CO2 / MWh = 172.3 g CO2 / kWh
    df["carbon_intensity_g_kwh"] = 172.3
    df.loc[df["month"].isin([6, 7, 8]), "carbon_intensity_g_kwh"] = 210.5
    df.loc[df["month"].isin([12, 1, 2]), "carbon_intensity_g_kwh"] = 190.2
    
    # Scope 2 = usage (kWh) * carbon intensity (g/kWh) / 1,000,000 to get Metric Tons
    df["scope_2_emissions_mt"] = (usage * df["carbon_intensity_g_kwh"]) / 1_000_000.0
    
    # 5b. Peak & Base Load Analytics
    # If peak_demand is missing, estimate as usage * 0.005
    peak_est = df["peak_demand"].replace(0.0, np.nan).fillna(usage * 0.005)
    # Estimate base load as usage * 0.001
    base_est = usage * 0.001
    
    df["peak_to_base_ratio"] = (peak_est / base_est.clip(lower=0.1)).round(3)
    df["base_load_fraction"] = (base_est / usage.clip(lower=1)).round(3)
    
    # 5c. Demand Response Readiness (Score 0 to 1)
    # DR Readiness increases with peak-to-base ratio (shiftable loads) and dynamic pricing capability
    has_smart_meter = 1.0 # assume True for SaaS profiles
    has_dynamic = df.get("dynamic_pricing_flag", pd.Series(0, index=df.index)).fillna(0).astype(float)
    df["dr_readiness_score"] = np.clip(0.3 * has_smart_meter + 0.3 * has_dynamic + 0.4 * (df["peak_to_base_ratio"] / 10.0), 0.0, 1.0).round(2)
    
    # 5d. Energy Intensity (kWh / sqft)
    # Default property area of 2000 sqft if not provided in user profile
    property_sqft = 2000.0
    df["energy_intensity_kwh_sqft"] = (usage / property_sqft).round(4)
    
    # 5e. Portfolio Benchmarking (customer usage vs county/state average)
    benchmark_usage = df.get("county_avg_elec_kwh", pd.Series(800.0, index=df.index)).fillna(800.0)
    # scale benchmark down to household scale if county totals are huge
    if benchmark_usage.mean() > 50000.0:
        benchmark_usage = benchmark_usage / 1200.0 # household scale factor proxy
    df["usage_vs_benchmark_ratio"] = (usage / benchmark_usage.clip(lower=1)).round(3)
    
    # 5f. Weather Normalization
    # usage_norm = usage / (1 + beta_hdd * (HDD - HDD_avg) + beta_cdd * (CDD - CDD_avg))
    hdd = df["monthly_HDD"] if "monthly_HDD" in df.columns else pd.Series(200, index=df.index)
    cdd = df["monthly_CDD"] if "monthly_CDD" in df.columns else pd.Series(50, index=df.index)
    
    # Base seasonal normal HDD/CDD for NJ
    normal_hdd = 350.0
    normal_cdd = 100.0
    
    # Elasticity proxy coefficients
    beta_hdd = 0.0012
    beta_cdd = 0.0025
    
    weather_adjustment = 1.0 + beta_hdd * (hdd - normal_hdd) + beta_cdd * (cdd - normal_cdd)
    df["weather_normalized_usage_kwh"] = (usage / weather_adjustment.clip(lower=0.5)).round(2)
    
    return df


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
    
    # 7b. Add Unified Feature Store Features
    df = add_unified_store_features(df)
    
    # 8. Rate component shares
    cost_cols = [c for c in df.columns if c.endswith("_cost") and c != "total_bill"]
    for c in cost_cols:
        df[f"{c}_share"] = df[c] / df["subtotal"].clip(lower=1)
    
    # 9. Drop rows with NaN from lagging (first 12 months)
    df = df.dropna().reset_index(drop=True)
    
    # 10. Select features
    exclude = ["date", "utility", "state", "customer_class", "season",
               target_col, "year_month", "utility_name", "county"]
    feature_cols = [c for c in df.columns 
                    if c not in exclude and df[c].dtype in [np.float64, np.int64, np.int32, np.float32]]
    
    logger.info(f"Feature matrix: {df.shape[0]} rows, {len(feature_cols)} features")
    
    return df, feature_cols, target_col

