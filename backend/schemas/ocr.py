"""
backend.schemas.ocr — Pydantic schemas for raw OCR output and text block extractions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for extracted text elements."""
    x1: float = Field(0.0, description="Left coordinate")
    y1: float = Field(0.0, description="Top coordinate")
    x2: float = Field(0.0, description="Right coordinate")
    y2: float = Field(0.0, description="Bottom coordinate")


class OCRTextBlock(BaseModel):
    """Extracted text block or field entry from OCR processing."""
    field_name: str = Field(..., description="Target field identifier")
    ground_truth_value: Optional[str] = Field(None, description="Ground truth text if known")
    extracted_value: str = Field("", description="Raw text extracted by OCR")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="OCR confidence score")
    ocr_error_flag: bool = Field(False, description="Flag indicating potential extraction anomaly")
    bbox: Optional[str] = Field(None, description="Bounding box string representation 'x1,y1,x2,y2'")


class OCRResult(BaseModel):
    """Validated OCR extraction result payload."""
    bill_hash: str = Field(..., description="SHA-256 hash of the processed document")
    filename: str = Field("bill.pdf", description="Original filename")
    raw_text: str = Field("", description="Complete plain text extracted from document")
    page_count: int = Field(1, ge=1, description="Total document pages")
    field_blocks: List[OCRTextBlock] = Field(default_factory=list, description="Extracted field blocks")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Overall extraction confidence average")
    ocr_version: str = Field("1.0.0", description="OCR engine version tag")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Extraction timestamp")
    quality_flags: List[str] = Field(default_factory=list, description="Quality warnings or anomaly flags")
