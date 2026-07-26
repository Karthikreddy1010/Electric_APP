"""
Phase 3 Infrastructure Unit & Integration Test Suite.

Tests all 10 Phase 3 infrastructure subsystems:
  1. OpenTelemetry & Distributed Tracing (`infra.observability.otel`)
  2. Prometheus Metrics Export (`infra.observability.prometheus`)
  3. Structured JSON Logging (`infra.observability.logging`)
  4. Event Bus Architecture (`infra.events`)
  5. AI Gateway — Rate Limiter, Circuit Breaker, Cost Tracker (`infra.gateway`)
  6. Security & Audit Trail (`infra.security`)
  7. AIOps Metrics & Health Monitoring (`infra.aiops`)
  8. Multi-Tenancy Context & Store (`infra.tenancy`)
  9. Enterprise Notification System (`infra.notifications`)
 10. DR Health Aggregator (`infra.dr`)
"""
import pytest
import asyncio
import json

from infra.observability.otel import get_tracer, trace_span, traced
from infra.observability.prometheus import (
    get_metrics, record_api_request, record_ai_inference,
    record_cache_hit, record_validation_pass
)
from infra.observability.logging import StructuredJSONFormatter
from infra.events import (
    DomainEvent, EventType, InMemoryEventBus, make_event
)
from infra.gateway import (
    TokenBucketRateLimiter, CircuitBreaker, CircuitState, CostTracker
)
from infra.security import SecretManager, AuditLogger, AuditEntry
from infra.aiops import AIQualityMetrics, ModelHealthMonitor
from infra.tenancy import TenantStore, TenantConfig
from infra.notifications import NotificationDispatcher, Notification, NotificationChannel
from infra.dr import HealthAggregator, HealthStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── 1. Observability: OpenTelemetry & Metrics & Logging ───────────────────

class TestObservabilitySubsystems:
    def test_opentelemetry_span_context_manager(self):
        with trace_span("test_span", {"test_key": "test_val"}) as span:
            pass  # Should not raise even if OTel SDK is unconfigured

    @traced("test_traced_func")
    def _sample_traced_func(self):
        return 42

    def test_traced_decorator(self):
        res = self._sample_traced_func()
        assert res == 42

    def test_prometheus_metrics_export(self):
        record_api_request("GET", "/test", 200, 0.05)
        record_ai_inference("MockLLMProvider", "mock-model", "bill_analysis", "success", 0.1, tokens=50)
        record_cache_hit()
        record_validation_pass()

        metrics_bytes = get_metrics()
        assert isinstance(metrics_bytes, bytes)

    def test_structured_json_logging(self):
        import logging
        formatter = StructuredJSONFormatter(service_name="test-service")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Sample log message",
            args=(),
            exc_info=None
        )
        record.tenant_id = "tenant-123"
        json_output = formatter.format(record)
        data = json.loads(json_output)
        assert data["service"] == "test-service"
        assert data["message"] == "Sample log message"
        assert data["tenant_id"] == "tenant-123"


# ── 2. Event Bus Architecture ──────────────────────────────────────────────

class TestEventBusSubsystem:
    @pytest.mark.anyio
    async def test_in_memory_event_bus_publish_subscribe(self):
        bus = InMemoryEventBus()
        received_events = []

        async def handler(event: DomainEvent):
            received_events.append(event)

        await bus.subscribe(EventType.BILL_UPLOADED, handler)
        evt = make_event(EventType.BILL_UPLOADED, {"bill_id": "bill-100"}, tenant_id="tenant-A")
        await bus.publish(evt)

        assert len(received_events) == 1
        assert received_events[0].payload["bill_id"] == "bill-100"
        assert received_events[0].tenant_id == "tenant-A"


# ── 3. AI Gateway Subsystem ───────────────────────────────────────────────

