"""
Bill Impact Engine Endpoints.
Provides deterministic, statistical, and causal analysis of electricity bill components.
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.schemas import (
    SensitivityRequest, SensitivityResponse,
    WhatIfRequest, WhatIfResponse,
    RankResponse,
    CausalRequest, CausalResponse
)
from api.services.bill_impact_engine import bill_impact_engine, COMPONENT_TYPES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/impact", tags=["bill-impact-engine"])

@router.post("/sensitivity", response_model=SensitivityResponse)
async def impact_sensitivity(req: SensitivityRequest):
    """
    Change ONE component by a percentage and measure the deterministic impact.
    """
    result = bill_impact_engine.sensitivity_analysis(
        component=req.component,
        change_pct=req.change_pct,
        kwh=req.kwh
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

@router.post("/what-if", response_model=WhatIfResponse)
async def impact_what_if(req: WhatIfRequest):
    """
    Modify MULTIPLE components simultaneously and simulate total bill change.
    Includes analytical demand response.
    """
    if not req.changes:
        raise HTTPException(400, "No changes provided")
    
    result = bill_impact_engine.what_if_simulation(
        modifications=req.changes,
        kwh=req.kwh
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

@router.get("/rank", response_model=RankResponse)
async def impact_rank():
    """
    Rank all components by their share of the total bill and elasticity.
    """
    try:
        rankings = bill_impact_engine.rank_components()
        return {"rankings": rankings}
    except Exception as e:
        logger.exception("Ranking error")
        raise HTTPException(500, str(e))

@router.post("/causal", response_model=CausalResponse)
async def impact_causal(req: CausalRequest):
    """
    Estimate the causal impact of a component rate on the total bill.
    Controls for usage as a confounder.
    """
    if req.treatment not in COMPONENT_TYPES:
        raise HTTPException(400, f"Invalid treatment component: {req.treatment}")
        
    result = bill_impact_engine.get_causal_impact(req.treatment)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result
