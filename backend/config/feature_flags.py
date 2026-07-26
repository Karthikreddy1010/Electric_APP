"""
backend.config.feature_flags — Phase-aware feature toggles.

Controls which backend capabilities are active for Phase 1 vs Phase 2+.
All flags default to Phase 1 safe values. Override via environment variables.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FeatureFlags(BaseSettings):
    """Runtime feature toggles for phased capability rollout."""

    # Phase 1: enabled
    enable_ocr_pipeline: bool = Field(
        default=True, description="Enable OCR text extraction pipeline"
    )
    enable_bill_parser: bool = Field(
        default=True, description="Enable regex-based bill parser"
    )
    enable_analytics_engine: bool = Field(
        default=True, description="Enable deterministic analytics engine"
    )
    enable_redis_cache: bool = Field(
        default=True, description="Enable Redis caching layer"
    )
    enable_celery_workers: bool = Field(
        default=True, description="Enable Celery async workers"
    )
    enable_object_storage: bool = Field(
        default=True, description="Enable object storage for artifacts"
    )
    enable_sync_fallback: bool = Field(
        default=True,
        description="Fall back to synchronous processing when Celery unavailable",
    )

    # Phase 2: disabled by default
    enable_llm_orchestration: bool = Field(
        default=False, description="Enable LLM-powered explanations (Phase 2)"
    )
    enable_ml_forecasting: bool = Field(
        default=False,
        description="Enable ML forecast models (Prophet/SARIMA) (Phase 2)",
    )
    enable_rag_retrieval: bool = Field(
        default=False, description="Enable RAG document retrieval (Phase 2)"
    )
    enable_streaming_responses: bool = Field(
        default=False, description="Enable SSE streaming responses (Phase 2)"
    )
    enable_ml_recommendations: bool = Field(
        default=False, description="Enable ML-ranked recommendations (Phase 2)"
    )

    # Phase 3: disabled by default
    enable_gpu_inference: bool = Field(
        default=False, description="Enable GPU-accelerated inference (Phase 3)"
    )
    enable_distributed_tracing: bool = Field(
        default=False,
        description="Enable OpenTelemetry distributed tracing (Phase 3)",
    )

    class Config:
        env_prefix = "FEATURE_"
        env_file = str(PROJECT_ROOT / ".env")
        extra = "ignore"


feature_flags = FeatureFlags()
