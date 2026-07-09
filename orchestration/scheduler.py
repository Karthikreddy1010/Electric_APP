"""
ETL & ML Scheduler — manages scheduled background jobs (ETL, model retraining).

Implements a lightweight, robust background thread loop to run jobs at specified intervals.
Does not require external dependencies like APScheduler.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, NamedTuple, Optional

from orchestration.tasks import (
    run_etl_pipeline_task,
    retrain_forecast_models_task,
    update_elasticity_model_task,
    fetch_eia_demand_task,
    sync_eia861m_task,
    sync_openei_tariffs_task,
    sync_eia930_task,
)

logger = logging.getLogger(__name__)


class ScheduledJob(NamedTuple):
    name: str
    target: Callable[[], None]
    interval_seconds: int
    last_run: datetime = None


class BackgroundScheduler:
    """Lightweight background scheduler running on a daemon thread."""

    def __init__(self):
        self._jobs: list[ScheduledJob] = []
        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ElectricTaskWorker")

    def add_job(self, name: str, target: Callable[[], None], interval_seconds: int) -> None:
        """Register a job to run periodically."""
        self._jobs.append(ScheduledJob(name=name, target=target, interval_seconds=interval_seconds))
        logger.info(f"Registered background job: '{name}' (every {interval_seconds}s)")

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler is already running.")
            return

        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="ElectricAIScheduler", daemon=True)
        self._thread.start()
        logger.info("Background scheduler started successfully.")

    def stop(self) -> None:
        """Gracefully stop the background scheduler."""
        if not self._thread or not self._thread.is_alive():
            return
        
        logger.info("Stopping background scheduler...")
        self._shutdown_event.set()
        self._thread.join(timeout=5.0)
        self._executor.shutdown(wait=False)
        logger.info("Background scheduler stopped.")

    def _run_job_with_retry(self, name: str, target: Callable) -> None:
        """Run task with exponential backoff retry logic for fetching/syncing tasks."""
        is_sync_task = any(kw in name.lower() for kw in ["sync", "fetch", "ingestion"])
        max_retries = 3 if is_sync_task else 0
        backoff_factor = 2.0
        initial_delay = 5.0
        
        retries = 0
        while not self._shutdown_event.is_set():
            try:
                logger.info(f"Worker running task '{name}' (attempt {retries + 1}/{max_retries + 1})")
                target()
                logger.info(f"Task '{name}' completed successfully.")
                break
            except Exception as e:
                if retries < max_retries and not self._shutdown_event.is_set():
                    delay = initial_delay * (backoff_factor ** retries)
                    logger.warning(
                        f"Task '{name}' failed with error: {e}. "
                        f"Retrying in {delay:.1f} seconds (retry {retries + 1}/{max_retries})..."
                    )
                    retries += 1
                    # Sleep in small increments to respond to shutdown event quickly
                    for _ in range(int(delay)):
                        if self._shutdown_event.is_set():
                            break
                        time.sleep(1)
                else:
                    logger.error(f"Task '{name}' failed after {max_retries} retries: {e}", exc_info=True)
                    break

    def _run_loop(self) -> None:
        """Main loop that evaluates when jobs need execution."""
        # Record startup times for each job to avoid running everything at exact startup
        job_states = {
            job.name: {
                "target": job.target,
                "interval": job.interval_seconds,
                "last_run": datetime.now()
            }
            for job in self._jobs
        }

        # Let the API startup settle
        time.sleep(5)

        while not self._shutdown_event.is_set():
            now = datetime.now()
            
            for name, state in job_states.items():
                if self._shutdown_event.is_set():
                    break
                
                # Check if interval elapsed
                elapsed = (now - state["last_run"]).total_seconds()
                if elapsed >= state["interval"]:
                    logger.info(f"Scheduler submitting job '{name}' to worker pool")
                    try:
                        self._executor.submit(self._run_job_with_retry, name, state["target"])
                    except Exception as e:
                        logger.error(f"Failed to submit job '{name}' to worker pool: {e}")
                    state["last_run"] = datetime.now()

            # Sleep in small increments to remain responsive to shutdown requests
            for _ in range(30):
                if self._shutdown_event.is_set():
                    break
                time.sleep(1)


# Global scheduler instance
_scheduler = BackgroundScheduler()

# Add standard jobs:
# 1. Run ETL pipeline every 24 hours (86400 seconds)
_scheduler.add_job(
    name="ETL Pipeline Ingestion",
    target=run_etl_pipeline_task,
    interval_seconds=86400,
)

# 2. Fetch fresh EIA demand data + retrain forecast models daily (86400 seconds)
_scheduler.add_job(
    name="Fetch EIA Demand + Retrain Forecast",
    target=fetch_eia_demand_task,
    interval_seconds=86400,
)

# 3. Update demand response elasticity coefficients weekly
_scheduler.add_job(
    name="Update Elasticity Model",
    target=update_elasticity_model_task,
    interval_seconds=604800,
)

# 4. Sync EIA-861M monthly utility data every 30 days
_scheduler.add_job(
    name="EIA-861M Monthly Sync",
    target=sync_eia861m_task,
    interval_seconds=2592000,
)

# 5. Sync OpenEI utility tariff metadata every 30 days
_scheduler.add_job(
    name="OpenEI Tariffs Sync",
    target=sync_openei_tariffs_task,
    interval_seconds=2592000,
)

# 6. Sync EIA-930 hourly grid operations data every 1 hour
_scheduler.add_job(
    name="EIA-930 Hourly Sync",
    target=sync_eia930_task,
    interval_seconds=3600,
)


def start_scheduler() -> None:
    """Start the global scheduler."""
    _scheduler.start()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    _scheduler.stop()
