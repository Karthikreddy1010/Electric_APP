"""
Dataset Metadata Tool for Grounded AI Assistant.
"""
import os
import json
from typing import Dict, Any, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field

DATASET_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "dataset_catalog.json")


class DataSourcesQuery(BaseModel):
    filter_keyword: str = Field(default="", description="Optional keyword to filter data sources by name, variable, or region")


@tool(args_schema=DataSourcesQuery)
def get_available_data_sources(filter_keyword: str = "") -> Dict[str, Any]:
    """
    Returns dataset metadata including dataset name, coverage, geography, time period,
    variables, update frequency, and limitations for all internal datasets.
    Use this to determine whether a requested fact exists in internal datasets.
    """
    if not os.path.exists(DATASET_CATALOG_PATH):
        return {
            "success": False,
            "error": f"Catalog file not found at {DATASET_CATALOG_PATH}",
            "datasets": []
        }

    try:
        with open(DATASET_CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        datasets = catalog.get("datasets", [])
        if filter_keyword:
            kw = filter_keyword.lower()
            filtered = [
                d for d in datasets
                if kw in d.get("name", "").lower() or
                   kw in d.get("id", "").lower() or
                   kw in str(d.get("variables", {})).lower() or
                   kw in str(d.get("spatial_coverage", {})).lower()
            ]
            datasets = filtered

        results = []
        for d in datasets:
            results.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "owner": d.get("owner"),
                "source": d.get("source"),
                "update_frequency": d.get("update_frequency"),
                "temporal_coverage": d.get("temporal_coverage"),
                "spatial_coverage": d.get("spatial_coverage"),
                "variables": list(d.get("variables", {}).keys()) if isinstance(d.get("variables"), dict) else d.get("variables"),
                "citation": d.get("citation")
            })

        return {
            "success": True,
            "count": len(results),
            "datasets": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "datasets": []
        }
