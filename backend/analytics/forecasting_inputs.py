"""
backend.analytics.forecasting_inputs — Pure load feature extraction for downstream forecast models.

Generates normalized baseline metrics, load factors, and seasonal indicators.
Note: Prophet, SARIMA, and ML forecast model training is strictly isolated to Phase 2.
"""
from __future__ import annotations

from datetime import datetime
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import ForecastInputsSchema
from backend.config.constants import SEASONAL_MULTIPLIERS


def calculate_forecast_inputs(parsed_bill: ParsedBill) -> ForecastInputsSchema:
    """Extract deterministic baseline features and seasonal indicators."""
    days = parsed_bill.days if parsed_bill.days > 0 else 30
    baseline_daily_kwh = (
        parsed_bill.average_daily_usage
        if parsed_bill.average_daily_usage > 0
        else round(parsed_bill.usage_kwh / days, 2)
    )

    month = 6
    try:
        dt = datetime.strptime(parsed_bill.bill_date, "%Y-%m-%d")
        month = dt.month
    except Exception:
        pass

    seasonal_factor = SEASONAL_MULTIPLIERS.get(month, 1.0)
    annual_projection = round(baseline_daily_kwh * 365 * seasonal_factor, 1)

    return ForecastInputsSchema(
        baseline_daily_kwh=baseline_daily_kwh,
        peak_demand_ratio=1.15,
        seasonal_factor=seasonal_factor,
        weather_sensitivity_factor=0.85,
        base_annual_kwh_projection=annual_projection,
        trend_coefficient=0.01,
    )
