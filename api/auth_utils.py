"""
Auth Utilities — password hashing, JWT creation/decode, cookie helpers.

Replaces the legacy api/auth.py HMAC-SHA256 implementation with:
- Argon2 password hashing (via passlib)
- Standard JWT (via python-jose)
- HTTP-only Secure cookie helpers
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Request, Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.auth_config import auth_config

logger = logging.getLogger(__name__)

# ── Password Hashing ──────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,   # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 (or bcrypt) hash."""
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


def validate_password_strength(password: str) -> list[str]:
    """
    Return a list of unmet requirements. Empty list = password is valid.
    Rules: 8+ chars, uppercase, lowercase, digit, special character.
    """
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("Password must contain at least one special character.")
    return errors


# ── Token Generation ──────────────────────────────────────────────────────────

def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Hash a raw token for storage (so DB never holds plaintext tokens)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, auth_config.SECRET_KEY, algorithm=auth_config.ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=auth_config.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, auth_config.REFRESH_SECRET_KEY, algorithm=auth_config.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and verify an access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, auth_config.SECRET_KEY, algorithms=[auth_config.ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError as e:
        logger.debug(f"Access token decode failed: {e}")
        return None


def decode_refresh_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and verify a refresh token. Returns payload or None."""
    try:
        payload = jwt.decode(token, auth_config.REFRESH_SECRET_KEY, algorithms=[auth_config.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError as e:
        logger.debug(f"Refresh token decode failed: {e}")
        return None


# ── Cookie Helpers ─────────────────────────────────────────────────────────────

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    remember_me: bool = False,
) -> None:
    """Set HTTP-only auth cookies on the response."""
    refresh_max_age = (
        auth_config.REMEMBER_ME_DAYS * 86400 if remember_me
        else auth_config.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    access_max_age = auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    cookie_kwargs = {
        "httponly": True,
        "secure": auth_config.COOKIE_SECURE,
        "samesite": auth_config.COOKIE_SAMESITE,
    }
    if auth_config.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = auth_config.COOKIE_DOMAIN

    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=access_max_age,
        path="/",
        **cookie_kwargs,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=refresh_max_age,
        path="/auth/refresh",  # Scoped to refresh endpoint only
        **cookie_kwargs,
    )
    # Also allow logout to clear it
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=refresh_max_age,
        path="/auth/logout",
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    """Expire auth cookies on the response."""
    for path in ["/", "/auth/refresh", "/auth/logout"]:
        response.delete_cookie(ACCESS_COOKIE, path=path)
        response.delete_cookie(REFRESH_COOKIE, path=path)


def get_access_token_from_cookie(request: Request) -> Optional[str]:
    """Extract the access token from the request cookies."""
    return request.cookies.get(ACCESS_COOKIE)


def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
    """Extract the refresh token from the request cookies."""
    return request.cookies.get(REFRESH_COOKIE)


# ── CSRF ──────────────────────────────────────────────────────────────────────

def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set a readable (non-httponly) CSRF cookie for double-submit pattern."""
    response.set_cookie(
        auth_config.CSRF_COOKIE_NAME,
        token,
        max_age=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        httponly=False,  # Intentionally readable by JS
        secure=auth_config.COOKIE_SECURE,
        samesite=auth_config.COOKIE_SAMESITE,
    )


def validate_csrf(request: Request) -> bool:
    """
    Double-submit cookie CSRF validation.
    Checks that X-CSRF-Token header matches the csrf_token cookie.
    """
    cookie_token = request.cookies.get(auth_config.CSRF_COOKIE_NAME)
    header_token = request.headers.get(auth_config.CSRF_HEADER_NAME)
    if not cookie_token or not header_token:
        return False
    return secrets.compare_digest(cookie_token, header_token)
