"""
tests/test_analytics.py — Unit tests for the modular Analytics Engine.
"""
import pytest
from backend.schemas.parsed_bill import ParsedBill
from backend.analytics.engine import analytics_engine
from backend.analytics.tariff import calculate_tariff_details
from backend.analytics.components import calculate_fixed_charges, calculate_variable_charges, calculate_taxes
from backend.analytics.history import calculate_historical_comparison
from backend.analytics.weather import calculate_weather_normalization
from backend.analytics.trends import calculate_trend_analysis
from backend.analytics.anomalies import calculate_anomalies
from backend.analytics.savings import calculate_savings_estimation
from backend.analytics.recommendations import calculate_recommendations
from backend.analytics.forecasting_inputs import calculate_forecast_inputs
from backend.analytics.validation import validate_analytics_result


@pytest.fixture
def sample_parsed_bill():
    return ParsedBill(
        bill_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        customer_id="TEST-CUSTOMER-123",
        utility="PSE&G",
        zip_code="07102",
        rate_schedule="RS",
        bill_date="2026-06-30",
        billing_period="2026-06-01 to 2026-06-30",
        days=30,
        usage_kwh=750.0,
        monthly_service_charge=8.24,
        delivery_charge=41.25,
        supply_charge=81.00,
        tax=8.41,
        total_bill=138.90,
        effective_rate=0.1852,
    )


def test_tariff_calculations(sample_parsed_bill):
    tariff = calculate_tariff_details(sample_parsed_bill)
    assert tariff.utility_name == "PSE&G"
    assert tariff.bgs_rate == 0.1052
    assert tariff.distribution_rate == 0.0422


def test_component_fixed_variable_taxes(sample_parsed_bill):
    tariff = calculate_tariff_details(sample_parsed_bill)
    fixed = calculate_fixed_charges(sample_parsed_bill)
    var = calculate_variable_charges(sample_parsed_bill, tariff)
    taxes = calculate_taxes(fixed, var, sample_parsed_bill.tax)

    assert fixed.total_fixed_charges == 8.24
    assert var.usage_kwh == 750.0
    assert taxes.billed_tax == 8.41


def test_historical_comparison(sample_parsed_bill):
    hist = calculate_historical_comparison(sample_parsed_bill)
    assert hist.month_over_month.pct_change_kwh > 0
    assert hist.year_over_year.pct_change_kwh > 0


def test_weather_normalization(sample_parsed_bill):
    weather = calculate_weather_normalization(sample_parsed_bill)
    assert weather.month == 6
    assert weather.cdd == 180.0
    assert weather.weather_driven_kwh > 0


def test_trend_analysis(sample_parsed_bill):
    trend = calculate_trend_analysis(sample_parsed_bill)
    assert trend.moving_avg_3m_kwh > 0
    assert trend.direction in ["UPWARD", "DOWNWARD", "STABLE"]


def test_anomaly_detection(sample_parsed_bill):
    anomaly = calculate_anomalies(sample_parsed_bill)
    assert isinstance(anomaly.has_anomalies, bool)


def test_savings_estimation(sample_parsed_bill):
    savings = calculate_savings_estimation(sample_parsed_bill)
    assert savings.total_potential_annual_savings > 0
    assert len(savings.opportunities) >= 3


def test_recommendations_ranking(sample_parsed_bill):
    savings = calculate_savings_estimation(sample_parsed_bill)
    recs = calculate_recommendations(sample_parsed_bill, savings)
    assert len(recs) > 0
    assert recs[0].rank == 1
    assert recs[0].score >= recs[-1].score


def test_forecast_inputs(sample_parsed_bill):
    fc_inputs = calculate_forecast_inputs(sample_parsed_bill)
    assert fc_inputs.baseline_daily_kwh == 25.0
    assert fc_inputs.base_annual_kwh_projection > 0


def test_full_analytics_engine_orchestration(sample_parsed_bill):
    result = analytics_engine.calculate(sample_parsed_bill)
    assert result.bill_hash == sample_parsed_bill.bill_hash
    assert result.analytics_version == "1.0.0"
    assert result.tariff_version == "2026.07"
    assert result.component_breakdown.total_bill > 0

    # Verify accounting identity check passed
    val_res = validate_analytics_result(result)
    assert val_res["passed"] is True
