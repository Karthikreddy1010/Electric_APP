"""
Data loading and generation module for the Streamlit MVP.
Generates synthetic PSE&G billing data if none exists, and provides
all data access functions for the app.
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def generate_billing_data(start="2019-01-01", end="2025-12-31", seed=42):
    """Generate realistic PSE&G monthly billing data."""
    np.random.seed(seed)
    dates = pd.date_range(start, end, freq="MS")
    n = len(dates)
    month_idx = dates.month

    base_usage = 750
    seasonal = np.where(month_idx.isin([6, 7, 8]), 1.45,
               np.where(month_idx.isin([12, 1, 2]), 1.25,
               np.where(month_idx.isin([5, 9, 10]), 1.05, 0.95)))
    usage = np.clip(base_usage * seasonal + np.random.normal(0, 40, n), 300, 2000)

    yr = (dates.year - 2019).astype(float)

    # PSE&G rate components with realistic trends
    customer_charge = np.full(n, 4.95)  # fixed monthly
    bgs_r = 0.085 + 0.004 * yr + np.random.normal(0, 0.003, n)
    trans_r = 0.016 + 0.0015 * yr + np.random.normal(0, 0.001, n)
    dist_r = 0.038 + 0.001 * yr + np.random.normal(0, 0.002, n)
    sbc_r = 0.004 + 0.0008 * yr + np.random.normal(0, 0.0005, n)
    nug_r = np.clip(0.004 - 0.0003 * yr + np.random.normal(0, 0.0003, n), 0.001, 0.006)
    rider_r = 0.003 + 0.0005 * yr + np.random.normal(0, 0.0003, n)
    mkt_trans_r = np.clip(0.002 - 0.0002 * yr + np.random.normal(0, 0.0002, n), 0.0005, 0.004)
    weather_adj = np.where(month_idx.isin([7, 8, 1, 2]),
                           np.random.uniform(-2, 4, n), np.random.uniform(-1, 1, n))
    dr_credit = np.where(month_idx.isin([6, 7, 8]), -np.random.uniform(2, 8, n), 0)

    bgs_c = usage * bgs_r
    trans_c = usage * trans_r
    dist_c = usage * dist_r
    sbc_c = usage * sbc_r
    nug_c = usage * nug_r
    rider_c = usage * rider_r
    mkt_trans_c = usage * mkt_trans_r

    sub = customer_charge + bgs_c + trans_c + dist_c + sbc_c + nug_c + rider_c + mkt_trans_c + weather_adj + dr_credit
    tax = sub * 0.06625

    return pd.DataFrame({
        "date": dates, "usage_kwh": np.round(usage, 1),
        "customer_charge": np.round(customer_charge, 2),
        "bgs_rate": np.round(bgs_r, 5), "bgs_cost": np.round(bgs_c, 2),
        "transmission_rate": np.round(trans_r, 5), "transmission_cost": np.round(trans_c, 2),
        "distribution_rate": np.round(dist_r, 5), "distribution_cost": np.round(dist_c, 2),
        "sbc_rate": np.round(sbc_r, 5), "sbc_cost": np.round(sbc_c, 2),
        "nug_rate": np.round(nug_r, 5), "nug_cost": np.round(nug_c, 2),
        "rider_rate": np.round(rider_r, 5), "rider_cost": np.round(rider_c, 2),
        "market_transition_rate": np.round(mkt_trans_r, 5), "market_transition_cost": np.round(mkt_trans_c, 2),
        "weather_adjustment": np.round(weather_adj, 2),
        "dr_credit": np.round(dr_credit, 2),
        "subtotal": np.round(sub, 2),
        "sales_tax": np.round(tax, 2),
        "total_bill": np.round(sub + tax, 2),
        "utility": "PSE&G", "state": "NJ", "customer_class": "residential",
    })


def generate_benchmark_data(seed=42):
    """Generate NJ vs US state benchmark data."""
    np.random.seed(seed)
    states_data = [
        ("NJ", 0.167), ("NY", 0.195), ("CT", 0.218), ("MA", 0.228), ("PA", 0.135),
        ("MD", 0.138), ("DE", 0.128), ("VA", 0.118), ("OH", 0.112), ("IL", 0.127),
        ("TX", 0.118), ("CA", 0.225), ("FL", 0.121), ("GA", 0.112), ("WA", 0.098),
        ("OR", 0.105), ("MI", 0.158), ("WI", 0.143), ("MN", 0.128), ("HI", 0.328),
        ("AK", 0.218), ("ME", 0.168), ("NH", 0.188), ("VT", 0.178), ("RI", 0.218),
    ]
    rows = []
    for abbr, base in states_data:
        for yr in range(2019, 2026):
            rate = base * (1 + 0.025 * (yr - 2019)) + np.random.normal(0, 0.005)
            rows.append({"state": abbr, "year": yr, "avg_rate": round(rate, 4),
                         "avg_bill": round(rate * 900, 2)})
    return pd.DataFrame(rows)


def generate_retail_plans():
    """Generate sample retail electricity plans for comparison."""
    return pd.DataFrame([
        {"provider": "PSE&G (BGS Default)", "type": "variable", "rate": 0.1052,
         "term_months": 0, "etf": 0, "green_pct": 0, "volatility": 0.015},
        {"provider": "Direct Energy Fixed", "type": "fixed", "rate": 0.0989,
         "term_months": 12, "etf": 150, "green_pct": 0, "volatility": 0.0},
        {"provider": "Direct Energy Green", "type": "fixed", "rate": 0.1089,
         "term_months": 12, "etf": 150, "green_pct": 100, "volatility": 0.0},
        {"provider": "Constellation 24mo", "type": "fixed", "rate": 0.0945,
         "term_months": 24, "etf": 200, "green_pct": 0, "volatility": 0.0},
        {"provider": "Verde Energy", "type": "variable", "rate": 0.0999,
         "term_months": 0, "etf": 0, "green_pct": 50, "volatility": 0.018},
        {"provider": "CleanChoice Solar", "type": "fixed", "rate": 0.1199,
         "term_months": 12, "etf": 0, "green_pct": 100, "volatility": 0.0},
        {"provider": "SmartEnergy Saver", "type": "variable", "rate": 0.0879,
         "term_months": 0, "etf": 0, "green_pct": 0, "volatility": 0.022},
        {"provider": "NRG Home", "type": "fixed", "rate": 0.0959,
         "term_months": 18, "etf": 100, "green_pct": 25, "volatility": 0.0},
    ])


def load_or_generate_data():
    """Load existing data or generate fresh synthetic data."""
    billing_path = DATA_DIR / "billing.parquet"
    bench_path = DATA_DIR / "state_benchmark.parquet"
    plans_path = DATA_DIR / "retail_plans.parquet"

    if billing_path.exists():
        billing = pd.read_parquet(billing_path)
        # Ensure columns exist (add if missing from older generation)
        if "customer_charge" not in billing.columns:
            billing["customer_charge"] = 4.95
        if "rider_cost" not in billing.columns:
            billing["rider_cost"] = billing["usage_kwh"] * 0.003
            billing["rider_rate"] = 0.003
        if "market_transition_cost" not in billing.columns:
            billing["market_transition_cost"] = billing["usage_kwh"] * 0.002
            billing["market_transition_rate"] = 0.002
        if "weather_adjustment" not in billing.columns:
            billing["weather_adjustment"] = 0.0
    else:
        billing = generate_billing_data()

    benchmark = pd.read_parquet(bench_path) if bench_path.exists() else generate_benchmark_data()
    plans = pd.read_parquet(plans_path) if plans_path.exists() else generate_retail_plans()

    # Ensure date column is datetime
    billing["date"] = pd.to_datetime(billing["date"])

    return billing, benchmark, plans
