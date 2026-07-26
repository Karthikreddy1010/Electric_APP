"""
backend.analytics.validation — Analytical output verification and identity checks.
"""
from __future__ import annotations

from typing import Dict, Any, List
from backend.schemas.analytics import AnalyticsResult
from backend.utils.exceptions import AnalyticsException


def validate_analytics_result(analytics: AnalyticsResult) -> Dict[str, Any]:
    """
    Verify mathematical accounting identities and sanity checks.
    
    Accounting Identity:
    Total Bill == Fixed Charges + Variable Charges + Billed Taxes
    """
    audit_results: Dict[str, Any] = {"passed": True, "checks": []}
    warnings: List[str] = []

    # 1. Total bill match check
    calc_total = round(
        analytics.component_breakdown.fixed_total
        + analytics.component_breakdown.variable_total
        + analytics.component_breakdown.taxes_total,
        2,
    )
    actual_total = round(analytics.component_breakdown.total_bill, 2)
    diff = abs(calc_total - actual_total)

    if diff > 0.05:
        audit_results["passed"] = False
        audit_results["checks"].append(
            f"Accounting identity failed: calc_total (${calc_total}) != actual_total (${actual_total})"
        )
        warnings.append(f"Accounting identity discrepancy of ${diff:.2f}")
    else:
        audit_results["checks"].append("Accounting identity check PASSED")

    # 2. Non-negative usage check
    if analytics.variable_charges.usage_kwh < 0:
        audit_results["passed"] = False
        audit_results["checks"].append("Usage kWh cannot be negative")

    # 3. Effective rate sanity check
    if analytics.tariff_calculations.effective_volumetric_rate > 1.50:
        warnings.append(
            f"Unusually high effective rate: ${analytics.tariff_calculations.effective_volumetric_rate}/kWh"
        )

    analytics.warnings.extend(warnings)
    analytics.quality_checks.update(audit_results)
    return audit_results
