"""
Phase 3 — AIOps: Model Health Monitor.

Tracks real-time provider health (latency, error rate, availability)
to feed the Circuit Breaker and Model Router with live status data.
"""
import time
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ProviderHealthRecord:
    def __init__(self):
        self.total_calls = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0.0
        self.last_success_time = 0.0
        self.last_failure_time = 0.0
        self.consecutive_failures = 0

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failure_count / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_failures < 5 and self.error_rate < 0.3


class ModelHealthMonitor:
    """Monitors provider health and feeds live status to Router and Gateway."""

    def __init__(self):
        self._lock = threading.Lock()
        self._providers: Dict[str, ProviderHealthRecord] = {}

    def _get_record(self, provider: str) -> ProviderHealthRecord:
        if provider not in self._providers:
            self._providers[provider] = ProviderHealthRecord()
        return self._providers[provider]

    def record_success(self, provider: str, latency_ms: float):
        with self._lock:
            rec = self._get_record(provider)
            rec.total_calls += 1
            rec.success_count += 1
            rec.total_latency_ms += latency_ms
            rec.last_success_time = time.time()
            rec.consecutive_failures = 0

    def record_failure(self, provider: str):
        with self._lock:
            rec = self._get_record(provider)
            rec.total_calls += 1
            rec.failure_count += 1
            rec.last_failure_time = time.time()
            rec.consecutive_failures += 1

    def is_healthy(self, provider: str) -> bool:
        with self._lock:
            rec = self._get_record(provider)
            return rec.is_healthy

    def get_dashboard(self) -> Dict[str, Any]:
        with self._lock:
            dashboard = {}
            for name, rec in self._providers.items():
                dashboard[name] = {
                    "healthy": rec.is_healthy,
                    "total_calls": rec.total_calls,
                    "success_count": rec.success_count,
                    "failure_count": rec.failure_count,
                    "error_rate": round(rec.error_rate * 100, 2),
                    "avg_latency_ms": round(rec.avg_latency_ms, 2),
                    "consecutive_failures": rec.consecutive_failures,
                }
            return dashboard


# Global singleton
model_health_monitor = ModelHealthMonitor()
