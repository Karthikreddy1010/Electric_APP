"""
Admin Analytics & Data Quality Router
Provides coverage reports, missing values audit, growth trends, dataset freshness, and data quality dashboards.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter
from feature_store.base.feature_store import global_feature_store
from feature_store.base.validation import validate_eia_retail_dataframe
from api.explainability import attach_explainability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin-analytics", tags=["admin-analytics"])


@router.get("/quality-dashboard")
@attach_explainability(
    data_sources=["DataRegistry System Audit"],
    calculation_method="Automated schema drift & null value validation engine",
)
async def get_admin_quality_dashboard():
    """Returns data quality monitoring and coverage report across all registered datasets."""
    df_eia = global_feature_store.get_dataset("EIA Retail", requesting_module="admin_analytics")
    
    eia_report = validate_eia_retail_dataframe(df_eia) if not df_eia.empty else None

    registered_datasets = global_feature_store.list_all_datasets()
    registered_features = global_feature_store.list_all_features()

    return {
        "overall_health": "Healthy" if (eia_report and eia_report.is_passed) else "Attention Required",
        "registered_datasets_count": len(registered_datasets),
        "registered_features_count": len(registered_features),
        "datasets": registered_datasets,
        "eia_quality_report": eia_report.to_dict() if eia_report else {},
    }
