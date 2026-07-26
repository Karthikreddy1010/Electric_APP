"""
Phase 3 — OpenTelemetry SDK Integration.

Provides distributed tracing and span propagation across the full
ElectricAI pipeline: HTTP Ingress → Worker → Analytics Engine → AIOrchestrator → LLM Server.

Initializes the OTel TracerProvider with OTLP exporter for Jaeger
and exposes helper decorators for manual span creation.
"""
import os
import logging
import functools
from typing import Optional, Any, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ── Lazy OTel imports (graceful degradation if not installed) ──────────────

_tracer = None
_initialized = False


def _init_otel():
    """Initialize OpenTelemetry tracing. Safe to call multiple times."""
    global _tracer, _initialized
    if _initialized:
        return

    try:
        import importlib
        trace = importlib.import_module("opentelemetry.trace")
        sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
        TracerProvider = sdk_trace.TracerProvider
        BatchSpanProcessor = sdk_trace.export.BatchSpanProcessor
        Resource = importlib.import_module("opentelemetry.sdk.resources").Resource

        # Check for OTLP exporter availability
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        service_name = os.environ.get("OTEL_SERVICE_NAME", "electricai-api")

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        try:
            otlp_module = importlib.import_module("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
            OTLPSpanExporter = otlp_module.OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OpenTelemetry OTLP exporter initialized → {otlp_endpoint}")
        except Exception:
            # Fall back to console exporter for dev
            ConsoleSpanExporter = sdk_trace.export.ConsoleSpanExporter
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("OpenTelemetry ConsoleSpanExporter initialized (OTLP not available)")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("electricai")
        _initialized = True

    except Exception:
        logger.info("OpenTelemetry SDK not installed. Tracing disabled.")
        _initialized = True  # Don't retry


def get_tracer():
    """Get the global OpenTelemetry tracer instance. Returns None if OTel is not available."""
    _init_otel()
    return _tracer


@contextmanager
def trace_span(name: str, attributes: Optional[dict] = None):
    """
    Context manager for creating a traced span.
    Degrades gracefully to a no-op if OpenTelemetry is not installed.

    Usage:
        with trace_span("ai.orchestrator.execute", {"task": "bill_analysis"}):
            result = await orchestrator.execute(...)
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield span


def traced(name: Optional[str] = None):
    """
    Decorator for adding tracing to sync or async functions.

    Usage:
        @traced("ai.inference.generate")
        async def generate(prompt: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(span_name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(span_name):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
