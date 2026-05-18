"""
Geo Insights API — interactive electricity price heatmap data.

GET /geo/data   — all states for a given month (map data)
GET /geo/trend  — monthly time series for a state
GET /geo/detail — component breakdown for a state/month
GET /geo/meta   — available months and states
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.services.geo_insights_service import (
    get_map_data,
    get_trend_data,
    get_detail_data,
    get_available_months,
    get_available_states,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geo-insights"])


@router.get("/data")
async def geo_data(
    month: str = Query("2025-12", description="Month in YYYY-MM format"),
    type: str = Query("bill", description="'bill' or 'price'"),
    state: str | None = Query(None, description="Filter by state code"),
):
    """
    Return all states for a given month — feeds the choropleth map.
    Fast (<50ms), designed for real-time slider interaction.
    """
    monthly = app_state.get("geo_monthly_df")
    if monthly is None:
        raise HTTPException(503, "Geo data not initialized")

    if type not in ("bill", "price"):
        raise HTTPException(400, "type must be 'bill' or 'price'")

    data = get_map_data(monthly, month, data_type=type, state_filter=state)
    return {"month": month, "type": type, "count": len(data), "data": data}


@router.get("/trend")
async def geo_trend(
    region: str = Query("NJ", description="State code"),
    type: str = Query("bill", description="'bill' or 'price'"),
):
    """
    Monthly time series for a specific state.
    Feeds the trend line chart.
    """
    monthly = app_state.get("geo_monthly_df")
    if monthly is None:
        raise HTTPException(503, "Geo data not initialized")

    result = get_trend_data(monthly, state=region, data_type=type)
    if not result["months"]:
        raise HTTPException(404, f"No trend data for state '{region}'")

    return result


@router.get("/detail")
async def geo_detail(
    state: str = Query("NJ", description="State code"),
    month: str = Query("2025-12", description="Month in YYYY-MM format"),
):
    """
    Detailed breakdown for a specific state/month.
    For NJ: uses actual billing data with real component costs.
    For others: uses synthetic breakdown from benchmark data.
    """
    monthly = app_state.get("geo_monthly_df")
    billing = app_state.get("billing_df")
    if monthly is None:
        raise HTTPException(503, "Geo data not initialized")

    result = get_detail_data(billing, monthly, state=state, month=month)
    if "error" in result:
        raise HTTPException(404, result["error"])

    return result


@router.get("/meta")
async def geo_meta():
    """Return available months and states for the timeline slider."""
    monthly = app_state.get("geo_monthly_df")
    if monthly is None:
        raise HTTPException(503, "Geo data not initialized")

    return {
        "months": get_available_months(monthly),
        "states": get_available_states(monthly),
        "default_month": "2025-12",
        "default_state": "NJ",
    }

# ═══════════════════════════════════════════════════════════════════════════
#  AI GEO INSIGHTS GENERATION
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import List, Optional

class GeoLocation(BaseModel):
    state: str
    zip_codes: List[str]

class GeoElectricityData(BaseModel):
    zip_code: str
    state: str
    month: int
    year: int
    avg_price: float
    consumption_kwh: float
    peak_demand: float
    renewable_ratio: float

class GeoInsightsRequest(BaseModel):
    location: GeoLocation
    electricity_data: List[GeoElectricityData]

class ZipComparison(BaseModel):
    vs_state_avg: str
    vs_national_avg: Optional[str] = None

class ZipMetrics(BaseModel):
    avg_price: float
    consumption_kwh: float
    peak_demand: float
    renewable_ratio: float

class ZipInsight(BaseModel):
    zip_code: str
    summary: str
    metrics: ZipMetrics
    comparisons: ZipComparison
    anomaly_detection: str
    recommendation: str

class TrendTimeSeries(BaseModel):
    year: int
    month: str
    avg_price: float
    consumption_kwh: float

class GrowthMetrics(BaseModel):
    mom: str
    yoy: str

class StateTrend(BaseModel):
    time_series: List[TrendTimeSeries]
    trend_analysis: str
    growth_metrics: GrowthMetrics
    forecast_hint: str

class GeoInsightsResponse(BaseModel):
    zip_insights: List[ZipInsight]
    state_trend: StateTrend

@router.post("/generate-insights", response_model=GeoInsightsResponse)
async def generate_geo_insights(req: GeoInsightsRequest):
    """
    Generate detailed AI insights at the ZIP code and State level
    returning structured JSON optimized for frontend rendering.
    """
    import ollama
    import json
    
    prompt = f"""
    You are an advanced energy analytics assistant embedded in a web application called "ElectricAI".

    Your task is to generate Geo Insights at both:
    1) ZIP Code Level (granular insights)
    2) State Level (aggregated trends with time series)

    You must return structured JSON optimized for frontend rendering.

    -----------------------------------
    INPUT DATA STRUCTURE
    -----------------------------------
    {req.model_dump_json()}

    -----------------------------------
    TASK 1: ZIP CODE LEVEL INSIGHTS
    -----------------------------------
    For EACH zip code, generate:
    1. summary: short insight (1-2 lines), highlight if cost is high/low vs state average
    2. metrics: avg_price, consumption_kwh, peak_demand, renewable_ratio
    3. comparisons: vs_state_avg (% difference), vs_national_avg (if available)
    4. anomaly_detection: detect unusual spikes or drops, label: ["spike", "drop", "stable"]
    5. recommendation: actionable suggestion (e.g., reduce peak usage, shift load, solar adoption)

    -----------------------------------
    TASK 2: STATE TREND LINE (MONTH + YEAR)
    -----------------------------------
    Aggregate ALL data at state level. Generate:
    1. time_series: [ {{"year": 2023, "month": "Jan", "avg_price": 0.12, "consumption_kwh": 800}} ]
    2. trend_analysis: identify seasonal patterns, upward/downward trends, volatility
    3. growth_metrics: month_over_month_growth (%), year_over_year_growth (%)
    4. forecast_hint: short prediction for next 3 months

    -----------------------------------
    OUTPUT FORMAT (STRICT JSON)
    -----------------------------------
    {{
      "zip_insights": [
        {{
          "zip_code": "string",
          "summary": "string",
          "metrics": {{ "avg_price": 0.0, "consumption_kwh": 0.0, "peak_demand": 0.0, "renewable_ratio": 0.0 }},
          "comparisons": {{ "vs_state_avg": "string", "vs_national_avg": "string" }},
          "anomaly_detection": "string",
          "recommendation": "string"
        }}
      ],
      "state_trend": {{
        "time_series": [
          {{ "year": 2023, "month": "Jan", "avg_price": 0.0, "consumption_kwh": 0.0 }}
        ],
        "trend_analysis": "string",
        "growth_metrics": {{ "mom": "string", "yoy": "string" }},
        "forecast_hint": "string"
      }}
    }}
    
    RULES:
    - ONLY output valid JSON. No markdown blocks like ```json ... ```, just the raw JSON text.
    - No hallucinated data. If data is missing, return null.
    - Keep explanations sharp and data-driven.
    """
    
    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model="qwen3:4b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
            format="json"
        )
        
        content = response['message']['content'].strip()
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        logger.exception("Geo Insights AI generation failed")
        raise HTTPException(500, f"Failed to generate insights: {str(e)}")
