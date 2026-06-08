import pytest
import numpy as np
from models.pjm_market_physics import (
    compute_marginal_cost,
    compute_lmp,
    compute_effective_kwh,
    compute_settlement_charge,
    decompose_lmp,
    compute_energy_charge_simple,
    compute_energy_charge_two_settlement,
    compute_transmission_rate,
    compute_total_bill,
    sample_market_parameters,
    compute_bills_pjm_vectorized,
)

def test_compute_marginal_cost():
    # marginal_cost = (7500 * 3.50) / 1000 + 4.0 = 26.25 + 4.0 = 30.25
    val = compute_marginal_cost(7500.0, 3.50, 4.0)
    assert pytest.approx(val) == 30.25

def test_compute_lmp():
    val = compute_lmp(30.0, 5.0, 2.0)
    assert val == 37.0

def test_compute_effective_kwh():
    val = compute_effective_kwh(1000.0, 0.043)
    assert pytest.approx(val) == 1043.0

def test_compute_settlement_charge():
    val = compute_settlement_charge(100.0, 30.0, 110.0, 35.0)
    assert val == 3350.0

def test_decompose_lmp():
    # total LMP = 37, congestion = 5, loss_factor = 0.043
    # loss_price = 37 * 0.043 / 1.043 = 1.5254
    # energy_price = 37 - 5 - 1.5254 = 30.4746
    decomp = decompose_lmp(37.0, 5.0, 0.043)
    assert pytest.approx(decomp["loss"]) == 1.525407
    assert pytest.approx(decomp["congestion"]) == 5.0
    assert pytest.approx(decomp["energy"]) == 30.47459

def test_compute_energy_charge_simple():
    val = compute_energy_charge_simple(37.0, 1043.0)
    assert pytest.approx(val) == 38.591

def test_compute_energy_charge_two_settlement():
    res = compute_energy_charge_two_settlement(1043.0, 30.0, 35.0, 0.95)
    # da_mwh = 1.043 * 0.95 = 0.99085
    # rt_mwh = 1.043 * 0.05 = 0.05215
    # da_charge = 0.99085 * 30 = 29.7255
    # rt_charge = 0.05215 * 35 = 1.82525
    assert pytest.approx(res["da_charge"]) == 29.7255
    assert pytest.approx(res["rt_charge"]) == 1.82525
    assert pytest.approx(res["total_energy_charge"]) == 31.55075

def test_compute_transmission_rate():
    val = compute_transmission_rate(0.015, 0.003)
    assert val == 0.018

def test_compute_total_bill():
    res = compute_total_bill(
        customer_charge=8.24,
        energy_charge=31.55,
        distribution_cost=40.0,
        transmission_cost=15.0,
        policy_charges=5.0,
        tax_rate=0.06625
    )
    # subtotal = 8.24 + 31.55 + 40.0 + 15.0 + 5.0 = 99.79
    # tax = 99.79 * 0.06625 = 6.6110875
    # total = 106.4010875
    assert pytest.approx(res["subtotal"]) == 99.79
    assert pytest.approx(res["tax"]) == 6.6110875
    assert pytest.approx(res["total_bill"]) == 106.4010875

def test_sample_market_parameters():
    params = sample_market_parameters(n_sim=10, seed=42)
    assert len(params["lmp"]) == 10
    assert np.all(params["lmp"] >= 0)
    assert np.all(params["loss_factor"] >= 0.01)

def test_compute_bills_pjm_vectorized():
    n_sim = 5
    lmp_mwh = np.array([30.0, 32.0, 35.0, 28.0, 40.0])
    effective_kwh = np.array([1000.0, 1050.0, 1020.0, 980.0, 1100.0])
    dist_rate = 0.04
    base_trans = 0.015
    cong_per_kwh = np.array([0.001, 0.002, 0.0015, 0.0005, 0.003])
    policy_rate = 0.005
    customer_charge = 8.24
    usage_kwh = np.array([960.0, 1000.0, 980.0, 940.0, 1050.0])
    
    bills = compute_bills_pjm_vectorized(
        lmp_mwh=lmp_mwh,
        effective_kwh=effective_kwh,
        distribution_rate=dist_rate,
        base_transmission_rate=base_trans,
        congestion_per_kwh=cong_per_kwh,
        policy_rate=policy_rate,
        customer_charge=customer_charge,
        usage_kwh=usage_kwh,
        tax_rate=0.06625
    )
    assert len(bills) == n_sim
    assert np.all(bills > 0)
