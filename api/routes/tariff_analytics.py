import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database.connection import get_db
import api.services.tariff_lookup_service as tariff_service

router = APIRouter(prefix="/tariffs", tags=["Tariffs"])

@router.get("/active")
def get_active_tariff(utility_code: str = Query(..., description="Utility code (e.g., PSEG)"), schedule: str = Query(..., description="Rate schedule (e.g., RS, GLP)"), db: Session = Depends(get_db)):
    """Get the currently active tariff components for a specific schedule."""
    rates = tariff_service.get_active_tariff(db, utility_code, schedule)
    return {"utility": utility_code, "schedule": schedule, "rates": rates}

@router.get("/history")
def get_tariff_history(utility_code: str, schedule: str, db: Session = Depends(get_db)):
    """Get the complete history of a rate schedule over time."""
    history = tariff_service.get_tariff_history(db, utility_code, schedule)
    return {"utility": utility_code, "schedule": schedule, "history": history}

@router.get("/component-history")
def get_component_history(utility_code: str, component: str, db: Session = Depends(get_db)):
    """Get the history of a specific tariff component across all schedules."""
    history = tariff_service.get_component_history(db, utility_code, component)
    return {"utility": utility_code, "component": component, "history": history}

@router.get("/compare")
def compare_tariffs(utility_code: str, version1: str, version2: str, schedule: str, db: Session = Depends(get_db)):
    """Compare two specific tariff versions for a given schedule."""
    comparison = tariff_service.compare_tariffs(db, utility_code, version1, version2, schedule)
    return comparison

@router.get("/schedules")
def get_schedules(utility_code: str, db: Session = Depends(get_db)):
    """List all available rate schedules for a utility."""
    schedules = tariff_service.get_available_rate_schedules(db, utility_code)
    return {"utility": utility_code, "schedules": schedules}

@router.get("/summary")
def get_summary(utility_code: str, db: Session = Depends(get_db)):
    """Get high-level statistics about the tariff database for a utility."""
    return tariff_service.get_tariff_summary(db, utility_code)
