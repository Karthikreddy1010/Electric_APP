"""
Phase 2 — Semantic Cache Manager.

Constructs deterministic SHA-256 cache keys from:
    SHA256(AnalyticsResult.bill_hash + Prompt Version + Model ID)

This guarantees cache hits across identical bill analytics regardless of
transient metadata timestamp shifts or formatting changes.
"""
import hashlib
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SemanticCacheManager:
    """
    In-memory LRU cache keyed by semantic content hash rather than raw dict identity.
    """

    def __init__(self, capacity: int = 500):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._capacity = capacity

    def _generate_key(
        self,
        task: str,
        context_data: Dict[str, Any],
        model_id: str,
        prompt_version: str,
        user_message: str = ""
    ) -> str:
        """
        Build a deterministic cache key:
        SHA256(task + user_message + bill_hash + prompt_version + model_id)
        """
        bill_hash = ""
        if isinstance(context_data, dict):
            bill_hash = context_data.get("bill_hash", "")
            if not bill_hash:
                for sub_key in ("bill", "analytics_result", "uploadedBill"):
                    sub = context_data.get(sub_key, {})
                    if isinstance(sub, dict) and "bill_hash" in sub:
                        bill_hash = sub["bill_hash"]
                        break

        if bill_hash:
            raw_key = f"{task}:{user_message}:{bill_hash}:{prompt_version}:{model_id}"
        else:
            serialized = json.dumps(context_data, sort_keys=True, default=str)
            raw_key = f"{task}:{user_message}:{model_id}:{prompt_version}:{serialized}"

        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(
        self,
        task: str,
        context_data: Dict[str, Any],
        model_id: str,
        prompt_version: str,
        user_message: str = ""
    ) -> Optional[Dict[str, Any]]:
        key = self._generate_key(task, context_data, model_id, prompt_version, user_message)
        if key in self._cache:
            logger.debug(f"SemanticCache HIT for key {key[:12]}")
            return self._cache[key]
        return None

    def set(
        self,
        task: str,
        context_data: Dict[str, Any],
        model_id: str,
        prompt_version: str,
        response_data: Dict[str, Any],
        user_message: str = ""
    ) -> None:
        if len(self._cache) >= self._capacity:
            # Evict oldest entry (FIFO)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        key = self._generate_key(task, context_data, model_id, prompt_version, user_message)
        self._cache[key] = response_data

    def clear(self) -> None:
        self._cache.clear()


# Global singleton — backward compatible name
semantic_cache = SemanticCacheManager()
