"""
backend.utils.logging — Correlation-aware structured JSON logging.

Attaches request_id, task_id, and correlation_id to every log record
for end-to-end traceability across HTTP handlers, Celery workers, and
database operations. Uses standard Python logging (no OpenTelemetry).
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ── Context Variables for Correlation IDs ────────────────────────────────────
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
task_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "task_id", default=""
)
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req-{uuid.uuid4().hex[:12]}"


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for pipeline tracing."""
    return f"cor-{uuid.uuid4().hex[:12]}"


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach correlation IDs if present
        req_id = request_id_var.get("")
        task_id = task_id_var.get("")
        cor_id = correlation_id_var.get("")

        if req_id:
            log_entry["request_id"] = req_id
        if task_id:
            log_entry["task_id"] = task_id
        if cor_id:
            log_entry["correlation_id"] = cor_id

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development with correlation context."""

    FORMAT = (
        "%(asctime)s  %(levelname)-8s  [%(correlation_ids)s]  "
        "%(name)s: %(message)s"
    )

    def format(self, record: logging.LogRecord) -> str:
        parts = []
        req_id = request_id_var.get("")
        task_id = task_id_var.get("")
        cor_id = correlation_id_var.get("")

        if req_id:
            parts.append(req_id)
        if task_id:
            parts.append(task_id)
        if cor_id:
            parts.append(cor_id)

        record.correlation_ids = " | ".join(parts) if parts else "-"
        self._style = logging.PercentStyle(self.FORMAT)
        self._fmt = self.FORMAT
        return super().format(record)


def setup_backend_logging(
    level: int = logging.INFO,
    json_format: bool = False,
) -> None:
    """
    Configure structured logging for backend modules.

    Args:
        level: Log level for the backend logger hierarchy.
        json_format: If True, emit JSON-structured logs (production).
                     If False, emit human-readable logs (development).
    """
    backend_logger = logging.getLogger("backend")
    backend_logger.setLevel(level)

    # Avoid duplicate handlers
    if backend_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(HumanReadableFormatter())

    backend_logger.addHandler(handler)
    backend_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger under the backend.* hierarchy.

    Usage:
        from backend.utils.logging import get_logger
        logger = get_logger(__name__)
    """
    if not name.startswith("backend"):
        name = f"backend.{name}"
    return logging.getLogger(name)
