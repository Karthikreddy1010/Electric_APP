"""
tests/test_cache.py — Unit tests for Versioned Redis Cache.
"""
import pytest
import anyio
from backend.cache.redis_cache import versioned_cache
from backend.schemas.parsed_bill import ParsedBill
from backend.analytics.engine import analytics_engine


@pytest.mark.anyio
async def test_cache_set_and_get_analytics():
    parsed = ParsedBill(
        bill_hash="a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
        bill_date="2026-06-30",
        billing_period="2026-06-01 to 2026-06-30",
        usage_kwh=800.0,
        total_bill=150.00,
        effective_rate=0.1875,
    )
    analytics = analytics_engine.calculate(parsed)

    await versioned_cache.set_analytics("test_hash_123", analytics)
    cached = await versioned_cache.get_analytics("test_hash_123")

    assert cached is not None
    assert cached.bill_hash == analytics.bill_hash
    assert cached.analytics_version == "1.0.0"
