"""
Analytics Service Layer
========================
Thin wrapper that provides a clean interface between Flask routes
and the existing analytics modules. Encapsulates access to
app.config-stored data/models and offers caching for heavy operations.

This demonstrates the service-layer pattern. Routes import from here
rather than touching models/shared modules directly — keeping route
files thin and testable.
"""
import logging
from functools import lru_cache
from typing import Any

import pandas as pd
from flask import current_app

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Singleton-style service that wraps analytics module calls.

    Usage in a route handler::

        from app.services.analytics import get_analytics_service
        svc = get_analytics_service()
        breakdown = svc.get_bill_breakdown(months=12)
    """

    # ── Data access helpers ──────────────────────────────────────
    @staticmethod
    def _billing() -> pd.DataFrame:
        df = current_app.config.get("BILLING_DF")
        if df is None:
            raise RuntimeError("Billing data not loaded")
        return df

    @staticmethod
    def _forecast_model():
        model = current_app.config.get("FORECAST_MODEL")
        if model is None:
            raise RuntimeError("Forecast model not loaded")
        return model

    @staticmethod
    def _impact_model():
        model = current_app.config.get("IMPACT_MODEL")
        if model is None:
            raise RuntimeError("Impact model not loaded")
        return model

    # ── Bill Breakdown ───────────────────────────────────────────
    def get_bill_breakdown(self, months: int = 12) -> list[dict]:
        """Compute detailed bill breakdown for the last *months* months."""
        billing = self._billing()
        full = billing.copy()
        full["yoy_change_pct"] = full["total_bill"].pct_change(12) * 100
        recent = full.tail(months)

        results = []
        for _, row in recent.iterrows():
            yoy = round(float(row["yoy_change_pct"]), 2) if pd.notna(row["yoy_change_pct"]) else None
            results.append({
                "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
                "total_bill": round(float(row["total_bill"]), 2),
                "components": {
                    "bgs": round(float(row["bgs_cost"]), 2),
                    "transmission": round(float(row["transmission_cost"]), 2),
                    "distribution": round(float(row["distribution_cost"]), 2),
                    "sbc": round(float(row["sbc_cost"]), 2),
                    "nug": round(float(row["nug_cost"]), 2),
                    "dr_credit": round(float(row["dr_credit"]), 2),
                    "tax": round(float(row["sales_tax"]), 2),
                },
                "rates": {
                    "bgs": round(float(row["bgs_rate"]), 5),
                    "transmission": round(float(row["transmission_rate"]), 5),
                    "distribution": round(float(row["distribution_rate"]), 5),
                    "sbc": round(float(row["sbc_rate"]), 5),
                    "nug": round(float(row["nug_rate"]), 5),
                },
                "usage_kwh": round(float(row["usage_kwh"]), 1),
                "effective_rate": round(float(row["total_bill"]) / float(row["usage_kwh"]), 5),
                "yoy_change_pct": yoy,
            })
        return results

    # ── Trends ───────────────────────────────────────────────────
    def get_trends(self, months: int = 36) -> dict:
        """Return historical trend data."""
        billing = self._billing()
        df = billing.tail(months).copy()
        df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
        df["yoy_change"] = df["total_bill"].pct_change(12) * 100

        return {
            "months": df["date"].dt.strftime("%Y-%m").tolist(),
            "total_bills": df["total_bill"].round(2).tolist(),
            "usage": df["usage_kwh"].round(1).tolist(),
            "rates": df["effective_rate"].round(5).tolist(),
            "yoy_changes": [round(x, 1) if pd.notna(x) else None for x in df["yoy_change"]],
        }

    # ── Contribution ─────────────────────────────────────────────
    def get_contribution(self, month_index: int = -1) -> dict:
        """Component contribution analysis for a specific month."""
        from shared.bill_analytics import compute_contributions, classify_components

        billing = self._billing()
        row = billing.iloc[month_index]
        contribs = compute_contributions(row)

        return {
            "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
            "total_bill": round(float(row["total_bill"]), 2),
            "contributions": [
                {
                    "component": c.component, "label": c.label, "category": c.category,
                    "driver": c.driver, "value": c.value,
                    "pct_of_total": c.pct_of_total, "pct_of_subtotal": c.pct_of_subtotal,
                }
                for c in contribs
            ],
            "classification": classify_components(),
        }


# Module-level accessor — import this in routes if desired
def get_analytics_service() -> AnalyticsService:
    """Return an AnalyticsService instance (stateless, so safe to create per request)."""
    return AnalyticsService()
