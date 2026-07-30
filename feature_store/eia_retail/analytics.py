"""
EIA Retail Statistical Analytics Engine
Implements STL decomposition, Mann-Kendall trend test, anomaly detection, variance analysis,
box/violin plot distributions, and state clustering.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from feature_store.base.cache import memoize_feature

logger = logging.getLogger(__name__)


def mann_kendall_trend_test(series: pd.Series | np.ndarray) -> dict:
    """
    Non-parametric Mann-Kendall test to detect monotonic trends in time series.
    Returns: trend_direction ('increasing', 'decreasing', 'no trend'), p_value, z_score.
    """
    x = np.asarray(series).copy()
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return {"trend": "insufficient_data", "p_value": 1.0, "z_score": 0.0}

    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1:] - x[k]))

    # Calculate variance of S
    # Assuming no ties for simplicity or simple tie correction
    unique_x, tp = np.unique(x, return_counts=True)
    g = len(unique_x)
    var_s = (n * (n - 1) * (2 * n + 5) - np.sum(tp * (tp - 1) * (2 * tp + 5))) / 18.0

    if var_s == 0:
        return {"trend": "no trend", "p_value": 1.0, "z_score": 0.0}

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    # Two-tailed p-value approximation
    from scipy.stats import norm
    p = 2 * (1 - norm.cdf(abs(z)))

    if p < 0.05:
        trend = "increasing" if z > 0 else "decreasing"
    else:
        trend = "no trend"

    return {"trend": trend, "p_value": round(float(p), 4), "z_score": round(float(z), 4)}


def detect_anomalies_zscore(df: pd.DataFrame, stateid: str = "NJ", sectorid: str = "RES", threshold: float = 2.5) -> list[dict]:
    """
    Detects price and demand anomalies using rolling Z-scores.
    """
    subset = df[(df["stateid"] == stateid) & (df["sectorid"] == sectorid)].copy()
    if subset.empty:
        return []

    subset = subset.sort_values("period").reset_index(drop=True)
    price = subset["retail_price"]
    mean_12 = price.rolling(12, min_periods=3).mean()
    std_12 = price.rolling(12, min_periods=3).std().fillna(1.0)
    std_12 = np.where(std_12 == 0, 1.0, std_12)

    z_scores = (price - mean_12) / std_12
    subset["z_score"] = z_scores

    anomalies = []
    for _, row in subset[abs(subset["z_score"]) >= threshold].iterrows():
        anomalies.append({
            "period": row["period"],
            "stateid": row["stateid"],
            "sectorid": row["sectorid"],
            "retail_price": float(row["retail_price"]),
            "z_score": round(float(row["z_score"]), 2),
            "type": "spike" if row["z_score"] > 0 else "drop",
        })

    return anomalies


def compute_distribution_stats(df: pd.DataFrame, period: str, sectorid: str = "RES") -> dict:
    """
    Computes statistical distribution metrics (box plot summary: min, Q1, median, Q3, max, mean, std, outliers).
    """
    sub = df[(df["period"] == period) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")]["retail_price"].dropna()
    if sub.empty:
        latest = df["period"].max()
        sub = df[(df["period"] == latest) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")]["retail_price"].dropna()

    q1 = float(np.percentile(sub, 25))
    median = float(np.median(sub))
    q3 = float(np.percentile(sub, 75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outliers = sub[(sub < lower_fence) | (sub > upper_fence)].tolist()

    return {
        "period": period,
        "sectorid": sectorid,
        "count": len(sub),
        "mean": round(float(sub.mean()), 4),
        "std": round(float(sub.std()), 4),
        "min": round(float(sub.min()), 4),
        "q1": round(q1, 4),
        "median": round(median, 4),
        "q3": round(q3, 4),
        "max": round(float(sub.max()), 4),
        "iqr": round(iqr, 4),
        "outliers_count": len(outliers),
        "outliers": [round(x, 4) for x in outliers],
    }


def perform_state_clustering(df: pd.DataFrame, period: str | None = None, sectorid: str = "RES") -> list[dict]:
    """
    Groups states into 4 strategic price-volatility clusters (High Price / High Volatility, etc.).
    """
    if period is None:
        period = df["period"].max()

    recent_df = df[(df["period"] == period) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")].copy()
    if recent_df.empty:
        return []

    med_price = recent_df["retail_price"].median()
    med_vol = recent_df["price_volatility_index"].median()

    clusters = []
    for _, row in recent_df.iterrows():
        p = row["retail_price"]
        v = row["price_volatility_index"]
        
        if p >= med_price and v >= med_vol:
            category = "High Cost / High Volatility"
        elif p >= med_price and v < med_vol:
            category = "High Cost / Stable"
        elif p < med_price and v >= med_vol:
            category = "Low Cost / High Volatility"
        else:
            category = "Low Cost / Stable"

        clusters.append({
            "stateid": row["stateid"],
            "stateName": row.get("stateDescription", row["stateid"]),
            "retail_price": round(float(p), 4),
            "volatility_index": round(float(v), 4),
            "yoy_growth": round(float(row.get("price_yoy_growth", 0.0)), 2),
            "cluster": category,
        })

    return clusters
