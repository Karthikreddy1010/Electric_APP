"""
Explainability & Metadata Layer
Attaches transparency metadata (data sources, time period, calculation method, confidence level, assumptions)
to API responses.
"""
from __future__ import annotations
import functools
from typing import Dict, Any, List, Optional


def build_explainability_metadata(
    data_sources: List[str],
    time_period: str = "2001-01 to 2026-05",
    calculation_method: str = "State-level monthly aggregation & rolling statistics",
    confidence_level: str = "High (95% CI)",
    assumptions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if assumptions is None:
        assumptions = ["Historical trends assume standard weather degree-day distribution"]

    return {
        "data_sources": data_sources,
        "time_period": time_period,
        "calculation_method": calculation_method,
        "confidence_level": confidence_level,
        "assumptions": assumptions,
    }


def attach_explainability(
    data_sources: List[str],
    calculation_method: str = "Standard statistical calculation",
    confidence_level: str = "High",
):
    """Decorator to automatically append explainability block to route response dicts."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            res = await func(*args, **kwargs)
            if isinstance(res, dict):
                res["explainability"] = build_explainability_metadata(
                    data_sources=data_sources,
                    calculation_method=calculation_method,
                    confidence_level=confidence_level,
                )
            return res

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            if isinstance(res, dict):
                res["explainability"] = build_explainability_metadata(
                    data_sources=data_sources,
                    calculation_method=calculation_method,
                    confidence_level=confidence_level,
                )
            return res

        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
