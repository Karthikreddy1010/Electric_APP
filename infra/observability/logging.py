"""
Phase 3 — Structured JSON Logging Configuration.

Replaces the Phase 1 plain-text logging with structured JSON output tagged
with trace_id, tenant_id, and service_name for Grafana Loki ingestion.
"""
import os
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class StructuredJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects for Loki/ELK ingestion.

    Output format:
        {"timestamp": "...", "level": "INFO", "service": "electricai-api",
         "logger": "api.routes.llm", "message": "...", "trace_id": "...",
         "tenant_id": "...", "file": "llm.py", "line": 42}
    """

    def __init__(self, service_name: str = "electricai-api"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }

        # Inject trace context if available (OpenTelemetry)
        try:
            import importlib
            otel_trace = importlib.import_module("opentelemetry.trace")
            span = otel_trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and getattr(ctx, "trace_id", None):
                log_entry["trace_id"] = format(ctx.trace_id, "032x")
                log_entry["span_id"] = format(ctx.span_id, "016x")
        except Exception:
            pass

        # Inject tenant_id if set on the record
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_structured_logging(
    service_name: str = "electricai-api",
    log_level: str = "INFO",
    json_output: bool = True
):
    """
    Configure structured logging for the application.

    Args:
        service_name: Service identifier for log tagging.
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, emit JSON logs; otherwise plain text.
    """
    # Resolve from environment
    env_level = os.environ.get("LOG_LEVEL", log_level).upper()
    env_json = os.environ.get("LOG_FORMAT", "json" if json_output else "text").lower() == "json"
    env_service = os.environ.get("OTEL_SERVICE_NAME", service_name)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, env_level, logging.INFO))
    root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)

    if env_json:
        handler.setFormatter(StructuredJSONFormatter(service_name=env_service))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s"
        ))

    root_logger.addHandler(handler)

    # Suppress noisy library loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
