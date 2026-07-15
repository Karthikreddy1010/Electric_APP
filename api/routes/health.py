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


@router.get("/health/llm")
async def health_llm():
    """
    Diagnose connection to Ollama server, verify configured model tag exists,
    measure latency, and perform a quick single-token probe.
    """
    import time
    import httpx
    from api.services.llm.llm_service import llm_service

    server_reachable = False
    model_available = False
    inference_successful = False
    latency_ms = 0.0
    status = "unhealthy"
    model_name = llm_service.provider.model
    base_url = llm_service.provider.base_url

    start_time = time.time()
    try:
        # Check socket / reachability
        server_reachable = llm_service.provider.is_available()
        if server_reachable:
            # Query tags to check if configured model exists
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    models_list = [m.get("name") for m in models]
                    for m_name in models_list:
                        if m_name == model_name or m_name.split(":")[0] == model_name.split(":")[0]:
                            model_available = True
                            break

            # Try generating 1 token as a probe
            if model_available:
                probe_payload = {
                    "model": model_name,
                    "prompt": "healthcheck",
                    "stream": False,
                    "options": {"num_predict": 1}
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    probe_url = f"{base_url.rstrip('/')}/api/generate"
                    probe_resp = await client.post(probe_url, json=probe_payload)
                    if probe_resp.status_code == 200:
                        inference_successful = True
                        status = "healthy"
                    else:
                        status = "degraded"
            else:
                status = "degraded"
        else:
            status = "unhealthy"
    except Exception:
        status = "unhealthy"

    latency_ms = round((time.time() - start_time) * 1000.0, 2)

    return {
        "status": status,
        "server_reachable": server_reachable,
        "selected_model": model_name,
        "model_available": model_available,
        "inference_successful": inference_successful,
        "latency_ms": latency_ms
    }
