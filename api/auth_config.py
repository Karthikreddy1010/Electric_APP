"""
Auth Configuration — Pydantic Settings for JWT, cookies, and SMTP.

All values are read from environment variables with sensible dev defaults.
"""
from __future__ import annotations

import os
import secrets


class AuthConfig:
    """Centralized authentication configuration."""

    # ── JWT ──────────────────────────────────────────────────────────────────
    # IMPORTANT: Override these via environment variables in production!
    SECRET_KEY: str = os.environ.get(
        "JWT_SECRET_KEY",
        "dev-only-insecure-secret-please-change-in-production-" + secrets.token_hex(8),
    )
    REFRESH_SECRET_KEY: str = os.environ.get(
        "JWT_REFRESH_SECRET_KEY",
        "dev-only-insecure-refresh-secret-change-in-prod-" + secrets.token_hex(8),
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )
    REMEMBER_ME_DAYS: int = int(os.environ.get("REMEMBER_ME_DAYS", "30"))

    # ── Cookies ───────────────────────────────────────────────────────────────
    COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = os.environ.get("COOKIE_SAMESITE", "lax")
    COOKIE_DOMAIN: str | None = os.environ.get("COOKIE_DOMAIN") or None

    # ── Account Security ──────────────────────────────────────────────────────
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    # ── Email Verification & Password Reset ───────────────────────────────────
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    RESET_TOKEN_EXPIRE_HOURS: int = 1
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:8000")

    # ── SMTP ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.environ.get("SMTP_FROM", "noreply@electricai.app")
    SMTP_USE_TLS: bool = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    # When true, emails are logged to console instead of actually sent (dev mode)
    EMAIL_CONSOLE_ONLY: bool = os.environ.get("EMAIL_CONSOLE_ONLY", "true").lower() == "true"

    # ── CSRF ─────────────────────────────────────────────────────────────────
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"


# Singleton instance
auth_config = AuthConfig()
