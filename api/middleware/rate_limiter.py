"""
Rate Limiter Middleware — protects the API against DDoS and brute force.

Limits requests per client IP address. Uses Redis when connected,
falling back to a fast thread-safe in-memory cache otherwise.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from api.cache import get_cache

logger = logging.getLogger(__name__)


class InMemoryLimiter:
    """Thread-safe sliding window rate limiter in memory."""

    def __init__(self, requests_limit: int = 100, window_seconds: int = 60):
        self.limit = requests_limit
        self.window = window_seconds
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            # Filter timestamps outside the window
            cutoff = now - self.window
            self._history[key] = [t for t in self._history[key] if t > cutoff]
            
            # Check limit
            if len(self._history[key]) >= self.limit:
                return True
                
            # Log this request
            self._history[key].append(now)
            return False


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    HTTP Rate Limiting Middleware.
    
    Default: 100 requests per 60 seconds per client IP.
    """

    def __init__(
        self,
        app,
        requests_limit: int = 100,
        window_seconds: int = 60
    ):
        super().__init__(app)
        self.limit = requests_limit
        self.window = window_seconds
        self._in_memory = InMemoryLimiter(requests_limit, window_seconds)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for static assets or health checks
        path = request.url.path
        if path.startswith("/static") or path == "/health" or path.startswith("/app"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown-client"
        
        # Build rate limiting key
        key = f"rate_limit:{client_ip}:{path}"
        
        # Check cache
        cache = get_cache()
        is_limited = False
        
        # If cache is Redis, try using Redis-based rate limiting
        # To avoid complex dependencies, we fall back to in-memory if not Redis
        if cache.__class__.__name__ == "RedisCache":
            try:
                # Retrieve Redis client from cache singleton wrapper
                redis = cache._redis
                # Increment the key count
                current = await redis.incr(key)
                if current == 1:
                    # Set expiry for the window
                    await redis.expire(key, self.window)
                if current > self.limit:
                    is_limited = True
            except Exception as e:
                logger.debug(f"Redis rate limiting failed: {e}. Falling back to memory.")
                is_limited = self._in_memory.is_rate_limited(client_ip)
        else:
            is_limited = self._in_memory.is_rate_limited(client_ip)

        if is_limited:
            logger.warning(f"Rate limit exceeded for client: {client_ip} on path {path}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )

        return await call_next(request)
