"""
Celery configuration for background task processing.
Uses Redis as the message broker and results backend.
Falls back to synchronous "eager" execution if Redis is unreachable.
"""
from __future__ import annotations

import logging
import os
import importlib

try:
    _celery_mod = importlib.import_module("celery")
    Celery = getattr(_celery_mod, "Celery")
    HAS_CELERY = True
except Exception:
    HAS_CELERY = False

    class DummyCeleryConf(dict):
        def update(self, *args, **kwargs):
            super().update(*args, **kwargs)

    class DummyCelery:
        def __init__(self, *args, **kwargs):
            self.conf = DummyCeleryConf()

        def task(self, *args, **kwargs):
            def decorator(f):
                f.delay = f
                return f
            return decorator

    Celery = DummyCelery

logger = logging.getLogger(__name__)

# Fetch connection settings
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "electric_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Configuration defaults
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="US/Eastern",
    enable_utc=True,
)

# Test Redis connection; fall back to eager execution if unavailable
try:
    import redis
    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2.0)
    client.ping()
    logger.info(f"Celery successfully connected to Redis broker at {REDIS_URL.split('/')[-1]}")
except Exception as e:
    logger.warning(
        f"Redis broker at {REDIS_URL} is unreachable ({e}). "
        f"Configuring Celery to run tasks synchronously (task_always_eager=True)."
    )
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
