"""Phase 3 — Observability Package."""
from infra.observability.otel import get_tracer, trace_span, traced
from infra.observability.prometheus import get_metrics, record_api_request, record_ai_inference
from infra.observability.logging import setup_structured_logging

__all__ = [
    "get_tracer", "trace_span", "traced",
    "get_metrics", "record_api_request", "record_ai_inference",
    "setup_structured_logging",
]
