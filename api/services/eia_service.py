"""
EIA Data Access Service
Single Source of Truth service layer for API routes querying EIA Retail data.
Enforces dataset access policies via DataRegistry.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from feature_store.base.feature_store import global_feature_store
from feature_store.data_registry import AccessPolicy
from feature_store.base.cache import memoize_feature
from feature_store.eia_retail.rankings import add_rankings_and_percentiles, get_top_and_bottom_states

logger = logging.getLogger(__name__)


class EIAService:
    @staticmethod
    def get_eia_df(module_id: str, required_policy: AccessPolicy = AccessPolicy.READ_ANALYZE) -> pd.DataFrame:
        """Retrieves the EIA Retail features DataFrame, enforcing module access policy."""
        return global_feature_store.get_dataset("EIA Retail", requesting_module=module_id, required_policy=required_policy)

    @staticmethod
    def get_state_prices(module_id: str, state_id: str = "NJ", sector_id: str = "RES") -> Dict[str, Any]:
        """Returns price history and current metrics for a state and sector."""
        df = EIAService.get_eia_df(module_id, AccessPolicy.READ_ANALYZE)
        if df.empty:
            return {}

        state_id = state_id.upper()
        sector_id = sector_id.upper()

        sub = df[(df["stateid"] == state_id) & (df["sectorid"] == sector_id)].copy()
        if sub.empty:
            return {}

        sub = sub.sort_values("period").reset_index(drop=True)
        latest = sub.iloc[-1].to_dict()

        history = sub[["period", "date", "retail_price", "effective_price", "price_yoy_growth", "price_rolling_12m"]].to_dict("records")

        return {
            "stateid": state_id,
            "sectorid": sector_id,
            "latest_period": latest.get("period"),
            "current_price": round(float(latest.get("retail_price", 0.0)), 4),
            "effective_price": round(float(latest.get("effective_price", 0.0)), 4),
            "yoy_growth": round(float(latest.get("price_yoy_growth", 0.0)), 2),
            "rolling_12m": round(float(latest.get("price_rolling_12m", 0.0)), 4),
            "volatility_index": round(float(latest.get("price_volatility_index", 0.0)), 4),
            "history": history,
        }

    @staticmethod
    def get_state_rankings(module_id: str, period: Optional[str] = None, sector_id: str = "RES") -> List[Dict[str, Any]]:
        """Returns state ranking table for a given period and sector."""
        df = EIAService.get_eia_df(module_id, AccessPolicy.READ_ANALYZE)
        if df.empty:
            return []

        sector_id = sector_id.upper()
        if period is None:
            period = df["period"].max()

        period_df = df[(df["period"] == period) & (df["sectorid"] == sector_id) & (df["stateid"] != "US")].copy()
        if period_df.empty:
            period = df["period"].max()
            period_df = df[(df["period"] == period) & (df["sectorid"] == sector_id) & (df["stateid"] != "US")].copy()

        # Add rankings if not already computed
        if "national_rank" not in period_df.columns:
            period_df = add_rankings_and_percentiles(period_df)

        period_df = period_df.sort_values("retail_price", ascending=False)
        
        ranks = []
        for _, row in period_df.iterrows():
            ranks.append({
                "stateid": row["stateid"],
                "stateName": row.get("stateDescription", row["stateid"]),
                "retail_price": round(float(row["retail_price"]), 4),
                "national_rank": int(row.get("national_rank", 0)),
                "regional_rank": int(row.get("regional_rank", 0)),
                "percentile_rank": round(float(row.get("percentile_rank", 0.0)), 1),
                "yoy_growth": round(float(row.get("price_yoy_growth", 0.0)), 2),
                "region": row.get("region", "Other"),
            })

        return ranks

    @staticmethod
    def get_dashboard_summary(module_id: str = "dashboard", focus_state: str = "NJ") -> Dict[str, Any]:
        """Provides high-level dashboard metrics for the focus state."""
        df = EIAService.get_eia_df(module_id, AccessPolicy.READ_ANALYZE)
        if df.empty:
            return {}

        focus_state = focus_state.upper()
        latest_period = df["period"].max()

        # Res sector latest
        res_df = df[(df["period"] == latest_period) & (df["sectorid"] == "RES")].copy()
        if "national_rank" not in res_df.columns:
            res_df = add_rankings_and_percentiles(res_df)

        nj_row = res_df[res_df["stateid"] == focus_state]
        us_row = res_df[res_df["stateid"] == "US"]

        nj_price = float(nj_row["retail_price"].iloc[0]) if not nj_row.empty else 0.0
        us_price = float(us_row["retail_price"].iloc[0]) if not us_row.empty else float(res_df["retail_price"].mean())
        nj_rank = int(nj_row["national_rank"].iloc[0]) if not nj_row.empty else 0

        # Highest & Lowest states
        state_only = res_df[res_df["stateid"] != "US"].sort_values("retail_price", ascending=False)
        highest_row = state_only.iloc[0] if not state_only.empty else {}
        lowest_row = state_only.iloc[-1] if not state_only.empty else {}

        # 12-month sparkline series for focus state
        nj_hist = df[(df["stateid"] == focus_state) & (df["sectorid"] == "RES")].sort_values("period").tail(12)
        sparkline = [
            {"period": r["period"], "price": round(float(r["retail_price"]), 4)}
            for _, r in nj_hist.iterrows()
        ]

        # Neighbor states (PA, NY, DE, MD)
        neighbors = ["PA", "NY", "DE", "MD"]
        neighbor_comparison = []
        for n_code in neighbors:
            n_row = res_df[res_df["stateid"] == n_code]
            if not n_row.empty:
                n_price = float(n_row["retail_price"].iloc[0])
                diff_pct = round((nj_price - n_price) / n_price * 100.0, 1) if n_price > 0 else 0.0
                neighbor_comparison.append({
                    "stateid": n_code,
                    "stateName": n_row.get("stateDescription", pd.Series([n_code])).iloc[0],
                    "retail_price": round(n_price, 4),
                    "vs_nj_pct": diff_pct,
                })

        return {
            "period": latest_period,
            "focus_state": focus_state,
            "current_price": round(nj_price, 4),
            "yoy_growth": round(float(nj_row["price_yoy_growth"].iloc[0]), 2) if not nj_row.empty else 0.0,
            "mom_growth": round(float(nj_row["price_mom_growth"].iloc[0]), 2) if not nj_row.empty else 0.0,
            "state_rank": nj_rank,
            "total_states": len(state_only),
            "national_avg": round(us_price, 4),
            "vs_national_pct": round((nj_price - us_price) / us_price * 100.0, 1) if us_price > 0 else 0.0,
            "highest_state": {
                "stateid": highest_row.get("stateid"),
                "stateName": highest_row.get("stateDescription"),
                "retail_price": round(float(highest_row.get("retail_price", 0.0)), 4),
            },
            "lowest_state": {
                "stateid": lowest_row.get("stateid"),
                "stateName": lowest_row.get("stateDescription"),
                "retail_price": round(float(lowest_row.get("retail_price", 0.0)), 4),
            },
            "sparkline": sparkline,
            "neighbors": neighbor_comparison,
        }


# Global EIA Service Instance
eia_service = EIAService()
