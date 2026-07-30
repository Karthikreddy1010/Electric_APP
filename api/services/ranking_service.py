"""
Ranking & Regional Benchmarking Service
Provides national, regional, rolling, and percentile state ranking analysis.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List
import pandas as pd

from feature_store.base.feature_store import global_feature_store
from feature_store.data_registry import AccessPolicy
from feature_store.eia_retail.rankings import get_top_and_bottom_states, add_rankings_and_percentiles

logger = logging.getLogger(__name__)


class RankingService:
    @staticmethod
    def get_benchmark_rankings(module_id: str = "benchmark", period: str | None = None, sectorid: str = "RES") -> Dict[str, Any]:
        """Provides full benchmark ranking matrix across states and regions."""
        df = global_feature_store.get_dataset("EIA Retail", requesting_module=module_id, required_policy=AccessPolicy.READ_ANALYZE)
        if df.empty:
            return {}

        sectorid = sectorid.upper()
        if period is None:
            period = df["period"].max()

        # Compute top/bottom states
        top_bottom = get_top_and_bottom_states(df, period=period, sectorid=sectorid, top_n=10)

        # Region averages
        p_df = df[(df["period"] == period) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")].copy()
        if "region" not in p_df.columns:
            p_df = add_rankings_and_percentiles(p_df)

        reg_avgs = p_df.groupby("region")["retail_price"].mean().round(4).to_dict()

        # National average
        nat_avg = round(float(p_df["retail_price"].mean()), 4)

        return {
            "period": period,
            "sectorid": sectorid,
            "national_avg": nat_avg,
            "regional_averages": reg_avgs,
            "top_10_expensive": top_bottom.get("most_expensive", []),
            "cheapest_10": top_bottom.get("cheapest", []),
        }


ranking_service = RankingService()
