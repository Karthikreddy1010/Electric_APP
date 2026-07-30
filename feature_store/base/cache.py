"""
Memory & Disk Caching Engine for Feature Store & Analytics
Caches heavy computations (rankings, rolling statistics, forecasts, spatial maps) with TTL invalidation.
"""
from __future__ import annotations
import time
import functools
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class FeatureStoreCache:
    def __init__(self, default_ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self.default_ttl:
                logger.debug(f"Cache HIT for key: {key}")
                return value
            else:
                logger.debug(f"Cache EXPIRED for key: {key}")
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = (time.time(), value)

    def clear(self):
        self._cache.clear()
        logger.info("FeatureStoreCache cleared.")


global_cache = FeatureStoreCache()


def memoize_feature(ttl: int = 3600):
    """Decorator to cache feature store query results."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_parts = [func.__name__]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)

            cached_val = global_cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            res = func(*args, **kwargs)
            global_cache.set(cache_key, res, ttl=ttl)
            return res

        return wrapper

    return decorator
