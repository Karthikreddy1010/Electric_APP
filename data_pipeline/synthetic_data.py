"""
Synthetic data generator for development and testing.
Produces realistic electricity billing, weather, and market data.
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def generate_billing_data(start="2019-01-01", end="2025-12-31", seed=42):
    np.random.seed(seed)
    dates = pd.date_range(start, end, freq="MS")
    n = len(dates)
    month_idx = dates.month
    base_usage = 750
    seasonal = np.where(month_idx.isin([6,7,8]), 1.45,
               np.where(month_idx.isin([12,1,2]), 1.25,
               np.where(month_idx.isin([5,9,10]), 1.05, 0.95)))
    usage = np.clip(base_usage * seasonal + np.random.normal(0, 40, n), 300, 2000)
    yr = (dates.year - 2019).astype(float)
    bgs_r = 0.085 + 0.004*yr + np.random.normal(0, 0.003, n)
    trans_r = 0.016 + 0.0015*yr + np.random.normal(0, 0.001, n)
    dist_r = 0.038 + 0.001*yr + np.random.normal(0, 0.002, n)
    sbc_r = 0.004 + 0.0008*yr + np.random.normal(0, 0.0005, n)
    nug_r = np.clip(0.004 - 0.0003*yr + np.random.normal(0, 0.0003, n), 0.001, 0.006)
    dr = np.where(month_idx.isin([6,7,8]), -np.random.uniform(2, 8, n), 0)
    bgs_c, trans_c, dist_c = usage*bgs_r, usage*trans_r, usage*dist_r
    sbc_c, nug_c = usage*sbc_r, usage*nug_r
    sub = bgs_c + trans_c + dist_c + sbc_c + nug_c + dr
    tax = sub * 0.06625
    return pd.DataFrame({
        "date": dates, "usage_kwh": np.round(usage,1),
        "bgs_rate": np.round(bgs_r,5), "bgs_cost": np.round(bgs_c,2),
        "transmission_rate": np.round(trans_r,5), "transmission_cost": np.round(trans_c,2),
        "distribution_rate": np.round(dist_r,5), "distribution_cost": np.round(dist_c,2),
        "sbc_rate": np.round(sbc_r,5), "sbc_cost": np.round(sbc_c,2),
        "nug_rate": np.round(nug_r,5), "nug_cost": np.round(nug_c,2),
        "dr_credit": np.round(dr,2), "subtotal": np.round(sub,2),
        "sales_tax": np.round(tax,2), "total_bill": np.round(sub+tax,2),
        "utility": "PSE&G", "state": "NJ", "customer_class": "residential",
    })


def generate_weather_data(start="2019-01-01", end="2025-12-31", seed=42):
    np.random.seed(seed)
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)
    doy = dates.dayofyear
    temp = 54 + 24*np.sin(2*np.pi*(doy-105)/365) + np.random.normal(0, 6, n)
    return pd.DataFrame({
        "date": dates, "station": "NEWARK_NJ",
        "avg_temp_f": np.round(temp,1),
        "hdd": np.round(np.maximum(65-temp,0),1),
        "cdd": np.round(np.maximum(temp-65,0),1),
        "precip_in": np.round(np.where(np.random.random(n)>0.35, np.random.exponential(0.12,n),0),2),
        "humidity_pct": np.round(np.clip(55+15*np.sin(2*np.pi*(doy-80)/365)+np.random.normal(0,8,n),20,100),1),
    })


def generate_pjm_data(start="2019-01-01", end="2025-12-31", seed=42):
    np.random.seed(seed)
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)
    yr = (dates.year-2019).values.astype(float)
    doy = dates.dayofyear
    base = 35 + 3*yr + 12*np.sin(2*np.pi*(doy-30)/365)
    noise = np.random.lognormal(0, 0.15, n)*5
    spikes = (np.random.random(n)<0.02)*np.random.uniform(50,200,n)
    lmp = np.clip(base+noise+spikes, 10, 500)
    cap = np.array([120,140,135,165,180,195,210])[np.clip((dates.year-2019).values,0,6)].astype(float)
    return pd.DataFrame({
        "date": dates, "zone": "PSEG",
        "lmp_da": np.round(lmp,2), "lmp_rt": np.round(lmp*(1+np.random.normal(0,0.05,n)),2),
        "capacity_price": np.round(cap+np.random.normal(0,3,n),2),
        "congestion": np.round(np.abs(np.random.normal(2,3,n)),2),
    })


def generate_state_benchmarks(seed=42):
    np.random.seed(seed)
    states_data = [
        ("NJ",0.167),("NY",0.195),("CT",0.218),("MA",0.228),("PA",0.135),
        ("MD",0.138),("DE",0.128),("VA",0.118),("OH",0.112),("IL",0.127),
        ("TX",0.118),("CA",0.225),("FL",0.121),("GA",0.112),("WA",0.098),
        ("OR",0.105),("MI",0.158),("WI",0.143),("MN",0.128),("HI",0.328),
        ("AK",0.218),("ME",0.168),("NH",0.188),("VT",0.178),("RI",0.218),
    ]
    rows = []
    for abbr, base in states_data:
        for yr in range(2019, 2026):
            rate = base*(1+0.025*(yr-2019)) + np.random.normal(0, 0.005)
            rows.append({"state": abbr, "year": yr, "avg_rate": round(rate,4),
                         "avg_bill": round(rate*900,2)})
    return pd.DataFrame(rows)


def generate_retail_plans():
    return pd.DataFrame([
        {"provider":"PSE&G (BGS)","type":"variable","rate":0.1052,"term_months":0,"etf":0,"green_pct":0,"volatility":0.015},
        {"provider":"Direct Energy","type":"fixed","rate":0.0989,"term_months":12,"etf":150,"green_pct":0,"volatility":0.0},
        {"provider":"Direct Energy Green","type":"fixed","rate":0.1089,"term_months":12,"etf":150,"green_pct":100,"volatility":0.0},
        {"provider":"Constellation","type":"fixed","rate":0.0945,"term_months":24,"etf":200,"green_pct":0,"volatility":0.0},
        {"provider":"Verde Energy","type":"variable","rate":0.0999,"term_months":0,"etf":0,"green_pct":50,"volatility":0.018},
        {"provider":"CleanChoice","type":"fixed","rate":0.1199,"term_months":12,"etf":0,"green_pct":100,"volatility":0.0},
        {"provider":"SmartEnergy","type":"variable","rate":0.0879,"term_months":0,"etf":0,"green_pct":0,"volatility":0.022},
        {"provider":"NRG Home","type":"fixed","rate":0.0959,"term_months":18,"etf":100,"green_pct":25,"volatility":0.0},
    ])


def generate_all(output_dir=None):
    if output_dir is None:
        output_dir = str(DATA_DIR / "raw")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    datasets = {
        "billing": generate_billing_data(),
        "weather": generate_weather_data(),
        "pjm_market": generate_pjm_data(),
        "state_benchmark": generate_state_benchmarks(),
        "retail_plans": generate_retail_plans(),
    }
    for name, df in datasets.items():
        df.to_parquet(out / f"{name}.parquet", index=False, engine="pyarrow")
        df.to_csv(out / f"{name}.csv", index=False)
        print(f"  [OK] {name}: {len(df)} rows")
    return datasets


if __name__ == "__main__":
    print("Generating synthetic electricity data...")
    generate_all()
