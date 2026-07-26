"""
backend.api.routes.bill_routes — Phase 1 Enterprise Bill API routes.

Provides versioned endpoints under /api/v1/bill/*:
- POST /api/v1/bill/upload
- GET  /api/v1/bill/status
- GET  /api/v1/bill/analytics/{bill_id}
- POST /api/v1/bill/recalculate
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Form
from backend.schemas.api import (
    BillUploadResponse,
    BillStatusResponse,
    RecalculateRequest,
    APIErrorResponse,
)
from backend.schemas.analytics import AnalyticsResult
from backend.services.bill_pipeline_service import bill_pipeline_service, BillPipelineService
from backend.utils.exceptions import ElectricAIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bill", tags=["phase1-bill-analytics"])
legacy_router = APIRouter(prefix="/bill", tags=["phase1-bill-analytics-legacy"])


@router.post(
    "/upload",
    response_model=BillUploadResponse,
    summary="Upload utility bill PDF/image for processing",
)
@legacy_router.post("/upload-v1", response_model=BillUploadResponse)
async def upload_bill_v1(
    file: Optional[UploadFile] = File(None),
    dev_mock: bool = Form(False),
) -> BillUploadResponse:
    """Upload PDF/image bill and initiate asynchronous processing pipeline."""
    try:
        if dev_mock or not file:
            content_bytes = b"%PDF-1.4 Mock Electricity Bill PSE&G Usage 750 kWh Total $138.90"
            filename = "synthetic_bill_000001.pdf"
        else:
            content_bytes = await file.read()
            filename = file.filename or "uploaded_bill.pdf"

        return await bill_pipeline_service.handle_upload(content_bytes, filename=filename)

    except ElectricAIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Upload endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status",
    response_model=BillStatusResponse,
    summary="Get pipeline status for a processing task",
)
@legacy_router.get("/status-v1", response_model=BillStatusResponse)
async def get_bill_status_v1(
    task_id: str = Query(..., description="Asynchronous task ID")
) -> BillStatusResponse:
    """Retrieve granular pipeline execution state by task ID."""
    try:
        return await bill_pipeline_service.get_status(task_id)
    except ElectricAIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/analytics/{bill_id}",
    response_model=AnalyticsResult,
    summary="Retrieve strongly typed AnalyticsResult for a bill",
)
@legacy_router.get("/analytics-v1/{bill_id}", response_model=AnalyticsResult)
async def get_bill_analytics_v1(bill_id: str) -> AnalyticsResult:
    """Fetch complete AnalyticsResult JSON payload for a bill."""
    try:
        return await bill_pipeline_service.get_analytics(bill_id)
    except ElectricAIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/recalculate",
    response_model=AnalyticsResult,
    summary="Recalculate analytics with modified parameters",
)
@legacy_router.post("/recalculate-v1", response_model=AnalyticsResult)
async def recalculate_bill_v1(
    bill_id: str = Query("bill-default", description="Target bill ID"),
    body: RecalculateRequest = RecalculateRequest(),
) -> AnalyticsResult:
    """Recalculate analytics for a bill with rate overrides and usage scaling."""
    try:
        return await bill_pipeline_service.recalculate_analytics(
            bill_id=bill_id,
            rate_overrides=body.rate_overrides,
            usage_multiplier=body.usage_multiplier,
        )
    except ElectricAIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
