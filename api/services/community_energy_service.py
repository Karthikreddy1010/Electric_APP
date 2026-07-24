"""
Community Energy Analytics Service.

Provides regional energy benchmarking, community rankings,
sector-level consumption history, and municipal comparisons
using DVRPC and NJ DEP community/municipal energy datasets.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CommunityEnergyService:
    """Deterministic community energy analytics engine."""

    def __init__(self, engine=None):
        self._engine = engine

    def _get_engine(self):
        if self._engine is None:
            from database.connection import get_sync_engine
            self._engine = get_sync_engine()
        return self._engine

    # ── Community Rankings ─────────────────────────────────────────────────

    def get_community_rankings(
        self,
        county: str = None,
        year: int = None,
        top_n: int = 20,
    ) -> list[dict]:
        """Rank communities by total electricity consumption."""
        engine = self._get_engine()

        conditions = []
        params: dict = {"limit": top_n}

        if county:
            conditions.append("county = :county")
            params["county"] = county.title()
        if year:
            conditions.append("year = :year")
            params["year"] = year

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT municipality, county, year,
                   total_electricity_kwh, total_natural_gas_therms,
                   residential_electricity, commercial_electricity,
                   industrial_electricity
            FROM community_energy
            {where}
            ORDER BY total_electricity_kwh DESC
            LIMIT :limit
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query community_energy: {e}")
            return []

        if df.empty:
            return []

        records = []
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            total_kwh = float(row["total_electricity_kwh"]) if pd.notna(row["total_electricity_kwh"]) else 0
            res_kwh = float(row["residential_electricity"]) if pd.notna(row.get("residential_electricity")) else 0
            comm_kwh = float(row["commercial_electricity"]) if pd.notna(row.get("commercial_electricity")) else 0
            ind_kwh = float(row["industrial_electricity"]) if pd.notna(row.get("industrial_electricity")) else 0
            gas_therms = float(row["total_natural_gas_therms"]) if pd.notna(row["total_natural_gas_therms"]) else 0

            records.append({
                "rank": rank,
                "municipality": str(row["municipality"]),
                "county": str(row["county"]),
                "year": int(row["year"]),
                "total_electricity_kwh": round(total_kwh, 0),
                "residential_kwh": round(res_kwh, 0),
                "commercial_kwh": round(comm_kwh, 0),
                "industrial_kwh": round(ind_kwh, 0),
                "natural_gas_therms": round(gas_therms, 0),
                "electrification_ratio": round(total_kwh / (total_kwh + gas_therms * 29.3) if (total_kwh + gas_therms * 29.3) > 0 else 0.5, 3),
            })

        return records

    # ── Sector History ────────────────────────────────────────────────────

    def get_sector_history(self, municipality: str = None, county: str = None) -> list[dict]:
        """Return yearly consumption broken down by sector (residential, commercial, industrial)."""
        engine = self._get_engine()

        conditions = []
        params: dict = {}

        if municipality:
            conditions.append("municipality = :municipality")
            params["municipality"] = municipality.title()
        if county:
            conditions.append("county = :county")
            params["county"] = county.title()

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT year,
                   SUM(residential_electricity_kwh) as residential_kwh,
                   SUM(commercial_electricity_kwh) as commercial_kwh,
                   SUM(industrial_electricity_kwh) as industrial_kwh,
                   SUM(total_electricity_kwh) as total_kwh,
                   SUM(total_natural_gas_therms) as total_gas_therms
            FROM community_energy
            {where}
            GROUP BY year
            ORDER BY year
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query sector history: {e}")
            return []

        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            total = float(row["total_kwh"]) if pd.notna(row["total_kwh"]) else 1
            records.append({
                "year": int(row["year"]),
                "residential_kwh": round(float(row["residential_kwh"]) if pd.notna(row["residential_kwh"]) else 0, 0),
                "commercial_kwh": round(float(row["commercial_kwh"]) if pd.notna(row["commercial_kwh"]) else 0, 0),
                "industrial_kwh": round(float(row["industrial_kwh"]) if pd.notna(row["industrial_kwh"]) else 0, 0),
                "total_kwh": round(total, 0),
                "total_gas_therms": round(float(row["total_gas_therms"]) if pd.notna(row["total_gas_therms"]) else 0, 0),
            })

        return records

    # ── Municipal Comparisons ─────────────────────────────────────────────

    def compare_municipalities(
        self,
        municipalities: list[str],
        year: int = None,
    ) -> list[dict]:
        """Compare energy metrics across multiple municipalities."""
        engine = self._get_engine()

        placeholders = ", ".join([f":m{i}" for i in range(len(municipalities))])
        params = {f"m{i}": m.title() for i, m in enumerate(municipalities)}

        year_filter = ""
        if year:
            year_filter = "AND year = :year"
            params["year"] = year

        query = text(f"""
            SELECT municipality, county, year,
                   total_electricity_kwh, total_natural_gas_therms,
                   residential_electricity_kwh, commercial_electricity_kwh,
                   industrial_electricity_kwh
            FROM community_energy
            WHERE municipality IN ({placeholders}) {year_filter}
            ORDER BY municipality, year
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query municipal comparison: {e}")
            return []

        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            total = float(row["total_electricity_kwh"]) if pd.notna(row["total_electricity_kwh"]) else 0
            records.append({
                "municipality": str(row["municipality"]),
                "county": str(row["county"]),
                "year": int(row["year"]),
                "total_electricity_kwh": round(total, 0),
                "natural_gas_therms": round(float(row["total_natural_gas_therms"]) if pd.notna(row["total_natural_gas_therms"]) else 0, 0),
                "residential_kwh": round(float(row["residential_electricity_kwh"]) if pd.notna(row.get("residential_electricity_kwh")) else 0, 0),
                "commercial_kwh": round(float(row["commercial_electricity_kwh"]) if pd.notna(row.get("commercial_electricity_kwh")) else 0, 0),
            })

        return records

    # ── County Benchmark ──────────────────────────────────────────────────

    def get_county_benchmarks(self, year: int = None) -> list[dict]:
        """Get county-level aggregated energy benchmarks."""
        engine = self._get_engine()

        params: dict = {}
        year_filter = ""
        if year:
            year_filter = "WHERE year = :year"
            params["year"] = year

        query = text(f"""
            SELECT county, year,
                   AVG(total_electricity_kwh) as avg_elec_kwh,
                   SUM(total_electricity_kwh) as total_elec_kwh,
                   AVG(total_natural_gas_therms) as avg_gas_therms,
                   COUNT(*) as municipality_count
            FROM community_energy
            {year_filter}
            GROUP BY county, year
            ORDER BY total_elec_kwh DESC
        """)

        try:
            df = pd.read_sql(query, con=engine, params=params)
        except Exception as e:
            logger.warning(f"Failed to query county benchmarks: {e}")
            return []

        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            records.append({
                "county": str(row["county"]),
                "year": int(row["year"]),
                "avg_electricity_kwh": round(float(row["avg_elec_kwh"]) if pd.notna(row["avg_elec_kwh"]) else 0, 0),
                "total_electricity_kwh": round(float(row["total_elec_kwh"]) if pd.notna(row["total_elec_kwh"]) else 0, 0),
                "avg_gas_therms": round(float(row["avg_gas_therms"]) if pd.notna(row["avg_gas_therms"]) else 0, 0),
                "municipality_count": int(row["municipality_count"]),
            })

        return records


# Module-level singleton
community_energy_service = CommunityEnergyService()
