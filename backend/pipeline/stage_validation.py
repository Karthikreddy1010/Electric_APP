"""
backend.pipeline.stage_validation — Multi-stage validation gates for bill processing pipeline.

Guarantees that malformed stage outputs are caught immediately before propagating
to downstream pipeline stages.
"""
from __future__ import annotations

from typing import Dict, Any
from backend.schemas.ocr import OCRResult
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import AnalyticsResult
from backend.utils.exceptions import ValidationException


def validate_ocr_stage(ocr_result: OCRResult) -> Dict[str, Any]:
    """Validate Stage 1: OCR Extraction output."""
    if not ocr_result:
        raise ValidationException("OCR Stage Validation Failed: Null OCRResult payload.")
    if not ocr_result.raw_text or len(ocr_result.raw_text.strip()) < 10:
        raise ValidationException(
            "OCR Stage Validation Failed: Insufficient plain text extracted from document.",
            details={"raw_text_length": len(ocr_result.raw_text) if ocr_result.raw_text else 0},
        )
    return {"stage": "ocr", "passed": True, "confidence": ocr_result.confidence_score}


def validate_parser_stage(parsed_bill: ParsedBill) -> Dict[str, Any]:
    """Validate Stage 2: Bill Parser output."""
    if not parsed_bill:
        raise ValidationException("Parser Stage Validation Failed: Null ParsedBill payload.")
    if parsed_bill.usage_kwh <= 0:
        raise ValidationException(
            "Parser Stage Validation Failed: Usage kWh must be greater than zero.",
            details={"usage_kwh": parsed_bill.usage_kwh},
        )
    if parsed_bill.total_bill <= 0:
        raise ValidationException(
            "Parser Stage Validation Failed: Total bill amount must be greater than zero.",
            details={"total_bill": parsed_bill.total_bill},
        )
    return {"stage": "parser", "passed": True, "utility": parsed_bill.utility}


def validate_analytics_stage(analytics_result: AnalyticsResult) -> Dict[str, Any]:
    """Validate Stage 3: Deterministic Analytics Engine output."""
    if not analytics_result:
        raise ValidationException("Analytics Stage Validation Failed: Null AnalyticsResult payload.")
    
    # Verify accounting identity
    calc_sum = round(
        analytics_result.component_breakdown.fixed_total
        + analytics_result.component_breakdown.variable_total
        + analytics_result.component_breakdown.taxes_total,
        2,
    )
    actual = round(analytics_result.component_breakdown.total_bill, 2)
    
    if abs(calc_sum - actual) > 0.05:
        raise ValidationException(
            f"Analytics Stage Validation Failed: Accounting identity sum (${calc_sum}) != actual bill (${actual}).",
            details={"calculated_total": calc_sum, "actual_total": actual},
        )
    return {"stage": "analytics", "passed": True, "total_bill": actual}
