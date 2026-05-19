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

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
NATIONAL_AVG_PRICE = 0.1284  # EIA 2024 residential avg $/kWh


def _compute_deterministic_insights(req: GeoInsightsRequest) -> dict:
    """
    Fully deterministic fallback: computes ZIP & state insights from raw input
    data using statistical aggregation. No LLM required.
    """
    import statistics

    data = req.electricity_data
    if not data:
        return {"zip_insights": [], "state_trend": {"time_series": [], "trend_analysis": "No data", "growth_metrics": {"mom": "0%", "yoy": "0%"}, "forecast_hint": "Insufficient data."}}

    # ── State-level aggregation by month ──────────────────────────────────────
    from collections import defaultdict
    monthly: dict = defaultdict(list)
    for row in data:
        key = (row.year, row.month)
        monthly[key].append(row)

    time_series = []
    sorted_keys = sorted(monthly.keys())
    for (yr, mo) in sorted_keys:
        rows = monthly[(yr, mo)]
        avg_p = statistics.mean(r.avg_price for r in rows)
        avg_c = statistics.mean(r.consumption_kwh for r in rows)
        time_series.append({
            "year": yr,
            "month": MONTH_NAMES[mo - 1],
            "avg_price": round(avg_p, 5),
            "consumption_kwh": round(avg_c, 1),
        })

    # Growth metrics
    prices = [t["avg_price"] for t in time_series]
    mom = round((prices[-1] - prices[-2]) / prices[-2] * 100, 2) if len(prices) >= 2 else 0.0
    yoy_idx = -13 if len(prices) >= 13 else 0
    yoy = round((prices[-1] - prices[yoy_idx]) / prices[yoy_idx] * 100, 2) if len(prices) >= 13 else 0.0

    trend_dir = "upward" if prices[-1] > prices[0] else "downward"
    volatility = round(statistics.stdev(prices) * 100, 3) if len(prices) > 1 else 0
    trend_analysis = (
        f"NJ shows a {trend_dir} price trend from {time_series[0]['month']} {time_series[0]['year']} "
        f"to {time_series[-1]['month']} {time_series[-1]['year']}. "
        f"Price volatility is {volatility}¢/kWh (std dev). "
        f"Summer months show elevated consumption due to cooling load."
    )
    forecast_price = round(prices[-1] * (1 + mom / 100), 5)
    forecast_hint = (
        f"Based on {mom:+.2f}% MoM trend, next 3 months avg price is projected around "
        f"${forecast_price}/kWh. Expect seasonal uptick if entering summer/winter period."
    )

    # ── ZIP-level aggregation ─────────────────────────────────────────────────
    zip_map: dict = defaultdict(list)
    for row in data:
        zip_map[row.zip_code].append(row)

    state_avg_price = statistics.mean(r.avg_price for r in data)

    zip_insights = []
    for zip_code, rows in zip_map.items():
        avg_price = statistics.mean(r.avg_price for r in rows)
        avg_kwh   = statistics.mean(r.consumption_kwh for r in rows)
        avg_peak  = statistics.mean(r.peak_demand for r in rows)
        avg_renew = statistics.mean(r.renewable_ratio for r in rows)

        vs_state  = round((avg_price - state_avg_price) / state_avg_price * 100, 1)
        vs_nation = round((avg_price - NATIONAL_AVG_PRICE) / NATIONAL_AVG_PRICE * 100, 1)

        vs_state_str  = f"{vs_state:+.1f}%"
        vs_nation_str = f"{vs_nation:+.1f}%"

        # Anomaly: detect if latest price is >10% above/below the zip's own avg
        prices_zip = [r.avg_price for r in sorted(rows, key=lambda r: (r.year, r.month))]
        latest = prices_zip[-1]
        rolling_avg = statistics.mean(prices_zip[:-1]) if len(prices_zip) > 1 else latest
        pct_dev = (latest - rolling_avg) / rolling_avg * 100 if rolling_avg else 0
        if pct_dev > 10:
            anomaly = "spike"
        elif pct_dev < -10:
            anomaly = "drop"
        else:
            anomaly = "stable"

        direction = "above" if vs_state >= 0 else "below"
        summary = (
            f"ZIP {zip_code} avg rate is ${avg_price:.5f}/kWh — {abs(vs_state):.1f}% {direction} the NJ state average. "
            f"Renewable mix at {avg_renew*100:.0f}%, peak demand {avg_peak:.2f} kW."
        )

        if avg_renew < 0.1:
            rec = "Low renewable ratio — consider enrolling in a green energy plan or installing solar panels."
        elif avg_peak > 3.5:
            rec = "High peak demand detected — shift heavy appliances (HVAC, EV charging) to off-peak hours."
        elif vs_state > 5:
            rec = "Above-average rate — compare retail energy suppliers in the Plans tab for potential savings."
        else:
            rec = "Stable usage profile. Consider a fixed-rate plan to lock in current favorable rates."

        zip_insights.append({
            "zip_code": zip_code,
            "summary": summary,
            "metrics": {
                "avg_price": round(avg_price, 5),
                "consumption_kwh": round(avg_kwh, 1),
                "peak_demand": round(avg_peak, 2),
                "renewable_ratio": round(avg_renew, 3),
            },
            "comparisons": {
                "vs_state_avg": vs_state_str,
                "vs_national_avg": vs_nation_str,
            },
            "anomaly_detection": anomaly,
            "recommendation": rec,
        })

    return {
        "zip_insights": zip_insights,
        "state_trend": {
            "time_series": time_series,
            "trend_analysis": trend_analysis,
            "growth_metrics": {"mom": f"{mom:+.2f}%", "yoy": f"{yoy:+.2f}%"},
            "forecast_hint": forecast_hint,
        }
    }


