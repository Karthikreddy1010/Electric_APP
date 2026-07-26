"""
backend.schemas.analytics — Strongly typed AnalyticsResult Pydantic schema.

The single source of truth contract for all downstream services and UI endpoints.
Exposes full versioning, execution metadata, and all 14 deterministic calculation outputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ── Sub-schemas for the 14 Deterministic Analytics Dimensions ────────────────

class ComponentItemSchema(BaseModel):
    """Individual bill ledger charge item."""
    name: str = Field(..., description="Component charge name")
    amount: float = Field(0.0, description="Dollar amount ($)")
    percentage: float = Field(0.0, description="Percentage of total bill (%)")
    category: str = Field("delivery", description="fixed | delivery | supply | tax")
    type: str = Field("variable", description="fixed | variable")
    controllable: str = Field("No", description="Yes | No | Partial")
    driver: str = Field("market", description="Primary economic driver")
    rate_per_kwh: Optional[float] = Field(None, description="Volumetric unit rate if variable ($/kWh)")


class ComponentBreakdownSchema(BaseModel):
    """1. Bill Component Breakdown."""
    fixed_total: float = Field(0.0, description="Sum of all fixed monthly charges ($)")
    variable_total: float = Field(0.0, description="Sum of all volumetric usage charges ($)")
    supply_total: float = Field(0.0, description="Total generation/commodity charges ($)")
    delivery_total: float = Field(0.0, description="Total utility distribution & transmission charges ($)")
    taxes_total: float = Field(0.0, description="Total sales & municipal taxes ($)")
    total_bill: float = Field(0.0, description="Total bill amount ($)")
    components: List[ComponentItemSchema] = Field(default_factory=list, description="Itemized component list")


class TariffCalculationsSchema(BaseModel):
    """2. Tariff Calculations."""
    utility_name: str = Field("PSE&G", description="Utility company")
    rate_schedule: str = Field("RS", description="Rate schedule code")
    effective_volumetric_rate: float = Field(0.0, description="Blended volumetric rate ($/kWh)")
    bgs_rate: float = Field(0.0, description="Basic Generation Service rate ($/kWh)")
    distribution_rate: float = Field(0.0, description="Distribution rate ($/kWh)")
    transmission_rate: float = Field(0.0, description="Transmission rate ($/kWh)")
    sbc_rate: float = Field(0.0, description="Societal benefits rate ($/kWh)")
    transition_rate: float = Field(0.0, description="Market transition rate ($/kWh)")
    rider_rate: float = Field(0.0, description="Rider rate ($/kWh)")
    nug_rate: float = Field(0.0, description="NUG rate ($/kWh)")


class FixedChargesSchema(BaseModel):
    """3. Fixed Charges."""
    customer_charge: float = Field(8.24, description="Monthly fixed customer charge ($)")
    meter_fee: float = Field(0.0, description="Fixed meter lease fee ($)")
    total_fixed_charges: float = Field(8.24, description="Total fixed monthly liability ($)")


class VariableChargesSchema(BaseModel):
    """4. Variable Charges."""
    usage_kwh: float = Field(0.0, description="Billed consumption (kWh)")
    bgs_supply_cost: float = Field(0.0, description="BGS supply total ($)")
    distribution_cost: float = Field(0.0, description="Distribution charge total ($)")
    transmission_cost: float = Field(0.0, description="Transmission charge total ($)")
    sbc_cost: float = Field(0.0, description="SBC charge total ($)")
    transition_cost: float = Field(0.0, description="Transition charge total ($)")
    rider_cost: float = Field(0.0, description="Rider charges total ($)")
    nug_cost: float = Field(0.0, description="NUG charge total ($)")
    total_variable_charges: float = Field(0.0, description="Total volumetric charges ($)")


class TaxesSchema(BaseModel):
    """5. Taxes."""
    tax_rate: float = Field(0.06625, description="State utility tax rate (6.625% for NJ)")
    taxable_subtotal: float = Field(0.0, description="Pre-tax bill subtotal ($)")
    calculated_tax: float = Field(0.0, description="Calculated tax amount ($)")
    billed_tax: float = Field(0.0, description="Actual billed tax amount ($)")
    tax_discrepancy: float = Field(0.0, description="Difference between calculated & billed ($)")


class UsageChangeSchema(BaseModel):
    """Usage and cost change metrics."""
    kwh_change: float = Field(0.0, description="Absolute change in consumption (kWh)")
    pct_change_kwh: float = Field(0.0, description="Percentage change in consumption (%)")
    cost_change: float = Field(0.0, description="Absolute change in total cost ($)")
    pct_change_cost: float = Field(0.0, description="Percentage change in total cost (%)")


class HistoricalComparisonSchema(BaseModel):
    """6. Historical Comparison (MoM & YoY)."""
    prior_period_kwh: float = Field(0.0, description="Previous month consumption (kWh)")
    prior_period_cost: float = Field(0.0, description="Previous month total cost ($)")
    prior_year_kwh: float = Field(0.0, description="Same month prior year consumption (kWh)")
    prior_year_cost: float = Field(0.0, description="Same month prior year total cost ($)")
    month_over_month: UsageChangeSchema = Field(default_factory=UsageChangeSchema, description="7. Month-over-Month metrics")
    year_over_year: UsageChangeSchema = Field(default_factory=UsageChangeSchema, description="8. Year-over-Year metrics")


class WeatherNormalizationSchema(BaseModel):
    """9. Weather Normalization."""
    month: int = Field(6, ge=1, le=12, description="Billing period month")
    hdd: float = Field(0.0, description="Heating Degree Days (HDD)")
    cdd: float = Field(0.0, description="Cooling Degree Days (CDD)")
    base_temperature_f: float = Field(65.0, description="Base temperature threshold (°F)")
    temperature_sensitivity_kwh_per_degree: float = Field(0.85, description="kWh sensitivity per degree day")
    weather_driven_kwh: float = Field(0.0, description="Estimated weather-driven consumption (kWh)")
    weather_driven_cost: float = Field(0.0, description="Estimated weather-driven cost ($)")
    base_discretionary_kwh: float = Field(0.0, description="Baseline non-weather consumption (kWh)")
    weather_normalized_kwh: float = Field(0.0, description="Usage adjusted to average weather baseline (kWh)")


class TrendAnalysisSchema(BaseModel):
    """10. Trend Analysis."""
    direction: str = Field("STABLE", description="UPWARD | DOWNWARD | STABLE")
    velocity_kwh_per_month: float = Field(0.0, description="Rate of change in usage (kWh/month)")
    moving_avg_3m_kwh: float = Field(0.0, description="3-month moving average consumption (kWh)")
    moving_avg_6m_kwh: float = Field(0.0, description="6-month moving average consumption (kWh)")
    cost_trend_slope: float = Field(0.0, description="Monthly cost trend slope ($/month)")


class AnomalyItemSchema(BaseModel):
    """Individual flagged line item anomaly."""
    field: str = Field(..., description="Flagged field name")
    actual_value: float = Field(0.0, description="Actual observed value")
    expected_value: float = Field(0.0, description="Expected baseline value")
    z_score: float = Field(0.0, description="Statistical Z-score")
    severity: str = Field("LOW", description="LOW | MEDIUM | HIGH | CRITICAL")
    description: str = Field("", description="Human-readable anomaly description")


class AnomalyDetectionSchema(BaseModel):
    """11. Anomaly Detection."""
    has_anomalies: bool = Field(False, description="True if any anomalies detected")
    anomaly_count: int = Field(0, description="Total count of flagged anomalies")
    anomalies: List[AnomalyItemSchema] = Field(default_factory=list, description="Itemized anomalies list")


class SavingsOpportunitySchema(BaseModel):
    """Individual savings opportunity item."""
    category: str = Field(..., description="Rate Tier | Conservation | Demand Shift")
    title: str = Field(..., description="Opportunity summary title")
    estimated_annual_savings: float = Field(0.0, description="Estimated annual cost reduction ($)")
    estimated_kwh_reduction: float = Field(0.0, description="Estimated annual kWh reduction")
    feasibility: str = Field("EASY", description="EASY | MODERATE | COMPLEX")
    payback_months: int = Field(0, description="Estimated payback period in months")


class SavingsEstimationSchema(BaseModel):
    """12. Savings Estimation."""
    total_potential_annual_savings: float = Field(0.0, description="Combined potential annual savings ($)")
    potential_savings_pct: float = Field(0.0, description="Percentage reduction off baseline bill (%)")
    opportunities: List[SavingsOpportunitySchema] = Field(default_factory=list, description="Savings opportunity list")


class RecommendationItemSchema(BaseModel):
    """13. Recommendation Ranking Item."""
    rank: int = Field(1, description="Priority rank order")
    title: str = Field(..., description="Action recommendation headline")
    description: str = Field(..., description="Detailed action steps")
    category: str = Field("Behavioral", description="Behavioral | Equipment | Tariff | Solar")
    score: float = Field(0.0, description="Weighted priority score (0.0-100.0)")
    estimated_monthly_savings: float = Field(0.0, description="Estimated monthly dollar savings ($)")


class ForecastInputsSchema(BaseModel):
    """14. Forecast Inputs (Pure features for downstream ML models)."""
    baseline_daily_kwh: float = Field(0.0, description="Baseline daily consumption rate (kWh/day)")
    peak_demand_ratio: float = Field(1.0, description="Ratio of peak to average daily load")
    seasonal_factor: float = Field(1.0, description="Seasonal multiplier for current month")
    weather_sensitivity_factor: float = Field(0.85, description="kWh/degree-day temperature elasticity")
    base_annual_kwh_projection: float = Field(0.0, description="Linear annual projected consumption (kWh)")
    trend_coefficient: float = Field(0.0, description="Monthly growth factor")


# ── Top-Level Strongly Typed AnalyticsResult Contract ───────────────────────

class AnalyticsResult(BaseModel):
    """
    Strongly Typed AnalyticsResult Contract.
    Consumed by all downstream services, export engines, and API responses.
    """

    # ── Execution Versioning & Audit Metadata ───────────────────────────────
    bill_hash: str = Field(..., description="SHA-256 hash of source bill document")
    customer_id: str = Field("UPLOADED-BILL", description="Customer identifier")
    utility_name: str = Field("PSE&G", description="Utility company name")
    zip_code: str = Field("07102", description="ZIP code of service location")
    rate_schedule: str = Field("RS", description="Utility rate schedule identifier")

    analytics_version: str = Field("1.0.0", description="Analytics Engine version")
    ocr_version: str = Field("1.0.0", description="OCR Engine version")
    parser_version: str = Field("1.0.0", description="Bill Parser version")
    tariff_version: str = Field("2026.07", description="Tariff schedule dataset version")
    weather_version: str = Field("2026.07", description="Weather baseline dataset version")
    dataset_version: str = Field("2026.07", description="Master benchmark dataset version")

    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC generation timestamp ISO-8601",
    )
    processing_time_ms: Dict[str, float] = Field(
        default_factory=dict,
        description="Pipeline stage latencies in milliseconds",
    )
    confidence_score: float = Field(
        1.0, ge=0.0, le=1.0, description="Overall pipeline confidence metric"
    )
    quality_checks: Dict[str, Any] = Field(
        default_factory=dict, description="Stage validation rule audit results"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal data quality flags"
    )

    # ── The 14 Deterministic Analytics Dimensions ───────────────────────────
    component_breakdown: ComponentBreakdownSchema = Field(default_factory=ComponentBreakdownSchema)
    tariff_calculations: TariffCalculationsSchema = Field(default_factory=TariffCalculationsSchema)
    fixed_charges: FixedChargesSchema = Field(default_factory=FixedChargesSchema)
    variable_charges: VariableChargesSchema = Field(default_factory=VariableChargesSchema)
    taxes: TaxesSchema = Field(default_factory=TaxesSchema)
    historical_comparison: HistoricalComparisonSchema = Field(default_factory=HistoricalComparisonSchema)
    month_over_month: UsageChangeSchema = Field(default_factory=UsageChangeSchema)
    year_over_year: UsageChangeSchema = Field(default_factory=UsageChangeSchema)
    weather_normalization: WeatherNormalizationSchema = Field(default_factory=WeatherNormalizationSchema)
    trend_analysis: TrendAnalysisSchema = Field(default_factory=TrendAnalysisSchema)
    anomaly_detection: AnomalyDetectionSchema = Field(default_factory=AnomalyDetectionSchema)
    savings_estimation: SavingsEstimationSchema = Field(default_factory=SavingsEstimationSchema)
    recommendations: List[RecommendationItemSchema] = Field(default_factory=list)
    forecast_inputs: ForecastInputsSchema = Field(default_factory=ForecastInputsSchema)
