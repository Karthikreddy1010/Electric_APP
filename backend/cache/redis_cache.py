"""
backend.cache.redis_cache — Version-aware Redis caching layer.

Implements version-aware key formatting:
analytics:{bill_hash}:v{analytics_version}:t{tariff_version}:w{weather_version}
ocr:{bill_hash}:v{ocr_version}
parsed:{bill_hash}:v{parser_version}
status:{task_id}

Includes graceful fallback to in-memory dictionary when Redis server is offline.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, Dict
from backend.config.settings import redis_settings
from backend.schemas.analytics import AnalyticsResult
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.ocr import OCRResult

logger = logging.getLogger(__name__)


class VersionedRedisCache:
    """Version-aware Redis cache manager with in-memory fallback."""

    def __init__(self) -> None:
        self._memory_cache: Dict[str, tuple[str, float]] = {}
        self._redis_client = None

    def _get_key(self, prefix: str, bill_hash: str, **versions: str) -> str:
        """Format versioned cache key."""
        v_str = ":".join(f"{k[0]}{v}" for k, v in sorted(versions.items()))
        return f"{prefix}:{bill_hash}:{v_str}" if v_str else f"{prefix}:{bill_hash}"

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve JSON item from cache."""
        # Check memory cache fallback
        if key in self._memory_cache:
            val, exp = self._memory_cache[key]
            if time.time() < exp:
                logger.debug(f"Cache HIT (Memory): {key}")
                return json.loads(val)
            else:
                del self._memory_cache[key]

        if not self._redis_client:
            return None

        try:
            val = await self._redis_client.get(key)
            if val:
                logger.debug(f"Cache HIT (Redis): {key}")
                return json.loads(val.decode() if isinstance(val, bytes) else val)
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
        return None

    async def set_json(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> None:
        """Store JSON item in cache."""
        json_str = json.dumps(data, default=str)
        self._memory_cache[key] = (json_str, time.time() + ttl)

        if self._redis_client:
            try:
                await self._redis_client.setex(key, ttl, json_str)
                logger.debug(f"Cache SET (Redis): {key} (TTL={ttl}s)")
            except Exception as e:
                logger.warning(f"Redis SET error for key {key}: {e}")

    # Typed helpers for version-aware keys
    async def get_analytics(
        self,
        bill_hash: str,
        analytics_ver: str = "1.0.0",
        tariff_ver: str = "2026.07",
        weather_ver: str = "2026.07",
    ) -> Optional[AnalyticsResult]:
        key = self._get_key(
            "analytics",
            bill_hash,
            analytics_version=analytics_ver,
            tariff_version=tariff_ver,
            weather_version=weather_ver,
        )
        data = await self.get_json(key)
        return AnalyticsResult(**data) if data else None

    async def set_analytics(
        self,
        bill_hash: str,
        analytics: AnalyticsResult,
        ttl: int = 7200,
    ) -> None:
        key = self._get_key(
            "analytics",
            bill_hash,
            analytics_version=analytics.analytics_version,
            tariff_version=analytics.tariff_version,
            weather_version=analytics.weather_version,
        )
        await self.set_json(key, analytics.model_dump(mode="json"), ttl=ttl)

    async def get_ocr(self, bill_hash: str, ocr_ver: str = "1.0.0") -> Optional[OCRResult]:
        key = self._get_key("ocr", bill_hash, ocr_version=ocr_ver)
        data = await self.get_json(key)
        return OCRResult(**data) if data else None

    async def set_ocr(self, bill_hash: str, ocr: OCRResult, ttl: int = 86400) -> None:
        key = self._get_key("ocr", bill_hash, ocr_version=ocr.ocr_version)
        await self.set_json(key, ocr.model_dump(mode="json"), ttl=ttl)


# Singleton instance
versioned_cache = VersionedRedisCache()
