"""
POST /impact        — component contribution + sensitivity analysis
GET  /contribution  — contribution for a specific month
GET  /sensitivity   — sensitivity analysis
POST /simulate-bill — bill simulation with overrides
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.schemas import ImpactRequest
from api.services.impact_service import (
    run_impact_analysis,
    run_contribution,
    run_sensitivity_analysis,
    run_bill_simulation,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["impact"])


@router.post("/impact")
async def bill_impact_analysis(req: ImpactRequest):
    """Deterministic component contribution and sensitivity analysis."""
    model = app_state["impact_model"]
    billing = app_state["billing_df"]
    if model is None:
        raise HTTPException(503, "Impact model not loaded")
    if billing is None:
        raise HTTPException(503, "Billing data not loaded")

    try:
        return run_impact_analysis(model, billing, req.top_n)
    except Exception as e:
        logger.exception("Impact error")
        raise HTTPException(500, f"Impact analysis error: {str(e)}")


@router.get("/contribution")
async def get_contribution(month_index: int = Query(-1, ge=-84, le=-1)):
    """Component contribution analysis for a specific month."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    try:
        return run_contribution(billing, month_index)
    except Exception as e:
        logger.exception("Contribution error")
        raise HTTPException(500, str(e))


@router.get("/sensitivity")
async def get_sensitivity(
    month_index: int = Query(-1, ge=-84, le=-1),
    pct: float = Query(10.0, ge=1, le=50),
):
    """Sensitivity analysis: impact of +/- pct% change per component."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    try:
        return run_sensitivity_analysis(billing, month_index, pct)
    except Exception as e:
        logger.exception("Sensitivity error")
        raise HTTPException(500, str(e))


@router.post("/simulate-bill")
async def post_simulate_bill(overrides: dict):
    """Simulate a bill with user-specified component overrides."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    try:
        return run_bill_simulation(billing, overrides)
    except Exception as e:
        logger.exception("Simulate-bill error")
        raise HTTPException(500, str(e))
