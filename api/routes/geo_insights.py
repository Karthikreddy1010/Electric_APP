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
