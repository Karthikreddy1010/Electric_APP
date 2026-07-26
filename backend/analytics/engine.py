"""
backend.analytics.engine — Deterministic Analytics Engine Orchestrator.

Orchestrates single-responsibility analytics submodules to construct strongly typed,
versioned AnalyticsResult schemas.
The Analytics Engine is the ONLY component permitted to calculate numbers.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional, List
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import AnalyticsResult
from backend.analytics.tariff import calculate_tariff_details
from backend.analytics.components import (
    calculate_fixed_charges,
    calculate_variable_charges,
    calculate_taxes,
    calculate_component_breakdown,
)
from backend.analytics.history import calculate_historical_comparison
from backend.analytics.weather import calculate_weather_normalization, WeatherProvider
from backend.analytics.trends import calculate_trend_analysis
from backend.analytics.anomalies import calculate_anomalies
from backend.analytics.savings import calculate_savings_estimation
from backend.analytics.recommendations import calculate_recommendations
from backend.analytics.forecasting_inputs import calculate_forecast_inputs
from backend.analytics.validation import validate_analytics_result
from backend.utils.exceptions import AnalyticsException

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Deterministic Analytics Engine Orchestrator.
    Constructs AnalyticsResult by executing modular calculation functions.
    """

    def __init__(
        self,
        analytics_version: str = "1.0.0",
        weather_provider: Optional[WeatherProvider] = None,
    ) -> None:
        self.analytics_version = analytics_version
        self.weather_provider = weather_provider

    def calculate(
        self,
        parsed_bill: ParsedBill,
        rate_overrides: Optional[Dict[str, float]] = None,
        usage_multiplier: float = 1.0,
        weather_provider_override: Optional[WeatherProvider] = None,
        prior_period_data: Optional[Dict[str, float]] = None,
        prior_year_data: Optional[Dict[str, float]] = None,
    ) -> AnalyticsResult:
        """
        Execute deterministic analytics calculation pipeline.
        
        Args:
            parsed_bill: Validated ParsedBill input schema.
            rate_overrides: Optional tariff rate modification overrides.
            usage_multiplier: Volumetric usage scaling multiplier.
            weather_provider_override: Custom weather provider instance.
            prior_period_data: Prior month usage/cost data dict.
            prior_year_data: Prior year same month data dict.
            
        Returns:
            Strongly typed, versioned AnalyticsResult schema payload.
        """
        start_time = time.perf_counter()
        latencies: Dict[str, float] = {}

        if not parsed_bill:
            raise AnalyticsException("Cannot run analytics on null ParsedBill payload.")

        # Apply usage multiplier if non-default
        if usage_multiplier != 1.0 and usage_multiplier > 0:
            parsed_bill.usage_kwh = round(parsed_bill.usage_kwh * usage_multiplier, 2)
            parsed_bill.total_bill = round(parsed_bill.total_bill * usage_multiplier, 2)

        try:
            # 1. Tariff Calculations
            t0 = time.perf_counter()
            tariff_res = calculate_tariff_details(parsed_bill, rate_overrides=rate_overrides)
            latencies["tariff_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 2. Fixed Charges
            t0 = time.perf_counter()
            fixed_res = calculate_fixed_charges(parsed_bill)
            latencies["fixed_charges_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 3. Variable Charges
            t0 = time.perf_counter()
            var_res = calculate_variable_charges(parsed_bill, tariff_res)
            latencies["variable_charges_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 4. Taxes
            t0 = time.perf_counter()
            taxes_res = calculate_taxes(fixed_res, var_res, parsed_bill.tax)
            latencies["taxes_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 5. Component Breakdown
            t0 = time.perf_counter()
            breakdown_res = calculate_component_breakdown(
                fixed_res, var_res, taxes_res, tariff_res
            )
            latencies["breakdown_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 6. Historical Comparison (MoM & YoY)
            t0 = time.perf_counter()
            hist_res = calculate_historical_comparison(
                parsed_bill, prior_period_data, prior_year_data
            )
            latencies["historical_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 7. Weather Normalization
            t0 = time.perf_counter()
            w_provider = weather_provider_override or self.weather_provider
            weather_res = calculate_weather_normalization(parsed_bill, weather_provider=w_provider)
            latencies["weather_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 8. Trend Analysis
            t0 = time.perf_counter()
            trend_res = calculate_trend_analysis(parsed_bill)
            latencies["trends_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 9. Anomaly Detection
            t0 = time.perf_counter()
            anomaly_res = calculate_anomalies(parsed_bill)
            latencies["anomalies_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 10. Savings Estimation
            t0 = time.perf_counter()
            savings_res = calculate_savings_estimation(parsed_bill)
            latencies["savings_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 11. Recommendations
            t0 = time.perf_counter()
            recs_res = calculate_recommendations(parsed_bill, savings_res)
            latencies["recommendations_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # 12. Forecast Inputs
            t0 = time.perf_counter()
            forecast_inputs_res = calculate_forecast_inputs(parsed_bill)
            latencies["forecast_inputs_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            latencies["total_engine_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

            # Construct AnalyticsResult schema
            analytics_result = AnalyticsResult(
                bill_hash=parsed_bill.bill_hash,
                customer_id=parsed_bill.customer_id,
                utility_name=parsed_bill.utility,
                zip_code=parsed_bill.zip_code,
                rate_schedule=parsed_bill.rate_schedule,
                analytics_version=self.analytics_version,
                ocr_version="1.0.0",
                parser_version=parsed_bill.parser_version,
                tariff_version="2026.07",
                weather_version="2026.07",
                dataset_version="2026.07",
                processing_time_ms=latencies,
                confidence_score=parsed_bill.parser_confidence,
                component_breakdown=breakdown_res,
                tariff_calculations=tariff_res,
                fixed_charges=fixed_res,
                variable_charges=var_res,
                taxes=taxes_res,
                historical_comparison=hist_res,
                month_over_month=hist_res.month_over_month,
                year_over_year=hist_res.year_over_year,
                weather_normalization=weather_res,
                trend_analysis=trend_res,
                anomaly_detection=anomaly_res,
                savings_estimation=savings_res,
                recommendations=recs_res,
                forecast_inputs=forecast_inputs_res,
            )

            # 13. Audit & Validate Result
            validate_analytics_result(analytics_result)
            return analytics_result

        except Exception as e:
            logger.error(f"Deterministic Analytics Engine execution failed: {e}", exc_info=True)
            if isinstance(e, AnalyticsException):
                raise
            raise AnalyticsException(f"Analytics engine calculation error: {e}", cause=e)


# Singleton instance
analytics_engine = AnalyticsEngine()
