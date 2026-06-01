"""
Simulation Service V2 — Vectorized Monte Carlo with Component Interactions.

Replaces the sequential 1000-iteration loop in bill_impact_engine.py with:
1. Multivariate rate sampling (correlated components via covariance matrix)
2. Weather variability (CDD/HDD sampled from monthly distributions)
3. Demand model integration (learned kWh response, not fixed elasticity)
4. Vectorized NumPy operations (target <300ms for 2000 simulations)

Maintains backward compatibility by providing a wrapper that returns the
existing WhatIfResponse shape.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# NJ Sales Tax
NJ_TAX_RATE = 0.06625

# Rate component keys (variable charges)
RATE_KEYS = ["bgs_rate", "distribution_rate", "transmission_rate", "sbc_rate"]

# Scenario presets — modifiers applied to the base simulation
SCENARIO_PRESETS: Dict[str, Dict[str, Any]] = {
    "cold_winter": {
        "description": "Severe winter with 30% higher heating degree days and 15% higher usage",
        "weather_override": {"hdd_multiplier": 1.30, "cdd_multiplier": 0.0},
        "rate_changes": {},
        "usage_multiplier": 1.15,
    },
    "hot_summer": {
        "description": "Extreme summer with 40% higher cooling degree days and 25% higher usage",
        "weather_override": {"hdd_multiplier": 0.0, "cdd_multiplier": 1.40},
        "rate_changes": {},
        "usage_multiplier": 1.25,
    },
    "high_market": {
        "description": "Wholesale market spike: BGS +25%, transmission +15%",
        "weather_override": {},
        "rate_changes": {"bgs_rate": 25, "transmission_rate": 15},
        "usage_multiplier": 1.0,
    },
    "low_usage": {
        "description": "Energy-efficient household using 30% less electricity",
        "weather_override": {},
        "rate_changes": {},
        "usage_multiplier": 0.70,
    },
    "conservation": {
        "description": "Conservation scenario: 15% usage reduction, stable rates",
        "weather_override": {},
        "rate_changes": {},
        "usage_multiplier": 0.85,
    },
}


def get_scenario_presets() -> Dict[str, str]:
    """Return available scenario names and descriptions."""
    return {k: v["description"] for k, v in SCENARIO_PRESETS.items()}


def build_rate_covariance(billing_df: pd.DataFrame, scale: float = 0.01) -> np.ndarray:
    """
    Compute the empirical covariance matrix of rate components from historical data.
    Scaled down for simulation noise (we don't want to resample the full historical
    variance — just capture inter-component correlations).

    Parameters
    ----------
    billing_df : historical billing DataFrame with rate columns
    scale : multiplier to control noise magnitude (default: 1% of empirical cov)

    Returns
    -------
    (n_rates, n_rates) covariance matrix
    """
    available = [k for k in RATE_KEYS if k in billing_df.columns]
    if len(available) < 2:
        return np.eye(len(RATE_KEYS)) * 1e-6

    cov = billing_df[available].cov().values * scale

    # Ensure positive semi-definite (numerical safety)
    eigvals = np.linalg.eigvalsh(cov)
    if np.any(eigvals < 0):
        cov += np.eye(len(available)) * (abs(eigvals.min()) + 1e-10)

    # Pad to full RATE_KEYS size if some columns were missing
    if len(available) < len(RATE_KEYS):
        full_cov = np.eye(len(RATE_KEYS)) * 1e-6
        idx = [RATE_KEYS.index(k) for k in available]
        for i, ri in enumerate(idx):
            for j, rj in enumerate(idx):
                full_cov[ri, rj] = cov[i, j]
        return full_cov

    return cov


def build_weather_stats(feature_df: pd.DataFrame) -> Dict[int, Dict[str, float]]:
    """
    Compute monthly CDD/HDD mean and std from the feature matrix.

    Returns
    -------
    dict mapping month (1-12) to {"cdd_mean", "cdd_std", "hdd_mean", "hdd_std"}
    """
    stats = {}
    if "month" not in feature_df.columns:
        # Fallback: NJ climatology
        for m in range(1, 13):
            stats[m] = {
                "cdd_mean": max(0, 25 * np.sin(2 * np.pi * (m - 4) / 12)),
                "cdd_std": 10,
                "hdd_mean": max(0, 25 * np.sin(2 * np.pi * (m - 10) / 12)),
                "hdd_std": 10,
            }
        return stats

    cdd_col = "monthly_CDD" if "monthly_CDD" in feature_df.columns else "monthly_cdd"
    hdd_col = "monthly_HDD" if "monthly_HDD" in feature_df.columns else "monthly_hdd"

    for m in range(1, 13):
        mask = feature_df["month"] == m
        subset = feature_df[mask]
        if len(subset) < 2:
            stats[m] = {"cdd_mean": 0, "cdd_std": 5, "hdd_mean": 0, "hdd_std": 5}
            continue

        cdd_vals = subset[cdd_col].values if cdd_col in subset.columns else np.zeros(len(subset))
        hdd_vals = subset[hdd_col].values if hdd_col in subset.columns else np.zeros(len(subset))

        stats[m] = {
            "cdd_mean": float(np.mean(cdd_vals)),
            "cdd_std": float(max(np.std(cdd_vals), 1.0)),  # floor at 1 to avoid zero variance
            "hdd_mean": float(np.mean(hdd_vals)),
            "hdd_std": float(max(np.std(hdd_vals), 1.0)),
        }

    return stats


def simulate_v2(
    modifications: Dict[str, float],
    billing_df: pd.DataFrame,
    feature_df: Optional[pd.DataFrame],
    demand_model: Optional[Any] = None,
    rate_cov: Optional[np.ndarray] = None,
    weather_stats: Optional[Dict[int, Dict[str, float]]] = None,
    scenario: Optional[str] = None,
    kwh_override: Optional[float] = None,
    n_sim: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Enhanced What-If Monte Carlo simulation.

    Parameters
    ----------
    modifications : {component: pct_change} e.g., {"bgs_rate": 15}
    billing_df : historical billing DataFrame
    feature_df : feature-engineered DataFrame (for weather/market context)
    demand_model : trained DemandResponseModel (optional — falls back to elasticity)
    rate_cov : (n_rates, n_rates) covariance matrix for correlated sampling
    weather_stats : monthly CDD/HDD distributions
    scenario : named scenario preset (optional, merged with modifications)
    kwh_override : explicit usage override (bypasses demand model)
    n_sim : number of Monte Carlo draws
    seed : random seed

    Returns
    -------
    dict with simulation results including decomposition
    """
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)

    latest = billing_df.iloc[-1].to_dict()
    base_kwh = kwh_override if kwh_override is not None else float(latest.get("usage_kwh", 750))

    # ── Apply scenario preset ────────────────────────────────────────────
    scenario_applied = None
    usage_multiplier = 1.0
    weather_override = {}

    if scenario and scenario in SCENARIO_PRESETS:
        preset = SCENARIO_PRESETS[scenario]
        scenario_applied = scenario
        usage_multiplier = preset.get("usage_multiplier", 1.0)
        weather_override = preset.get("weather_override", {})
        # Merge preset rate changes with user modifications (user takes priority)
        for k, v in preset.get("rate_changes", {}).items():
            if k not in modifications:
                modifications[k] = v

    base_kwh *= usage_multiplier

    # ── Build base and modified rates ────────────────────────────────────
    base_rates = np.array([float(latest.get(k, 0.0)) for k in RATE_KEYS])
    mod_pcts = np.array([modifications.get(k, 0.0) / 100.0 for k in RATE_KEYS])
    mod_rates = base_rates * (1 + mod_pcts)

    # ── Compute base bill ────────────────────────────────────────────────
    fixed_charge = float(latest.get("customer_charge", 8.24))
    base_bill = _compute_bill_scalar(base_rates, base_kwh, fixed_charge)

    # ── Determine month for weather sampling ─────────────────────────────
    try:
        month = pd.to_datetime(latest.get("date")).month
    except Exception:
        month = 6  # default to June

    # ── Sample correlated rate noise ─────────────────────────────────────
    if rate_cov is not None:
        rate_noise = rng.multivariate_normal(np.zeros(len(RATE_KEYS)), rate_cov, n_sim)
    else:
        rate_noise = np.zeros((n_sim, len(RATE_KEYS)))

    sim_rates = mod_rates[np.newaxis, :] + rate_noise  # (n_sim, n_rates)
    sim_rates = np.clip(sim_rates, 0.001, None)  # rates can't be negative

    # ── Sample weather variability ───────────────────────────────────────
    if weather_stats and month in weather_stats:
        ws = weather_stats[month]
        cdd_mean = ws["cdd_mean"] * weather_override.get("cdd_multiplier", 1.0)
        hdd_mean = ws["hdd_mean"] * weather_override.get("hdd_multiplier", 1.0)
        cdd_draws = np.clip(rng.normal(cdd_mean, ws["cdd_std"], n_sim), 0, None)
        hdd_draws = np.clip(rng.normal(hdd_mean, ws["hdd_std"], n_sim), 0, None)
    else:
        cdd_draws = np.zeros(n_sim)
        hdd_draws = np.zeros(n_sim)

    # ── Predict usage for each simulation draw ───────────────────────────
    if demand_model is not None and demand_model.is_trained and kwh_override is None:
        # Use learned demand model
        effective_rates = sim_rates.sum(axis=1)  # composite price per kWh

        # Build base feature values from latest feature row
        base_features = {}
        if feature_df is not None and len(feature_df) > 0:
            last_feat_row = feature_df.iloc[-1].to_dict()
            base_features = demand_model.build_features_from_row(last_feat_row)

        # Build batch features
        X_sim = demand_model.build_features_batch(
            base_features, effective_rates, cdd_draws, hdd_draws, month
        )
        sim_kwh = demand_model.predict_batch(X_sim)  # (n_sim,)
        sim_kwh *= usage_multiplier

        learned_elasticity = demand_model.get_learned_elasticity()
    else:
        # Fallback: fixed elasticity with weather adjustment
        learned_elasticity = -0.20
        effective_rate_base = base_rates.sum()
        effective_rate_mod = sim_rates.sum(axis=1)
        price_change_pct = (effective_rate_mod - effective_rate_base) / effective_rate_base

        # Simple demand response
        kwh_response = base_kwh * price_change_pct * learned_elasticity
        sim_kwh = np.clip(base_kwh + kwh_response, 100, 5000)

    # ── Compute simulated bills (vectorized) ─────────────────────────────
    sim_bills = _compute_bills_vectorized(sim_rates, sim_kwh, fixed_charge)

    # ── Compute decomposition ────────────────────────────────────────────
    median_bill = float(np.median(sim_bills))
    mean_kwh = float(np.mean(sim_kwh))
    kwh_change = mean_kwh - base_kwh

    # Decomposition: separate direct price effect from indirect behavioral effect
    # Direct price effect: ΔRate × base_usage
    direct_price = float(np.sum((mod_rates - base_rates) * base_kwh) * (1 + NJ_TAX_RATE))
    # Indirect behavioral: ΔUsage × modified_rates
    indirect_behavioral = float(kwh_change * mod_rates.sum() * (1 + NJ_TAX_RATE))
    # Weather effect: difference from weather-induced usage shifts
    weather_effect = 0.0
    if weather_stats and month in weather_stats:
        ws = weather_stats[month]
        base_cdd = ws["cdd_mean"] * weather_override.get("cdd_multiplier", 1.0)
        base_hdd = ws["hdd_mean"] * weather_override.get("hdd_multiplier", 1.0)
        normal_cdd = ws["cdd_mean"]
        normal_hdd = ws["hdd_mean"]
        # Rough weather attribution using demand model coefficients or defaults
        if demand_model and demand_model.is_trained:
            coefs = demand_model.get_coefficients()
            cdd_coef = coefs.get("monthly_CDD", 0.85)
            hdd_coef = coefs.get("monthly_HDD", 0.45)
        else:
            cdd_coef, hdd_coef = 0.85, 0.45
        weather_kwh_shift = cdd_coef * (base_cdd - normal_cdd) + hdd_coef * (base_hdd - normal_hdd)
        weather_effect = float(weather_kwh_shift * mod_rates.sum() * (1 + NJ_TAX_RATE))

    # Interaction effect: residual = total - (direct + indirect + weather)
    total_impact = median_bill - base_bill
    interaction_effect = total_impact - direct_price - indirect_behavioral - weather_effect

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # ── Build per-component contribution breakdown ───────────────────────
    contributions = {}
    from api.services.bill_impact_engine import COMPONENT_TYPES
    for key, meta in COMPONENT_TYPES.items():
        if meta["type"] == "variable" and key in RATE_KEYS:
            mod_rate = float(mod_rates[RATE_KEYS.index(key)])
            base_rate = float(base_rates[RATE_KEYS.index(key)])
            contributions[meta["label"]] = round(
                float(mod_rate * mean_kwh * (1 + NJ_TAX_RATE)), 2
            )
        elif meta["type"] == "fixed":
            contributions[meta["label"]] = round(
                float(latest.get(key, 0)) * (1 + NJ_TAX_RATE), 2
            )

    return {
        # V1 backward-compatible fields
        "base_bill": round(base_bill, 2),
        "new_bill": round(median_bill, 2),
        "total_impact": round(total_impact, 2),
        "confidence_interval": [
            round(float(np.percentile(sim_bills, 2.5)), 2),
            round(float(np.percentile(sim_bills, 97.5)), 2),
        ],
        "usage_response": round(kwh_change, 2),
        "contributions": contributions,
        # V2 enhanced fields
        "simulated_bill": round(median_bill, 2),
        "usage_change_kwh": round(kwh_change, 2),
        "learned_elasticity": round(learned_elasticity, 4),
        "decomposition": {
            "direct_price_effect": round(direct_price, 2),
            "indirect_behavioral_effect": round(indirect_behavioral, 2),
            "weather_effect": round(weather_effect, 2),
            "interaction_effect": round(interaction_effect, 2),
        },
        "scenario_applied": scenario_applied,
        "model_info": {
            "method": "Vectorized Monte Carlo V2",
            "n_simulations": n_sim,
            "runtime_ms": round(elapsed_ms, 1),
            "demand_model": "learned" if (demand_model and demand_model.is_trained) else "fallback",
            "rate_correlation": rate_cov is not None,
            "weather_sampling": weather_stats is not None,
        },
        # Distribution statistics
        "distribution": {
            "mean": round(float(np.mean(sim_bills)), 2),
            "std": round(float(np.std(sim_bills)), 2),
            "p5": round(float(np.percentile(sim_bills, 5)), 2),
            "p25": round(float(np.percentile(sim_bills, 25)), 2),
            "p50": round(float(np.percentile(sim_bills, 50)), 2),
            "p75": round(float(np.percentile(sim_bills, 75)), 2),
            "p95": round(float(np.percentile(sim_bills, 95)), 2),
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  VECTORIZED BILL COMPUTATION
# ─────────────────────────────────────────────────────────────────────────

def _compute_bill_scalar(rates: np.ndarray, kwh: float, fixed_charge: float) -> float:
    """Compute a single bill from rates, usage, and fixed charge."""
    variable_cost = float(np.sum(rates * kwh))
    subtotal = fixed_charge + variable_cost
    tax = subtotal * NJ_TAX_RATE
    return round(subtotal + tax, 2)


def _compute_bills_vectorized(
    rates: np.ndarray, kwh: np.ndarray, fixed_charge: float
) -> np.ndarray:
    """
    Vectorized bill computation for Monte Carlo.

    Parameters
    ----------
    rates : (n_sim, n_rates) array of rate values
    kwh : (n_sim,) array of usage values
    fixed_charge : scalar fixed charge

    Returns
    -------
    (n_sim,) array of total bill values
    """
    # variable_costs: (n_sim,) = sum across rates of (rate_i * kwh)
    variable_costs = np.sum(rates * kwh[:, np.newaxis], axis=1)
    subtotals = fixed_charge + variable_costs
    taxes = subtotals * NJ_TAX_RATE
    return subtotals + taxes
