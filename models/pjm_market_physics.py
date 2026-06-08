"""
PJM Market Physics Engine — M15 (Cost Development) & M28 (Settlement Accounting).

Implements the physical pricing chain:
    fuel → generator cost → LMP → settlement → bill

All functions are pure (no side effects) and NumPy-vectorized for Monte Carlo use.

References:
    - PJM Manual 15: Cost Development Guidelines
    - PJM Manual 28: Operating Agreement Accounting (Settlement)
    - PJM Manual 11: Energy & Ancillary Services Market Operations
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULTS — PSEG Zone, NJ Residential
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PJMMarketDefaults:
    """
    Default parameters for the PSEG zone (NJ residential).

    These are physically calibrated to PJM-East market conditions.
    All can be overridden at runtime for scenario analysis.
    """
    # M15: Generator cost stack (typical PJM marginal unit — gas CC)
    heat_rate_btu_per_kwh: float = 7500.0       # BTU/kWh (gas combined cycle)
    fuel_price_per_mmbtu: float = 3.50           # $/MMBtu (Henry Hub proxy)
    variable_om_per_mwh: float = 4.00            # $/MWh variable O&M

    # M28: Loss factors (PSEG zone aggregate)
    distribution_loss_factor: float = 0.032      # 3.2% distribution losses
    transmission_loss_factor: float = 0.011      # 1.1% transmission losses

    # M28: LMP decomposition defaults (used when no market data available)
    default_congestion_per_mwh: float = 3.50     # $/MWh average congestion
    default_loss_price_per_mwh: float = 1.20     # $/MWh marginal loss component

    # Settlement: DA/RT split (typical residential is 100% DA settled)
    da_settlement_fraction: float = 0.95         # 95% DA, 5% RT deviation

    # Tax
    nj_sales_tax_rate: float = 0.06625

    # Stochastic parameters for Monte Carlo
    fuel_price_volatility: float = 0.25          # annual vol for lognormal
    heat_rate_std_pct: float = 0.05              # ±5% variation
    congestion_volatility: float = 0.40          # high variance
    loss_factor_std: float = 0.005               # ±0.5% variation

    # Correlation between fuel price and congestion (empirical PJM)
    fuel_congestion_correlation: float = 0.35

    @property
    def total_loss_factor(self) -> float:
        """Combined distribution + transmission loss factor."""
        return self.distribution_loss_factor + self.transmission_loss_factor


# Singleton default instance
DEFAULT_PJM = PJMMarketDefaults()


# ─────────────────────────────────────────────────────────────────────────────
#  M15: GENERATOR COST MODEL
# ─────────────────────────────────────────────────────────────────────────────

def compute_marginal_cost(
    heat_rate: Union[float, np.ndarray] = DEFAULT_PJM.heat_rate_btu_per_kwh,
    fuel_price: Union[float, np.ndarray] = DEFAULT_PJM.fuel_price_per_mmbtu,
    variable_om: Union[float, np.ndarray] = DEFAULT_PJM.variable_om_per_mwh,
) -> Union[float, np.ndarray]:
    """
    M15 Generator Cost Stack: marginal cost of the price-setting unit.

    Formula:
        marginal_cost ($/MWh) = (heat_rate [BTU/kWh] × fuel_price [$/MMBtu]) / 1000
                                + variable_OM [$/MWh]

    Note: heat_rate in BTU/kWh × fuel_price in $/MMBtu → $/MWh requires /1000
    because 1 MMBtu = 1,000,000 BTU and 1 MWh = 1000 kWh.

    Parameters
    ----------
    heat_rate : BTU/kWh of marginal generator
    fuel_price : $/MMBtu fuel cost
    variable_om : $/MWh variable operations & maintenance

    Returns
    -------
    Marginal cost in $/MWh
    """
    return (heat_rate * fuel_price) / 1000.0 + variable_om


# ─────────────────────────────────────────────────────────────────────────────
#  M28: LMP DECOMPOSITION
# ─────────────────────────────────────────────────────────────────────────────

def compute_lmp(
    energy_price: Union[float, np.ndarray],
    congestion_price: Union[float, np.ndarray] = 0.0,
    loss_price: Union[float, np.ndarray] = 0.0,
) -> Union[float, np.ndarray]:
    """
    M28 Locational Marginal Price decomposition.

    Formula:
        LMP = energy_component + congestion_component + loss_component

    All values in $/MWh.

    Parameters
    ----------
    energy_price : energy component (≈ marginal cost of price-setting generator)
    congestion_price : transmission congestion rent at this node
    loss_price : marginal loss component at this node

    Returns
    -------
    LMP in $/MWh
    """
    return energy_price + congestion_price + loss_price


def decompose_lmp(
    lmp: Union[float, np.ndarray],
    congestion: Union[float, np.ndarray] = 0.0,
    loss_factor: float = DEFAULT_PJM.total_loss_factor,
) -> Dict[str, Union[float, np.ndarray]]:
    """
    Decompose an observed LMP into energy, congestion, and loss components.

    When only total LMP and congestion are known (typical case with our data),
    we estimate the loss component from the loss factor and derive energy as residual.

    Parameters
    ----------
    lmp : total LMP ($/MWh)
    congestion : congestion component ($/MWh)
    loss_factor : total system loss factor (fraction)

    Returns
    -------
    dict with 'energy', 'congestion', 'loss' components ($/MWh)
    """
    # Loss price ≈ LMP × loss_factor / (1 + loss_factor)
    loss_price = lmp * loss_factor / (1.0 + loss_factor)
    energy_price = lmp - congestion - loss_price

    # Guard: energy price should be non-negative
    if isinstance(energy_price, np.ndarray):
        energy_price = np.maximum(energy_price, 0.0)
    else:
        energy_price = max(energy_price, 0.0)

    return {
        "energy": energy_price,
        "congestion": congestion,
        "loss": loss_price,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  M28: LOSS-ADJUSTED CONSUMPTION
# ─────────────────────────────────────────────────────────────────────────────

def compute_effective_kwh(
    usage_kwh: Union[float, np.ndarray],
    loss_factor: Union[float, np.ndarray] = DEFAULT_PJM.total_loss_factor,
) -> Union[float, np.ndarray]:
    """
    M28 Loss-adjusted load: what the grid must generate to deliver usage_kwh to the meter.

    Formula:
        effective_kwh = usage_kwh × (1 + loss_factor)

    Parameters
    ----------
    usage_kwh : metered consumption in kWh
    loss_factor : combined distribution + transmission loss fraction

    Returns
    -------
    Loss-adjusted kWh (always ≥ usage_kwh)
    """
    return usage_kwh * (1.0 + loss_factor)


# ─────────────────────────────────────────────────────────────────────────────
#  M28: TWO-SETTLEMENT (DA + RT)
# ─────────────────────────────────────────────────────────────────────────────

def compute_settlement_charge(
    da_mwh: Union[float, np.ndarray],
    da_price: Union[float, np.ndarray],
    rt_mwh: Union[float, np.ndarray],
    rt_price: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    M28 Two-Settlement System.

    Formula:
        da_charge = da_mwh × da_price
        rt_charge = (rt_mwh − da_mwh) × rt_price
        total = da_charge + rt_charge

    Parameters
    ----------
    da_mwh : day-ahead scheduled MWh
    da_price : day-ahead LMP ($/MWh)
    rt_mwh : real-time actual MWh
    rt_price : real-time LMP ($/MWh)

    Returns
    -------
    Total energy charge in $
    """
    da_charge = da_mwh * da_price
    rt_charge = (rt_mwh - da_mwh) * rt_price
    return da_charge + rt_charge


