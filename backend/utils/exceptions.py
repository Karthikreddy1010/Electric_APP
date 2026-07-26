"""
backend.utils.exceptions — Domain exception hierarchy.

Provides structured, typed exceptions for every pipeline stage so that
error handlers can return precise HTTP status codes and diagnostic payloads.
Each exception carries a machine-readable error_code for downstream logging.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class ElectricAIException(Exception):
    """Base exception for all ElectricAI backend errors."""

    error_code: str = "ELECTRIC_AI_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception for API error responses."""
        payload: Dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.cause:
            payload["cause"] = str(self.cause)
        return payload


class OCRException(ElectricAIException):
    """Raised when OCR text extraction fails or returns unusable output."""

    error_code = "OCR_EXTRACTION_FAILED"
    status_code = 422


class ValidationException(ElectricAIException):
    """Raised when data fails schema or stage validation checks."""

    error_code = "VALIDATION_FAILED"
    status_code = 422


class ParserException(ElectricAIException):
    """Raised when bill parsing fails to extract required fields."""

    error_code = "PARSER_EXTRACTION_FAILED"
    status_code = 422


class AnalyticsException(ElectricAIException):
    """Raised when deterministic analytics calculations fail."""

    error_code = "ANALYTICS_CALCULATION_FAILED"
    status_code = 500


class StorageException(ElectricAIException):
    """Raised when object storage operations fail."""

    error_code = "STORAGE_OPERATION_FAILED"
    status_code = 502


class CacheException(ElectricAIException):
    """Raised when Redis cache operations fail critically."""

    error_code = "CACHE_OPERATION_FAILED"
    status_code = 502


class PipelineException(ElectricAIException):
    """Raised when the bill processing pipeline encounters an unrecoverable error."""

    error_code = "PIPELINE_FAILED"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        stage: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)
        self.stage = stage
        self.details["stage"] = stage


class BillNotFoundException(ElectricAIException):
    """Raised when a requested bill record does not exist."""

    error_code = "BILL_NOT_FOUND"
    status_code = 404


class ConfigurationException(ElectricAIException):
    """Raised when required configuration is missing or invalid."""

    error_code = "CONFIGURATION_ERROR"
    status_code = 500
