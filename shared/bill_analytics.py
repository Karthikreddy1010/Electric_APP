"""
Shared Bill Analytics Engine
=============================
Core analytical logic for electricity bill component analysis.
This module is the SINGLE SOURCE OF TRUTH — imported by both:
  - FastAPI backend (api/main.py)
  - Streamlit app (streamlit_app/app.py)

Features:
  1. Component contribution analysis (% and absolute)
  2. Sensitivity simulation (+/-% per component)
  3. Component classification (fixed / usage-based / external)
  4. Auto-generated natural-language insights

⚠️  Components are correlated — this module does NOT claim causal inference.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────
# COMPONENT REGISTRY — PSE&G NJ Bill Structure
# ─────────────────────────────────────────────────────

@dataclass
class ComponentMeta:
    """Metadata for a single bill component."""
    key: str                 # column name in data
    label: str               # human-readable label
    category: str            # "fixed" | "usage_based" | "external"
    driver: str              # "policy" | "market" | "weather" | "regulatory" | "infrastructure"
    description: str = ""
    rate_key: str | None = None   # optional: column for the per-kWh rate


# Canonical registry — every component the system knows about
COMPONENT_REGISTRY: list[ComponentMeta] = [
    ComponentMeta("customer_charge",          "Customer Charge",            "fixed",       "regulatory",
                  "Fixed monthly service fee independent of usage"),
    ComponentMeta("bgs_cost",                 "BGS Supply",                 "usage_based", "market",
                  "Basic Generation Service — wholesale energy cost passed to ratepayer",
                  rate_key="bgs_rate"),
    ComponentMeta("distribution_cost",        "Distribution Charge",        "usage_based", "infrastructure",
                  "Cost of delivering electricity through local distribution network",
                  rate_key="distribution_rate"),
    ComponentMeta("transmission_cost",        "Transmission Charge",        "usage_based", "market",
                  "High-voltage transmission grid usage charge",
                  rate_key="transmission_rate"),
    ComponentMeta("sbc_cost",                 "Societal Benefits Charge",   "usage_based", "policy",
                  "Funds for energy efficiency, renewables, and low-income assistance",
                  rate_key="sbc_rate"),
    ComponentMeta("nug_cost",                 "Non-Utility Generation",     "usage_based", "regulatory",
                  "Charges related to legacy non-utility generation contracts",
                  rate_key="nug_rate"),
    ComponentMeta("rider_cost",               "Rider Charges",              "usage_based", "regulatory",
                  "Supplemental charges for infrastructure recovery and programs",
                  rate_key="rider_rate"),
    ComponentMeta("market_transition_cost",   "Market Transition Charge",   "usage_based", "policy",
                  "Transition charge from deregulation of electricity markets",
                  rate_key="market_transition_rate"),
    ComponentMeta("weather_adjustment",       "Weather Normalization",      "external",    "weather",
                  "Seasonal billing adjustment for abnormal weather conditions"),
    ComponentMeta("dr_credit",                "Demand Response Credit",     "external",    "policy",
                  "Credit for participating in demand response programs"),
    ComponentMeta("sales_tax",                "Sales Tax (NJ 6.625%)",      "external",    "policy",
                  "New Jersey state sales tax applied to subtotal"),
]

# Lookup helpers
_REGISTRY_MAP: dict[str, ComponentMeta] = {c.key: c for c in COMPONENT_REGISTRY}


def get_component_meta(key: str) -> ComponentMeta | None:
    return _REGISTRY_MAP.get(key)


def get_known_component_keys() -> list[str]:
    return [c.key for c in COMPONENT_REGISTRY]


def classify_components() -> dict[str, list[dict]]:
    """Return components grouped by category."""
    groups: dict[str, list[dict]] = {"fixed": [], "usage_based": [], "external": []}
    for c in COMPONENT_REGISTRY:
        groups[c.category].append({
            "key": c.key, "label": c.label, "driver": c.driver,
            "description": c.description,
        })
    return groups


# ─────────────────────────────────────────────────────
# 1. CONTRIBUTION ANALYSIS
# ─────────────────────────────────────────────────────

@dataclass
class ContributionResult:
    component: str
    label: str
    category: str
    driver: str
    value: float
    pct_of_total: float
    pct_of_subtotal: float  # excluding tax


def compute_contributions(bill_row: dict | pd.Series) -> list[ContributionResult]:
    """
    Compute each component's absolute value and percentage contribution.

    Parameters
    ----------
    bill_row : single bill record (dict or Series) with component columns

    Returns
    -------
    list of ContributionResult sorted by absolute value descending
    """
    total = float(bill_row.get("total_bill", 0)) or 1.0
    tax = float(bill_row.get("sales_tax", 0))
    subtotal = total - tax or 1.0

    results = []
    for meta in COMPONENT_REGISTRY:
        val = float(bill_row.get(meta.key, 0))
        results.append(ContributionResult(
            component=meta.key,
            label=meta.label,
            category=meta.category,
            driver=meta.driver,
            value=round(val, 2),
            pct_of_total=round(val / total * 100, 2) if total else 0,
            pct_of_subtotal=round(val / subtotal * 100, 2) if subtotal else 0,
        ))

    results.sort(key=lambda r: abs(r.value), reverse=True)
    return results


def contributions_to_df(results: list[ContributionResult]) -> pd.DataFrame:
    """Convert contribution results to a DataFrame for display."""
    return pd.DataFrame([
        {"Component": r.label, "Amount ($)": r.value,
         "% of Total": r.pct_of_total, "% of Subtotal": r.pct_of_subtotal,
         "Category": r.category.replace("_", " ").title(),
         "Driver": r.driver.title()}
        for r in results if r.value != 0
    ])


# ─────────────────────────────────────────────────────
# 2. SENSITIVITY ANALYSIS
# ─────────────────────────────────────────────────────

@dataclass
class SensitivityResult:
    component: str
    label: str
    category: str
    base_value: float
    pct_change: float
    delta: float            # change in component value
    new_component_value: float
    new_total: float
    base_total: float
    total_delta: float      # change in total bill
    total_pct_change: float # % change in total bill
    elasticity: float       # % change in total / % change in component


def run_sensitivity(
    bill_row: dict | pd.Series,
    pct_changes: list[float] | None = None,
    components: list[str] | None = None,
    usage_kwh: float | None = None,
) -> list[SensitivityResult]:
    """
    Simulate the effect of changing each component by given percentages.

    Parameters
    ----------
    bill_row    : a single bill record
    pct_changes : list of % changes to simulate (default: [-10, -5, +5, +10])
    components  : which components to test (default: all known)
    usage_kwh   : if provided, used for rate-based recalculation

    Returns
    -------
    list of SensitivityResult
    """
    if pct_changes is None:
        pct_changes = [-10.0, -5.0, 5.0, 10.0]
    if components is None:
        components = get_known_component_keys()

    base_total = float(bill_row.get("total_bill", 0))
    tax_rate = 0.06625  # NJ sales tax

    results = []
    for comp_key in components:
        meta = get_component_meta(comp_key)
        if meta is None:
            continue
        base_val = float(bill_row.get(comp_key, 0))
        if base_val == 0:
            continue

        for pct in pct_changes:
            delta = base_val * (pct / 100.0)
            new_val = base_val + delta

            # Recompute total: the tax applies to the subtotal
            # so a component change also changes tax proportionally
            if meta.key == "sales_tax":
                # changing tax itself: just shift
                new_total = base_total + delta
            else:
                # component change + proportional tax change
                tax_delta = delta * tax_rate
                new_total = base_total + delta + tax_delta

            total_delta = new_total - base_total
            total_pct = (total_delta / base_total * 100) if base_total else 0
            elasticity = (total_pct / pct) if pct != 0 else 0

            results.append(SensitivityResult(
                component=comp_key,
                label=meta.label,
                category=meta.category,
                base_value=round(base_val, 2),
                pct_change=pct,
                delta=round(delta, 2),
                new_component_value=round(new_val, 2),
                new_total=round(new_total, 2),
                base_total=round(base_total, 2),
                total_delta=round(total_delta, 2),
                total_pct_change=round(total_pct, 2),
                elasticity=round(elasticity, 4),
            ))

    return results


def sensitivity_to_df(results: list[SensitivityResult]) -> pd.DataFrame:
    return pd.DataFrame([
        {"Component": r.label, "Change (%)": f"{r.pct_change:+.0f}%",
         "Base ($)": r.base_value, "Δ Component ($)": r.delta,
         "New Total ($)": r.new_total, "Δ Total ($)": r.total_delta,
         "Δ Total (%)": f"{r.total_pct_change:+.2f}%",
         "Elasticity": r.elasticity, "Category": r.category.replace("_", " ").title()}
        for r in results
    ])


def sensitivity_summary(results: list[SensitivityResult], pct: float = 10.0) -> pd.DataFrame:
    """One-row-per-component summary at a given % change."""
    filtered = [r for r in results if r.pct_change == pct]
    return pd.DataFrame([
        {"Component": r.label, "Category": r.category.replace("_", " ").title(),
         f"+{pct:.0f}% Impact ($)": r.total_delta,
         f"+{pct:.0f}% Impact (%)": r.total_pct_change,
         "Elasticity": r.elasticity}
        for r in filtered
    ]).sort_values(f"+{pct:.0f}% Impact ($)", ascending=False, key=abs)


# ─────────────────────────────────────────────────────
# 3. INTERACTIVE BILL SIMULATOR
# ─────────────────────────────────────────────────────

def simulate_bill(
    base_row: dict | pd.Series,
    overrides: dict[str, float] | None = None,
    usage_kwh: float | None = None,
) -> dict:
    """
    Recompute the total bill with user-supplied component overrides.

    Parameters
    ----------
    base_row   : original bill record
    overrides  : {component_key: new_value} for components user adjusted
    usage_kwh  : optional override for kWh (recomputes usage-based components)

    Returns
    -------
    dict with "components", "subtotal", "tax", "total", "delta_vs_base"
    """
    if overrides is None:
        overrides = {}

    tax_rate = 0.06625
    row = dict(base_row) if not isinstance(base_row, dict) else dict(base_row)
    base_total = float(row.get("total_bill", 0))

    # Apply overrides
    for key, val in overrides.items():
        row[key] = val

    # If usage changed, recompute usage-based components via rates
    if usage_kwh is not None:
        for meta in COMPONENT_REGISTRY:
            if meta.category == "usage_based" and meta.rate_key and meta.rate_key in row:
                row[meta.key] = float(row[meta.rate_key]) * usage_kwh
        row["usage_kwh"] = usage_kwh

    # Recompute subtotal and tax
    subtotal = 0.0
    components = {}
    for meta in COMPONENT_REGISTRY:
        if meta.key == "sales_tax":
            continue
        val = float(row.get(meta.key, 0))
        components[meta.label] = round(val, 2)
        subtotal += val

    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    return {
        "components": components,
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total,
        "base_total": round(base_total, 2),
        "delta": round(total - base_total, 2),
        "delta_pct": round((total - base_total) / base_total * 100, 2) if base_total else 0,
        "usage_kwh": float(row.get("usage_kwh", 0)),
    }


# ─────────────────────────────────────────────────────
# 4. INSIGHT GENERATION
# ─────────────────────────────────────────────────────

def generate_insights(
    contributions: list[ContributionResult],
    sensitivity_results: list[SensitivityResult] | None = None,
    bill_row: dict | pd.Series | None = None,
) -> list[str]:
    """
    Generate human-readable insights from analysis results.
    Returns a list of insight strings.
    """
    insights: list[str] = []

    # --- Contribution insights ---
    positive = [c for c in contributions if c.value > 0]
    if positive:
        top = positive[0]
        insights.append(
            f"💡 **{top.label}** is the largest cost driver at **${top.value:.2f}** "
            f"({top.pct_of_total:.1f}% of your total bill). "
            f"This is a {top.category.replace('_', '-')} charge driven by {top.driver} factors."
        )

    # Fixed vs usage-based split
    fixed_total = sum(c.value for c in contributions if c.category == "fixed" and c.value > 0)
    usage_total = sum(c.value for c in contributions if c.category == "usage_based" and c.value > 0)
    external_total = sum(c.value for c in contributions if c.category == "external")
    grand = fixed_total + usage_total + abs(external_total) or 1

    insights.append(
        f"📊 Your bill is **{usage_total / grand * 100:.0f}% usage-based**, "
        f"**{fixed_total / grand * 100:.0f}% fixed**, and "
        f"**{abs(external_total) / grand * 100:.0f}% external/tax**. "
        f"Reducing consumption directly lowers the usage-based portion "
        f"(${usage_total:.2f})."
    )

    # --- Sensitivity insights ---
    if sensitivity_results:
        up10 = [r for r in sensitivity_results if r.pct_change == 10.0]
        if up10:
            up10.sort(key=lambda r: abs(r.total_delta), reverse=True)
            most = up10[0]
            least_nonzero = [r for r in up10 if r.total_delta != 0]
            least = least_nonzero[-1] if least_nonzero else None
            insights.append(
                f"📈 A **+10% increase** in {most.label} has the **largest impact**: "
                f"total bill changes by **${most.total_delta:+.2f}** "
                f"({most.total_pct_change:+.2f}%)."
            )
            if least and least.component != most.component:
                insights.append(
                    f"📉 In contrast, a +10% change in {least.label} only shifts the "
                    f"total by **${least.total_delta:+.2f}** — minimal impact."
                )

    # --- Component-specific insights ---
    for c in contributions:
        if c.driver == "weather" and c.value != 0:
            insights.append(
                f"🌡️ **{c.label}** (${c.value:+.2f}) reflects seasonal weather "
                f"conditions. This component shows high variability across months."
            )
        if c.category == "fixed" and c.value > 0:
            insights.append(
                f"🔒 **{c.label}** (${c.value:.2f}) is a fixed charge — it does NOT "
                f"scale with your kWh usage. Even at zero consumption you pay this."
            )
            break  # only first fixed

    # Usage insight
    if bill_row is not None:
        usage = float(bill_row.get("usage_kwh", 0))
        if usage > 1000:
            insights.append(
                f"⚡ Your usage of **{usage:.0f} kWh** is above the NJ residential "
                f"average (~700 kWh). All usage-based charges are amplified."
            )
        elif usage < 500:
            insights.append(
                f"⚡ Your usage of **{usage:.0f} kWh** is below average. "
                f"Fixed charges represent a larger share of your bill."
            )

    return insights


# ─────────────────────────────────────────────────────
# 5. HISTORICAL ANALYSIS HELPERS
# ─────────────────────────────────────────────────────

def compute_historical_contributions(billing_df: pd.DataFrame) -> pd.DataFrame:
    """Compute component contributions for every row in a billing DataFrame."""
    records = []
    for _, row in billing_df.iterrows():
        total = float(row.get("total_bill", 0)) or 1
        entry = {"date": row["date"]}
        for meta in COMPONENT_REGISTRY:
            val = float(row.get(meta.key, 0))
            entry[meta.label] = round(val, 2)
            entry[f"{meta.label} (%)"] = round(val / total * 100, 2)
        records.append(entry)
    return pd.DataFrame(records)


def compute_component_trends(billing_df: pd.DataFrame) -> pd.DataFrame:
    """Rolling averages and YoY changes per component."""
    df = billing_df.copy()
    for meta in COMPONENT_REGISTRY:
        if meta.key in df.columns:
            df[f"{meta.key}_roll6"] = df[meta.key].rolling(6, min_periods=1).mean()
            df[f"{meta.key}_yoy"] = df[meta.key].pct_change(12) * 100
    return df
