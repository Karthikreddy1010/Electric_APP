import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

import api.services.tariff_lookup_service as tariff_service

def reconstruct_historical_bill(
    session: Session,
    utility_code: str,
    bill_date: datetime.date,
    schedule: str,
    usage_kwh: float,
    demand_kw: float = 0.0
) -> Dict[str, Any]:
    """
    Reconstruct what a bill would have looked like historically based on the exact tariff version
    active on `bill_date`.
    """
    bill = tariff_service.calculate_bill_using_tariff(
        session, utility_code, bill_date, schedule, usage_kwh, demand_kw
    )
    
    if "error" in bill:
        return bill
        
    return {
        "reconstruction_date": bill_date,
        "utility": utility_code,
        "schedule": schedule,
        "usage_kwh": usage_kwh,
        "demand_kw": demand_kw,
        "tariff_version": bill["tariff_version"],
        "total_cost": bill["total_cost"],
        "components": bill["components"]
    }

def compare_historical_bills(
    session: Session,
    utility_code: str,
    date1: datetime.date,
    date2: datetime.date,
    schedule: str,
    usage_kwh: float,
    demand_kw: float = 0.0
) -> Dict[str, Any]:
    """
    Compare two historical bill reconstructions to explain exactly why the bill changed.
    """
    bill1 = reconstruct_historical_bill(session, utility_code, date1, schedule, usage_kwh, demand_kw)
    bill2 = reconstruct_historical_bill(session, utility_code, date2, schedule, usage_kwh, demand_kw)
    
    if "error" in bill1:
        return {"error": f"Failed to calculate bill 1: {bill1['error']}"}
    if "error" in bill2:
        return {"error": f"Failed to calculate bill 2: {bill2['error']}"}
        
    map1 = {c["component"]: c["cost"] for c in bill1["components"]}
    map2 = {c["component"]: c["cost"] for c in bill2["components"]}
    
    all_components = set(map1.keys()) | set(map2.keys())
    
    comparison = []
    for comp in all_components:
        c1 = map1.get(comp, 0.0)
        c2 = map2.get(comp, 0.0)
        comparison.append({
            "component": comp,
            "date1_cost": c1,
            "date2_cost": c2,
            "difference": c2 - c1,
            "percent_change": ((c2 - c1) / c1 * 100) if c1 else None
        })
        
    return {
        "utility": utility_code,
        "schedule": schedule,
        "usage_kwh": usage_kwh,
        "demand_kw": demand_kw,
        "date1": date1,
        "date2": date2,
        "date1_version": bill1["tariff_version"],
        "date2_version": bill2["tariff_version"],
        "date1_total": bill1["total_cost"],
        "date2_total": bill2["total_cost"],
        "total_difference": bill2["total_cost"] - bill1["total_cost"],
        "total_percent_change": ((bill2["total_cost"] - bill1["total_cost"]) / bill1["total_cost"] * 100) if bill1["total_cost"] else None,
        "components": comparison
    }