def compute_energy_charge_simple(
    lmp_per_mwh: Union[float, np.ndarray],
    effective_kwh: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Simplified M28 energy charge (single-settlement approximation).

    Formula:
        energy_charge = (lmp / 1000) × effective_kwh

    Converts LMP from $/MWh to $/kWh before multiplying.

    Parameters
    ----------
    lmp_per_mwh : LMP in $/MWh
    effective_kwh : loss-adjusted consumption in kWh

    Returns
    -------
    Energy charge in $
    """
    lmp_per_kwh = lmp_per_mwh / 1000.0
    return lmp_per_kwh * effective_kwh


def compute_energy_charge_two_settlement(
    effective_kwh: Union[float, np.ndarray],
    da_price_mwh: Union[float, np.ndarray],
    rt_price_mwh: Union[float, np.ndarray],
    da_fraction: Union[float, np.ndarray] = DEFAULT_PJM.da_settlement_fraction,
) -> Dict[str, Union[float, np.ndarray]]:
    """
    Full M28 two-settlement energy charge for retail load.

    Parameters
    ----------
    effective_kwh : loss-adjusted consumption in kWh
    da_price_mwh : day-ahead LMP ($/MWh)
    rt_price_mwh : real-time LMP ($/MWh)
    da_fraction : fraction of load settled at DA price

    Returns
    -------
    dict with 'da_charge', 'rt_charge', 'total_energy_charge' (all in $)
    """
    effective_mwh = effective_kwh / 1000.0
    da_mwh = effective_mwh * da_fraction
    rt_mwh = effective_mwh * (1.0 - da_fraction)

    da_charge = da_mwh * da_price_mwh
    rt_charge = rt_mwh * rt_price_mwh
    total = da_charge + rt_charge

    return {
        "da_charge": da_charge,
        "rt_charge": rt_charge,
        "total_energy_charge": total,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  TRANSMISSION RATE LINK
# ─────────────────────────────────────────────────────────────────────────────

def compute_transmission_rate(
    base_transmission: Union[float, np.ndarray],
    congestion_component: Union[float, np.ndarray] = 0.0,
) -> Union[float, np.ndarray]:
    """
    M28 Transmission rate with congestion pass-through.

    Formula:
        transmission_rate = base_transmission + congestion_price_component

    Parameters
    ----------
    base_transmission : base $/kWh transmission rate (from tariff)
    congestion_component : $/kWh congestion pass-through (congestion_$/MWh / 1000)

    Returns
    -------
    Effective transmission rate in $/kWh
    """
    return base_transmission + congestion_component


# ─────────────────────────────────────────────────────────────────────────────
#  FULL BILL ASSEMBLY (M28 Settlement → Retail Bill)
# ─────────────────────────────────────────────────────────────────────────────

def compute_total_bill(
    customer_charge: Union[float, np.ndarray],
    energy_charge: Union[float, np.ndarray],
    distribution_cost: Union[float, np.ndarray],
    transmission_cost: Union[float, np.ndarray],
    policy_charges: Union[float, np.ndarray] = 0.0,
    tax_rate: float = DEFAULT_PJM.nj_sales_tax_rate,
) -> Dict[str, Union[float, np.ndarray]]:
    """
    Final retail bill assembly per M28 settlement accounting.

    Formula:
        subtotal = customer_charge + energy_charge + distribution_cost
                   + transmission_cost + policy_charges
        tax = subtotal × tax_rate
        total = subtotal + tax

    Parameters
    ----------
    customer_charge : fixed monthly service charge ($)
    energy_charge : LMP × effective_kwh ($)
    distribution_cost : local delivery charge ($)
    transmission_cost : regional grid charge ($)
    policy_charges : SBC + riders + NUG + other mandated charges ($)
    tax_rate : sales tax rate (default: NJ 6.625%)

    Returns
    -------
    dict with 'subtotal', 'tax', 'total_bill'
    """
    subtotal = (customer_charge + energy_charge + distribution_cost
                + transmission_cost + policy_charges)
    tax = subtotal * tax_rate
    total = subtotal + tax

    return {
        "subtotal": subtotal,
        "tax": tax,
        "total_bill": total,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MONTE CARLO: STOCHASTIC MARKET PARAMETER SAMPLING
# ─────────────────────────────────────────────────────────────────────────────

def sample_market_parameters(
    n_sim: int,
    defaults: PJMMarketDefaults = DEFAULT_PJM,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate correlated stochastic draws for Monte Carlo simulation.

    Samples:
        - fuel_price ~ LogNormal (captures right-skew spikes)
        - heat_rate ~ Normal (mechanical variation)
        - congestion_price ~ correlated with fuel_price
        - loss_factor ~ Normal (small variation)

    Parameters
    ----------
    n_sim : number of simulation draws
    defaults : PJMMarketDefaults with base values and volatilities
    seed : random seed for reproducibility

    Returns
    -------
    dict with (n_sim,) arrays: 'fuel_price', 'heat_rate', 'congestion_price',
    'loss_factor', 'marginal_cost', 'lmp'
    """
    rng = np.random.default_rng(seed)

    # 1. Correlated normals for fuel_price and congestion (Cholesky)
    rho = defaults.fuel_congestion_correlation
    cov = np.array([[1.0, rho], [rho, 1.0]])
    L = np.linalg.cholesky(cov)
    z = rng.standard_normal((n_sim, 2))
    correlated = z @ L.T  # (n_sim, 2)

    # 2. Fuel price — LogNormal
    fuel_mu = np.log(defaults.fuel_price_per_mmbtu) - 0.5 * defaults.fuel_price_volatility ** 2
    fuel_sigma = defaults.fuel_price_volatility
    fuel_price = np.exp(fuel_mu + fuel_sigma * correlated[:, 0])
    fuel_price = np.clip(fuel_price, 1.0, 20.0)  # physical bounds

    # 3. Heat rate — Normal with ±std%
    heat_rate_std = defaults.heat_rate_btu_per_kwh * defaults.heat_rate_std_pct
    heat_rate = rng.normal(defaults.heat_rate_btu_per_kwh, heat_rate_std, n_sim)
    heat_rate = np.clip(heat_rate, 6000, 12000)  # physical bounds

    # 4. Congestion — Half-normal (always ≥ 0), correlated with fuel
    cong_base = defaults.default_congestion_per_mwh
    cong_vol = defaults.congestion_volatility
    congestion_raw = cong_base + cong_base * cong_vol * correlated[:, 1]
    congestion_price = np.clip(congestion_raw, 0.0, 50.0)

    # 5. Loss factor — Normal with small std
    loss_factor = rng.normal(defaults.total_loss_factor, defaults.loss_factor_std, n_sim)
    loss_factor = np.clip(loss_factor, 0.01, 0.15)

    # 6. Derived: marginal cost and LMP
    marginal_cost = compute_marginal_cost(heat_rate, fuel_price, defaults.variable_om_per_mwh)

    # Loss price ≈ marginal_cost × loss_factor
    loss_price = marginal_cost * loss_factor
    lmp = compute_lmp(marginal_cost, congestion_price, loss_price)

    return {
        "fuel_price": fuel_price,
        "heat_rate": heat_rate,
        "congestion_price": congestion_price,
        "loss_factor": loss_factor,
        "marginal_cost": marginal_cost,
        "loss_price": loss_price,
        "lmp": lmp,
    }


def compute_bills_pjm_vectorized(
    lmp_mwh: np.ndarray,
    effective_kwh: np.ndarray,
    distribution_rate: Union[float, np.ndarray],
    base_transmission_rate: Union[float, np.ndarray],
    congestion_per_kwh: Union[float, np.ndarray],
    policy_rate: Union[float, np.ndarray],
    customer_charge: float,
    usage_kwh: np.ndarray,
    tax_rate: float = DEFAULT_PJM.nj_sales_tax_rate,
) -> np.ndarray:
    """
    Vectorized PJM-physics bill computation for Monte Carlo.

    Parameters
    ----------
    lmp_mwh : (n_sim,) LMP in $/MWh
    effective_kwh : (n_sim,) loss-adjusted consumption
    distribution_rate : $/kWh distribution rate (scalar or array)
    base_transmission_rate : $/kWh base transmission rate
    congestion_per_kwh : $/kWh congestion pass-through (congestion_$/MWh / 1000)
    policy_rate : $/kWh combined SBC + riders + NUG
    customer_charge : fixed monthly charge ($)
    usage_kwh : (n_sim,) metered usage (for distribution/policy charges)
    tax_rate : sales tax rate

    Returns
    -------
    (n_sim,) array of total bill values
    """
    # Energy charge: LMP-based
    energy_charge = (lmp_mwh / 1000.0) * effective_kwh

    # Distribution: rate × metered usage
    distribution_cost = distribution_rate * usage_kwh

    # Transmission: (base + congestion pass-through) × metered usage
    transmission_cost = (base_transmission_rate + congestion_per_kwh) * usage_kwh

    # Policy charges: SBC + riders + NUG
    policy_cost = policy_rate * usage_kwh

    # Assembly
    subtotal = customer_charge + energy_charge + distribution_cost + transmission_cost + policy_cost
    tax = subtotal * tax_rate
    return subtotal + tax
