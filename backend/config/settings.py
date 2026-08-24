"""
backend.config.settings — Pydantic BaseSettings for all backend modules.

Centralizes all configurable parameters (Redis, Celery, storage paths,
analytics thresholds) into validated, environment-aware settings classes.
Delegates to the existing config/settings.py for DB, API, and LLM settings
to maintain backward compatibility.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class RedisSettings(BaseSettings):
    """Redis connection configuration for cache and Celery broker."""

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching layer",
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Redis URL for Celery task broker",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Redis URL for Celery result backend",
    )
    default_ttl: int = Field(
        default=3600,
        ge=60,
        description="Default cache TTL in seconds",
    )
    ocr_ttl: int = Field(
        default=86400,
        ge=300,
        description="TTL for cached OCR results (24h default)",
    )
    analytics_ttl: int = Field(
        default=7200,
        ge=300,
        description="TTL for cached analytics results (2h default)",
    )
    max_connections: int = Field(
        default=20,
        ge=1,
        description="Maximum Redis connection pool size",
    )

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


class StorageSettings(BaseSettings):
    """Object storage configuration for PDFs, OCR, and analytics artifacts."""

    backend: str = Field(
        default="local",
        description="Storage backend type: 'local' or 's3'",
    )
    local_root: str = Field(
        default=str(PROJECT_ROOT / "storage"),
        description="Root directory for local file storage",
    )
    s3_bucket: str = Field(default="", description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="AWS region")
    s3_endpoint_url: str = Field(
        default="", description="S3 endpoint URL (for MinIO)"
    )

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


class AnalyticsSettings(BaseSettings):
    """Thresholds and parameters for the deterministic analytics engine."""

    anomaly_z_threshold: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="Z-score threshold for anomaly detection",
    )
    trend_window_short: int = Field(
        default=3,
        ge=2,
        description="Short-term moving average window (months)",
    )
    trend_window_long: int = Field(
        default=6,
        ge=3,
        description="Long-term moving average window (months)",
    )
    savings_conservation_pct: float = Field(
        default=0.10,
        ge=0.01,
        le=0.50,
        description="Default conservation savings percentage",
    )
    recommendation_max_items: int = Field(
        default=10,
        ge=1,
        description="Maximum recommendation items to return",
    )
    weather_base_temp_f: float = Field(
        default=65.0,
        description="Base temperature (°F) for HDD/CDD calculations",
    )

    model_config = SettingsConfigDict(
        env_prefix="ANALYTICS_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


class CelerySettings(BaseSettings):
    """Celery worker configuration."""

    task_serializer: str = Field(default="json")
    result_serializer: str = Field(default="json")
    accept_content: list[str] = Field(default=["json"])
    timezone: str = Field(default="US/Eastern")
    task_track_started: bool = Field(default=True)
    task_time_limit: int = Field(
        default=300, description="Hard time limit per task in seconds"
    )
    task_soft_time_limit: int = Field(
        default=240, description="Soft time limit per task in seconds"
    )
    worker_concurrency: int = Field(
        default=4, ge=1, description="Number of concurrent worker processes"
    )

    model_config = SettingsConfigDict(
        env_prefix="CELERY_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


# ── Singleton instances ──────────────────────────────────────────────────────

redis_settings = RedisSettings()
storage_settings = StorageSettings()
analytics_settings = AnalyticsSettings()
celery_settings = CelerySettings()
