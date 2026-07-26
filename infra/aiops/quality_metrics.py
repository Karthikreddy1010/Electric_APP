"""
Phase 3 — AIOps: AI Quality Metrics Collector.

Continuously tracks response quality, grounding compliance,
hallucination rates, and cost efficiency across the AI pipeline.
"""
import time
import threading
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AIQualityMetrics:
    """Collects and reports AI pipeline quality metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self.total_generations = 0
        self.validation_passes = 0
        self.validation_failures = 0
        self.hallucination_detections = 0
        self.fallback_activations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self._prompt_version_usage: Dict[str, int] = {}
        self._model_usage: Dict[str, int] = {}

    def record_generation(
        self,
        model: str,
        prompt_version: str,
        validated: bool,
        hallucination_detected: bool,
        fallback_used: bool,
        cache_hit: bool,
        tokens: int = 0,
        cost_usd: float = 0.0
    ):
        with self._lock:
            self.total_generations += 1
            if validated:
                self.validation_passes += 1
            else:
                self.validation_failures += 1
            if hallucination_detected:
                self.hallucination_detections += 1
            if fallback_used:
                self.fallback_activations += 1
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            self.total_tokens_used += tokens
            self.total_cost_usd += cost_usd
            self._model_usage[model] = self._model_usage.get(model, 0) + 1
            self._prompt_version_usage[prompt_version] = self._prompt_version_usage.get(prompt_version, 0) + 1

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            grounding_rate = (
                (self.validation_passes / self.total_generations * 100)
                if self.total_generations > 0 else 100.0
            )
            hallucination_rate = (
                (self.hallucination_detections / self.total_generations * 100)
                if self.total_generations > 0 else 0.0
            )
            cache_hit_rate = (
                (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
                if (self.cache_hits + self.cache_misses) > 0 else 0.0
            )
            return {
                "total_generations": self.total_generations,
                "grounding_compliance_rate": round(grounding_rate, 2),
                "hallucination_rate": round(hallucination_rate, 2),
                "validation_passes": self.validation_passes,
                "validation_failures": self.validation_failures,
                "fallback_activations": self.fallback_activations,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "total_tokens_used": self.total_tokens_used,
                "total_cost_usd": round(self.total_cost_usd, 4),
                "model_usage": dict(self._model_usage),
                "prompt_version_usage": dict(self._prompt_version_usage),
            }

    def reset(self):
        with self._lock:
            self.__init__()


# Global singleton
ai_quality_metrics = AIQualityMetrics()
