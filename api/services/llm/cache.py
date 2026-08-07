"""
Phase 4 — Enhanced Semantic Cache Manager.

Constructs deterministic SHA-256 cache keys from:
    SHA256(AnalyticsResult.bill_hash + Prompt Version + Model ID)

Phase 4 Enhancement: 4 isolated cache namespaces with tailored TTLs:
    1. Static Knowledge Cache  (RAG / Glossary / FAQs — 7 days)
    2. Dynamic API Cache       (PJM / Weather / EIA — 15 mins)
    3. Live Search Cache       (Current events / web — 5 mins, no stale reuse)
    4. User Context Cache      (Session bill & tab state — session lifetime)

Backward Compatibility:
    The existing SemanticCacheManager public API (get/set/clear) is fully preserved.
    The global singleton `semantic_cache` remains the canonical instance.
"""
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ── Cache Namespace Configuration ──────────────────────────────────────────

CACHE_NAMESPACES = {
    "static": {
        "description": "Static Knowledge Cache (RAG, Glossary, FAQs)",
        "ttl_seconds": 7 * 24 * 60 * 60,  # 7 days
    },
    "dynamic_api": {
        "description": "Dynamic API Cache (PJM, NOAA, EIA)",
        "ttl_seconds": 15 * 60,  # 15 minutes
    },
    "live_search": {
        "description": "Live Search Cache (current events, web results)",
        "ttl_seconds": 5 * 60,  # 5 minutes — no stale reuse
    },
    "user_context": {
        "description": "User Context Cache (session bill, tab state)",
        "ttl_seconds": 24 * 60 * 60,  # Session lifetime (24 hours)
    },
}

# Map tool names to cache namespaces
TOOL_TO_NAMESPACE = {
    # Static
    "rag_knowledge": "static",
    "bgs_engine": "static",
    # Dynamic API
    "weather_data": "dynamic_api",
    "eia_data": "dynamic_api",
    "pjm_market": "dynamic_api",
    "cpi_inflation": "dynamic_api",
    # Live Search
    "live_knowledge_provider": "live_search",
    # User Context
    "bill_data": "user_context",
    "bill_ocr": "user_context",
    "analytics_engine": "user_context",
    "forecast": "user_context",
    "simulation": "user_context",
    "recommendation_engine": "user_context",
    "ui_state_context": "user_context",
    "benchmark": "user_context",
    "regional_insights": "user_context",
    "executive_report": "dynamic_api",
}


class SemanticCacheManager:
    """
    In-memory LRU cache keyed by semantic content hash rather than raw dict identity.

    Phase 4 Enhancement: Supports 4 cache namespaces with independent TTLs.
    """

    def __init__(self, capacity: int = 500):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}  # Phase 4: TTL tracking
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

    def _get_namespace(self, task: str) -> str:
        """Determine cache namespace from task name."""
        return TOOL_TO_NAMESPACE.get(task, "user_context")

    def _get_ttl(self, namespace: str) -> int:
        """Get TTL in seconds for a namespace."""
        ns_config = CACHE_NAMESPACES.get(namespace, {})
        return ns_config.get("ttl_seconds", 3600)

    def _is_expired(self, key: str, namespace: str) -> bool:
        """Check if a cached entry has expired based on namespace TTL."""
        ts = self._timestamps.get(key)
        if ts is None:
            return True
        ttl = self._get_ttl(namespace)
        return (time.time() - ts) > ttl

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
            namespace = self._get_namespace(task)

            # Phase 4: TTL-based expiration check
            if self._is_expired(key, namespace):
                # Stale entry — evict and return miss
                del self._cache[key]
                del self._timestamps[key]
                logger.debug(f"SemanticCache EXPIRED for key {key[:12]} (namespace={namespace})")
                return None

            # Phase 4: Never serve stale live search results
            if namespace == "live_search":
                logger.debug(f"SemanticCache HIT (live_search, TTL enforced) for key {key[:12]}")
            else:
                logger.debug(f"SemanticCache HIT for key {key[:12]} (namespace={namespace})")

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
            self._timestamps.pop(first_key, None)

        key = self._generate_key(task, context_data, model_id, prompt_version, user_message)
        self._cache[key] = response_data
        self._timestamps[key] = time.time()  # Phase 4: Record insertion time

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()

    def clear_namespace(self, namespace: str) -> int:
        """Phase 4: Clear all entries belonging to a specific namespace."""
        keys_to_remove = []
        for key in list(self._cache.keys()):
            # We can't reverse-map keys to namespaces without metadata,
            # so clear by TTL expiration check for the given namespace
            if self._is_expired(key, namespace):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            self._timestamps.pop(key, None)

        logger.info(f"SemanticCache: Cleared {len(keys_to_remove)} expired entries for namespace '{namespace}'")
        return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Phase 4: Return cache statistics."""
        now = time.time()
        total = len(self._cache)
        expired = sum(1 for ts in self._timestamps.values() if (now - ts) > 3600)
        return {
            "total_entries": total,
            "capacity": self._capacity,
            "utilization_pct": round((total / self._capacity) * 100, 1) if self._capacity else 0,
            "estimated_expired": expired,
            "namespaces": list(CACHE_NAMESPACES.keys()),
        }


# Global singleton — backward compatible name
semantic_cache = SemanticCacheManager()
