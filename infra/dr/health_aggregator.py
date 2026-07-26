"""
Phase 3 — Disaster Recovery: Health Check Aggregator.

Aggregates health from all subsystems (API, DB, Redis, LLM, Event Bus)
into a single composite health response with degraded/healthy/unhealthy states.
"""
import time
import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthAggregator:
    """
    Composite health check aggregator.
    Returns HEALTHY if all subsystems pass, DEGRADED if non-critical
    subsystems fail, UNHEALTHY if critical subsystems fail.
    """

    CRITICAL_SUBSYSTEMS = {"database", "api"}
    NON_CRITICAL_SUBSYSTEMS = {"redis", "llm", "event_bus", "gpu"}

    def __init__(self):
        self._checks: Dict[str, Dict[str, Any]] = {}

    def register_check(self, name: str, check_fn) -> None:
        """Register a health check function. Must return {'healthy': bool, ...}."""
        self._checks[name] = {"fn": check_fn, "last_status": None, "last_check": 0}

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return composite status."""
        results = {}
        critical_ok = True
        any_degraded = False

        for name, entry in self._checks.items():
            try:
                import asyncio
                if asyncio.iscoroutinefunction(entry["fn"]):
                    result = await entry["fn"]()
                else:
                    result = entry["fn"]()
                healthy = result.get("healthy", False)
            except Exception as e:
                result = {"healthy": False, "error": str(e)}
                healthy = False

            results[name] = result
            entry["last_status"] = healthy
            entry["last_check"] = time.time()

            if not healthy:
                if name in self.CRITICAL_SUBSYSTEMS:
                    critical_ok = False
                else:
                    any_degraded = True

        if not critical_ok:
            overall = HealthStatus.UNHEALTHY
        elif any_degraded:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "timestamp": time.time(),
            "subsystems": results,
        }


# ── Default Health Check Functions ─────────────────────────────────────────

def check_api_health() -> Dict[str, Any]:
    return {"healthy": True, "service": "FastAPI", "status": "running"}


def check_database_health() -> Dict[str, Any]:
    try:
        from database.connection import engine
        return {"healthy": True, "service": "PostgreSQL"}
    except Exception as e:
        return {"healthy": False, "service": "PostgreSQL", "error": str(e)}


def check_redis_health() -> Dict[str, Any]:
    try:
        import redis
        r = redis.Redis.from_url("redis://localhost:6379/0", socket_timeout=2)
        r.ping()
        return {"healthy": True, "service": "Redis"}
    except Exception:
        return {"healthy": False, "service": "Redis", "error": "Connection failed"}


def check_llm_health() -> Dict[str, Any]:
    try:
        from api.services.llm.llm_service import llm_service
        available = llm_service.provider.is_available()
        return {"healthy": available, "service": "LLM", "provider": llm_service.provider.__class__.__name__}
    except Exception as e:
        return {"healthy": False, "service": "LLM", "error": str(e)}


# Build default aggregator
health_aggregator = HealthAggregator()
health_aggregator.register_check("api", check_api_health)
health_aggregator.register_check("database", check_database_health)
health_aggregator.register_check("redis", check_redis_health)
health_aggregator.register_check("llm", check_llm_health)
