"""
Auth Configuration — Pydantic Settings for JWT, cookies, and SMTP.

All values are read from environment variables with sensible dev defaults.
Production environments MUST set JWT_SECRET_KEY and JWT_REFRESH_SECRET_KEY
to strong random values (64+ hex characters).
"""
from __future__ import annotations

import logging
import os
import secrets
import sys

logger = logging.getLogger(__name__)

_INSECURE_PREFIXES = (
    "dev-only-",
    "change-me-",
)


def _get_jwt_secret(env_var: str, dev_fallback_prefix: str) -> str:
    """Return the JWT secret from the environment, or a random dev-only fallback."""
    value = os.environ.get(env_var, "").strip()
    if value:
        return value
    return dev_fallback_prefix + secrets.token_hex(16)


class AuthConfig:
    """Centralized authentication configuration."""

    # ── JWT ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = _get_jwt_secret(
        "JWT_SECRET_KEY",
        "dev-only-insecure-secret-",
    )
    REFRESH_SECRET_KEY: str = _get_jwt_secret(
        "JWT_REFRESH_SECRET_KEY",
        "dev-only-insecure-refresh-",
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
    EMAIL_CONSOLE_ONLY: bool = os.environ.get("EMAIL_CONSOLE_ONLY", "true").lower() == "true"

    # ── CSRF ─────────────────────────────────────────────────────────────────
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    def validate_production_secrets(self) -> None:
        """Refuse to start in production mode with insecure default secrets."""
        if not self.COOKIE_SECURE:
            # Dev mode — warn but allow startup
            for name, val in [("JWT_SECRET_KEY", self.SECRET_KEY),
                              ("JWT_REFRESH_SECRET_KEY", self.REFRESH_SECRET_KEY)]:
                if any(val.startswith(p) for p in _INSECURE_PREFIXES):
                    logger.warning(
                        "⚠️  %s is using an auto-generated dev-only secret. "
                        "Set a strong value in .env before deploying to production.",
                        name,
                    )
            return

        # Production mode (COOKIE_SECURE=true) — hard fail on insecure secrets
        for name, val in [("JWT_SECRET_KEY", self.SECRET_KEY),
                          ("JWT_REFRESH_SECRET_KEY", self.REFRESH_SECRET_KEY)]:
            if any(val.startswith(p) for p in _INSECURE_PREFIXES):
                logger.critical(
                    "🚨 FATAL: %s is still set to an insecure default. "
                    "Generate a strong secret: python -c \"import secrets; print(secrets.token_hex(32))\"",
                    name,
                )
                sys.exit(1)
            if len(val) < 32:
                logger.critical(
                    "🚨 FATAL: %s is too short (%d chars). Use at least 32 characters.",
                    name, len(val),
                )
                sys.exit(1)


# Singleton instance
auth_config = AuthConfig()
auth_config.validate_production_secrets()

