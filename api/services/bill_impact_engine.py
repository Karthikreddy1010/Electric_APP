"""
Bill Impact Engine — Deterministic bill calculation and impact analysis.

This module answers: "If a specific electricity bill component changes,
how much does the total bill change?" using actual billing logic, not ML.

Architecture:
  - calculate_total_bill()  — core billing math
  - sensitivity_analysis()  — single-component impact
  - what_if_analysis()      — multi-component scenario
  - rank_components()       — rank by influence
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
#  COMPONENT REGISTRY — canonical metadata for every bill component
# ═══════════════════════════════════════════════════════════════════════════

NJ_SALES_TAX_RATE = 0.06625

COMPONENT_TYPES: dict[str, dict[str, str]] = {
    "bgs_rate": {
        "type": "variable",
        "cost_col": "bgs_cost",
        "label": "BGS Supply",
        "driver": "market",
        "insight": "Scales with usage (kWh). Largest variable component; wholesale energy cost.",
    },
    "transmission_rate": {
        "type": "variable",
        "cost_col": "transmission_cost",
        "label": "Transmission Charge",
        "driver": "market",
        "insight": "Scales with usage (kWh). Reflects regional grid congestion costs.",
    },
    "distribution_rate": {
        "type": "variable",
        "cost_col": "distribution_cost",
        "label": "Distribution Charge",
        "driver": "infrastructure",
        "insight": "Scales with usage (kWh). Local delivery network cost.",
    },
    "sbc_rate": {
        "type": "variable",
        "cost_col": "sbc_cost",
        "label": "Societal Benefits Charge",
        "driver": "policy",
        "insight": "Scales with usage (kWh). Funds energy efficiency & renewables.",
    },
    "nug_rate": {
        "type": "variable",
        "cost_col": "nug_cost",
        "label": "Non-Utility Generation",
        "driver": "regulatory",
        "insight": "Scales with usage (kWh). Legacy non-utility generation contracts.",
    },
    "dr_credit": {
        "type": "adjustment",
        "cost_col": "dr_credit",
        "label": "Demand Response Credit",
        "driver": "policy",
        "insight": "Irregular / policy-driven impact. Credit for demand response participation.",
    },
    "sales_tax": {
        "type": "tax",
        "cost_col": "sales_tax",
        "label": "Sales Tax (NJ 6.625%)",
        "driver": "policy",
        "insight": "Proportional to subtotal. Changes propagate from all other components.",
    },
}

# Components that are rates (multiplied by kWh)
_VARIABLE_RATE_KEYS = [k for k, v in COMPONENT_TYPES.items() if v["type"] == "variable"]

# Components that are direct dollar amounts
_DIRECT_COST_KEYS = ["dr_credit"]


# ═══════════════════════════════════════════════════════════════════════════
#  CORE: calculate_total_bill
# ═══════════════════════════════════════════════════════════════════════════

def calculate_total_bill(
    components: dict[str, float],
    kwh: float,
    tax_rate: float = NJ_SALES_TAX_RATE,
) -> dict[str, Any]:
    """
    Deterministic bill calculation from component rates/values + kWh.

    Parameters
    ----------
    components : dict
        Keys are rate names (e.g. "bgs_rate") or direct costs ("dr_credit").
        Values are the rate ($/kWh) or dollar amount.
    kwh : float
        Monthly electricity usage in kWh.
    tax_rate : float
        Sales tax rate (default: NJ 6.625%).

    Returns
    -------
    dict with: total_bill, subtotal, tax, line_items (component breakdown)
    """
    line_items: dict[str, float] = {}

    # Variable components: rate × kWh
    for key in _VARIABLE_RATE_KEYS:
        rate = components.get(key, 0.0)
        cost = round(rate * kwh, 2)
        cost_col = COMPONENT_TYPES[key]["cost_col"]
        line_items[cost_col] = cost

    # Direct cost components
    for key in _DIRECT_COST_KEYS:
        line_items[key] = round(components.get(key, 0.0), 2)

    subtotal = round(sum(line_items.values()), 2)
    tax = round(subtotal * tax_rate, 2)
    total_bill = round(subtotal + tax, 2)

    return {
        "total_bill": total_bill,
        "subtotal": subtotal,
        "sales_tax": tax,
        "usage_kwh": kwh,
        "line_items": line_items,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Extract current component values from a billing row
# ═══════════════════════════════════════════════════════════════════════════

def _extract_components(row: dict) -> dict[str, float]:
    """Pull current rate/cost values from a billing data row."""
    components: dict[str, float] = {}
    for key in _VARIABLE_RATE_KEYS:
        components[key] = float(row.get(key, 0.0))
    for key in _DIRECT_COST_KEYS:
        components[key] = float(row.get(key, 0.0))
    return components


# ═══════════════════════════════════════════════════════════════════════════
#  SENSITIVITY: change one component, measure total bill impact
# ═══════════════════════════════════════════════════════════════════════════

def sensitivity_analysis(
    row: dict,
    component: str,
    change_pct: float,
    kwh: float | None = None,
) -> dict[str, Any]:
    """
    Change ONE component by change_pct% and measure total bill impact.

    Parameters
    ----------
    row         : latest billing row as dict
    component   : key from COMPONENT_TYPES (e.g. "bgs_rate")
    change_pct  : percentage change (e.g. 10.0 for +10%)
    kwh         : override kWh (default: from row)
    """
    if component not in COMPONENT_TYPES:
        raise ValueError(
            f"Unknown component '{component}'. "
            f"Valid: {list(COMPONENT_TYPES.keys())}"
        )

    usage = kwh if kwh is not None else float(row.get("usage_kwh", 750))
    base_components = _extract_components(row)
    base_bill = calculate_total_bill(base_components, usage)

    # Apply change
    modified = dict(base_components)
    original_value = modified.get(component, 0.0)
    delta = original_value * (change_pct / 100.0)
    modified[component] = original_value + delta

    new_bill = calculate_total_bill(modified, usage)

    impact = round(new_bill["total_bill"] - base_bill["total_bill"], 2)
    pct_impact = round((impact / base_bill["total_bill"]) * 100, 4) if base_bill["total_bill"] else 0.0
    elasticity = round(pct_impact / change_pct, 4) if change_pct != 0 else 0.0

    meta = COMPONENT_TYPES[component]

    return {
        "component": component,
        "label": meta["label"],
        "component_type": meta["type"],
        "driver": meta["driver"],
        "change_pct": change_pct,
        "original_value": round(original_value, 6),
        "new_value": round(original_value + delta, 6),
        "base_bill": base_bill["total_bill"],
        "new_bill": new_bill["total_bill"],
        "impact_dollars": impact,
        "impact_pct": pct_impact,
        "elasticity": elasticity,
        "insight": meta["insight"],
        "base_breakdown": base_bill["line_items"],
        "new_breakdown": new_bill["line_items"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  WHAT-IF: modify multiple components simultaneously
# ═══════════════════════════════════════════════════════════════════════════

def what_if_analysis(
    row: dict,
    changes: dict[str, float],
    kwh: float | None = None,
) -> dict[str, Any]:
    """
    Modify multiple components (by % change) and return updated bill.

    Parameters
    ----------
    row     : latest billing row as dict
    changes : {component_key: change_pct, ...}
    kwh     : override kWh (default: from row)
    """
    usage = kwh if kwh is not None else float(row.get("usage_kwh", 750))
    base_components = _extract_components(row)
    base_bill = calculate_total_bill(base_components, usage)

    # Apply all changes
    modified = dict(base_components)
    change_details = []

    for component, change_pct in changes.items():
        if component not in COMPONENT_TYPES:
            continue
        original = modified.get(component, 0.0)
        delta = original * (change_pct / 100.0)
        modified[component] = original + delta

        meta = COMPONENT_TYPES[component]
        cost_col = meta["cost_col"]
        base_cost = base_bill["line_items"].get(cost_col, 0.0)

        change_details.append({
            "component": component,
            "label": meta["label"],
            "type": meta["type"],
            "change_pct": change_pct,
            "original_rate": round(original, 6),
            "new_rate": round(original + delta, 6),
            "base_cost": base_cost,
            "insight": meta["insight"],
        })

    new_bill = calculate_total_bill(modified, usage)

    # Per-component new costs
    for detail in change_details:
        meta = COMPONENT_TYPES[detail["component"]]
        cost_col = meta["cost_col"]
        new_cost = new_bill["line_items"].get(cost_col, 0.0)
        detail["new_cost"] = new_cost
        detail["cost_delta"] = round(new_cost - detail["base_cost"], 2)

    total_impact = round(new_bill["total_bill"] - base_bill["total_bill"], 2)
    pct_impact = round((total_impact / base_bill["total_bill"]) * 100, 4) if base_bill["total_bill"] else 0.0

    return {
        "usage_kwh": usage,
        "base_bill": base_bill["total_bill"],
        "new_bill": new_bill["total_bill"],
        "total_impact": total_impact,
        "total_impact_pct": pct_impact,
        "base_breakdown": base_bill,
        "new_breakdown": new_bill,
        "changes_applied": change_details,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RANK: order components by influence on total bill
# ═══════════════════════════════════════════════════════════════════════════

def rank_components(
    row: dict,
    test_pct: float = 10.0,
    kwh: float | None = None,
) -> dict[str, Any]:
    """
    Rank ALL components by their influence on total bill.
    Tests a uniform +test_pct% change on each component independently.

    Returns ranked list (highest impact first) with elasticities.
    """
    usage = kwh if kwh is not None else float(row.get("usage_kwh", 750))
    base_components = _extract_components(row)
    base_bill = calculate_total_bill(base_components, usage)

    rankings = []
    for component, meta in COMPONENT_TYPES.items():
        if meta["type"] == "tax":
            continue  # tax is derived, not an input

        original = base_components.get(component, 0.0)
        if original == 0.0:
            rankings.append({
                "rank": 0,
                "component": component,
                "label": meta["label"],
                "type": meta["type"],
                "driver": meta["driver"],
                "current_value": 0.0,
                "impact_dollars": 0.0,
                "impact_pct": 0.0,
                "elasticity": 0.0,
                "insight": meta["insight"],
            })
            continue

        # Test +test_pct% change
        modified = dict(base_components)
        modified[component] = original * (1 + test_pct / 100.0)
        new_bill = calculate_total_bill(modified, usage)

        impact = round(new_bill["total_bill"] - base_bill["total_bill"], 2)
        pct_impact = round((impact / base_bill["total_bill"]) * 100, 4) if base_bill["total_bill"] else 0.0
        elasticity = round(pct_impact / test_pct, 4) if test_pct else 0.0

        # Current cost contribution
        cost_col = meta["cost_col"]
        current_cost = base_bill["line_items"].get(cost_col, 0.0)

        rankings.append({
            "rank": 0,  # assigned after sort
            "component": component,
            "label": meta["label"],
            "type": meta["type"],
            "driver": meta["driver"],
            "current_rate": round(original, 6),
            "current_cost": round(current_cost, 2),
            "pct_of_bill": round((current_cost / base_bill["total_bill"]) * 100, 2) if base_bill["total_bill"] else 0.0,
            "impact_dollars": impact,
            "impact_pct": pct_impact,
            "elasticity": elasticity,
            "insight": meta["insight"],
        })

    # Sort by absolute impact (highest first)
    rankings.sort(key=lambda x: abs(x["impact_dollars"]), reverse=True)
    for i, item in enumerate(rankings):
        item["rank"] = i + 1

    return {
        "test_pct": test_pct,
        "usage_kwh": usage,
        "base_bill": base_bill["total_bill"],
        "base_breakdown": base_bill,
        "rankings": rankings,
    }
