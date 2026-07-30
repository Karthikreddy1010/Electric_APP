"""
Statistical & Trend Analytics Service
Provides STL decomposition, Mann-Kendall trend tests, rolling Z-score anomaly detection,
box/violin plot distributions, and state cluster analysis across datasets.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from feature_store.base.feature_store import global_feature_store
from feature_store.data_registry import AccessPolicy
from feature_store.eia_retail.analytics import (
    mann_kendall_trend_test,
    detect_anomalies_zscore,
    compute_distribution_stats,
    perform_state_clustering,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    @staticmethod
    def get_statistical_report(module_id: str = "regional_insights", stateid: str = "NJ", sectorid: str = "RES") -> Dict[str, Any]:
        """Calculates comprehensive statistical metrics (trend, anomalies, distribution, clusters)."""
        df = global_feature_store.get_dataset("EIA Retail", requesting_module=module_id, required_policy=AccessPolicy.READ_ANALYZE)
        if df.empty:
            return {}

        stateid = stateid.upper()
        sectorid = sectorid.upper()

        sub = df[(df["stateid"] == stateid) & (df["sectorid"] == sectorid)].sort_values("period")
        if sub.empty:
            return {}

        # 1. Mann-Kendall Trend Test
        prices = sub["retail_price"].values
        mk_res = mann_kendall_trend_test(prices)

        # 2. Anomaly Detection (Z-score spikes/drops)
        anomalies = detect_anomalies_zscore(df, stateid=stateid, sectorid=sectorid, threshold=2.2)

        # 3. Distribution Summary (Box Plot metrics)
        latest_period = df["period"].max()
        dist_stats = compute_distribution_stats(df, period=latest_period, sectorid=sectorid)

        # 4. State Clusters
        clusters = perform_state_clustering(df, period=latest_period, sectorid=sectorid)

        # 5. Descriptive Stats
        desc = {
            "mean": round(float(np.mean(prices)), 4),
            "std": round(float(np.std(prices)), 4),
            "variance": round(float(np.var(prices)), 4),
            "min": round(float(np.min(prices)), 4),
            "max": round(float(np.max(prices)), 4),
            "skewness": round(float(pd.Series(prices).skew()), 4),
        }

        return {
            "stateid": stateid,
            "sectorid": sectorid,
            "descriptive_stats": desc,
            "mann_kendall_trend": mk_res,
            "anomalies_count": len(anomalies),
            "anomalies": anomalies,
            "distribution": dist_stats,
            "clusters": clusters,
        }


# Global Singleton Analytics Service Instance
analytics_service = AnalyticsService()
