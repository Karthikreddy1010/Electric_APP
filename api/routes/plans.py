"""POST /plan-simulation — Monte Carlo plan comparison."""
import logging
from fastapi import APIRouter, HTTPException

from api.state import app_state
from api.schemas import PlanSimRequest, PlanSimResponse
from api.services.simulation_service import run_plan_simulation

logger = logging.getLogger(__name__)
router = APIRouter(tags=["plans"])


@router.post("/plan-simulation", response_model=PlanSimResponse)
async def plan_simulation(req: PlanSimRequest):
    """Run Monte Carlo simulation comparing electricity plans."""
    plans_df = app_state["plans_df"]
    billing_df = app_state["billing_df"]
    if plans_df is None or billing_df is None:
        raise HTTPException(500, "Data not loaded")
    try:
        return run_plan_simulation(plans_df, billing_df, req)
    except Exception as e:
        logger.exception("Simulation error")
        raise HTTPException(500, f"Simulation error: {str(e)}")
