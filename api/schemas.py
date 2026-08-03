"""
Pydantic request/response schemas for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


# ===== /forecast =====
class ForecastRequest(BaseModel):
    months_ahead: int = Field(12, ge=1, le=36, description="Forecast horizon")
    model_type: str = Field("ensemble", description="sarima|prophet|lstm|ensemble")
    include_ci: bool = Field(True, description="Include confidence intervals")

class ForecastPoint(BaseModel):
    month: str
    forecast: float
    lower: Optional[float] = None
    upper: Optional[float] = None

class ForecastResponse(BaseModel):
    model_type: str
    horizon_months: int
    forecasts: list[ForecastPoint]
    metrics: dict


# ===== /impact =====
class ImpactRequest(BaseModel):
    top_n: int = Field(10, ge=1, le=30, description="Top N features to return")
    include_causal: bool = Field(False, description="Run DoWhy causal analysis")

class ComponentImpact(BaseModel):
    feature: str
    shap_value: float
    direction: str  # "increases" or "decreases"
    magnitude: str  # "high", "medium", "low"

class ImpactResponse(BaseModel):
    base_value: float
    predicted_value: float
    top_drivers: list[ComponentImpact]
    category_impacts: dict
    model_metrics: dict


# ===== /benchmark =====
class BenchmarkRequest(BaseModel):
    year: int = Field(2025, ge=2019, le=2026)
    compare_state: str = Field("NJ", description="State to highlight")

class StateData(BaseModel):
    state: str
    avg_rate: float
    avg_bill: float
    rank: Optional[int] = None

class BenchmarkResponse(BaseModel):
    year: int
    focus_state: StateData
    national_avg: float
    states: list[StateData]



# ===== /simulate =====
class SimulateRequest(BaseModel):
    modifications: dict[str, float]  # e.g. {"bgs_rate": 10}
    kwh: Optional[float] = None

class SimulateResult(BaseModel):
    old_bill: float
    new_bill: float
    delta_abs: float
    delta_pct: float
    formula: str
    explanation: str

# ===== /geo =====
class GeoPoint(BaseModel):
    state: str
    avg_bill: float
    avg_rate: float
    rank: int

class GeoTrendPoint(BaseModel):
    months: list[str]
    values: list[float]
    total_growth_pct: float

class GeoDetailResponse(BaseModel):
    state: str
    month: str
    avg_bill: float
    avg_rate: float
    usage_kwh: float
    yoy_change: Optional[float]
    components: Optional[dict[str, float]]

class GeoResponse(BaseModel):
    data: list[GeoPoint]
    top_5_expensive: list[GeoPoint]
    top_5_cheapest: list[GeoPoint]
    available_months: list[str]
    current_month: str


# ===== /bill-breakdown =====
class BillBreakdownResponse(BaseModel):
    date: str
    total_bill: float
    components: dict[str, float]
    rates: dict[str, float]
    usage_kwh: float
    effective_rate: float
    yoy_change_pct: Optional[float] = None


# ===== /trends =====
class TrendResponse(BaseModel):
    months: list[str]
    total_bills: list[float]
    usage: list[float]
    rates: list[float]
    yoy_changes: list[Optional[float]]
    mom_changes: Optional[list[Optional[float]]] = None


# ===== /overview =====
class OverviewKPI(BaseModel):
    current_bill: float
    usage_kwh: float
    effective_rate: float
    forecast_next_month: float
    bill_change_pct: float
    usage_change_pct: Optional[float] = None
    rate_change_pct: Optional[float] = None

class BillComponent(BaseModel):
    label: str
    value: float
    percentage: float

class EIA861MSummary(BaseModel):
    year: int
    month: int
    period: str
    monthly_sales_mwh: float
    monthly_revenue_k: float
    customer_count: int
    avg_price_cents_kwh: float

class EIA923Summary(BaseModel):
    state: Optional[str] = "NJ"
    utility_fuel_cost_dollars_mmbtu: Optional[float] = None
    fuel_cost_mom_change_pct: Optional[float] = None
    grid_clean_share_pct: Optional[float] = None
    grid_carbon_intensity_lbs_mwh: Optional[float] = None
    battery_roundtrip_efficiency_pct: Optional[float] = None

class OverviewResponse(BaseModel):
    kpis: OverviewKPI
    breakdown: list[BillComponent]
    historical_breakdown: list[dict[str, Any]]
    trends: TrendResponse
    vs_national_pct: Optional[float] = None
    vs_national_label: Optional[str] = None
    state_rank: Optional[int] = None
    state_percentile: Optional[float] = None
    insights: Optional[list[str]] = None
    alerts: Optional[list[str]] = None
    eia861m_summary: Optional[EIA861MSummary] = None
    eia923_summary: Optional[EIA923Summary] = None



# ===== Health =====
class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: dict[str, bool]
    data_freshness: Optional[str] = None
    database: Optional[dict[str, Any]] = None
    cache: Optional[dict[str, Any]] = None


# ===== /impact/sensitivity =====
class SensitivityRequest(BaseModel):
    component: str = Field(..., description="Component key, e.g. 'bgs_rate'")
    change_pct: float = Field(10.0, ge=-100, le=500, description="Percentage change to apply")
    kwh: Optional[float] = Field(None, ge=0, le=10000, description="Override usage (kWh)")

class SensitivityResponse(BaseModel):
    component: str
    label: str
    base_bill: float
    new_bill: float
    absolute_impact: float
    percent_impact: float
    elasticity: float
    component_type: str
    reasoning: str
    details: dict

# ===== /impact/what-if =====
class WhatIfRequest(BaseModel):
    changes: dict[str, float] = Field(
        ...,
        description="Map of component -> change_pct, e.g. {'bgs_rate': 15, 'sbc_rate': -5}",
    )
    kwh: Optional[float] = Field(None, ge=0, le=10000, description="Override usage (kWh)")

class WhatIfResponse(BaseModel):
    base_bill: float
    new_bill: float
    total_impact: float
    confidence_interval: list[float] = Field(..., description="95% CI from Monte Carlo simulation")
    usage_response: float
    contributions: dict

# ===== /impact/what-if-v2 =====
class WhatIfV2Request(BaseModel):
    changes: dict[str, float] = Field(
        default_factory=dict, description="Map of component -> change_pct, e.g. {'bgs_rate': 15, 'sbc_rate': -5}"
    )
    kwh: Optional[float] = Field(None, ge=0, le=10000)
    scenario: Optional[str] = Field(
        None, description="Named scenario preset: cold_winter, hot_summer, high_market, low_usage, conservation"
    )
    n_simulations: int = Field(2000, ge=500, le=10000)
    base_rates: Optional[dict[str, float]] = Field(None, description="Baseline rates from the uploaded bill")
    base_costs: Optional[dict[str, float]] = Field(None, description="Baseline costs from the uploaded bill")

class ImpactExplainRequest(BaseModel):
    uploaded_bill: dict = Field(..., description="Structured bill object")
    simulation_results: dict = Field(..., description="Simulation results dictionary")
    scenario_inputs: dict = Field(..., description="Slider changes and usage override")

class ImpactExplainResponse(BaseModel):
    success: bool
    explanation: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ImpactChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    uploaded_bill: dict
    simulation_results: dict

class ImpactChatResponse(BaseModel):
    success: bool
    answer: str

class UniversalLLMExplainRequest(BaseModel):
    task: str = Field(..., description="Task identifier e.g. bill_analysis, impact, forecast, overview, recommendations, benchmark, geo")
    context_data: dict = Field(..., description="Structured JSON context matching task schema")
    bypass_cache: bool = Field(False, description="Whether to bypass cache")
    user_tier: str = Field("free", description="User subscription tier (free, pro, enterprise)")

class UniversalLLMExplainResponse(BaseModel):
    success: bool
    text: str
    explanation: str
    metadata: dict

class UniversalLLMChatRequest(BaseModel):
    task: str = Field("chat", description="Task identifier")
    message: str = Field(..., description="User query text")
    history: list[ChatMessage] = Field(default_factory=list)
    context_data: dict = Field(..., description="Context data dictionary")
    current_tab: str = Field("Impact", description="Active frontend tab")
    user_tier: str = Field("free", description="User subscription tier (free, pro, enterprise)")

class UniversalLLMChatResponse(BaseModel):
    success: bool
    answer: str
    text: str
    metadata: dict


class BillDecomposition(BaseModel):
    direct_price_effect: float
    indirect_behavioral_effect: float
    weather_effect: float
    interaction_effect: float

class PJMMarketPhysicsData(BaseModel):
    marginal_cost: float
    lmp: float
    effective_kwh: float
    da_charge: float
    rt_charge: float
    loss_factor: float
    simulated_bill_pjm: float
    distribution_pjm: Optional[dict] = None

class WhatIfV2Response(BaseModel):
    base_bill: float
    simulated_bill: float
    confidence_interval: list[float] = Field(..., description="95% CI from Monte Carlo simulation")
    usage_change_kwh: float
    learned_elasticity: float
    decomposition: BillDecomposition
    contributions: dict
    scenario_applied: Optional[str] = None
    model_info: dict
    distribution: Optional[dict] = None
    pjm_physics: Optional[PJMMarketPhysicsData] = None

# ===== /impact/rank =====
class RankItem(BaseModel):
    component: str
    label: str
    share_pct: float
    elasticity: float
    type: str
    reasoning: str

class RankResponse(BaseModel):
    rankings: list[RankItem]

# ===== /impact/causal =====
class CausalRequest(BaseModel):
    treatment: str = Field(..., description="Component rate to test for causal impact")

class CausalResponse(BaseModel):
    treatment: str
    causal_effect_estimate: float
    p_value: float
    interpretation: str
    caveat: str

class CausalV2Response(BaseModel):
    treatment: str
    causal_effect_estimate: float
    std_error: float
    p_value: float
    ci_95: list[float]
    confounders_controlled: list[str]
    method: str
    interpretation: str
    caveat: str


# ===== Bill OCR Extraction & Analysis =====
class BillAnalysisRequest(BaseModel):
    bill_text: str = Field(..., description="Raw OCR text extracted from the electricity bill")

class BillAnalysisCharges(BaseModel):
    supply: Optional[float] = None
    delivery: Optional[float] = None
    fixed: Optional[float] = None
    tax: Optional[float] = None

class BillAnalysisPercentages(BaseModel):
    supply_pct: Optional[float] = None
    delivery_pct: Optional[float] = None
    fixed_pct: Optional[float] = None
    tax_pct: Optional[float] = None

class BillAnalysisResponse(BaseModel):
    utility_name: Optional[str] = None
    billing_period: Optional[str] = None
    kwh_used: Optional[float] = None
    total_amount: Optional[float] = None
    charges: BillAnalysisCharges
    percentages: BillAnalysisPercentages
    driver: Optional[str] = None  # "usage", "rate", "fixed"
    insight: Optional[str] = None


# ===== EIA-861M =====
class EIA861MRecord(BaseModel):
    year: int
    month: int
    state: str
    sector: str
    period: str
    data_status: Optional[str] = None
    revenue_k_dollars: Optional[float] = None
    sales_mwh: Optional[float] = None
    customers: Optional[int] = None
    price_cents_kwh: Optional[float] = None

class EIA861MStateTrends(BaseModel):
    state: str
    periods: list[str]
    sales: list[float]
    revenue: list[float]
    prices: list[float]
    customers: list[int]

class EIA861MRankingItem(BaseModel):
    state: str
    price_cents_kwh: float
    sales_mwh: float
    customers: int
    rank: int


# ===== OpenEI Utility / ZIP =====
class UtilityLookupResponse(BaseModel):
    eia_utility_id: int
    utility_name: str
    state: str
    ownership_type: Optional[str] = None
    zip_code: str
    service_type: Optional[str] = None
    residential_rate: Optional[float] = None
    commercial_rate: Optional[float] = None
    industrial_rate: Optional[float] = None

class UtilityDetailResponse(BaseModel):
    eia_utility_id: int
    utility_name: str
    state: str
    ownership_type: Optional[str] = None
    residential_rate: Optional[float] = None
    commercial_rate: Optional[float] = None
    industrial_rate: Optional[float] = None
    zip_count: int

class UtilityCompareResponse(BaseModel):
    utilities: list[UtilityDetailResponse]
    residential_diff_pct: Optional[float] = None
    commercial_diff_pct: Optional[float] = None
    industrial_diff_pct: Optional[float] = None


# ===== EIA-930 Hourly Grid Operations =====
class HourlyDemandPoint(BaseModel):
    period: str
    demand: float
    forecast: Optional[float] = None
    generation: Optional[float] = None

class FuelMixPoint(BaseModel):
    fuel_type: str
    fuel_type_name: str
    value_mwh: float
    percentage: float

class SubregionDemandPoint(BaseModel):
    subba_code: str
    subba_name: str
    value_mwh: float

class InterchangePoint(BaseModel):
    neighbor: str
    neighbor_name: str
    net_interchange_mwh: float  # positive means exporting, negative means importing

class GridStatusResponse(BaseModel):
    ba_code: str
    ba_name: str
    latest_period: str
    current_demand_mwh: float
    current_forecast_mwh: Optional[float] = None
    current_generation_mwh: Optional[float] = None
    fuel_mix: list[FuelMixPoint]
    subregions: list[SubregionDemandPoint]
    interchange: list[InterchangePoint]


