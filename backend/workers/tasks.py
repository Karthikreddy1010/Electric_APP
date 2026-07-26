"""
backend.workers.tasks — Asynchronous task definitions.

Implements background tasks for long-running bill processing and analytics calculations.
Includes synchronous fallback runner for non-Celery environments.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from backend.workers.celery_app import celery_app, CELERY_AVAILABLE
from backend.pipeline.orchestrator import pipeline_orchestrator
from backend.cache.redis_cache import versioned_cache
from backend.storage.object_storage import object_storage
from backend.schemas.api import PipelineStatusEnum

logger = logging.getLogger(__name__)


def execute_bill_pipeline_task(
    task_id: str,
    bill_hash: str,
    file_bytes: bytes,
    filename: str = "uploaded_bill.pdf",
    rate_overrides: Optional[Dict[str, float]] = None,
    usage_multiplier: float = 1.0,
) -> Dict[str, Any]:
    """Synchronous core pipeline task runner used by both Celery worker and local fallback."""
    logger.info(f"Task [{task_id}]: Starting bill pipeline execution for hash {bill_hash}")

    def update_task_status(status_str: str, progress_pct: int, msg: str):
        logger.info(f"Task [{task_id}] Status: {status_str} ({progress_pct}%) - {msg}")

    try:
        # Run pipeline orchestrator
        analytics = pipeline_orchestrator.process_file_bytes(
            file_bytes=file_bytes,
            filename=filename,
            rate_overrides=rate_overrides,
            usage_multiplier=usage_multiplier,
            status_callback=update_task_status,
        )

        # Cache result
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(versioned_cache.set_analytics(bill_hash, analytics))
            else:
                loop.run_until_complete(versioned_cache.set_analytics(bill_hash, analytics))
        except Exception as cache_err:
            logger.warning(f"Failed to cache analytics result in worker: {cache_err}")

        # Store analytics JSON artifact
        object_storage.store_analytics_json(
            analytics_data=analytics.model_dump(mode="json"),
            bill_hash=bill_hash,
            tenant_id=analytics.customer_id,
            analytics_version=analytics.analytics_version,
        )

        return {
            "success": True,
            "task_id": task_id,
            "bill_hash": bill_hash,
            "status": PipelineStatusEnum.COMPLETED.value,
            "analytics": analytics.model_dump(mode="json"),
        }

    except Exception as e:
        logger.error(f"Task [{task_id}] execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "task_id": task_id,
            "bill_hash": bill_hash,
            "status": PipelineStatusEnum.FAILED.value,
            "error": str(e),
        }


# Register Celery task if Celery is available
if CELERY_AVAILABLE and celery_app:
    @celery_app.task(name="tasks.process_bill_async", bind=True)
    def process_bill_async(
        self,
        bill_hash: str,
        file_bytes: bytes,
        filename: str = "uploaded_bill.pdf",
        rate_overrides: Optional[Dict[str, float]] = None,
        usage_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        task_id = self.request.id or f"task-{bill_hash[:8]}"
        return execute_bill_pipeline_task(
            task_id=task_id,
            bill_hash=bill_hash,
            file_bytes=file_bytes,
            filename=filename,
            rate_overrides=rate_overrides,
            usage_multiplier=usage_multiplier,
        )
