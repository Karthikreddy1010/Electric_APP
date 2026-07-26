"""
Phase 3 — Domain Event Contracts.

Strongly typed Pydantic schemas defining every domain event in the
ElectricAI asynchronous event-driven pipeline.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    BILL_UPLOADED = "bill.uploaded"
    OCR_COMPLETED = "bill.ocr_completed"
    ANALYTICS_COMPLETED = "analytics.completed"
    PROMPT_GENERATED = "prompt.generated"
    INFERENCE_STARTED = "inference.started"
    INFERENCE_COMPLETED = "inference.completed"
    VALIDATION_COMPLETED = "validation.completed"
    REPORT_GENERATED = "report.generated"
    NOTIFICATION_SENT = "notification.sent"


class DomainEvent(BaseModel):
    """Base event contract for all ElectricAI domain events."""
    event_id: str = Field(..., description="Unique event UUID")
    event_type: EventType = Field(..., description="Domain event type")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp"
    )
    tenant_id: str = Field("default", description="Tenant identifier")
    trace_id: str = Field("", description="OpenTelemetry trace propagation ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class BillUploadedEvent(DomainEvent):
    event_type: EventType = EventType.BILL_UPLOADED


class AnalyticsCompletedEvent(DomainEvent):
    event_type: EventType = EventType.ANALYTICS_COMPLETED


class InferenceCompletedEvent(DomainEvent):
    event_type: EventType = EventType.INFERENCE_COMPLETED


class ReportGeneratedEvent(DomainEvent):
    event_type: EventType = EventType.REPORT_GENERATED
