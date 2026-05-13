"""
GET /bill-breakdown — component-level bill breakdown
GET /trends         — historical trend data
"""
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.schemas import BillBreakdownResponse, TrendResponse
from api.services.billing_service import build_breakdown, build_trends

router = APIRouter(tags=["billing"])


@router.get("/bill-breakdown", response_model=list[BillBreakdownResponse])
async def bill_breakdown(months: int = Query(12, ge=1, le=84)):
    """Get detailed bill component breakdown for recent months."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    return build_breakdown(billing, months)


@router.get("/trends", response_model=TrendResponse)
async def get_trends(months: int = Query(36, ge=6, le=84)):
    """Get historical trend data."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    return build_trends(billing, months)
