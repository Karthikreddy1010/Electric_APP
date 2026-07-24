"""
BLS CPI Inflation Analytics Service.

Provides inflation-adjusted bill conversions, purchasing power analysis,
and real vs nominal cost trend decomposition.

All calculations are deterministic — LLMs only explain these outputs.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class InflationService:
    """Deterministic CPI inflation analytics engine."""

    def __init__(self, engine=None):
        self._engine = engine
        self._cpi_cache: Optional[pd.DataFrame] = None

    def _get_engine(self):
        if self._engine is None:
            from database.connection import get_sync_engine
            self._engine = get_sync_engine()
        return self._engine

    def _load_cpi(self) -> pd.DataFrame:
        """Load CPI data from database with caching."""
        if self._cpi_cache is not None and not self._cpi_cache.empty:
            return self._cpi_cache

        engine = self._get_engine()
        try:
            df = pd.read_sql("SELECT * FROM cpi_index ORDER BY year, month", con=engine)
            if not df.empty:
                self._cpi_cache = df
                return df
        except Exception as e:
            logger.warning(f"Failed to load CPI from DB: {e}")

        # Fallback: read CSV directly
        try:
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent
            csv_path = project_root / "data" / "raw" / "cpi_monthly.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                self._cpi_cache = df
                return df
        except Exception as e:
            logger.warning(f"Failed to load CPI from CSV fallback: {e}")

        return pd.DataFrame()

    # ── Core Lookups ──────────────────────────────────────────────────────

    def get_cpi_for_month(self, year: int, month: int) -> Optional[float]:
        """Get CPI value for a specific year/month."""
        df = self._load_cpi()
        if df.empty:
            return None
        match = df[(df["year"] == year) & (df["month"] == month)]
        if match.empty:
            return None
        return float(match.iloc[0]["cpi"])

    def get_deflator(self, year: int, month: int, base_year: int = None, base_month: int = None) -> float:
        """Calculate CPI deflator ratio relative to a base period."""
        df = self._load_cpi()
        if df.empty:
            return 1.0

        current_cpi = self.get_cpi_for_month(year, month)
        if current_cpi is None:
            return 1.0

        if base_year is None or base_month is None:
            # Use latest CPI as base
            latest = df.sort_values(["year", "month"]).iloc[-1]
            base_cpi = float(latest["cpi"])
        else:
            base_cpi_val = self.get_cpi_for_month(base_year, base_month)
            base_cpi = base_cpi_val if base_cpi_val else current_cpi

        return current_cpi / base_cpi if base_cpi > 0 else 1.0

    # ── Bill Adjustments ──────────────────────────────────────────────────

    def adjust_bill_for_inflation(self, nominal_bill: float, bill_year: int, bill_month: int) -> dict:
        """Convert a nominal bill to real (inflation-adjusted) dollars."""
        df = self._load_cpi()
        if df.empty:
            return {
                "nominal_bill": round(nominal_bill, 2),
                "real_bill": round(nominal_bill, 2),
                "deflator": 1.0,
                "inflation_adjustment": 0.0,
            }

        latest = df.sort_values(["year", "month"]).iloc[-1]
        base_cpi = float(latest["cpi"])

        bill_cpi = self.get_cpi_for_month(bill_year, bill_month)
        if bill_cpi is None:
            bill_cpi = base_cpi

        deflator = base_cpi / bill_cpi if bill_cpi > 0 else 1.0
        real_bill = nominal_bill * deflator
        adjustment = real_bill - nominal_bill

        return {
            "nominal_bill": round(nominal_bill, 2),
            "real_bill": round(real_bill, 2),
            "deflator": round(deflator, 4),
            "inflation_adjustment": round(adjustment, 2),
            "bill_year": bill_year,
            "bill_month": bill_month,
            "base_year": int(latest["year"]),
            "base_month": int(latest["month"]),
        }

    def adjust_bill_series(self, bills: list[dict]) -> list[dict]:
        """Adjust a time-series of bills for inflation.
        
        Each bill dict must have: total_bill, year, month.
        Returns list with added real_bill, deflator, inflation_pct fields.
        """
        df = self._load_cpi()
        if df.empty:
            return bills

        latest = df.sort_values(["year", "month"]).iloc[-1]
        base_cpi = float(latest["cpi"])

        adjusted = []
        for bill in bills:
            yr = int(bill.get("year", 2024))
            mo = int(bill.get("month", 1))
            nominal = float(bill.get("total_bill", 0))

            bill_cpi = self.get_cpi_for_month(yr, mo)
            if bill_cpi is None:
                bill_cpi = base_cpi

            deflator = base_cpi / bill_cpi if bill_cpi > 0 else 1.0
            real_bill = nominal * deflator

            entry = dict(bill)
            entry["real_bill"] = round(real_bill, 2)
            entry["deflator"] = round(deflator, 4)
            entry["inflation_pct"] = round((deflator - 1.0) * 100, 2)
            adjusted.append(entry)

        return adjusted

    # ── Trend Analytics ───────────────────────────────────────────────────

    def get_inflation_trend(self) -> list[dict]:
        """Return monthly CPI trend with year-over-year inflation rates."""
        df = self._load_cpi()
        if df.empty:
            return []

        df = df.sort_values(["year", "month"]).reset_index(drop=True)
        records = []
        for i, row in df.iterrows():
            yr = int(row["year"])
            mo = int(row["month"])
            cpi_val = float(row["cpi"])

            # YoY inflation
            prev = df[(df["year"] == yr - 1) & (df["month"] == mo)]
            yoy = 0.0
            if not prev.empty:
                prev_cpi = float(prev.iloc[0]["cpi"])
                yoy = ((cpi_val - prev_cpi) / prev_cpi * 100) if prev_cpi > 0 else 0.0

            records.append({
                "year": yr,
                "month": mo,
                "period": f"{yr}-{mo:02d}",
                "cpi": round(cpi_val, 2),
                "yoy_inflation_pct": round(yoy, 2),
            })

        return records

    def get_kpis(self) -> dict:
        """Return inflation KPIs: current rate, cumulative, purchasing power."""
        df = self._load_cpi()
        if df.empty:
            return {"inflation_rate": 0, "cumulative_inflation": 0, "purchasing_power": 1.0}

        df = df.sort_values(["year", "month"]).reset_index(drop=True)
        latest = df.iloc[-1]
        latest_cpi = float(latest["cpi"])
        latest_yr = int(latest["year"])
        latest_mo = int(latest["month"])

        # YoY inflation
        prev = df[(df["year"] == latest_yr - 1) & (df["month"] == latest_mo)]
        yoy_rate = 0.0
        if not prev.empty:
            yoy_rate = (latest_cpi - float(prev.iloc[0]["cpi"])) / float(prev.iloc[0]["cpi"]) * 100

        # Cumulative from first record
        first_cpi = float(df.iloc[0]["cpi"])
        cumulative = (latest_cpi - first_cpi) / first_cpi * 100

        # Purchasing power: $100 in first period = $X today
        purchasing_power = first_cpi / latest_cpi

        return {
            "inflation_rate": round(yoy_rate, 2),
            "cumulative_inflation": round(cumulative, 2),
            "purchasing_power": round(purchasing_power, 4),
            "latest_cpi": round(latest_cpi, 2),
            "period": f"{latest_yr}-{latest_mo:02d}",
        }


# Module-level singleton
inflation_service = InflationService()
