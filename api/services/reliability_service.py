"""
Utility Reliability Analytics Service.

Provides SAIDI/SAIFI/CAIDI reliability metrics, trend analysis,
and regional comparisons for distribution network reliability.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ReliabilityService:
    """Deterministic utility reliability analytics engine."""

    def __init__(self, engine=None):
        self._engine = engine

    def _get_engine(self):
        if self._engine is None:
            from database.connection import get_sync_engine
            self._engine = get_sync_engine()
        return self._engine

    # ── Core Metrics ──────────────────────────────────────────────────────

    def get_reliability_metrics(
        self,
        state: str = "NJ",
        utility_name: str = None,
        year: int = None,
    ) -> list[dict]:
        """Get SAIDI/SAIFI/CAIDI reliability metrics."""
        engine = self._get_engine()

        conditions = ["state = :state"]
        params: dict = {"state": state.upper()}

        if utility_name:
            conditions.append("utility_name LIKE :util_name")
            params["util_name"] = f"%{utility_name}%"
        if year:
            conditions.append("year = :year")
            params["year"] = year

        where = " AND ".join(conditions)

        query = text(f"""
            SELECT year, utility_id, utility_name, state,
                   saidi, saifi, caidi,
                   customers_affected, total_customers
            FROM utility_reliability
            WHERE {where}
            ORDER BY year DESC, utility_name
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query reliability metrics: {e}")
            return []

        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            saidi = float(row["saidi"]) if pd.notna(row["saidi"]) else 0
            saifi = float(row["saifi"]) if pd.notna(row["saifi"]) else 0
            caidi = float(row["caidi"]) if pd.notna(row["caidi"]) else 0
            total_cust = int(row["total_customers"]) if pd.notna(row["total_customers"]) else 0
            affected = int(row["customers_affected"]) if pd.notna(row["customers_affected"]) else 0

            # Reliability rating (IEEE benchmarks: SAIDI < 90 = good, < 200 = average, > 200 = poor)
            if saidi < 90:
                rating = "excellent"
            elif saidi < 150:
                rating = "good"
            elif saidi < 250:
                rating = "average"
            else:
                rating = "below_average"

            records.append({
                "year": int(row["year"]),
                "utility_id": int(row["utility_id"]),
                "utility_name": str(row["utility_name"]),
                "state": str(row["state"]),
                "saidi_minutes": round(saidi, 1),
                "saifi": round(saifi, 2),
                "caidi_minutes": round(caidi, 1),
                "customers_affected": affected,
                "total_customers": total_cust,
                "outage_hours_per_year": round(saidi / 60, 2),
                "reliability_rating": rating,
            })

        return records

    # ── Trend Analysis ────────────────────────────────────────────────────

    def get_reliability_trend(
        self,
        utility_name: str = None,
        state: str = "NJ",
    ) -> list[dict]:
        """Get SAIDI/SAIFI trends over years for a utility or state average."""
        engine = self._get_engine()

        params: dict = {"state": state.upper()}

        if utility_name:
            query = text("""
                SELECT year, utility_name,
                       AVG(saidi) as avg_saidi, AVG(saifi) as avg_saifi, AVG(caidi) as avg_caidi,
                       SUM(total_customers) as total_customers
                FROM utility_reliability
                WHERE state = :state AND utility_name LIKE :util_name
                GROUP BY year, utility_name
                ORDER BY year
            """)
            params["util_name"] = f"%{utility_name}%"
        else:
            # State average
            query = text("""
                SELECT year, 'State Average' as utility_name,
                       AVG(saidi) as avg_saidi, AVG(saifi) as avg_saifi, AVG(caidi) as avg_caidi,
                       SUM(total_customers) as total_customers
                FROM utility_reliability
                WHERE state = :state
                GROUP BY year
                ORDER BY year
            """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query reliability trend: {e}")
            return []

        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            records.append({
                "year": int(row["year"]),
                "utility_name": str(row["utility_name"]),
                "avg_saidi_minutes": round(float(row["avg_saidi"]) if pd.notna(row["avg_saidi"]) else 0, 1),
                "avg_saifi": round(float(row["avg_saifi"]) if pd.notna(row["avg_saifi"]) else 0, 2),
                "avg_caidi_minutes": round(float(row["avg_caidi"]) if pd.notna(row["avg_caidi"]) else 0, 1),
                "total_customers": int(row["total_customers"]) if pd.notna(row["total_customers"]) else 0,
            })

        return records

    # ── Regional Comparison ───────────────────────────────────────────────

    def compare_utilities(self, state: str = "NJ", year: int = None) -> list[dict]:
        """Compare SAIDI/SAIFI across utilities in a state for a given year."""
        engine = self._get_engine()

        params: dict = {"state": state.upper()}
        year_filter = ""
        if year:
            year_filter = "AND year = :year"
            params["year"] = year
        else:
            year_filter = "AND year = (SELECT MAX(year) FROM utility_reliability WHERE state = :state2)"
            params["state2"] = state.upper()

        query = text(f"""
            SELECT year, utility_id, utility_name, state,
                   saidi, saifi, caidi, total_customers
            FROM utility_reliability
            WHERE state = :state {year_filter}
            ORDER BY saidi ASC
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to compare utilities: {e}")
            return []

        if df.empty:
            return []

        # State average
        avg_saidi = float(df["saidi"].mean())
        avg_saifi = float(df["saifi"].mean())

        records = []
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            saidi = float(row["saidi"]) if pd.notna(row["saidi"]) else 0
            saifi = float(row["saifi"]) if pd.notna(row["saifi"]) else 0

            records.append({
                "rank": rank,
                "year": int(row["year"]),
                "utility_id": int(row["utility_id"]),
                "utility_name": str(row["utility_name"]),
                "saidi_minutes": round(saidi, 1),
                "saifi": round(saifi, 2),
                "caidi_minutes": round(float(row["caidi"]) if pd.notna(row["caidi"]) else 0, 1),
                "total_customers": int(row["total_customers"]) if pd.notna(row["total_customers"]) else 0,
                "vs_state_saidi_pct": round((saidi - avg_saidi) / avg_saidi * 100 if avg_saidi > 0 else 0, 1),
                "vs_state_saifi_pct": round((saifi - avg_saifi) / avg_saifi * 100 if avg_saifi > 0 else 0, 1),
            })

        return records

    # ── KPIs ──────────────────────────────────────────────────────────────

    def get_kpis(self, state: str = "NJ") -> dict:
        """Top-level reliability KPIs for the state."""
        engine = self._get_engine()

        query = text("""
            SELECT AVG(saidi) as avg_saidi, AVG(saifi) as avg_saifi, AVG(caidi) as avg_caidi,
                   MIN(saidi) as best_saidi, MAX(saidi) as worst_saidi,
                   SUM(total_customers) as total_customers, MAX(year) as latest_year
            FROM utility_reliability
            WHERE state = :state AND year = (SELECT MAX(year) FROM utility_reliability WHERE state = :state2)
        """)

        try:
            df = pd.read_sql(query, con=engine, params={"state": state.upper(), "state2": state.upper()})
        except Exception as e:
            logger.warning(f"Failed to get reliability KPIs: {e}")
            return {}

        if df.empty or pd.isna(df.iloc[0]["avg_saidi"]):
            return {"avg_saidi": 0, "avg_saifi": 0, "total_customers": 0}

        row = df.iloc[0]
        return {
            "avg_saidi_minutes": round(float(row["avg_saidi"]), 1),
            "avg_saifi": round(float(row["avg_saifi"]), 2),
            "avg_caidi_minutes": round(float(row["avg_caidi"]), 1),
            "best_saidi_minutes": round(float(row["best_saidi"]), 1),
            "worst_saidi_minutes": round(float(row["worst_saidi"]), 1),
            "total_customers": int(row["total_customers"]) if pd.notna(row["total_customers"]) else 0,
            "latest_year": int(row["latest_year"]) if pd.notna(row["latest_year"]) else 0,
            "state": state.upper(),
        }


# Module-level singleton
reliability_service = ReliabilityService()
