"""
backend.database.models — SQLAlchemy ORM models for Phase 1 backend persistence.

Extends the project's declarative Base to create tables for Bill upload tracking,
AnalyticsResult snapshots, and asynchronous task execution logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from database.models import Base


class BillRecord(Base):
    """ORM table recording uploaded bill metadata and processing state."""
    __tablename__ = "phase1_bills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_hash = Column(String(64), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False, default="uploaded_bill.pdf")
    file_path = Column(String(512), nullable=False)
    tenant_id = Column(String(64), default="default_tenant", index=True)
    customer_id = Column(String(64), default="UPLOADED-BILL", index=True)
    utility = Column(String(100), default="PSE&G")
    zip_code = Column(String(20), default="07102")
    status = Column(String(32), default="UPLOADED", index=True)
    progress_pct = Column(Integer, default=0)
    stage_message = Column(String(255), default="")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AnalyticsRecord(Base):
    """ORM table storing computed AnalyticsResult JSON documents."""
    __tablename__ = "phase1_analytics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_id = Column(String(36), index=True, nullable=False)
    bill_hash = Column(String(64), index=True, nullable=False)
    tenant_id = Column(String(64), default="default_tenant", index=True)
    
    analytics_version = Column(String(20), default="1.0.0")
    ocr_version = Column(String(20), default="1.0.0")
    parser_version = Column(String(20), default="1.0.0")
    tariff_version = Column(String(20), default="2026.07")
    weather_version = Column(String(20), default="2026.07")
    
    usage_kwh = Column(Float, default=0.0)
    total_bill = Column(Float, default=0.0)
    effective_rate = Column(Float, default=0.0)
    confidence_score = Column(Float, default=1.0)
    
    # Store complete strongly typed AnalyticsResult JSON payload
    analytics_result_json = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class TaskStatusRecord(Base):
    """ORM table tracking asynchronous task execution state."""
    __tablename__ = "phase1_tasks"

    task_id = Column(String(64), primary_key=True)
    bill_hash = Column(String(64), index=True, nullable=False)
    status = Column(String(32), default="PENDING", index=True)
    stage = Column(String(32), default="INIT")
    progress_pct = Column(Integer, default=0)
    result_payload = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
