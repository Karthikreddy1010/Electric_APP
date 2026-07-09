"""
Auth Router — all 11 authentication endpoints.

POST   /auth/register           - Create new account
POST   /auth/verify-email       - Verify email address
POST   /auth/resend-verification - Resend verification email
POST   /auth/login              - Authenticate, return tokens as cookies
POST   /auth/logout             - Clear cookies, revoke session
POST   /auth/refresh            - Rotate refresh token
POST   /auth/forgot-password    - Initiate password reset
POST   /auth/reset-password     - Complete password reset
GET    /auth/me                 - Get current user profile
PUT    /auth/profile            - Update profile
GET    /auth/sessions           - List active sessions
DELETE /auth/sessions/{id}      - Revoke a specific session
DELETE /auth/sessions           - Revoke all sessions (logout all)
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_config import auth_config
from api.auth_utils import (
    create_access_token,
    create_refresh_token,
    generate_token,
    generate_csrf_token,
    set_auth_cookies,
    set_csrf_cookie,
    clear_auth_cookies,
    get_refresh_token_from_cookie,
    decode_refresh_token,
)
from api.services import auth_service
from api.dependencies.auth_deps import get_current_verified_user, validate_csrf_dep
from database.auth_models import User
from database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field("", max_length=100)
    zip_code: str = Field("", max_length=20)
    utility_provider: str = Field("", max_length=200)
    country: str = Field("US", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in (info.data or {}) and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    utility_provider: Optional[str] = Field(None, max_length=200)
    country: Optional[str] = Field(None, max_length=100)
    preferences: Optional[dict] = None


# ── Response Helpers ──────────────────────────────────────────────────────────

def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "zip_code": user.zip_code,
        "utility_provider": user.utility_provider,
        "country": user.country,
        "role": user.role,
        "email_verified": user.email_verified,
        "account_status": user.account_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "preferences": user.preferences or {},
    }


def _issue_tokens_and_set_cookies(
    response: Response,
    user: User,
    remember_me: bool = False,
) -> tuple[str, str]:
    """Create access + refresh tokens, set cookies, set CSRF cookie."""
    expires_days = auth_config.REMEMBER_ME_DAYS if remember_me else auth_config.REFRESH_TOKEN_EXPIRE_DAYS
    expires_delta = timedelta(days=expires_days)

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id}, expires_delta=expires_delta)

    set_auth_cookies(response, access_token, refresh_token, remember_me=remember_me)

    # Issue CSRF token (readable by JS for double-submit)
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)

    return access_token, refresh_token


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account. Sends a verification email."""
    user = await auth_service.register_user(
        db=db,
        request=request,
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        zip_code=body.zip_code,
        utility_provider=body.utility_provider,
        country=body.country,
    )
    return {
        "message": "Account created. Please check your email to verify your account.",
        "email": user.email,
    }


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Activate a user account using the token from the verification email."""
    user = await auth_service.verify_email(db=db, request=request, raw_token=body.token)
    return {"message": "Email verified successfully. You can now log in.", "email": user.email}


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Resend the verification email. Always returns 200 to prevent email enumeration."""
    await auth_service.resend_verification_email(db=db, request=request, email=body.email)
    return {"message": "If that email exists and is unverified, a new verification link has been sent."}


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password. Sets HTTP-only auth cookies."""
    user = await auth_service.authenticate_user(
        db=db, request=request, email=body.email, password=body.password
    )
    raw_refresh_token = generate_token()
    expires_days = auth_config.REMEMBER_ME_DAYS if body.remember_me else auth_config.REFRESH_TOKEN_EXPIRE_DAYS

    _, raw_rt = _issue_tokens_and_set_cookies(response, user, remember_me=body.remember_me)

    await auth_service.create_session(
        db=db,
        request=request,
        user=user,
        raw_refresh_token=raw_rt,
        expires_days=expires_days,
    )
    return {"message": "Login successful.", "user": _user_response(user)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current refresh token session and clear auth cookies."""
    raw_rt = get_refresh_token_from_cookie(request)
    if raw_rt:
        payload = decode_refresh_token(raw_rt)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                from api.auth_utils import hash_token
                from sqlalchemy import select as sa_select
                from database.auth_models import RefreshToken
                token_hash = hash_token(raw_rt)
                result = await db.execute(
                    sa_select(RefreshToken).where(RefreshToken.token_hash == token_hash)
                )
                stored = result.scalars().first()
                if stored:
                    await auth_service.revoke_session(db, request, stored.id, user_id)
                await auth_service.log_event(db, "logout", request, user_id=user_id)

    clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate refresh token. Issues new access + refresh tokens.
    Detects and handles refresh token reuse (compromise signal).
    """
    raw_rt = get_refresh_token_from_cookie(request)
    if not raw_rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")

    user, _old_session = await auth_service.rotate_refresh_token(db=db, request=request, raw_refresh_token=raw_rt)

    # Determine remember_me from old token expiry duration
    from datetime import datetime, timezone
    remember_me = (_old_session.expires_at - _old_session.created_at).days >= auth_config.REMEMBER_ME_DAYS

    _, new_raw_rt = _issue_tokens_and_set_cookies(response, user, remember_me=remember_me)
    expires_days = auth_config.REMEMBER_ME_DAYS if remember_me else auth_config.REFRESH_TOKEN_EXPIRE_DAYS
    await auth_service.create_session(db=db, request=request, user=user, raw_refresh_token=new_raw_rt, expires_days=expires_days)

    return {"message": "Token refreshed.", "user": _user_response(user)}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Initiate a password reset. Always returns 200 to prevent email enumeration."""
    await auth_service.initiate_password_reset(db=db, request=request, email=body.email)
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete password reset using the token from the email link."""
    await auth_service.reset_password(
        db=db, request=request, raw_token=body.token, new_password=body.new_password
    )
    return {"message": "Password reset successfully. Please log in with your new password."}


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_verified_user),
):
    """Return the currently authenticated user's profile."""
    return {"user": _user_response(current_user)}


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    _csrf: None = Depends(validate_csrf_dep),
):
    """Update the current user's profile fields."""
    updated = await auth_service.update_profile(
        db=db,
        user=current_user,
        first_name=body.first_name,
        last_name=body.last_name,
        zip_code=body.zip_code,
        utility_provider=body.utility_provider,
        country=body.country,
        preferences=body.preferences,
    )
    return {"message": "Profile updated.", "user": _user_response(updated)}


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active (non-revoked) sessions for the current user."""
    sessions = await auth_service.get_active_sessions(db=db, user_id=current_user.id)
    return {
        "sessions": [
            {
                "id": s.id,
                "device_info": s.device_info,
                "ip_address": s.ip_address,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    _csrf: None = Depends(validate_csrf_dep),
):
    """Revoke a specific session by ID."""
    await auth_service.revoke_session(db=db, request=request, session_id=session_id, user_id=current_user.id)
    return {"message": "Session revoked."}


@router.delete("/sessions")
async def revoke_all_sessions(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    _csrf: None = Depends(validate_csrf_dep),
):
    """Revoke all sessions for the current user (logout all devices)."""
    await auth_service.revoke_all_sessions(db=db, request=request, user_id=current_user.id)
    clear_auth_cookies(response)
    return {"message": "All sessions revoked. You have been logged out from all devices."}
