"""
Recommendations Router
Generates multi-factor personalized energy recommendations by synthesizing state trends, weather, solar ROI, and tariff context.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Query
from api.services.recommendation_service import recommendation_service
from api.explainability import attach_explainability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
@attach_explainability(
    data_sources=["Customer Bill", "Utility Tariff", "NOAA Weather", "NASA POWER Solar", "EIA Retail State Trend"],
    calculation_method="Multi-layer synthesis recommendation engine",
)
async def get_personalized_recommendations(
    stateid: str = Query("NJ"),
    monthly_kwh: float = Query(750.0, ge=100.0, le=10000.0),
    effective_rate: float = Query(0.22, ge=0.05, le=1.00),
):
    """Generates personalized energy recommendations."""
    recs = recommendation_service.get_recommendations(
        module_id="recommendations",
        stateid=stateid,
        user_monthly_kwh=monthly_kwh,
        user_effective_rate=effective_rate,
    )
    return {"stateid": stateid, "total_recommendations": len(recs), "recommendations": recs}
