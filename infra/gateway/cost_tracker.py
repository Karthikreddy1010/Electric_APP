"""
Phase 3 — AI Gateway: Cost Tracker.

Tracks token usage and estimated cost per provider/tenant for
budget enforcement and cost-aware model routing.
"""
import time
import logging
import threading
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Cost per 1K tokens (output) by provider/model — kept up to date manually
_COST_TABLE = {
    "claude-3-5-sonnet-20241022": 15.00 / 1000,  # $15/MTok output
    "claude-3-haiku-20240307": 1.25 / 1000,
    "gpt-4o": 10.00 / 1000,
    "gpt-4o-mini": 0.60 / 1000,
    "gemini-1.5-pro": 5.00 / 1000,
    "vllm-local": 0.0,
    "sglang-local": 0.0,
    "ollama-local": 0.0,
    "mock-model": 0.0,
}


class CostTracker:
    """
    Tracks cumulative token usage and cost per tenant and provider.
    Thread-safe via lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[Dict[str, Any]] = []
        self._tenant_totals: Dict[str, float] = {}

    def record(
        self,
        tenant_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float
    ) -> float:
        """Record a usage event and return the estimated cost in USD."""
        cost_per_1k = _COST_TABLE.get(model, 0.0)
        estimated_cost = (completion_tokens / 1000.0) * cost_per_1k

        entry = {
            "timestamp": time.time(),
            "tenant_id": tenant_id,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "estimated_cost_usd": round(estimated_cost, 6)
        }

        with self._lock:
            self._records.append(entry)
            if len(self._records) > 10000:
                self._records = self._records[-5000:]  # Trim oldest

            self._tenant_totals[tenant_id] = self._tenant_totals.get(tenant_id, 0.0) + estimated_cost

        return estimated_cost

    def get_tenant_cost(self, tenant_id: str) -> float:
        """Get cumulative cost for a tenant."""
        with self._lock:
            return round(self._tenant_totals.get(tenant_id, 0.0), 4)

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate cost summary."""
        with self._lock:
            total_cost = sum(self._tenant_totals.values())
            return {
                "total_requests": len(self._records),
                "total_cost_usd": round(total_cost, 4),
                "tenant_costs": {k: round(v, 4) for k, v in self._tenant_totals.items()},
            }


# Global singleton
cost_tracker = CostTracker()
