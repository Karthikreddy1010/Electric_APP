"""
backend.pipeline.orchestrator — Dedicated Pipeline Orchestrator.

Orchestrates stage-by-stage execution with multi-stage validation gates:
Upload -> OCR -> Validation1 -> Parser -> Validation2 -> Analytics -> Validation3 -> Cache -> Storage -> Response.
Enforces granular pipeline state machine updates.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any
from backend.ocr.engine import OCREngine, ocr_engine
from backend.bill_parser.parser import BillParser, bill_parser
from backend.analytics.engine import AnalyticsEngine, analytics_engine
from backend.pipeline.stage_validation import (
    validate_ocr_stage,
    validate_parser_stage,
    validate_analytics_stage,
)
from backend.schemas.analytics import AnalyticsResult
from backend.schemas.api import PipelineStatusEnum
from backend.utils.exceptions import PipelineException, ValidationException

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Dedicated Pipeline Orchestrator managing end-to-end bill processing.
    Injects OCR, Parser, and Analytics dependencies for clean testing.
    """

    def __init__(
        self,
        ocr: Optional[OCREngine] = None,
        parser: Optional[BillParser] = None,
        analytics: Optional[AnalyticsEngine] = None,
    ) -> None:
        self.ocr = ocr or ocr_engine
        self.parser = parser or bill_parser
        self.analytics = analytics or analytics_engine

    def process_file_bytes(
        self,
        file_bytes: bytes,
        filename: str = "uploaded_bill.pdf",
        rate_overrides: Optional[Dict[str, float]] = None,
        usage_multiplier: float = 1.0,
        status_callback: Optional[Any] = None,
    ) -> AnalyticsResult:
        """
        Execute full bill pipeline with stage validation gates.
        
        Args:
            file_bytes: PDF/image binary content.
            filename: Original filename.
            rate_overrides: Tariff schedule rate modification overrides.
            usage_multiplier: Volumetric usage scale multiplier.
            status_callback: Optional callable(status_str, progress_pct, message) for state tracking.
            
        Returns:
            Validated AnalyticsResult object.
        """
        def update_state(status: PipelineStatusEnum, progress: int, msg: str):
            logger.info(f"Pipeline State [{status.value}] ({progress}%): {msg}")
            if status_callback:
                try:
                    status_callback(status.value, progress, msg)
                except Exception as cb_err:
                    logger.warning(f"Status callback failed: {cb_err}")

        update_state(PipelineStatusEnum.UPLOADED, 10, "Document uploaded and processing queued")

        try:
            # Stage 1: OCR Extraction
            update_state(PipelineStatusEnum.OCR_RUNNING, 25, "Running OCR text extraction")
            ocr_res = self.ocr.extract_from_bytes(file_bytes, filename=filename)
            
            # Validation Gate 1
            validate_ocr_stage(ocr_res)
            update_state(PipelineStatusEnum.OCR_COMPLETED, 40, "OCR extraction validated")

            # Stage 2: Bill Parsing
            update_state(PipelineStatusEnum.PARSING, 50, "Parsing layout & line items")
            parsed_bill = self.parser.parse(ocr_res)

            # Validation Gate 2
            update_state(PipelineStatusEnum.VALIDATING, 65, "Validating parsed line items")
            validate_parser_stage(parsed_bill)

            # Stage 3: Deterministic Analytics Engine
            update_state(PipelineStatusEnum.ANALYTICS, 80, "Calculating deterministic analytics")
            analytics_res = self.analytics.calculate(
                parsed_bill,
                rate_overrides=rate_overrides,
                usage_multiplier=usage_multiplier,
            )

            # Validation Gate 3
            validate_analytics_stage(analytics_res)

            update_state(PipelineStatusEnum.COMPLETED, 100, "Bill processing completed successfully")
            return analytics_res

        except Exception as e:
            update_state(PipelineStatusEnum.FAILED, 0, f"Pipeline failed: {str(e)}")
            logger.error(f"PipelineOrchestrator failed during execution: {e}", exc_info=True)
            if isinstance(e, (PipelineException, ValidationException)):
                raise
            raise PipelineException(f"Unrecoverable pipeline error: {e}", cause=e)


# Singleton instance
pipeline_orchestrator = PipelineOrchestrator()
