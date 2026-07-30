"""
EIA Retail Feature Store Router
Provides REST endpoints for querying engineered EIA Retail features, data quality audits, and dataset metadata.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.services.eia_service import eia_service
from feature_store.base.feature_store import global_feature_store
from feature_store.base.validation import validate_eia_retail_dataframe
from api.explainability import attach_explainability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eia-retail", tags=["eia-retail"])


@router.get("/summary")
@attach_explainability(
    data_sources=["EIA Retail Monthly (2001-2026)"],
    calculation_method="State-level monthly aggregation",
)
async def get_eia_summary(focus_state: str = Query("NJ")):
    """Returns high-level summary metrics for the focus state."""
    summary = eia_service.get_dashboard_summary(module_id="dashboard", focus_state=focus_state)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary data not available")
    return summary


@router.get("/state-prices")
@attach_explainability(
    data_sources=["EIA Retail Monthly"],
    calculation_method="Time-series historical price aggregation",
)
async def get_state_prices(
    stateid: str = Query("NJ"),
    sectorid: str = Query("RES"),
):
    """Returns full historical price series and current metrics for a state and sector."""
    res = eia_service.get_state_prices(module_id="regional_insights", state_id=stateid, sector_id=sectorid)
    if not res:
        raise HTTPException(status_code=404, detail=f"No data for state '{stateid}' and sector '{sectorid}'")
    return res


@router.get("/rankings")
@attach_explainability(
    data_sources=["EIA Retail Monthly"],
    calculation_method="National and regional percentile ranking algorithm",
)
async def get_state_rankings(
    period: Optional[str] = Query(None),
    sectorid: str = Query("RES"),
):
    """Returns ranking table across all US states for a specified period and sector."""
    ranks = eia_service.get_state_rankings(module_id="benchmark", period=period, sector_id=sectorid)
    return {"period": period, "sectorid": sectorid, "rankings": ranks}


@router.get("/quality-audit")
async def get_quality_audit():
    """Runs data quality audit engine over loaded EIA Retail feature store."""
    df = global_feature_store.get_dataset("EIA Retail", requesting_module="admin_analytics")
    if df.empty:
        return {"status": "error", "message": "EIA Retail DataFrame not loaded"}
    
    report = validate_eia_retail_dataframe(df)
    return report.to_dict()


@router.get("/datasets-registry")
async def get_datasets_registry():
    """Lists metadata and access policies for all registered datasets."""
    return {"datasets": global_feature_store.list_all_datasets()}


@router.get("/features-registry")
async def get_features_registry():
    """Lists metadata for all engineered features."""
    return {"features": global_feature_store.list_all_features()}
