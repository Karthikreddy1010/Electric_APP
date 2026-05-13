"""
Pydantic request/response schemas for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
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


# ===== /impact/what-if =====
class WhatIfRequest(BaseModel):
    changes: dict[str, float] = Field(
        ...,
        description="Map of component -> change_pct, e.g. {'bgs_rate': 15, 'sbc_rate': -5}",
    )
    kwh: Optional[float] = Field(None, ge=0, le=10000, description="Override usage (kWh)")
