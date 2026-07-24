"""
Inflation Analytics API Router.

Endpoints for CPI trend data, bill inflation adjustments,
purchasing power metrics, and inflation KPIs.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from api.services.inflation_service import inflation_service

router = APIRouter(prefix="/inflation", tags=["Inflation Analytics"])


class BillAdjustRequest(BaseModel):
    nominal_bill: float
    bill_year: int
    bill_month: int


class BillSeriesItem(BaseModel):
    total_bill: float
    year: int
    month: int


class BillSeriesRequest(BaseModel):
    bills: list[BillSeriesItem]


@router.get("/trend")
async def get_inflation_trend():
    """Monthly CPI trend with year-over-year inflation rates."""
    return {"data": inflation_service.get_inflation_trend()}


@router.get("/kpis")
async def get_inflation_kpis():
    """Top-level inflation KPIs: current rate, cumulative, purchasing power."""
    return inflation_service.get_kpis()


@router.post("/adjust-bill")
async def adjust_single_bill(req: BillAdjustRequest):
    """Adjust a single bill from nominal to real (inflation-adjusted) dollars."""
    return inflation_service.adjust_bill_for_inflation(
        nominal_bill=req.nominal_bill,
        bill_year=req.bill_year,
        bill_month=req.bill_month,
    )


@router.post("/adjust-series")
async def adjust_bill_series(req: BillSeriesRequest):
    """Adjust a time-series of bills for inflation."""
    bills = [item.model_dump() for item in req.bills]
    return {"data": inflation_service.adjust_bill_series(bills)}


@router.get("/deflator")
async def get_deflator(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month"),
    base_year: Optional[int] = Query(None),
    base_month: Optional[int] = Query(None),
):
    """Get CPI deflator for a specific year/month relative to a base period."""
    deflator = inflation_service.get_deflator(
        year=year, month=month, base_year=base_year, base_month=base_month
    )
    return {"year": year, "month": month, "deflator": round(deflator, 4)}
