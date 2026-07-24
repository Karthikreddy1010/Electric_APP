"""
PJM Wholesale Market Analytics Service.

Consumes real PJM day-ahead hourly LMP data to compute:
  - Daily/monthly price aggregates
  - Congestion indices
  - Price volatility & spike detection
  - Peak vs off-peak spread analysis
  - Wholesale cost exposure for customers
  - Load-shifting savings estimates
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PjmService:
    """Deterministic PJM wholesale market analytics engine."""

    def __init__(self, engine=None):
        self._engine = engine

    def _get_engine(self):
        if self._engine is None:
            from database.connection import get_sync_engine
            self._engine = get_sync_engine()
        return self._engine

    # ── Core Data Access ───────────────────────────────────────────────────

    def get_hourly_lmps(self, zone: str = "PSEG", days: int = 30) -> pd.DataFrame:
        """Retrieve hourly LMP data for a zone from pjm_lmp_hourly."""
        engine = self._get_engine()
        query = text("""
            SELECT h.timestamp, h.total_lmp, h.energy_comp, h.congestion_comp, h.loss_comp,
                   n.zone, n.name as node_name
            FROM pjm_lmp_hourly h
            JOIN pjm_lmp_nodes n ON h.node_id = n.node_id
            WHERE n.zone = :zone
            ORDER BY h.timestamp DESC
            LIMIT :limit
        """)
        try:
            df = pd.read_sql(query, con=engine, params={"zone": zone, "limit": days * 24})
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)
            return df
        except Exception as e:
            logger.warning(f"Failed to query PJM LMP data: {e}")
            return pd.DataFrame()

    # ── Analytics ──────────────────────────────────────────────────────────

    def compute_daily_analytics(self, zone: str = "PSEG", days: int = 30) -> list[dict]:
        """Compute daily aggregated LMP analytics."""
        df = self.get_hourly_lmps(zone, days)
        if df.empty:
            return []

        df["date"] = df["timestamp"].dt.date
        daily = df.groupby("date").agg(
            avg_lmp=("total_lmp", "mean"),
            max_lmp=("total_lmp", "max"),
            min_lmp=("total_lmp", "min"),
            avg_congestion=("congestion_comp", "mean"),
            max_congestion=("congestion_comp", "max"),
            avg_loss=("loss_comp", "mean"),
            avg_energy=("energy_comp", "mean"),
            volatility=("total_lmp", "std"),
        ).reset_index()

        records = []
        for _, row in daily.iterrows():
            records.append({
                "date": str(row["date"]),
                "avg_lmp": round(float(row["avg_lmp"]), 2),
                "max_lmp": round(float(row["max_lmp"]), 2),
                "min_lmp": round(float(row["min_lmp"]), 2),
                "avg_congestion": round(float(row["avg_congestion"]), 2),
                "max_congestion": round(float(row["max_congestion"]), 2),
                "avg_loss": round(float(row["avg_loss"]), 2),
                "avg_energy": round(float(row["avg_energy"]), 2),
                "volatility": round(float(row["volatility"]), 2),
                "is_spike": bool(row["max_lmp"] > row["avg_lmp"] * 2.5),
            })
        return records

    def compute_wholesale_exposure(
        self,
        usage_kwh: float,
        zone: str = "PSEG",
        days: int = 30
    ) -> dict:
        """Calculate customer wholesale market cost exposure."""
        df = self.get_hourly_lmps(zone, days)
        if df.empty:
            return {"error": "No LMP data available"}

        avg_lmp = float(df["total_lmp"].mean())
        max_lmp = float(df["total_lmp"].max())
        avg_congestion = float(df["congestion_comp"].mean())
        volatility = float(df["total_lmp"].std())

        # Convert $/MWh to $/kWh
        avg_rate_kwh = avg_lmp / 1000.0
        peak_rate_kwh = max_lmp / 1000.0

        # Peak hours = hours 14-19 (2PM-7PM), off-peak = rest
        df["hour"] = df["timestamp"].dt.hour
        peak_mask = df["hour"].between(14, 19)
        peak_avg = float(df.loc[peak_mask, "total_lmp"].mean()) if peak_mask.any() else avg_lmp
        offpeak_avg = float(df.loc[~peak_mask, "total_lmp"].mean()) if (~peak_mask).any() else avg_lmp

        monthly_wholesale_cost = usage_kwh * avg_rate_kwh
        peak_exposure = usage_kwh * 0.4 * (peak_avg / 1000.0)  # 40% usage during peak

        return {
            "avg_lmp_mwh": round(avg_lmp, 2),
            "max_lmp_mwh": round(max_lmp, 2),
            "avg_congestion_mwh": round(avg_congestion, 2),
            "volatility_mwh": round(volatility, 2),
            "peak_avg_lmp_mwh": round(peak_avg, 2),
            "offpeak_avg_lmp_mwh": round(offpeak_avg, 2),
            "peak_offpeak_spread": round(peak_avg - offpeak_avg, 2),
            "wholesale_cost_estimate": round(monthly_wholesale_cost, 2),
            "peak_exposure_cost": round(peak_exposure, 2),
            "usage_kwh": usage_kwh,
            "zone": zone,
        }

    def compute_load_shifting_savings(
        self,
        usage_kwh: float,
        shift_pct: float = 0.15,
        zone: str = "PSEG",
        days: int = 30
    ) -> dict:
        """Estimate savings from shifting load from peak to off-peak hours."""
        df = self.get_hourly_lmps(zone, days)
        if df.empty:
            return {"error": "No LMP data available"}

        df["hour"] = df["timestamp"].dt.hour
        peak_mask = df["hour"].between(14, 19)

        peak_avg = float(df.loc[peak_mask, "total_lmp"].mean()) if peak_mask.any() else 50.0
        offpeak_avg = float(df.loc[~peak_mask, "total_lmp"].mean()) if (~peak_mask).any() else 35.0

        spread_mwh = peak_avg - offpeak_avg
        spread_kwh = spread_mwh / 1000.0

        shifted_kwh = usage_kwh * shift_pct
        monthly_savings = shifted_kwh * spread_kwh
        annual_savings = monthly_savings * 12

        return {
            "peak_avg_lmp": round(peak_avg, 2),
            "offpeak_avg_lmp": round(offpeak_avg, 2),
            "spread_per_mwh": round(spread_mwh, 2),
            "shift_pct": shift_pct,
            "shifted_kwh": round(shifted_kwh, 1),
            "monthly_savings": round(monthly_savings, 2),
            "annual_savings": round(annual_savings, 2),
            "zone": zone,
        }

    def get_kpis(self, zone: str = "PSEG", days: int = 30) -> dict:
        """Return top-level PJM market KPIs."""
        df = self.get_hourly_lmps(zone, days)
        if df.empty:
            return {
                "avg_lmp": 0, "max_lmp": 0, "congestion_cost": 0,
                "peak_exposure": 0, "volatility": 0, "zone": zone,
            }

        spike_threshold = float(df["total_lmp"].mean()) + 2 * float(df["total_lmp"].std())
        spike_count = int((df["total_lmp"] > spike_threshold).sum())

        return {
            "avg_lmp": round(float(df["total_lmp"].mean()), 2),
            "max_lmp": round(float(df["total_lmp"].max()), 2),
            "congestion_cost": round(float(df["congestion_comp"].mean()), 2),
            "peak_exposure": round(float(df["total_lmp"].quantile(0.95)), 2),
            "volatility": round(float(df["total_lmp"].std()), 2),
            "spike_count": spike_count,
            "zone": zone,
        }


# Module-level singleton
pjm_service = PjmService()
