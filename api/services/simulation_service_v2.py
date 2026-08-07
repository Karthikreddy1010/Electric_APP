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
RATE_KEYS = ["bgs_rate", "distribution_rate", "transmission_rate", "sbc_rate", "transition_rate", "nug_rate", "rider_rate"]

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
    # ── Deterministic Weather Scenarios (NREL-backed) ────────────────
    "temp_plus_5c": {
        "description": "Temperature +5°C above normal — increased cooling demand",
        "weather_override": {"cdd_multiplier": 1.50, "hdd_multiplier": 0.70},
        "rate_changes": {},
        "usage_multiplier": 1.18,
        "weather_scenario": True,
    },
    "temp_minus_5c": {
        "description": "Temperature -5°C below normal — increased heating demand",
        "weather_override": {"hdd_multiplier": 1.50, "cdd_multiplier": 0.50},
        "rate_changes": {},
        "usage_multiplier": 1.12,
        "weather_scenario": True,
    },
    "heavy_rainfall": {
        "description": "Heavy rainfall week — reduced solar generation, stable demand",
        "weather_override": {"cdd_multiplier": 0.90},
        "rate_changes": {},
        "usage_multiplier": 1.03,
        "weather_scenario": True,
        "solar_impact_pct": -25.0,
    },
    "cloudy_week": {
        "description": "Overcast cloudy week — solar irradiance reduced by 50%",
        "weather_override": {},
        "rate_changes": {},
        "usage_multiplier": 1.05,
        "weather_scenario": True,
        "solar_impact_pct": -50.0,
    },
    "sunny_week": {
        "description": "Clear sunny week — solar irradiance increased by 30%",
        "weather_override": {"cdd_multiplier": 1.15},
        "rate_changes": {},
        "usage_multiplier": 0.97,
        "weather_scenario": True,
        "solar_impact_pct": 30.0,
    },
    "high_wind": {
        "description": "High wind week — wind chill reduces apparent temperature",
        "weather_override": {"hdd_multiplier": 1.20},
        "rate_changes": {},
        "usage_multiplier": 1.06,
        "weather_scenario": True,
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
    base_rates_override: Optional[Dict[str, float]] = None,
    base_costs_override: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Enhanced What-If Monte Carlo simulation.
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
    if base_rates_override:
        fixed_charge = float(base_rates_override.get("customer_charge", latest.get("customer_charge", 8.24)))
        # Map cost keys to rate keys if passed as cost keys
        def get_rate(k):
            # map keys like bgs_cost to bgs_rate
            cost_key = k.replace("_rate", "_cost")
            if k in base_rates_override:
                return float(base_rates_override[k])
            elif cost_key in base_rates_override and base_kwh > 0:
                return float(base_rates_override[cost_key]) / base_kwh
            return float(latest.get(k, 0.0))
        base_rates = np.array([get_rate(k) for k in RATE_KEYS])
    else:
        fixed_charge = float(latest.get("customer_charge", 8.24))
        base_rates = np.array([float(latest.get(k, 0.0)) for k in RATE_KEYS])

    # Check if modifications are for fixed charge or other items
    # customer_charge change_pct:
    fixed_charge_change = modifications.get("customer_charge", 0.0)
    sim_fixed_charge = fixed_charge * (1 + fixed_charge_change / 100.0)

    mod_pcts = np.array([modifications.get(k, 0.0) / 100.0 for k in RATE_KEYS])
    mod_rates = base_rates * (1 + mod_pcts)

    # ── Compute base bill ────────────────────────────────────────────────
    base_bill = _compute_bill_scalar(base_rates, base_kwh, fixed_charge)

    # ── Determine month for weather sampling ─────────────────────────────
    try:
        month = pd.to_datetime(latest.get("date")).month
    except Exception:
        month = 6  # default to June

    # ── Sample correlated rate noise ─────────────────────────────────────
    if rate_cov is not None:
        # Pad rate_cov if dimensions mismatch
        if rate_cov.shape[0] != len(RATE_KEYS):
            rate_cov_padded = np.eye(len(RATE_KEYS)) * 1e-6
            min_dim = min(rate_cov.shape[0], len(RATE_KEYS))
            rate_cov_padded[:min_dim, :min_dim] = rate_cov[:min_dim, :min_dim]
            rate_noise = rng.multivariate_normal(np.zeros(len(RATE_KEYS)), rate_cov_padded, n_sim)
        else:
            rate_noise = rng.multivariate_normal(np.zeros(len(RATE_KEYS)), rate_cov, n_sim)
    else:
        rate_noise = np.zeros((n_sim, len(RATE_KEYS)))

    sim_rates = mod_rates[np.newaxis, :] + rate_noise  # (n_sim, n_rates)
    sim_rates = np.clip(sim_rates, 0.0001, None)  # rates can't be negative

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
        effective_rates = sim_rates.sum(axis=1)  # composite price per kWh
        base_features = {}
        if feature_df is not None and len(feature_df) > 0:
            last_feat_row = feature_df.iloc[-1].to_dict()
            base_features = demand_model.build_features_from_row(last_feat_row)

        X_sim = demand_model.build_features_batch(
            base_features, effective_rates, cdd_draws, hdd_draws, month
        )
        sim_kwh = demand_model.predict_batch(X_sim)  # (n_sim,)
        sim_kwh *= usage_multiplier
        learned_elasticity = demand_model.get_learned_elasticity()
    else:
        learned_elasticity = -0.20
        effective_rate_base = base_rates.sum()
        effective_rate_mod = sim_rates.sum(axis=1)
        price_change_pct = np.zeros(n_sim)
        if effective_rate_base > 0:
            price_change_pct = (effective_rate_mod - effective_rate_base) / effective_rate_base

        kwh_response = base_kwh * price_change_pct * learned_elasticity
        sim_kwh = np.clip(base_kwh + kwh_response, 100, 5000)

    # ── Compute simulated bills (vectorized) ─────────────────────────────
    sim_bills = _compute_bills_vectorized(sim_rates, sim_kwh, sim_fixed_charge)

    # ── PJM Market Physics Stochastic Simulation ─────────────────────────
    from models.pjm_market_physics import (
        DEFAULT_PJM,
        sample_market_parameters,
        compute_bills_pjm_vectorized,
    )
    from api.state import app_state

    pjm_defaults = app_state.get("pjm_defaults") or DEFAULT_PJM
    market_params = sample_market_parameters(n_sim=n_sim, defaults=pjm_defaults, seed=seed)

    # Apply bgs_rate modifier to LMP
    bgs_mod_pct = modifications.get("bgs_rate", 0.0)
    lmp_mwh = market_params["lmp"] * (1.0 + bgs_mod_pct / 100.0)

    # Loss-adjusted usage
    effective_kwh = sim_kwh * (1.0 + market_params["loss_factor"])

    # Extract component rates
    dist_rate = sim_rates[:, RATE_KEYS.index("distribution_rate")]
    trans_rate = sim_rates[:, RATE_KEYS.index("transmission_rate")]
    cong_per_kwh = market_params["congestion_price"] / 1000.0
    pol_rate = sim_rates[:, RATE_KEYS.index("sbc_rate")]

    sim_bills_pjm = compute_bills_pjm_vectorized(
        lmp_mwh=lmp_mwh,
        effective_kwh=effective_kwh,
        distribution_rate=dist_rate,
        base_transmission_rate=trans_rate,
        congestion_per_kwh=cong_per_kwh,
        policy_rate=pol_rate,
        customer_charge=sim_fixed_charge,
        usage_kwh=sim_kwh,
        tax_rate=NJ_TAX_RATE,
    )

    da_fraction = pjm_defaults.da_settlement_fraction
    da_charge = (lmp_mwh / 1000.0) * effective_kwh * da_fraction
    rt_charge = (lmp_mwh / 1000.0) * effective_kwh * (1.0 - da_fraction)

    pjm_physics_data = {
        "marginal_cost": round(float(np.mean(market_params["marginal_cost"])), 2),
        "lmp": round(float(np.mean(market_params["lmp"])), 2),
        "effective_kwh": round(float(np.mean(effective_kwh)), 2),
        "da_charge": round(float(np.mean(da_charge)), 2),
        "rt_charge": round(float(np.mean(rt_charge)), 2),
        "loss_factor": round(float(np.mean(market_params["loss_factor"])), 4),
        "simulated_bill_pjm": round(float(np.median(sim_bills_pjm)), 2),
        "distribution_pjm": {
            "mean": round(float(np.mean(sim_bills_pjm)), 2),
            "std": round(float(np.std(sim_bills_pjm)), 2),
            "p5": round(float(np.percentile(sim_bills_pjm, 5)), 2),
            "p25": round(float(np.percentile(sim_bills_pjm, 25)), 2),
            "p50": round(float(np.percentile(sim_bills_pjm, 50)), 2),
            "p75": round(float(np.percentile(sim_bills_pjm, 75)), 2),
            "p95": round(float(np.percentile(sim_bills_pjm, 95)), 2),
        }
    }

    # ── Compute decomposition ────────────────────────────────────────────
    median_bill = float(np.median(sim_bills))
    mean_kwh = float(np.mean(sim_kwh))
    kwh_change = mean_kwh - base_kwh

    # Direct price effect: Sum of component rate modifications on base usage
    direct_price = float(np.sum((mod_rates - base_rates) * base_kwh) + (sim_fixed_charge - fixed_charge)) * (1 + NJ_TAX_RATE)
    # Indirect behavioral: usage response * mod_rates
    indirect_behavioral = float(kwh_change * mod_rates.sum()) * (1 + NJ_TAX_RATE)

    # Weather effect: difference from weather-induced usage shifts
    weather_effect = 0.0
    if weather_stats and month in weather_stats:
        ws = weather_stats[month]
        base_cdd = ws["cdd_mean"] * weather_override.get("cdd_multiplier", 1.0)
        base_hdd = ws["hdd_mean"] * weather_override.get("hdd_multiplier", 1.0)
        normal_cdd = ws["cdd_mean"]
        normal_hdd = ws["hdd_mean"]
        if demand_model and demand_model.is_trained:
            coefs = demand_model.get_coefficients()
            cdd_coef = coefs.get("monthly_CDD", 0.85)
            hdd_coef = coefs.get("monthly_HDD", 0.45)
        else:
            cdd_coef, hdd_coef = 0.85, 0.45
        weather_kwh_shift = cdd_coef * (base_cdd - normal_cdd) + hdd_coef * (base_hdd - normal_hdd)
        weather_effect = float(weather_kwh_shift * mod_rates.sum()) * (1 + NJ_TAX_RATE)

    total_impact = median_bill - base_bill
    interaction_effect = total_impact - direct_price - indirect_behavioral - weather_effect

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # ── Build per-component contribution breakdown (accounting identity) ─
    contributions = {}
    from api.services.bill_impact_engine import COMPONENT_TYPES
    
    # We will build subtotal costs excluding tax
    subtotal_sim = sim_fixed_charge
    subtotal_base = fixed_charge
    
    # customer charge
    contributions["customer_charge"] = {
        "name": "Customer Charge",
        "key": "customer_charge",
        "category": "Fixed Charge",
        "type": "fixed",
        "controllable": "No",
        "base_rate": fixed_charge,
        "base_cost": fixed_charge,
        "simulated_rate": sim_fixed_charge,
        "simulated_cost": sim_fixed_charge,
        "difference": round(sim_fixed_charge - fixed_charge, 2),
        "percent_difference": round(fixed_charge_change, 2)
    }
    
    for idx, key in enumerate(RATE_KEYS):
        mod_rate = float(mod_rates[idx])
        base_rate = float(base_rates[idx])
        
        sim_cost = round(mod_rate * mean_kwh, 2)
        base_cost = round(base_rate * base_kwh, 2)
        
        subtotal_sim += sim_cost
        subtotal_base += base_cost
        
        meta = COMPONENT_TYPES.get(key, {"label": key.replace("_", " ").title(), "type": "variable", "driver": "regulatory", "controllable": "No"})
        
        contributions[key] = {
            "name": meta["label"],
            "key": key,
            "category": "Supply Charge" if key == "bgs_rate" else "Delivery Charge",
            "type": "variable",
            "controllable": meta["controllable"],
            "base_rate": round(base_rate, 5),
            "base_cost": round(base_cost, 2),
            "simulated_rate": round(mod_rate, 5),
            "simulated_cost": round(sim_cost, 2),
            "difference": round(sim_cost - base_cost, 2),
            "percent_difference": round(((mod_rate - base_rate)/base_rate*100) if base_rate > 0 else 0.0, 2)
        }
        
    # Sales Tax
    sim_tax = round(subtotal_sim * NJ_TAX_RATE, 2)
    base_tax = round(subtotal_base * NJ_TAX_RATE, 2)
    
    contributions["sales_tax"] = {
        "name": "Sales Tax (6.625%)",
        "key": "sales_tax",
        "category": "Tax",
        "type": "tax",
        "controllable": "No",
        "base_rate": NJ_TAX_RATE,
        "base_cost": base_tax,
        "simulated_rate": NJ_TAX_RATE,
        "simulated_cost": sim_tax,
        "difference": round(sim_tax - base_tax, 2),
        "percent_difference": round(((sim_tax - base_tax)/base_tax*100) if base_tax > 0 else 0.0, 2)
    }

    # Sum of simulated costs + tax = total bill
    simulated_bill_sum = round(subtotal_sim + sim_tax, 2)
    base_bill_sum = round(subtotal_base + base_tax, 2)

    # Overwrite simulated_bill & base_bill with exact sums to preserve perfect accounting identity
    median_bill = simulated_bill_sum
    base_bill = base_bill_sum
    total_impact = round(median_bill - base_bill, 2)

    # Attach contribution_pct to each component
    for key, c in list(contributions.items()):
        c["contribution_pct"] = round((c["simulated_cost"] / simulated_bill_sum * 100), 2) if simulated_bill_sum > 0 else 0.0
        c["contribution_to_change"] = c["difference"]

    return {
        "base_bill": round(base_bill, 2),
        "new_bill": round(median_bill, 2),
        "total_impact": round(total_impact, 2),
        "confidence_interval": [
            round(float(np.percentile(sim_bills, 2.5)), 2),
            round(float(np.percentile(sim_bills, 97.5)), 2),
        ],
        "usage_response": round(kwh_change, 2),
        "contributions": contributions,
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
        "distribution": {
            "mean": round(float(np.mean(sim_bills)), 2),
            "std": round(float(np.std(sim_bills)), 2),
            "p5": round(float(np.percentile(sim_bills, 5)), 2),
            "p25": round(float(np.percentile(sim_bills, 25)), 2),
            "p50": round(float(np.percentile(sim_bills, 50)), 2),
            "p75": round(float(np.percentile(sim_bills, 75)), 2),
            "p95": round(float(np.percentile(sim_bills, 95)), 2),
        },
        "pjm_physics": pjm_physics_data,
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
