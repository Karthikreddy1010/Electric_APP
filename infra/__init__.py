"""
Phase 3 — Enterprise Infrastructure Package.

Central package exporting all production infrastructure subsystems:
  - Observability (OpenTelemetry, Prometheus, Structured JSON Logging)
  - Event Bus (Contracts, In-Memory, Redis Streams)
  - AI Gateway (Rate Limiter, Circuit Breaker, Cost Tracker, Middleware)
  - Security (Secret Manager, Vault, Audit Logger)
  - AIOps (Quality Metrics, Model Health Monitor)
  - Multi-Tenancy (Tenant Context, Config Store)
  - Notifications (Multi-Channel Dispatcher, Retries, Webhooks)
  - Disaster Recovery (Health Check Aggregator)
"""
from infra.observability import (
    get_tracer, trace_span, traced,
    get_metrics, record_api_request, record_ai_inference,
    setup_structured_logging
)
from infra.events import (
    DomainEvent, EventType, EventBus, InMemoryEventBus, RedisStreamsEventBus,
    create_event_bus, make_event
)
from infra.gateway import (
    rate_limiter, circuit_breaker, cost_tracker, AIGatewayMiddleware
)
from infra.security import (
    SecretManager, secret_manager, AuditLogger, audit_logger, AuditEntry
)
from infra.aiops import (
    AIQualityMetrics, ai_quality_metrics, ModelHealthMonitor, model_health_monitor
)
from infra.tenancy import (
    TenantContextMiddleware, TenantConfig, TenantStore, tenant_store
)
from infra.notifications import (
    NotificationDispatcher, notification_dispatcher, Notification, NotificationChannel
)
from infra.dr import (
    HealthAggregator, health_aggregator, HealthStatus
)

__all__ = [
    # Observability
    "get_tracer", "trace_span", "traced", "get_metrics",
    "record_api_request", "record_ai_inference", "setup_structured_logging",
    # Events
    "DomainEvent", "EventType", "EventBus", "InMemoryEventBus",
    "RedisStreamsEventBus", "create_event_bus", "make_event",
    # Gateway
    "rate_limiter", "circuit_breaker", "cost_tracker", "AIGatewayMiddleware",
    # Security
    "SecretManager", "secret_manager", "AuditLogger", "audit_logger",
    # AIOps
    "AIQualityMetrics", "ai_quality_metrics", "ModelHealthMonitor", "model_health_monitor",
    # Tenancy
    "TenantContextMiddleware", "TenantConfig", "TenantStore", "tenant_store",
    # Notifications
    "NotificationDispatcher", "notification_dispatcher", "Notification", "NotificationChannel",
    # DR
    "HealthAggregator", "health_aggregator", "HealthStatus",
]
