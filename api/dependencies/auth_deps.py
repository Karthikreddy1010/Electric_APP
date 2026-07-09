"""
Auth FastAPI Dependencies.

Provides reusable dependencies for route protection:
- get_current_user: reads access_token cookie, decodes JWT, fetches User
- get_current_verified_user: extends above, requires email_verified
- require_role: factory for role-based access control
- validate_csrf: enforces CSRF double-submit for state-mutating endpoints
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_utils import decode_access_token, get_access_token_from_cookie, validate_csrf
from database.auth_models import User
from database.connection import get_db

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: extract and validate access token from HTTP-only cookie.
    Returns the authenticated User ORM object.
    """
    token = get_access_token_from_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    if user.account_status == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended.")

    return user


async def get_current_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    """Extends get_current_user — additionally requires email_verified."""
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",
        )
    return user


class RequireRole:
    """RBAC dependency factory. Usage: Depends(RequireRole(['admin', 'developer']))"""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: User = Depends(get_current_verified_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {self.allowed_roles}",
            )
        return user


def validate_csrf_dep(request: Request) -> None:
    """
    Dependency: validate CSRF double-submit cookie for state-mutating requests.
    Skip for GET/HEAD/OPTIONS.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not validate_csrf(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch. Please refresh the page and try again.",
        )
