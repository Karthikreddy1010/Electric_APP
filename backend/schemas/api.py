"""
backend.schemas.api — Request and Response models for the /api/v1/bill endpoints.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PipelineStatusEnum(str, enum.Enum):
    """Granular state machine for bill upload processing."""
    UPLOADED = "UPLOADED"
    OCR_RUNNING = "OCR_RUNNING"
    OCR_COMPLETED = "OCR_COMPLETED"
    PARSING = "PARSING"
    VALIDATING = "VALIDATING"
    ANALYTICS = "ANALYTICS"
    CACHED = "CACHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BillUploadResponse(BaseModel):
    """Response payload returned immediately upon POST /api/v1/bill/upload."""
    success: bool = Field(True, description="Request status flag")
    task_id: str = Field(..., description="Asynchronous processing task ID")
    bill_id: str = Field(..., description="Unique bill record UUID")
    bill_hash: str = Field(..., description="SHA-256 binary digest of uploaded file")
    status: PipelineStatusEnum = Field(PipelineStatusEnum.UPLOADED, description="Initial pipeline state")
    message: str = Field("Bill uploaded successfully and processing initiated.", description="User message")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC upload timestamp",
    )


class BillStatusResponse(BaseModel):
    """Response payload returned by GET /api/v1/bill/status."""
    success: bool = Field(True, description="Request status flag")
    task_id: str = Field(..., description="Processing task ID")
    bill_id: str = Field(..., description="Unique bill UUID")
    bill_hash: str = Field(..., description="SHA-256 digest")
    status: PipelineStatusEnum = Field(..., description="Current granular pipeline state")
    progress_pct: int = Field(0, ge=0, le=100, description="Pipeline completion percentage (0-100%)")
    stage_message: str = Field("", description="Current processing stage description")
    error: Optional[str] = Field(None, description="Error message if status is FAILED")
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC last update timestamp",
    )


class RecalculateRequest(BaseModel):
    """Payload for POST /api/v1/bill/recalculate."""
    rate_overrides: Dict[str, float] = Field(
        default_factory=dict,
        description="Rate schedule overrides e.g. {'bgs_rate': 0.12, 'distribution_rate': 0.05}",
    )
    usage_multiplier: float = Field(
        1.0, ge=0.1, le=5.0, description="Volumetric usage scaling factor (e.g. 0.85 for 15% conservation)"
    )
    weather_scenario: Optional[str] = Field(
        None, description="Preset weather scenario e.g. 'hot_summer' or 'cold_winter'"
    )


class APIErrorResponse(BaseModel):
    """Standardized API error response payload."""
    success: bool = Field(False, description="Success status flag")
    error_code: str = Field(..., description="Machine-readable error code string")
    message: str = Field(..., description="Human-readable exception summary")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic payload details")
    correlation_id: str = Field("", description="Tracing correlation ID")
