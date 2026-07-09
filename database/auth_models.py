"""
Auth ORM Models — User, RefreshToken, PasswordResetToken, AuditLog.

These models are imported by database/models.py to ensure they are
included in Base.metadata and auto-created on startup.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from database.models import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Production User model with full security features.

    Password is always stored as an Argon2 hash — never plaintext.
    Accounts are locked after MAX_FAILED_LOGIN_ATTEMPTS consecutive failures.
    Email must be verified before the user can access the dashboard.
    """
    __tablename__ = "auth_users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(512), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False, default="")
    country = Column(String(100), default="US")
    zip_code = Column(String(20), default="")
    utility_provider = Column(String(200), default="")

    # Role: user | admin | developer
    role = Column(
        Enum("user", "admin", "developer", name="user_role"),
        nullable=False,
        default="user",
    )

    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token_hash = Column(String(64), nullable=True, index=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Account status: active | locked | suspended
    account_status = Column(
        Enum("active", "locked", "suspended", name="account_status"),
        nullable=False,
        default="active",
    )
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    # User preferences (JSON blob: theme, notifications, etc.)
    preferences = Column(JSON, default=dict)

    active_bill_id = Column(String(36), ForeignKey("user_bills.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    bills = relationship("UserBill", back_populates="user", foreign_keys="[UserBill.user_id]", cascade="all, delete-orphan")
    active_bill = relationship("UserBill", foreign_keys=[active_bill_id])
    reports = relationship("UserReport", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_auth_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


# ── RefreshToken ─────────────────────────────────────────────────────────────

class RefreshToken(Base):
    """
    Stored refresh tokens (hashed).

    We store the SHA-256 hash of the raw token, never the token itself.
    Refresh token rotation: when a token is used, it's revoked and a new one is issued.
    Token reuse detection: if a revoked token is reused, all sessions for the user
    are immediately revoked (compromise assumed).
    """
    __tablename__ = "auth_refresh_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    device_info = Column(String(500), nullable=True)  # User-Agent truncated
    ip_address = Column(String(45), nullable=True)    # IPv4 or IPv6
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_token_hash", "token_hash"),
        Index("ix_refresh_user_id", "user_id"),
    )


# ── PasswordResetToken ───────────────────────────────────────────────────────

class PasswordResetToken(Base):
    """
    Single-use password reset tokens (hashed).

    Tokens expire after RESET_TOKEN_EXPIRE_HOURS and are marked used after first use.
    """
    __tablename__ = "auth_password_reset_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")


# ── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Security audit log.

    Events: login, logout, signup, password_change, email_change,
    failed_login, account_locked, session_revoked, password_reset_requested,
    password_reset_completed, email_verified.
    """
    __tablename__ = "auth_audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_created_at", "created_at"),
    )


# ── UserBill ─────────────────────────────────────────────────────────────────

class UserBill(Base):
    """
    User uploaded utility bills (persistent SaaS data).
    Stores parsed values, ocr runs, forecast, regional comparison, and recommendations.
    """
    __tablename__ = "user_bills"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    bill_date = Column(Date, nullable=False)
    billing_period = Column(String(100), nullable=True)
    utility_provider = Column(String(200), nullable=True)
    usage_kwh = Column(Float, nullable=True)
    total_bill = Column(Float, nullable=True)
    status = Column(String(50), default="active", nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Cached results
    bill_data = Column(JSON, default=dict)
    ocr_results = Column(JSON, default=list)
    analysis_results = Column(JSON, default=dict)
    insights = Column(JSON, default=list)
    explanation = Column(Text, nullable=True)
    forecast_results = Column(JSON, default=dict)
    simulation_results = Column(JSON, default=dict)
    regional_comparison = Column(JSON, default=dict)
    recommendations = Column(JSON, default=dict)

    user = relationship("User", back_populates="bills", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_user_bills_user_id", "user_id"),
        Index("ix_user_bills_bill_date", "bill_date"),
    )


# ── UserReport ───────────────────────────────────────────────────────────────

class UserReport(Base):
    """
    Saved custom reports for the authenticated user.
    """
    __tablename__ = "user_reports"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_id = Column(String(36), ForeignKey("user_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    data = Column(JSON, default=dict)

    user = relationship("User", back_populates="reports")
    bill = relationship("UserBill")

    __table_args__ = (
        Index("ix_user_reports_user_id", "user_id"),
    )


# ── UserNotification ─────────────────────────────────────────────────────────

class UserNotification(Base):
    """
    In-app notification system for users.
    """
    __tablename__ = "user_notifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_user_notifications_user_id", "user_id"),
        Index("ix_user_notifications_is_read", "is_read"),
    )