class TestAIGatewaySubsystem:
    def test_token_bucket_rate_limiter(self):
        limiter = TokenBucketRateLimiter()
        # Free tier limit is 20
        for _ in range(20):
            assert limiter.allow("tenant-1", "free") is True
        # 21st request should be denied
        assert limiter.allow("tenant-1", "free") is False

    def test_circuit_breaker_transitions(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=0.1)
        provider = "TestProvider"

        assert cb.is_allowed(provider) is True
        assert cb.get_state(provider) == CircuitState.CLOSED

        # Record 3 failures to trigger OPEN state
        cb.record_failure(provider)
        cb.record_failure(provider)
        cb.record_failure(provider)

        assert cb.get_state(provider) == CircuitState.OPEN
        assert cb.is_allowed(provider) is False

    def test_cost_tracker_accumulation(self):
        tracker = CostTracker()
        cost1 = tracker.record("tenant-A", "ClaudeProvider", "claude-3-5-sonnet-20241022", 100, 500, 250.0)
        assert cost1 > 0.0
        assert tracker.get_tenant_cost("tenant-A") > 0.0


# ── 4. Enterprise Security & Audit ────────────────────────────────────────

class TestSecuritySubsystem:
    def test_secret_manager_default_resolution(self):
        sm = SecretManager()
        val = sm.get("NON_EXISTENT_SECRET_KEY", default="fallback")
        assert val == "fallback"

    def test_audit_logger_integrity_hashing(self):
        logger = AuditLogger()
        entry = logger.log(
            action="BILL_DELETE",
            actor="admin@electric.ai",
            tenant_id="tenant-X",
            resource="bill-999",
            details={"reason": "GDPR compliance"}
        )
        assert entry.integrity_hash != ""
        assert len(entry.integrity_hash) == 16
        assert logger.get_count() >= 1


# ── 5. AIOps Subsystem ───────────────────────────────────────────────────

class TestAIOpsSubsystem:
    def test_ai_quality_metrics_grounding_compliance(self):
        qm = AIQualityMetrics()
        qm.record_generation("mock-model", "2.0.0", validated=True, hallucination_detected=False, fallback_used=False, cache_hit=True)
        qm.record_generation("mock-model", "2.0.0", validated=True, hallucination_detected=False, fallback_used=False, cache_hit=False)

        snap = qm.get_snapshot()
        assert snap["total_generations"] == 2
        assert snap["grounding_compliance_rate"] == 100.0
        assert snap["hallucination_rate"] == 0.0

    def test_model_health_monitor(self):
        hm = ModelHealthMonitor()
        hm.record_success("ProviderA", 120.0)
        hm.record_success("ProviderA", 150.0)
        assert hm.is_healthy("ProviderA") is True

        dashboard = hm.get_dashboard()
        assert "ProviderA" in dashboard
        assert dashboard["ProviderA"]["success_count"] == 2


# ── 6. Multi-Tenancy Subsystem ────────────────────────────────────────────

class TestTenancySubsystem:
    def test_tenant_store_registration(self):
        store = TenantStore()
        cfg = TenantConfig(tenant_id="tenant-corp", name="Corp Inc", tier="enterprise")
        store.register(cfg)

        retrieved = store.get("tenant-corp")
        assert retrieved.name == "Corp Inc"
        assert retrieved.tier == "enterprise"


# ── 7. Notification Subsystem ─────────────────────────────────────────────

class TestNotificationSubsystem:
    @pytest.mark.anyio
    async def test_notification_dispatcher_dispatch(self):
        dispatcher = NotificationDispatcher()
        notif = Notification(
            channel=NotificationChannel.EMAIL,
            recipient="user@electric.ai",
            subject="High Usage Alert",
            body="Your electricity usage spiked by 25% today.",
            tenant_id="tenant-1"
        )
        success = await dispatcher.dispatch(notif)
        assert success is True


# ── 8. Disaster Recovery Health Aggregator ────────────────────────────────

class TestDisasterRecoverySubsystem:
    @pytest.mark.anyio
    async def test_health_aggregator_check(self):
        ha = HealthAggregator()
        ha.register_check("api", lambda: {"healthy": True})
        ha.register_check("db", lambda: {"healthy": True})

        res = await ha.check_all()
        assert res["status"] == HealthStatus.HEALTHY.value
        assert res["subsystems"]["api"]["healthy"] is True
