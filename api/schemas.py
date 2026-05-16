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


# ===== /plan-simulation =====
class PlanSimRequest(BaseModel):
    monthly_usage_kwh: float = Field(750, ge=100, le=5000)
    usage_growth_pct: float = Field(0.0, ge=-50, le=50)
    horizon_months: int = Field(12, ge=1, le=36)
    n_simulations: int = Field(10000, ge=1000, le=100000)

class PlanResult(BaseModel):
    provider: str
    plan_type: str
    rate: float
    expected_annual_cost: float
    median_annual_cost: float
    std_annual_cost: float
    p5_annual_cost: float
    p95_annual_cost: float
    risk_score: float
    monthly_expected: list[float]

class PlanSimResponse(BaseModel):
    comparison: list[PlanResult]
    recommended: str
    savings_vs_default: float


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


# ===== /overview =====
class OverviewKPI(BaseModel):
    current_bill: float
    usage_kwh: float
    effective_rate: float
    forecast_next_month: float
    bill_change_pct: float

class BillComponent(BaseModel):
    label: str
    value: float
    percentage: float

class OverviewResponse(BaseModel):
    kpis: OverviewKPI
    breakdown: list[BillComponent]
    historical_breakdown: list[dict[str, Any]]
    trends: TrendResponse


# ===== Health =====
class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: dict[str, bool]
    data_freshness: Optional[str] = None


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
