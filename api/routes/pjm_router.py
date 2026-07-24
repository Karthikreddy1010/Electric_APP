"""
PJM Wholesale Market API Router.

Endpoints for PJM day-ahead LMP analytics, wholesale cost exposure,
and load-shifting savings estimates.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional

from api.services.pjm_service import pjm_service

router = APIRouter(prefix="/pjm", tags=["PJM Wholesale Market"])


@router.get("/daily-analytics")
async def get_daily_analytics(
    zone: str = Query("PSEG", description="PJM pricing zone"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
):
    """Daily aggregated PJM LMP analytics (avg, max, volatility, spikes)."""
    return {"data": pjm_service.compute_daily_analytics(zone=zone, days=days)}


@router.get("/wholesale-exposure")
async def get_wholesale_exposure(
    usage_kwh: float = Query(750, ge=0, description="Monthly usage in kWh"),
    zone: str = Query("PSEG", description="PJM pricing zone"),
    days: int = Query(30, ge=1, le=365),
):
    """Customer wholesale market cost exposure analysis."""
    return pjm_service.compute_wholesale_exposure(
        usage_kwh=usage_kwh, zone=zone, days=days
    )


@router.get("/load-shifting")
async def get_load_shifting_savings(
    usage_kwh: float = Query(750, ge=0, description="Monthly usage in kWh"),
    shift_pct: float = Query(0.15, ge=0, le=1, description="Fraction of peak load to shift"),
    zone: str = Query("PSEG"),
    days: int = Query(30, ge=1, le=365),
):
    """Estimate savings from shifting peak load to off-peak hours."""
    return pjm_service.compute_load_shifting_savings(
        usage_kwh=usage_kwh, shift_pct=shift_pct, zone=zone, days=days
    )


@router.get("/kpis")
async def get_pjm_kpis(
    zone: str = Query("PSEG"),
    days: int = Query(30, ge=1, le=365),
):
    """Top-level PJM wholesale market KPIs."""
    return pjm_service.get_kpis(zone=zone, days=days)
