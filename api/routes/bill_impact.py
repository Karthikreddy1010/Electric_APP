"""
Deterministic Bill Impact Analysis Endpoints (NEW — additive only).

POST /impact/sensitivity — change ONE component, measure total bill impact
POST /impact/what-if     — change MULTIPLE components, return updated bill
GET  /impact/rank        — rank all components by influence on total bill

These complement the existing /impact endpoint (which uses BillImpactModel).
No existing endpoints are modified or replaced.
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.schemas import SensitivityRequest, WhatIfRequest
from api.services.bill_impact_engine import (
    COMPONENT_TYPES,
    sensitivity_analysis,
    what_if_analysis,
    rank_components,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/impact", tags=["bill-impact-engine"])


# ── POST /impact/sensitivity ─────────────────────────────────────────────────

@router.post("/sensitivity")
async def impact_sensitivity(req: SensitivityRequest):
    """
    Change ONE component by a percentage and measure the impact on total bill.

    Supports real-time UI sliders (< 100ms response).
    """
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(503, "Billing data not loaded")

    row = billing.iloc[-1].to_dict()

    try:
        result = sensitivity_analysis(
            row=row,
            component=req.component,
            change_pct=req.change_pct,
            kwh=req.kwh,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Sensitivity analysis error")
        raise HTTPException(500, f"Sensitivity error: {e}")


# ── POST /impact/what-if ─────────────────────────────────────────────────────

@router.post("/what-if")
async def impact_what_if(req: WhatIfRequest):
    """
    Modify MULTIPLE components simultaneously and return updated bill
    with per-change contribution breakdown.

    Example body:
    {
        "changes": {"bgs_rate": 15, "sbc_rate": -5, "distribution_rate": 8},
        "kwh": 900
    }
    """
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(503, "Billing data not loaded")

    if not req.changes:
        raise HTTPException(400, "At least one component change is required")

    # Validate component keys
    invalid = [k for k in req.changes if k not in COMPONENT_TYPES]
    if invalid:
        raise HTTPException(
            400,
            f"Unknown components: {invalid}. Valid: {list(COMPONENT_TYPES.keys())}",
        )

    row = billing.iloc[-1].to_dict()

    try:
        result = what_if_analysis(
            row=row,
            changes=req.changes,
            kwh=req.kwh,
        )
        return result
    except Exception as e:
        logger.exception("What-if analysis error")
        raise HTTPException(500, f"What-if error: {e}")


# ── GET /impact/rank ──────────────────────────────────────────────────────────

@router.get("/rank")
async def impact_rank(
    test_pct: float = Query(10.0, ge=1, le=100, description="% change to test"),
    kwh: float | None = Query(None, ge=0, le=10000, description="Override usage"),
):
    """
    Rank ALL bill components by their influence on total bill.

    Each component is tested independently with a uniform +test_pct% change.
    Returns ranked list (highest dollar impact first) with elasticities.
    """
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(503, "Billing data not loaded")

    row = billing.iloc[-1].to_dict()

    try:
        result = rank_components(
            row=row,
            test_pct=test_pct,
            kwh=kwh,
        )
        return result
    except Exception as e:
        logger.exception("Rank analysis error")
        raise HTTPException(500, f"Ranking error: {e}")
