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
from typing import Callable, NamedTuple

from orchestration.tasks import (
    run_etl_pipeline_task,
    retrain_forecast_models_task,
    update_elasticity_model_task,
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
        logger.info("Background scheduler stopped.")

    def _run_loop(self) -> None:
        """Main loop that evaluates when jobs need execution."""
        # Record startup times for each job to avoid running everything at exact startup
        job_states = {
            job.name: {
                "target": job.target,
                "interval": job.interval_seconds,
                "last_run": datetime.min
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
                    logger.info(f"Scheduler triggering job '{name}'")
                    try:
                        state["target"]()
                    except Exception as e:
                        logger.error(f"Error executing job '{name}': {e}", exc_info=True)
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

# 2. Retrain forecasting models weekly (604800 seconds)
_scheduler.add_job(
    name="Retrain Forecasting Models",
    target=retrain_forecast_models_task,
    interval_seconds=604800,
)

# 3. Update demand response elasticity coefficients weekly
_scheduler.add_job(
    name="Update Elasticity Model",
    target=update_elasticity_model_task,
    interval_seconds=604800,
)


def start_scheduler() -> None:
    """Start the global scheduler."""
    _scheduler.start()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    _scheduler.stop()
