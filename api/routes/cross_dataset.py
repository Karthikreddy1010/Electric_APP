"""
Cross-Dataset 360° Unified Analytics API Router.

Endpoints for retrieving unified 360° customer utility insights
joining all 14 project datasets.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from api.services.cross_dataset_service import cross_dataset_service

router = APIRouter(prefix="/cross-dataset", tags=["Cross-Dataset 360 Analytics"])


class Customer360Request(BaseModel):
    usage_kwh: float = 750.0
    nominal_bill: float = 160.65
    zip_code: str = "07101"
    state: str = "NJ"
    utility_name: str = "Public Service Elec & Gas Co"
    bill_year: int = 2024
    bill_month: int = 6


@router.get("/unified-insights")
async def get_unified_customer_insights(
    usage_kwh: float = Query(750.0, ge=0),
    nominal_bill: float = Query(160.65, ge=0),
    zip_code: str = Query("07101"),
    state: str = Query("NJ"),
    utility_name: str = Query("Public Service Elec & Gas Co"),
    bill_year: int = Query(2024),
    bill_month: int = Query(6, ge=1, le=12),
):
    """Retrieve unified 360° customer utility intelligence across all 14 project datasets."""
    return cross_dataset_service.get_unified_customer_360(
        usage_kwh=usage_kwh,
        nominal_bill=nominal_bill,
        zip_code=zip_code,
        state=state,
        utility_name=utility_name,
        bill_year=bill_year,
        bill_month=bill_month,
    )


@router.post("/unified-insights")
async def post_unified_customer_insights(req: Customer360Request):
    """Retrieve unified 360° customer utility intelligence via POST body."""
    return cross_dataset_service.get_unified_customer_360(
        usage_kwh=req.usage_kwh,
        nominal_bill=req.nominal_bill,
        zip_code=req.zip_code,
        state=req.state,
        utility_name=req.utility_name,
        bill_year=req.bill_year,
        bill_month=req.bill_month,
    )
