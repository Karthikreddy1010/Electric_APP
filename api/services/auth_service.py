"""
Auth Service — Business logic for all authentication operations.

This layer is called exclusively from the auth router.
It handles: registration, email verification, login, session management,
refresh token rotation, password reset, profile updates, and audit logging.
"""
from __future__ import annotations

import logging
import smtplib
import textwrap
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_config import auth_config
from api.auth_utils import (
    generate_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from database.auth_models import AuditLog, PasswordResetToken, RefreshToken, User

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "")[:500]


# ── Email ─────────────────────────────────────────────────────────────────────

async def _send_email(to: str, subject: str, body_html: str) -> None:
    """
    Send an email. In EMAIL_CONSOLE_ONLY mode (dev), logs the content instead.
    In production, configure SMTP_* env vars.
    """
    if auth_config.EMAIL_CONSOLE_ONLY:
        logger.info(
            f"\n{'='*60}\n"
            f"[DEV EMAIL] To: {to}\n"
            f"Subject: {subject}\n"
            f"{body_html}\n"
            f"{'='*60}"
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = auth_config.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html"))

    try:
        if auth_config.SMTP_USE_TLS:
            server = smtplib.SMTP(auth_config.SMTP_HOST, auth_config.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(auth_config.SMTP_HOST, auth_config.SMTP_PORT)
        if auth_config.SMTP_USER:
            server.login(auth_config.SMTP_USER, auth_config.SMTP_PASSWORD)
        server.sendmail(auth_config.SMTP_FROM, to, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")


async def send_verification_email(user: User, raw_token: str) -> None:
    verify_url = f"{auth_config.FRONTEND_URL}/app/verify-email?token={raw_token}"
    await _send_email(
        to=user.email,
        subject="Verify your ElectricAI account",
        body_html=textwrap.dedent(f"""
            <h2>Welcome to ElectricAI, {user.first_name}!</h2>
            <p>Please verify your email address to activate your account.</p>
            <p><a href="{verify_url}" style="background:#2563eb;color:white;padding:12px 24px;
               border-radius:6px;text-decoration:none;display:inline-block;">
               Verify Email Address
            </a></p>
            <p>Or copy this link: {verify_url}</p>
            <p>This link expires in {auth_config.VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
            <p>If you did not create an account, you can safely ignore this email.</p>
        """),
    )


async def send_password_reset_email(user: User, raw_token: str) -> None:
    reset_url = f"{auth_config.FRONTEND_URL}/app/reset-password?token={raw_token}"
    await _send_email(
        to=user.email,
        subject="Reset your ElectricAI password",
        body_html=textwrap.dedent(f"""
            <h2>Password Reset Request</h2>
            <p>We received a request to reset the password for your ElectricAI account ({user.email}).</p>
            <p><a href="{reset_url}" style="background:#2563eb;color:white;padding:12px 24px;
               border-radius:6px;text-decoration:none;display:inline-block;">
               Reset Password
            </a></p>
            <p>Or copy this link: {reset_url}</p>
            <p>This link expires in {auth_config.RESET_TOKEN_EXPIRE_HOURS} hour(s).</p>
            <p>If you did not request this, please ignore this email. Your password is unchanged.</p>
        """),
    )


# ── Audit Logging ─────────────────────────────────────────────────────────────

async def log_event(
    db: AsyncSession,
    event_type: str,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Write a security audit event."""
    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        details=details or {},
    )
    db.add(entry)
    # Don't commit — let the caller's transaction handle it


# ── Registration ──────────────────────────────────────────────────────────────

async def register_user(
    db: AsyncSession,
    request: Request,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    zip_code: str = "",
    utility_provider: str = "",
    country: str = "US",
) -> User:
    """
    Create a new user account.
    Raises HTTP 400 on validation errors or duplicate email.
    """
    # Validate password strength
    pw_errors = validate_password_strength(password)
    if pw_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_errors[0])

    # Check for existing email
    result = await db.execute(select(User).where(User.email == email.lower()))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Generate verification token
    raw_token = generate_token()
    token_hash = hash_token(raw_token)
    token_expires = _utcnow() + timedelta(hours=auth_config.VERIFICATION_TOKEN_EXPIRE_HOURS)

    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        zip_code=zip_code.strip(),
        utility_provider=utility_provider.strip(),
        country=country,
        email_verified=False,
        verification_token_hash=token_hash,
        verification_token_expires=token_expires,
    )
    db.add(user)
    await db.flush()  # Get user.id without committing

    await log_event(db, "signup", request, user_id=user.id, details={"email": user.email})
    await send_verification_email(user, raw_token)

    return user


# ── Email Verification ────────────────────────────────────────────────────────

async def verify_email(db: AsyncSession, request: Request, raw_token: str) -> User:
    """Mark account as email-verified. Raises 400 on invalid/expired token."""
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(User).where(
            User.verification_token_hash == token_hash,
            User.email_verified == False,  # noqa: E712
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used verification link.")

    if user.verification_token_expires and user.verification_token_expires < _utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link has expired. Please request a new one.")

    user.email_verified = True
    user.verification_token_hash = None
    user.verification_token_expires = None
    await log_event(db, "email_verified", request, user_id=user.id)
    return user


async def resend_verification_email(db: AsyncSession, request: Request, email: str) -> None:
    """Regenerate and resend the verification email."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalars().first()
    if not user or user.email_verified:
        return  # Silent — don't leak user existence

    raw_token = generate_token()
    user.verification_token_hash = hash_token(raw_token)
    user.verification_token_expires = _utcnow() + timedelta(hours=auth_config.VERIFICATION_TOKEN_EXPIRE_HOURS)
    await send_verification_email(user, raw_token)


# ── Login ─────────────────────────────────────────────────────────────────────

async def authenticate_user(
    db: AsyncSession,
    request: Request,
    email: str,
    password: str,
) -> User:
    """
    Validate credentials and return the User.
    Implements: account locking after repeated failures, email-verified check.
    """
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalars().first()

    # Use constant-time comparison to avoid user enumeration via timing
    if not user:
        # Still verify a dummy hash to prevent timing attacks
        verify_password("dummy", "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
        await log_event(db, "failed_login", request, details={"email": email, "reason": "user_not_found"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check account lock
    if user.locked_until and user.locked_until > _utcnow():
        minutes_remaining = int((user.locked_until - _utcnow()).total_seconds() / 60) + 1
        await log_event(db, "failed_login", request, user_id=user.id, details={"reason": "account_locked"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minute(s).",
        )

    if user.account_status == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended.")

    # Verify password
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= auth_config.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = _utcnow() + timedelta(minutes=auth_config.ACCOUNT_LOCK_MINUTES)
            user.account_status = "locked"
            await log_event(db, "account_locked", request, user_id=user.id,
                           details={"failed_attempts": user.failed_login_attempts})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Too many failed attempts. Account locked for {auth_config.ACCOUNT_LOCK_MINUTES} minutes.",
            )
        await log_event(db, "failed_login", request, user_id=user.id,
                       details={"attempts": user.failed_login_attempts})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid email or password. {auth_config.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts} attempt(s) remaining.",
        )

    # Check email verification
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",  # Frontend checks this specific string
        )

    # Reset failed attempts on success
    user.failed_login_attempts = 0
    user.locked_until = None
    user.account_status = "active"
    user.last_login = _utcnow()
    await log_event(db, "login", request, user_id=user.id)
    return user


# ── Session / Refresh Token Management ───────────────────────────────────────

async def create_session(
    db: AsyncSession,
    request: Request,
    user: User,
    raw_refresh_token: str,
    expires_days: int,
) -> None:
    """Store the hashed refresh token as a new session."""
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        device_info=_get_user_agent(request)[:500],
        ip_address=_get_client_ip(request),
        expires_at=_utcnow() + timedelta(days=expires_days),
    )
    db.add(token)


async def rotate_refresh_token(
    db: AsyncSession,
    request: Request,
    raw_refresh_token: str,
) -> tuple[User, RefreshToken]:
    """
    Refresh token rotation with reuse detection.
    Returns (user, new_db_token_record).
    Raises 401 on invalid/expired/revoked token.
    On reuse of a revoked token, ALL sessions are revoked (compromise assumed).
    """
    token_hash = hash_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalars().first()

    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    if stored.is_revoked:
        # Reuse of revoked token — possible compromise: revoke ALL sessions
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id)
            .values(is_revoked=True, revoked_at=_utcnow())
        )
        await log_event(db, "token_reuse_detected", request, user_id=stored.user_id,
                       details={"action": "all_sessions_revoked"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions have been revoked for security.",
        )

    if stored.expires_at < _utcnow():
        stored.is_revoked = True
        stored.revoked_at = _utcnow()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired.")

    # Get associated user
    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalars().first()
    if not user or user.account_status == "suspended":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is no longer active.")

    # Revoke old token
    stored.is_revoked = True
    stored.revoked_at = _utcnow()

    return user, stored


async def revoke_session(db: AsyncSession, request: Request, session_id: str, user_id: str) -> None:
    """Revoke a specific refresh token session by ID."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user_id,
        )
    )
    token = result.scalars().first()
    if token:
        token.is_revoked = True
        token.revoked_at = _utcnow()
        await log_event(db, "session_revoked", request, user_id=user_id, details={"session_id": session_id})


async def revoke_all_sessions(db: AsyncSession, request: Request, user_id: str) -> None:
    """Revoke all refresh token sessions for a user (logout all devices)."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
        .values(is_revoked=True, revoked_at=_utcnow())
    )
    await log_event(db, "logout_all", request, user_id=user_id)


async def get_active_sessions(db: AsyncSession, user_id: str) -> list[RefreshToken]:
    """Return all non-revoked, non-expired sessions for a user."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,  # noqa: E712
            RefreshToken.expires_at > _utcnow(),
        )
    )
    return result.scalars().all()


# ── Password Reset ────────────────────────────────────────────────────────────

async def initiate_password_reset(db: AsyncSession, request: Request, email: str) -> None:
    """Generate a password reset token and send the email. Silent on unknown email."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalars().first()
    if not user:
        return  # Silent — don't leak whether email exists

    raw_token = generate_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=_utcnow() + timedelta(hours=auth_config.RESET_TOKEN_EXPIRE_HOURS),
    )
    db.add(reset)
    await db.flush()
    await send_password_reset_email(user, raw_token)
    await log_event(db, "password_reset_requested", request, user_id=user.id)


async def reset_password(
    db: AsyncSession,
    request: Request,
    raw_token: str,
    new_password: str,
) -> User:
    """Validate reset token, update password, revoke all sessions."""
    pw_errors = validate_password_strength(new_password)
    if pw_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_errors[0])

    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used == False,  # noqa: E712
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used reset link.")

    if reset_token.expires_at < _utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset link has expired.")

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")

    # Mark token used and update password
    reset_token.is_used = True
    reset_token.used_at = _utcnow()
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.account_status = "active"

    # Revoke all sessions — forces re-login on all devices
    await revoke_all_sessions(db, request, user.id)
    await log_event(db, "password_reset_completed", request, user_id=user.id)
    return user


# ── Profile Update ────────────────────────────────────────────────────────────

async def update_profile(
    db: AsyncSession,
    user: User,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    zip_code: Optional[str] = None,
    utility_provider: Optional[str] = None,
    country: Optional[str] = None,
    preferences: Optional[dict] = None,
) -> User:
    """Update allowed profile fields."""
    if first_name is not None:
        user.first_name = first_name.strip()
    if last_name is not None:
        user.last_name = last_name.strip()
    if zip_code is not None:
        user.zip_code = zip_code.strip()
    if utility_provider is not None:
        user.utility_provider = utility_provider.strip()
    if country is not None:
        user.country = country.strip()
    if preferences is not None:
        existing = dict(user.preferences or {})
        existing.update(preferences)
        user.preferences = existing
    return user
