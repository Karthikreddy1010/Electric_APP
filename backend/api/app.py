"""
backend.api.app — Sub-application initialization and router registration helper.
"""
from __future__ import annotations

from fastapi import FastAPI
from backend.api.routes.bill_routes import router as bill_v1_router, legacy_router


def mount_backend_routes(app: FastAPI) -> None:
    """Mount Phase 1 backend routers onto the main FastAPI application."""
    app.include_router(bill_v1_router)
    app.include_router(legacy_router)