@router.post("/generate-insights", response_model=GeoInsightsResponse)
async def generate_geo_insights(req: GeoInsightsRequest):
    """
    Generate detailed AI insights at the ZIP code and State level.
    Uses Ollama/qwen3:4b when available; falls back to deterministic
    statistical analysis when the LLM is offline.
    """
    import ollama
    import json

    prompt = f"""
    You are an advanced energy analytics assistant embedded in a web application called "ElectricAI".
    Generate Geo Insights at ZIP Code and State level. Return STRICT JSON only — no markdown.

    INPUT: {req.model_dump_json()}

    OUTPUT FORMAT:
    {{
      "zip_insights": [
        {{
          "zip_code": "string",
          "summary": "string",
          "metrics": {{ "avg_price": 0.0, "consumption_kwh": 0.0, "peak_demand": 0.0, "renewable_ratio": 0.0 }},
          "comparisons": {{ "vs_state_avg": "+X.X%", "vs_national_avg": "+X.X%" }},
          "anomaly_detection": "spike|drop|stable",
          "recommendation": "string"
        }}
      ],
      "state_trend": {{
        "time_series": [{{"year": 2023, "month": "Jan", "avg_price": 0.0, "consumption_kwh": 0.0}}],
        "trend_analysis": "string",
        "growth_metrics": {{"mom": "+X.X%", "yoy": "+X.X%"}},
        "forecast_hint": "string"
      }}
    }}
    """

    try:
        # Step 1: Rapid socket check to see if Ollama is listening
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        res = sock.connect_ex(('127.0.0.1', 11434))
        sock.close()
        if res != 0:
            raise RuntimeError("Ollama daemon offline")

        # Step 2: Enforce 2.0s strict timeout on JSON model chat loading
        import asyncio
        client = ollama.AsyncClient()
        
        async def fetch_chat():
            return await client.chat(
                model="qwen3:4b",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 1500},
                format="json"
            )
            
        response = await asyncio.wait_for(fetch_chat(), timeout=2.0)
        content = response['message']['content'].strip()
        parsed = json.loads(content)
        logger.info("Geo insights generated via LLM")
        return parsed
    except Exception as e:
        logger.warning(f"LLM unavailable ({e}), using deterministic fallback")
        return _compute_deterministic_insights(req)

