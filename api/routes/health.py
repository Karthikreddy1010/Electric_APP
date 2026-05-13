"""GET /health — system status, model flags, data freshness."""
from fastapi import APIRouter
from api.state import app_state
from api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        models_loaded={
            "impact": app_state["impact_model"] is not None,
            "forecast": app_state["forecast_model"] is not None,
        },
        data_freshness=str(app_state["billing_df"]["date"].max())
        if app_state["billing_df"] is not None
        else None,
    )
