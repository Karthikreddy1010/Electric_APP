"""
Cache manager for LLM generated text responses.
Generates deterministic sha256 cache keys from context signature, task, model, and prompt version.
"""
import hashlib
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMCacheManager:
    def __init__(self, capacity: int = 250):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._capacity = capacity

    def _generate_key(
        self,
        task: str,
        context_data: Dict[str, Any],
        model: str,
        prompt_version: str
    ) -> str:
        serialized_context = json.dumps(context_data, sort_keys=True, default=str)
        raw_key = f"{task}:{model}:{prompt_version}:{serialized_context}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    def get(
        self,
        task: str,
        context_data: Dict[str, Any],
        model: str,
        prompt_version: str
    ) -> Optional[Dict[str, Any]]:
        key = self._generate_key(task, context_data, model, prompt_version)
        if key in self._cache:
            logger.debug(f"LLMCacheManager hit for key {key[:8]}")
            return self._cache[key]
        return None

    def set(
        self,
        task: str,
        context_data: Dict[str, Any],
        model: str,
        prompt_version: str,
        response_data: Dict[str, Any]
    ) -> None:
        if len(self._cache) >= self._capacity:
            # Evict first key (simple FIFO eviction)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        key = self._generate_key(task, context_data, model, prompt_version)
        self._cache[key] = response_data

    def clear(self) -> None:
        self._cache.clear()

llm_cache = LLMCacheManager()
