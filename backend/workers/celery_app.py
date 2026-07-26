"""
backend.workers.celery_app — Celery application configuration.

Initializes the Celery app using Redis as broker and result backend.
Configured with task timeouts, serializer settings, and concurrency.
"""
from __future__ import annotations

import logging
from backend.config.settings import redis_settings, celery_settings

logger = logging.getLogger(__name__)

# Fallback Celery stub when celery package is omitted
try:
    from celery import Celery

    celery_app = Celery(
        "electric_ai_workers",
        broker=redis_settings.celery_broker_url,
        backend=redis_settings.celery_result_backend,
    )

    celery_app.conf.update(
        task_serializer=celery_settings.task_serializer,
        result_serializer=celery_settings.result_serializer,
        accept_content=celery_settings.accept_content,
        timezone=celery_settings.timezone,
        task_track_started=celery_settings.task_track_started,
        task_time_limit=celery_settings.task_time_limit,
        task_soft_time_limit=celery_settings.task_soft_time_limit,
        worker_concurrency=celery_settings.worker_concurrency,
    )
    CELERY_AVAILABLE = True
except ImportError:
    logger.warning("Celery package not installed. Running workers in synchronous fallback mode.")
    celery_app = None
    CELERY_AVAILABLE = False
