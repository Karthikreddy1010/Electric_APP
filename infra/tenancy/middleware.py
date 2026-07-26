"""
Phase 3 — Multi-Tenancy: Tenant Context Middleware & Configuration.

Extracts tenant context from request headers and injects it into the
request state for downstream access by routes, services, and loggers.
"""
import logging
from typing import Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


# ── Tenant Configuration Store ────────────────────────────────────────────

class TenantConfig:
    """Per-tenant configuration profile."""

    def __init__(
        self,
        tenant_id: str,
        name: str = "Default Tenant",
        tier: str = "free",
        max_bills_per_month: int = 100,
        custom_branding: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        ai_model_override: Optional[str] = None,
    ):
        self.tenant_id = tenant_id
        self.name = name
        self.tier = tier
        self.max_bills_per_month = max_bills_per_month
        self.custom_branding = custom_branding or {}
        self.webhook_url = webhook_url
        self.ai_model_override = ai_model_override


class TenantStore:
    """In-memory tenant configuration store. Production: PostgreSQL table."""

    def __init__(self):
        self._tenants: Dict[str, TenantConfig] = {
            "default": TenantConfig(tenant_id="default", name="Default Tenant", tier="free"),
        }

    def get(self, tenant_id: str) -> TenantConfig:
        return self._tenants.get(tenant_id, self._tenants["default"])

    def register(self, config: TenantConfig) -> None:
        self._tenants[config.tenant_id] = config
        logger.info(f"TenantStore: Registered tenant '{config.tenant_id}' ({config.tier})")

    def list_tenants(self) -> list:
        return [{"tenant_id": t.tenant_id, "name": t.name, "tier": t.tier} for t in self._tenants.values()]


# Global singleton
tenant_store = TenantStore()


# ── Tenant Context Middleware ─────────────────────────────────────────────

class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extracts tenant_id from X-Tenant-ID header and injects
    tenant configuration into request.state for downstream use.
    """

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        tenant_config = tenant_store.get(tenant_id)

        # Inject into request state
        request.state.tenant_id = tenant_id
        request.state.tenant_config = tenant_config

        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
