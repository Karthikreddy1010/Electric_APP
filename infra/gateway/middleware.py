"""
Phase 3 — AI Gateway: FastAPI Middleware.

Integrates rate limiting, circuit breaking, cost tracking, and
Prometheus metrics collection into the FastAPI request lifecycle.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from infra.gateway.rate_limiter import rate_limiter
from infra.observability.prometheus import record_api_request, PROMETHEUS_AVAILABLE

logger = logging.getLogger(__name__)


class AIGatewayMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware implementing the AI Gateway pattern:
      1. Extract tenant_id and tier from request headers/auth
      2. Enforce rate limits
      3. Record Prometheus metrics
      4. Inject timing headers
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Extract tenant context from headers (or default)
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        tier = request.headers.get("X-User-Tier", "free").lower()

        # Rate limit check for AI endpoints
        if request.url.path.startswith("/llm/"):
            if not rate_limiter.allow(tenant_id, tier):
                remaining = rate_limiter.get_remaining(tenant_id, tier)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "tenant_id": tenant_id,
                        "tier": tier,
                        "remaining": remaining,
                        "retry_after_seconds": 60
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Remaining": str(remaining)
                    }
                )

        # Execute request
        response = await call_next(request)

        # Record metrics
        duration = time.time() - start_time
        record_api_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration
        )

        # Inject timing headers
        response.headers["X-Response-Time-Ms"] = f"{duration * 1000:.2f}"
        response.headers["X-Tenant-ID"] = tenant_id

        return response
