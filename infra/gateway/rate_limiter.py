"""
Phase 3 — AI Gateway: Rate Limiter.

Token-bucket rate limiter enforcing per-tenant, per-tier request quotas.
"""
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    In-memory token bucket rate limiter.

    Each tenant/tier combination gets an independent bucket that refills
    at a constant rate. Production deployments should use Redis-backed
    distributed rate limiting.
    """

    # Default tier limits (requests per minute)
    DEFAULT_LIMITS = {
        "free": 20,
        "pro": 200,
        "enterprise": 2000,
    }

    def __init__(self):
        self._buckets: Dict[str, Dict] = {}

    def _get_bucket(self, key: str, tier: str = "free") -> Dict:
        if key not in self._buckets:
            limit = self.DEFAULT_LIMITS.get(tier, 20)
            self._buckets[key] = {
                "tokens": float(limit),
                "max_tokens": float(limit),
                "refill_rate": limit / 60.0,  # tokens per second
                "last_refill": time.monotonic()
            }
        return self._buckets[key]

    def _refill(self, bucket: Dict) -> None:
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + elapsed * bucket["refill_rate"]
        )
        bucket["last_refill"] = now

    def allow(self, tenant_id: str, tier: str = "free", cost: float = 1.0) -> bool:
        """Check if a request is allowed under the rate limit."""
        key = f"{tenant_id}:{tier}"
        bucket = self._get_bucket(key, tier)
        self._refill(bucket)

        if bucket["tokens"] >= cost:
            bucket["tokens"] -= cost
            return True

        logger.warning(f"RateLimiter: tenant={tenant_id} tier={tier} DENIED (tokens={bucket['tokens']:.1f})")
        return False

    def get_remaining(self, tenant_id: str, tier: str = "free") -> int:
        key = f"{tenant_id}:{tier}"
        bucket = self._get_bucket(key, tier)
        self._refill(bucket)
        return int(bucket["tokens"])


# Global singleton
rate_limiter = TokenBucketRateLimiter()
