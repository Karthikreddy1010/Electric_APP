"""
backend.analytics.trends — Trend analysis submodule.

Calculates usage direction, 3-month and 6-month moving averages, usage velocity,
and cost trend slope.
"""
from __future__ import annotations

from typing import List, Optional
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import TrendAnalysisSchema


def calculate_trend_analysis(
    parsed_bill: ParsedBill,
    historical_usage_series: Optional[List[float]] = None,
    historical_cost_series: Optional[List[float]] = None,
) -> TrendAnalysisSchema:
    """Calculate moving averages, trend direction, and velocity."""
    curr_kwh = parsed_bill.usage_kwh
    curr_cost = parsed_bill.total_bill

    # Default historical series if none provided
    usage_series = historical_usage_series or [curr_kwh * 0.90, curr_kwh * 0.95, curr_kwh]
    cost_series = historical_cost_series or [curr_cost * 0.90, curr_cost * 0.95, curr_cost]

    # Moving averages
    m3_avg_kwh = round(sum(usage_series[-3:]) / len(usage_series[-3:]), 2)
    m6_avg_kwh = (
        round(sum(usage_series[-6:]) / len(usage_series[-6:]), 2)
        if len(usage_series) >= 6
        else m3_avg_kwh
    )

    # Velocity (monthly rate of change)
    if len(usage_series) >= 2:
        velocity = round(usage_series[-1] - usage_series[-2], 2)
    else:
        velocity = 0.0

    # Direction classification
    if velocity > 15.0:
        direction = "UPWARD"
    elif velocity < -15.0:
        direction = "DOWNWARD"
    else:
        direction = "STABLE"

    # Cost trend slope
    if len(cost_series) >= 2:
        cost_slope = round(cost_series[-1] - cost_series[-2], 2)
    else:
        cost_slope = 0.0

    return TrendAnalysisSchema(
        direction=direction,
        velocity_kwh_per_month=velocity,
        moving_avg_3m_kwh=m3_avg_kwh,
        moving_avg_6m_kwh=m6_avg_kwh,
        cost_trend_slope=cost_slope,
    )
