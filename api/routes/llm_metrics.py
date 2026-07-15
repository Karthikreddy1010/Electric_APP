"""
API Route exposing LLM Subsystem Telemetry & Performance Metrics.
"""
from fastapi import APIRouter
from api.services.llm.metrics import llm_metrics

router = APIRouter(prefix="/api/v1/llm", tags=["llm-telemetry"])

@router.get("/metrics")
def get_llm_metrics():
    """
    Returns diagnostic telemetry snapshot including request count,
    latency statistics, fallback counter, and recent errors.
    """
    return {
        "status": "success",
        "metrics": llm_metrics.get_snapshot()
    }
