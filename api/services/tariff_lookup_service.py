import datetime
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from database.models import TariffVersion, HistoricalUtilityTariff

def get_tariff(session: Session, utility_code: str, billing_date: datetime.date, schedule: str, component: str) -> Optional[float]:
    """
    Get a specific historical rate component for a specific utility, schedule, and date.
    """
    # 1. Find the active tariff version for this date
    version = session.execute(
        select(TariffVersion)
        .where(
            and_(
                TariffVersion.utility_code == utility_code,
                TariffVersion.effective_start <= billing_date,
                TariffVersion.effective_end >= billing_date
            )
        )
        .order_by(desc(TariffVersion.effective_start))
        .limit(1)
    ).scalar_one_or_none()
    
    if not version:
        return None
        
    # 2. Get the specific rate
    rate = session.execute(
        select(HistoricalUtilityTariff.rate)
        .where(
            and_(
                HistoricalUtilityTariff.tariff_version_id == version.id,
                HistoricalUtilityTariff.schedule == schedule,
                HistoricalUtilityTariff.component == component
            )
        )
        .limit(1)
    ).scalar_one_or_none()
    
    return rate

def get_active_tariff(session: Session, utility_code: str, schedule: str) -> List[Dict[str, Any]]:
    """
    Get all active rate components for the most recent tariff version.
    """
    version = session.execute(
        select(TariffVersion)
        .where(TariffVersion.utility_code == utility_code)
        .order_by(desc(TariffVersion.effective_start))
        .limit(1)
    ).scalar_one_or_none()
    
    if not version:
        return []
        
    rates = session.execute(
        select(HistoricalUtilityTariff)
        .where(
            and_(
                HistoricalUtilityTariff.tariff_version_id == version.id,
                HistoricalUtilityTariff.schedule == schedule
            )
        )
    ).scalars().all()
    
    return [
        {
            "component": r.component,
            "category": r.component_category,
            "rate": r.rate,
            "unit": r.unit,
            "season": r.season
        } for r in rates
    ]

def get_tariff_history(session: Session, utility_code: str, schedule: str) -> List[Dict[str, Any]]:
    """
    Get the entire historical timeline of tariffs for a given schedule.
    """
    query = (
        select(TariffVersion, HistoricalUtilityTariff)
        .join(HistoricalUtilityTariff, TariffVersion.id == HistoricalUtilityTariff.tariff_version_id)
        .where(
            and_(
                TariffVersion.utility_code == utility_code,
                HistoricalUtilityTariff.schedule == schedule
            )
        )
        .order_by(desc(TariffVersion.effective_start))
    )
    
    results = session.execute(query).all()
    
    history = {}
    for version, rate in results:
        v_id = version.id
        if v_id not in history:
            history[v_id] = {
                "version_name": version.tariff_version,
                "effective_start": version.effective_start,
                "effective_end": version.effective_end,
                "components": []
            }
        history[v_id]["components"].append({
            "component": rate.component,
            "rate": rate.rate,
            "unit": rate.unit,
            "category": rate.component_category
        })
        
    return list(history.values())

def get_component_history(session: Session, utility_code: str, component: str) -> List[Dict[str, Any]]:
    """
    Get the historical rates of a specific component over time across all schedules.
    """
    query = (
        select(TariffVersion.effective_start, TariffVersion.effective_end, HistoricalUtilityTariff.schedule, HistoricalUtilityTariff.rate)
        .join(HistoricalUtilityTariff, TariffVersion.id == HistoricalUtilityTariff.tariff_version_id)
        .where(
            and_(
                TariffVersion.utility_code == utility_code,
                HistoricalUtilityTariff.component == component
            )
        )
        .order_by(HistoricalUtilityTariff.schedule, desc(TariffVersion.effective_start))
    )
    
    results = session.execute(query).all()
    return [
        {
            "effective_start": r.effective_start,
            "effective_end": r.effective_end,
            "schedule": r.schedule,
            "rate": r.rate
        } for r in results
    ]

