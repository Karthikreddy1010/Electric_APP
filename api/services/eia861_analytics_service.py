"""
EIA-861 Advanced Analytics Service.

Provides utility operational benchmarking, Net Metering economics,
Demand Response incentive estimation, and Dynamic Pricing (TOU) analysis.

All calculations are deterministic.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class EIA861AnalyticsService:
    """Deterministic analytics engine for EIA-861 utility operational data."""

    def __init__(self, engine=None):
        self._engine = engine

    def _get_engine(self):
        if self._engine is None:
            from database.connection import get_sync_engine
            self._engine = get_sync_engine()
        return self._engine

    # ── Operational Benchmarking ───────────────────────────────────────────

    def get_operational_benchmark(self, state: str = "NJ", year: int = None) -> list[dict]:
        """Return utility operational metrics for benchmarking within a state."""
        engine = self._get_engine()
        query = text("""
            SELECT utility_id, utility_name, state, year,
                   total_revenue, total_sales_mwh, total_customers,
                   avg_price, peak_demand, total_load,
                   demand_response_flag, dynamic_pricing_flag,
                   nm_customers, nm_energy_mwh
            FROM eia861_master
            WHERE state = :state
            ORDER BY year DESC, total_sales_mwh DESC
        """)

        try:
            df = pd.read_sql(query, con=engine, params={"state": state.upper()})
        except Exception as e:
            logger.warning(f"Failed to query EIA-861 data: {e}")
            return []

        if df.empty:
            return []

        # Filter to specific year if provided
        if year:
            df = df[df["year"] == year]

        records = []
        for _, row in df.iterrows():
            total_sales = float(row["total_sales_mwh"]) if pd.notna(row["total_sales_mwh"]) else 0
            total_customers = float(row["total_customers"]) if pd.notna(row["total_customers"]) else 1
            total_revenue = float(row["total_revenue"]) if pd.notna(row["total_revenue"]) else 0
            peak_demand = float(row["peak_demand"]) if pd.notna(row["peak_demand"]) else 0
            total_load = float(row["total_load"]) if pd.notna(row["total_load"]) else 0

            # Grid transmission loss estimate
            grid_loss_pct = ((total_load - total_sales) / total_load * 100) if total_load > 0 else 5.0
            grid_loss_pct = max(min(grid_loss_pct, 15.0), 0.0)  # Clamp to reasonable range

            # Revenue per customer
            rev_per_cust = (total_revenue / total_customers) if total_customers > 0 else 0
            # Average consumption per customer (MWh)
            usage_per_cust = (total_sales / total_customers) if total_customers > 0 else 0

            records.append({
                "utility_id": int(row["utility_id"]),
                "utility_name": str(row["utility_name"]),
                "state": str(row["state"]),
                "year": int(row["year"]),
                "total_revenue_k": round(total_revenue, 0),
                "total_sales_mwh": round(total_sales, 0),
                "total_customers": int(total_customers),
                "avg_price_cents_kwh": round(float(row["avg_price"]) if pd.notna(row["avg_price"]) else 0, 2),
                "peak_demand_mw": round(peak_demand, 0),
                "grid_loss_pct": round(grid_loss_pct, 2),
                "revenue_per_customer": round(rev_per_cust, 2),
                "usage_per_customer_mwh": round(usage_per_cust, 1),
                "has_demand_response": bool(row["demand_response_flag"]),
                "has_dynamic_pricing": bool(row["dynamic_pricing_flag"]),
                "nm_customers": int(row["nm_customers"]) if pd.notna(row["nm_customers"]) else 0,
                "nm_energy_mwh": round(float(row["nm_energy_mwh"]) if pd.notna(row["nm_energy_mwh"]) else 0, 0),
            })

        return records

    # ── Incentive Programs ────────────────────────────────────────────────

    def get_available_incentives(self, utility_id: int = None, state: str = "NJ") -> dict:
        """Get available incentive programs (DR, Net Metering, Dynamic Pricing) for a utility."""
        engine = self._get_engine()

        params = {"state": state.upper()}
        where_clause = "WHERE state = :state"
        if utility_id:
            where_clause += " AND utility_id = :utility_id"
            params["utility_id"] = utility_id

        query = text(f"""
            SELECT utility_id, utility_name, year,
                   demand_response_flag, dynamic_pricing_flag,
                   nm_customers, nm_energy_mwh,
                   total_customers, total_sales_mwh, peak_demand
            FROM eia861_master
            {where_clause}
            ORDER BY year DESC
            LIMIT 20
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query EIA-861 incentives: {e}")
            return {"programs": []}

        if df.empty:
            return {"programs": []}

        # Get latest year data per utility
        latest = df.sort_values("year", ascending=False).drop_duplicates("utility_id", keep="first")

        programs = []
        for _, row in latest.iterrows():
            util_programs = []

            # Net Metering
            nm_custs = int(row["nm_customers"]) if pd.notna(row["nm_customers"]) else 0
            if nm_custs > 0:
                nm_energy = float(row["nm_energy_mwh"]) if pd.notna(row["nm_energy_mwh"]) else 0
                avg_export = nm_energy / nm_custs if nm_custs > 0 else 0
                # Estimate NJ solar export credit at ~$0.04/kWh SREC + retail offset
                annual_credit_estimate = avg_export * 1000 * 0.12  # rough residential estimate
                util_programs.append({
                    "type": "net_metering",
                    "label": "Solar Net Metering",
                    "available": True,
                    "enrolled_customers": nm_custs,
                    "avg_export_mwh": round(avg_export, 1),
                    "estimated_annual_credit": round(annual_credit_estimate, 0),
                    "description": f"Solar net metering available. {nm_custs:,} customers currently enrolled.",
                })

            # Demand Response
            if row.get("demand_response_flag"):
                peak = float(row["peak_demand"]) if pd.notna(row["peak_demand"]) else 0
                # Estimate DR credit: typical NJ residential = $50-200/year
                dr_credit = round(min(peak * 0.001 * 150, 200), 0)
                util_programs.append({
                    "type": "demand_response",
                    "label": "Demand Response Program",
                    "available": True,
                    "peak_demand_mw": round(peak, 0),
                    "estimated_annual_credit": dr_credit,
                    "description": "Active demand response program. Reduce peak loads during alerts for bill credits.",
                })

            # Dynamic Pricing / TOU
            if row.get("dynamic_pricing_flag"):
                util_programs.append({
                    "type": "dynamic_pricing",
                    "label": "Time-of-Use (TOU) Rates",
                    "available": True,
                    "description": "Dynamic TOU rate plan available. Shift usage to off-peak hours to save.",
                    "estimated_savings_pct": 12,  # Typical TOU savings for aware consumers
                })

            programs.append({
                "utility_id": int(row["utility_id"]),
                "utility_name": str(row["utility_name"]),
                "year": int(row["year"]),
                "programs": util_programs,
            })

        return {"utilities": programs}

    # ── TOU Savings Estimate ──────────────────────────────────────────────

    def estimate_tou_savings(
        self,
        monthly_usage_kwh: float = 750,
        peak_pct: float = 0.40,
        shift_pct: float = 0.15,
        peak_rate: float = 0.22,
        offpeak_rate: float = 0.09,
    ) -> dict:
        """Estimate savings from switching to a TOU rate plan."""
        peak_kwh = monthly_usage_kwh * peak_pct
        offpeak_kwh = monthly_usage_kwh * (1 - peak_pct)

        # Current flat rate cost
        flat_rate = (peak_rate + offpeak_rate) / 2
        flat_cost = monthly_usage_kwh * flat_rate

        # TOU cost without shifting
        tou_cost_no_shift = (peak_kwh * peak_rate) + (offpeak_kwh * offpeak_rate)

        # TOU cost with shifting
        shifted_kwh = peak_kwh * shift_pct
        new_peak_kwh = peak_kwh - shifted_kwh
        new_offpeak_kwh = offpeak_kwh + shifted_kwh
        tou_cost_shifted = (new_peak_kwh * peak_rate) + (new_offpeak_kwh * offpeak_rate)

        return {
            "monthly_usage_kwh": monthly_usage_kwh,
            "flat_rate_cost": round(flat_cost, 2),
            "tou_cost_no_shift": round(tou_cost_no_shift, 2),
            "tou_cost_with_shift": round(tou_cost_shifted, 2),
            "monthly_savings": round(tou_cost_no_shift - tou_cost_shifted, 2),
            "annual_savings": round((tou_cost_no_shift - tou_cost_shifted) * 12, 2),
            "shift_pct": shift_pct,
            "peak_rate": peak_rate,
            "offpeak_rate": offpeak_rate,
        }


# Module-level singleton
eia861_analytics_service = EIA861AnalyticsService()
