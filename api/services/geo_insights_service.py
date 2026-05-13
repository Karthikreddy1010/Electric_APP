"""
Geo Insights Service — generates monthly state-level data from yearly benchmarks
and provides NJ-specific detail from billing data.

Architecture:
  - build_monthly_state_data()  — interpolates yearly benchmark into monthly
  - get_map_data()              — returns all states for a given month
  - get_trend_data()            — returns time series for a specific state
  - get_detail_data()           — returns NJ component breakdown for a month
"""
from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Seasonal factors: peak in summer (Jul/Aug), trough in spring/fall
_SEASONAL = {
    1: 1.08, 2: 1.05, 3: 0.95, 4: 0.90, 5: 0.88, 6: 1.02,
    7: 1.15, 8: 1.18, 9: 1.05, 10: 0.92, 11: 0.90, 12: 1.02,
}


def build_monthly_state_data(benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand yearly state benchmark data into monthly granularity
    with seasonal variation. Cached at startup.
    """
    records = []
    for _, row in benchmark_df.iterrows():
        state = row["state"]
        year = int(row["year"])
        base_rate = float(row["avg_rate"])
        base_bill = float(row["avg_bill"])

        for month in range(1, 13):
            factor = _SEASONAL[month]
            # Slight deterministic variation per state+month
            seed = hash(f"{state}-{year}-{month}") % 1000
            jitter = 1.0 + (seed - 500) / 10000  # +/- 5%

            rate = round(base_rate * factor * jitter, 5)
            bill = round(base_bill * factor * jitter, 2)
            kwh = round(bill / rate, 1) if rate > 0 else 750.0

            records.append({
                "state": state,
                "year": year,
                "month": month,
                "month_str": f"{year}-{month:02d}",
                "avg_rate": rate,
                "avg_bill": bill,
                "usage_kwh": kwh,
            })

    df = pd.DataFrame(records)
    df = df.sort_values(["state", "year", "month"]).reset_index(drop=True)

    # Calculate YoY change
    df["yoy_change"] = df.groupby("state")["avg_bill"].pct_change(12) * 100
    df["yoy_change"] = df["yoy_change"].round(1)

    return df


def get_map_data(
    monthly_df: pd.DataFrame,
    month: str,
    data_type: str = "bill",
    state_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return all states for a given month (YYYY-MM format).
    data_type: 'bill' or 'price'
    """
    mask = monthly_df["month_str"] == month
    if state_filter:
        mask = mask & (monthly_df["state"] == state_filter.upper())

    subset = monthly_df[mask].copy()
    if subset.empty:
        return []

    results = []
    for _, row in subset.iterrows():
        value = row["avg_bill"] if data_type == "bill" else row["avg_rate"]
        results.append({
            "state": row["state"],
            "region": row["state"],
            "avg_bill": round(row["avg_bill"], 2),
            "avg_price": round(row["avg_rate"], 5),
            "usage_kwh": round(row["usage_kwh"], 1),
            "yoy_change": row["yoy_change"] if pd.notna(row["yoy_change"]) else None,
            "value": round(float(value), 4),
            "month": month,
        })

    return results


def get_trend_data(
    monthly_df: pd.DataFrame,
    state: str,
    data_type: str = "bill",
) -> dict[str, Any]:
    """
    Return monthly time series for a specific state.
    """
    mask = monthly_df["state"] == state.upper()
    subset = monthly_df[mask].sort_values("month_str")

    if subset.empty:
        return {"state": state, "months": [], "values": [], "bills": [], "rates": []}

    bills = subset["avg_bill"].round(2).tolist()
    rates = subset["avg_rate"].round(5).tolist()
    values = bills if data_type == "bill" else rates

    # Growth metric
    first_val = bills[0] if bills[0] > 0 else 1
    last_val = bills[-1]
    total_growth = round(((last_val - first_val) / first_val) * 100, 1)

    return {
        "state": state.upper(),
        "months": subset["month_str"].tolist(),
        "values": values,
        "bills": bills,
        "rates": rates,
        "usage": subset["usage_kwh"].round(1).tolist(),
        "total_growth_pct": total_growth,
        "period": f"{subset['month_str'].iloc[0]} to {subset['month_str'].iloc[-1]}",
    }


def get_detail_data(
    billing_df: pd.DataFrame | None,
    benchmark_monthly: pd.DataFrame,
    state: str,
    month: str,
) -> dict[str, Any]:
    """
    Return detailed breakdown for a state/month.
    Uses actual billing data for NJ, synthetic for others.
    """
    # State-level summary
    mask = (benchmark_monthly["state"] == state.upper()) & (benchmark_monthly["month_str"] == month)
    state_data = benchmark_monthly[mask]
    if state_data.empty:
        return {"error": f"No data for {state} in {month}"}

    row = state_data.iloc[0]

    # National average for comparison
    nat_mask = benchmark_monthly["month_str"] == month
    nat_avg_bill = benchmark_monthly[nat_mask]["avg_bill"].mean()
    nat_avg_rate = benchmark_monthly[nat_mask]["avg_rate"].mean()

    vs_national_bill = round(((row["avg_bill"] - nat_avg_bill) / nat_avg_bill) * 100, 1) if nat_avg_bill else 0
    vs_national_rate = round(((row["avg_rate"] - nat_avg_rate) / nat_avg_rate) * 100, 1) if nat_avg_rate else 0

    result = {
        "state": state.upper(),
        "month": month,
        "avg_bill": round(row["avg_bill"], 2),
        "avg_rate": round(row["avg_rate"], 5),
        "usage_kwh": round(row["usage_kwh"], 1),
        "effective_rate": round(row["avg_rate"], 5),
        "yoy_change": row["yoy_change"] if pd.notna(row["yoy_change"]) else None,
        "vs_national_bill_pct": vs_national_bill,
        "vs_national_rate_pct": vs_national_rate,
        "national_avg_bill": round(nat_avg_bill, 2),
        "national_avg_rate": round(nat_avg_rate, 5),
        "components": None,
    }

    # NJ: use actual billing data for component breakdown
    if state.upper() == "NJ" and billing_df is not None:
        year, mo = month.split("-")
        bill_mask = (billing_df["date"].dt.year == int(year)) & (billing_df["date"].dt.month == int(mo))
        nj_rows = billing_df[bill_mask]
        if not nj_rows.empty:
            nj = nj_rows.iloc[0]
            result["components"] = {
                "bgs": round(float(nj.get("bgs_cost", 0)), 2),
                "transmission": round(float(nj.get("transmission_cost", 0)), 2),
                "distribution": round(float(nj.get("distribution_cost", 0)), 2),
                "sbc": round(float(nj.get("sbc_cost", 0)), 2),
                "nug": round(float(nj.get("nug_cost", 0)), 2),
                "tax": round(float(nj.get("sales_tax", 0)), 2),
            }
            result["usage_kwh"] = round(float(nj["usage_kwh"]), 1)
            result["avg_bill"] = round(float(nj["total_bill"]), 2)
            result["effective_rate"] = round(float(nj["total_bill"]) / float(nj["usage_kwh"]), 5)
    else:
        # Synthetic breakdown for non-NJ states
        bill = row["avg_bill"]
        result["components"] = {
            "generation": round(bill * 0.45, 2),
            "transmission": round(bill * 0.12, 2),
            "distribution": round(bill * 0.28, 2),
            "sbc": round(bill * 0.04, 2),
            "tax": round(bill * 0.06, 2),
            "other": round(bill * 0.05, 2),
        }

    return result


def get_available_months(monthly_df: pd.DataFrame) -> list[str]:
    """Return sorted list of all available YYYY-MM strings."""
    return sorted(monthly_df["month_str"].unique().tolist())


def get_available_states(monthly_df: pd.DataFrame) -> list[str]:
    """Return sorted list of all available state codes."""
    return sorted(monthly_df["state"].unique().tolist())