def compare_tariffs(session: Session, utility_code: str, version1: str, version2: str, schedule: str) -> Dict[str, Any]:
    """
    Compare the components between two specific tariff versions.
    """
    v1 = session.execute(select(TariffVersion).where(TariffVersion.utility_code == utility_code, TariffVersion.tariff_version == version1)).scalar_one_or_none()
    v2 = session.execute(select(TariffVersion).where(TariffVersion.utility_code == utility_code, TariffVersion.tariff_version == version2)).scalar_one_or_none()
    
    if not v1 or not v2:
        return {"error": "Tariff version not found"}
        
    r1 = session.execute(select(HistoricalUtilityTariff).where(HistoricalUtilityTariff.tariff_version_id == v1.id, HistoricalUtilityTariff.schedule == schedule)).scalars().all()
    r2 = session.execute(select(HistoricalUtilityTariff).where(HistoricalUtilityTariff.tariff_version_id == v2.id, HistoricalUtilityTariff.schedule == schedule)).scalars().all()
    
    map1 = {r.component: r.rate for r in r1}
    map2 = {r.component: r.rate for r in r2}
    
    all_components = set(map1.keys()) | set(map2.keys())
    
    comparison = []
    for comp in all_components:
        rate1 = map1.get(comp, 0.0)
        rate2 = map2.get(comp, 0.0)
        comparison.append({
            "component": comp,
            "v1_rate": rate1,
            "v2_rate": rate2,
            "difference": rate2 - rate1,
            "percent_change": ((rate2 - rate1) / rate1 * 100) if rate1 else None
        })
        
    return {
        "schedule": schedule,
        "v1": version1,
        "v2": version2,
        "components": comparison
    }

def get_available_rate_schedules(session: Session, utility_code: str) -> List[str]:
    """
    Get a list of all distinct rate schedules available for a utility.
    """
    schedules = session.execute(
        select(HistoricalUtilityTariff.schedule)
        .join(TariffVersion, TariffVersion.id == HistoricalUtilityTariff.tariff_version_id)
        .where(TariffVersion.utility_code == utility_code)
        .distinct()
    ).scalars().all()
    return schedules

def calculate_component_cost(session: Session, utility_code: str, billing_date: datetime.date, schedule: str, component: str, usage_amount: float) -> float:
    """
    Helper to quickly calculate cost of a specific component based on historical rate.
    """
    rate = get_tariff(session, utility_code, billing_date, schedule, component)
    if rate is None:
        return 0.0
    return rate * usage_amount

def calculate_bill_using_tariff(session: Session, utility_code: str, billing_date: datetime.date, schedule: str, usage_kwh: float, demand_kw: float = 0.0) -> Dict[str, Any]:
    """
    Simulate a full bill calculation using the historical tariff engine.
    """
    version = session.execute(
        select(TariffVersion)
        .where(
            and_(
                TariffVersion.utility_code == utility_code,
                TariffVersion.effective_start <= billing_date,
                TariffVersion.effective_end >= billing_date
            )
        )
        .order_by(desc(TariffVersion.effective_start))
        .limit(1)
    ).scalar_one_or_none()
    
    if not version:
        return {"error": "No valid tariff found for date"}
        
    rates = session.execute(
        select(HistoricalUtilityTariff)
        .where(
            and_(
                HistoricalUtilityTariff.tariff_version_id == version.id,
                HistoricalUtilityTariff.schedule == schedule
            )
        )
    ).scalars().all()
    
    components = []
    total = 0.0
    
    for r in rates:
        cost = 0.0
        if r.component_category == "fixed":
            cost = r.rate
        elif r.component_category == "volumetric":
            cost = r.rate * usage_kwh
        elif r.component_category == "demand":
            cost = r.rate * demand_kw
            
        total += cost
        components.append({
            "component": r.component,
            "category": r.component_category,
            "rate": r.rate,
            "cost": cost
        })
        
    return {
        "tariff_version": version.tariff_version,
        "calculation_engine_version": "v2.0",
        "total_cost": total,
        "components": components
    }

def get_tariff_summary(session: Session, utility_code: str) -> Dict[str, Any]:
    """
    Returns summary metadata about the tariff engine data quality.
    """
    num_versions = session.query(func.count(TariffVersion.id)).where(TariffVersion.utility_code == utility_code).scalar()
    num_rates = session.query(func.count(HistoricalUtilityTariff.id)).join(TariffVersion).where(TariffVersion.utility_code == utility_code).scalar()
    schedules = get_available_rate_schedules(session, utility_code)
    
    return {
        "utility": utility_code,
        "total_versions": num_versions,
        "total_rates": num_rates,
        "schedules": schedules
    }
