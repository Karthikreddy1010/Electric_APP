"""
LLM Service Telemetry & Metrics Collector — Phase 3 Enhanced.
Provides in-memory metrics gathering for request counts, failures, retries,
fallbacks, latency stats, token throughput, Brain traces, and percentiles.
"""
import time
import threading
from typing import Dict, Any, List


class LLMMetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.timeout_count: int = 0
        self.retry_count: int = 0
        self.fallback_count: int = 0
        self.validation_failure_count: int = 0
        self.llm_bypass_count: int = 0
        self.critic_failure_count: int = 0
        self.prompt_tokens_total: int = 0
        self.eval_tokens_total: int = 0
        self.total_latency_ms: float = 0.0
        self.min_latency_ms: float = float("inf")
        self.max_latency_ms: float = 0.0
        self.latencies: List[float] = []
        self.recent_errors: List[Dict[str, Any]] = []
        self.brain_traces: List[Dict[str, Any]] = []
        self.intent_distribution: Dict[str, int] = {}

    def record_request_start(self):
        with self._lock:
            self.total_requests += 1

    def record_success(self, latency_ms: float, prompt_tokens: int = 0, eval_tokens: int = 0):
        with self._lock:
            self.successful_requests += 1
            self.total_latency_ms += latency_ms
            self.latencies.append(latency_ms)
            if len(self.latencies) > 1000:
                self.latencies.pop(0)
            if latency_ms < self.min_latency_ms:
                self.min_latency_ms = latency_ms
            if latency_ms > self.max_latency_ms:
                self.max_latency_ms = latency_ms
            self.prompt_tokens_total += prompt_tokens
            self.eval_tokens_total += eval_tokens

    def record_failure(self, error_type: str, message: str, endpoint: str = "", prompt_hash: str = ""):
        with self._lock:
            self.failed_requests += 1
            if "timeout" in error_type.lower() or "timeout" in message.lower():
                self.timeout_count += 1

            error_entry = {
                "timestamp": time.time(),
                "error_type": error_type,
                "message": message,
                "endpoint": endpoint,
                "prompt_hash": prompt_hash
            }
            self.recent_errors.append(error_entry)
            if len(self.recent_errors) > 20:
                self.recent_errors.pop(0)

    def record_retry(self):
        with self._lock:
            self.retry_count += 1

    def record_fallback(self):
        with self._lock:
            self.fallback_count += 1

    def record_validation_failure(self):
        with self._lock:
            self.validation_failure_count += 1

    def record_brain_trace(self, trace_data: Dict[str, Any]):
        """Record an end-to-end Brain execution trace."""
        with self._lock:
            if trace_data.get("llm_bypassed"):
                self.llm_bypass_count += 1
            if not trace_data.get("critic_passed"):
                self.critic_failure_count += 1

            intent = trace_data.get("intent", "unknown")
            self.intent_distribution[intent] = self.intent_distribution.get(intent, 0) + 1

            self.brain_traces.append({
                "timestamp": time.time(),
                **trace_data
            })
            if len(self.brain_traces) > 50:
                self.brain_traces.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (
                round(self.total_latency_ms / self.successful_requests, 2)
                if self.successful_requests > 0 else 0.0
            )
            min_lat = round(self.min_latency_ms, 2) if self.min_latency_ms != float("inf") else 0.0
            max_lat = round(self.max_latency_ms, 2)

            # Percentiles
            sorted_lat = sorted(self.latencies) if self.latencies else []
            n = len(sorted_lat)
            p50 = round(sorted_lat[int(n * 0.50)], 2) if n > 0 else 0.0
            p90 = round(sorted_lat[int(n * 0.90)], 2) if n > 0 else 0.0
            p99 = round(sorted_lat[int(n * 0.99)], 2) if n > 0 else 0.0

            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "timeout_count": self.timeout_count,
                "retry_count": self.retry_count,
                "fallback_count": self.fallback_count,
                "validation_failure_count": self.validation_failure_count,
                "llm_bypass_count": self.llm_bypass_count,
                "critic_failure_count": self.critic_failure_count,
                "intent_distribution": dict(self.intent_distribution),
                "tokens": {
                    "prompt_tokens_total": self.prompt_tokens_total,
                    "eval_tokens_total": self.eval_tokens_total,
                    "combined_tokens_total": self.prompt_tokens_total + self.eval_tokens_total
                },
                "latency_ms": {
                    "average": avg_latency,
                    "min": min_lat,
                    "max": max_lat,
                    "p50": p50,
                    "p90": p90,
                    "p99": p99,
                    "total": round(self.total_latency_ms, 2)
                },
                "recent_errors": list(self.recent_errors),
                "recent_brain_traces": list(self.brain_traces[-5:])
            }

    def reset(self):
        with self._lock:
            self.total_requests = 0
            self.successful_requests = 0
            self.failed_requests = 0
            self.timeout_count = 0
            self.retry_count = 0
            self.fallback_count = 0
            self.validation_failure_count = 0
            self.llm_bypass_count = 0
            self.critic_failure_count = 0
            self.prompt_tokens_total = 0
            self.eval_tokens_total = 0
            self.total_latency_ms = 0.0
            self.min_latency_ms = float("inf")
            self.max_latency_ms = 0.0
            self.latencies.clear()
            self.recent_errors.clear()
            self.brain_traces.clear()
            self.intent_distribution.clear()


# Global metrics collector instance
llm_metrics = LLMMetricsCollector()

