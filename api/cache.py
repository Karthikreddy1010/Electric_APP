"""
Redis Cache — decorator-based caching for FastAPI endpoints.

Features:
    - @cached(ttl=300) decorator for endpoint-level caching
    - Automatic key generation from request parameters
    - JSON serialization of response objects
    - Cache invalidation by pattern
    - Graceful fallback to in-memory dict if Redis unavailable

Usage:
    from api.cache import cached, get_cache

    @router.get("/expensive-endpoint")
    @cached(ttl=600)
    async def expensive_endpoint(param1: str, param2: int):
        # This response will be cached for 10 minutes
        return {"result": compute_expensive_thing()}

    # Invalidate cache
    cache = get_cache()
    await cache.invalidate_pattern("expensive-endpoint:*")
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract cache backend interface."""

    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def invalidate_pattern(self, pattern: str) -> int:
        raise NotImplementedError

    async def health_check(self) -> dict:
        raise NotImplementedError

    async def close(self) -> None:
        pass


class RedisCache(CacheBackend):
    """Redis-backed cache using aioredis (redis-py async)."""

    def __init__(self, redis_client):
        self._redis = redis_client
        self._hit_count = 0
        self._miss_count = 0

    async def get(self, key: str) -> Optional[str]:
        try:
            value = await self._redis.get(key)
            if value:
                self._hit_count += 1
                logger.debug(f"Cache HIT: {key}")
                return value.decode() if isinstance(value, bytes) else value
            self._miss_count += 1
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"Redis GET failed: {e}")
            self._miss_count += 1
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        try:
            await self._redis.setex(key, ttl, value)
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Redis SET failed: {e}")

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE failed: {e}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern."""
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} keys matching '{pattern}'")
            return len(keys)
        except Exception as e:
            logger.warning(f"Redis pattern invalidation failed: {e}")
            return 0

    async def health_check(self) -> dict:
        try:
            await self._redis.ping()
            info = await self._redis.info("memory")
            return {
                "status": "healthy",
                "backend": "redis",
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "hits": self._hit_count,
                "misses": self._miss_count,
                "hit_rate": round(
                    self._hit_count / max(self._hit_count + self._miss_count, 1) * 100, 1
                ),
            }
        except Exception as e:
            return {"status": "unhealthy", "backend": "redis", "error": str(e)}

    async def close(self) -> None:
        try:
            await self._redis.close()
        except Exception:
            pass


class InMemoryCache(CacheBackend):
    """
    In-memory LRU cache fallback.
    Used when Redis is unavailable or for local development.
    """

    def __init__(self, max_size: int = 1000):
        self._store: dict[str, tuple[str, float]] = {}  # key -> (value, expiry_time)
        self._max_size = max_size
        self._hit_count = 0
        self._miss_count = 0

    async def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            self._miss_count += 1
            return None
        value, expiry = entry
        if time.time() > expiry:
            del self._store[key]
            self._miss_count += 1
            return None
        self._hit_count += 1
        return value

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        # Evict oldest if at capacity
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest]
        self._store[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def invalidate_pattern(self, pattern: str) -> int:
        import fnmatch
        keys_to_delete = [
            k for k in self._store if fnmatch.fnmatch(k, pattern)
        ]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    async def health_check(self) -> dict:
        return {
            "status": "healthy",
            "backend": "in_memory",
            "entries": len(self._store),
            "max_size": self._max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": round(
                self._hit_count / max(self._hit_count + self._miss_count, 1) * 100, 1
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON CACHE INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_cache: Optional[CacheBackend] = None


async def init_cache() -> CacheBackend:
    """
    Initialize the cache backend.
    Tries Redis first, falls back to in-memory.
    Called during FastAPI lifespan startup.
    """
    global _cache

    redis_url = os.environ.get("REDIS_URL", os.environ.get("API_REDIS_URL", ""))

    if redis_url:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True,
            )
            await client.ping()
            _cache = RedisCache(client)
            logger.info(f"Redis cache connected: {redis_url}")
            return _cache
        except Exception as e:
            logger.warning(f"Redis connection failed ({e}) — falling back to in-memory cache")

    _cache = InMemoryCache(max_size=2000)
    logger.info("Using in-memory cache (Redis not available)")
    return _cache


async def close_cache() -> None:
    """Shutdown the cache backend."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None


def get_cache() -> CacheBackend:
    """Get the current cache backend instance."""
    if _cache is None:
        # Return a temporary in-memory cache if not initialized
        return InMemoryCache(max_size=100)
    return _cache


# ─────────────────────────────────────────────────────────────────────────────
#  @cached DECORATOR
# ─────────────────────────────────────────────────────────────────────────────

def _make_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """Generate a deterministic cache key from function arguments."""
    # Serialize arguments to a stable string
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        if k in ("request", "response", "db", "session"):
            continue  # Skip non-serializable FastAPI objects
        key_parts.append(f"{k}={v}")
    raw = ":".join(key_parts)
    # Hash long keys
    if len(raw) > 200:
        raw = prefix + ":" + hashlib.md5(raw.encode()).hexdigest()
    return raw


def cached(ttl: int = 300, prefix: Optional[str] = None):
    """
    Cache decorator for async functions.

    Parameters
    ----------
    ttl : cache time-to-live in seconds (default: 5 minutes)
    prefix : optional key prefix (defaults to function name)

    Usage:
        @cached(ttl=600)
        async def expensive_computation(region: str, year: int):
            ...
    """
    def decorator(func: Callable):
        cache_prefix = prefix or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            key = _make_cache_key(cache_prefix, args, kwargs)

            # Try cache first
            cached_value = await cache.get(key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except (json.JSONDecodeError, TypeError):
                    pass  # Corrupted cache entry — recompute

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            try:
                from fastapi.encoders import jsonable_encoder
                serialized = json.dumps(jsonable_encoder(result), default=str)
                await cache.set(key, serialized, ttl)
            except (TypeError, ValueError) as e:
                logger.debug(f"Could not cache result for {key}: {e}")

            return result

        return wrapper
    return decorator
