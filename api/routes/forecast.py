"""POST /forecast — cost forecast via trained ensemble."""
import logging

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.state import app_state
from api.schemas import ForecastRequest, ForecastResponse
from api.services.forecast_service import run_forecast

logger = logging.getLogger(__name__)
router = APIRouter(tags=["forecast"])


@router.post("/forecast", response_model=ForecastResponse)
async def forecast_costs(req: ForecastRequest):
    """Generate electricity cost forecast."""
    ensemble = app_state["forecast_model"]
    billing = app_state["billing_df"]
    if ensemble is None:
        raise HTTPException(500, "Forecast model not loaded")
    if billing is None:
        raise HTTPException(500, "Billing data not loaded")

    try:
        return run_forecast(ensemble, billing, req)
    except Exception as e:
        logger.exception("Forecast error")
        raise HTTPException(500, f"Forecast error: {str(e)}")
