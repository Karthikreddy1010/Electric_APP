"""GET /health — system status, model flags, data freshness."""
from fastapi import APIRouter
from api.state import app_state
from api.schemas import HealthResponse
from database.connection import check_db_health
from api.cache import get_cache

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    db_health = await check_db_health()
    cache_backend = get_cache()
    cache_health = await cache_backend.health_check()
    
    # Global status is degraded or unhealthy if either DB or cache is unhealthy
    overall_status = "healthy"
    if db_health.get("status") == "unhealthy" or cache_health.get("status") == "unhealthy":
        overall_status = "degraded"
        
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        models_loaded={
            "impact": app_state.get("impact_model") is not None,
            "forecast": app_state.get("forecast_model") is not None,
        },
        data_freshness=str(app_state["billing_df"]["date"].max())
        if app_state.get("billing_df") is not None
        else None,
        database=db_health,
        cache=cache_health,
    )
