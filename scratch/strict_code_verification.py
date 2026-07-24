import os
import re
from pathlib import Path

datasets = [
    {"name": "PJM Hourly LMP", "file": "pjm_market_pseg_cache.csv", "db_table": "pjm_lmp_hourly"},
    {"name": "Open-Meteo Weather", "file": "weather_openmeteo.csv", "db_table": "weather_openmeteo"},
    {"name": "Retail Supplier Plans", "file": "retail_plans.parquet", "db_table": "retail_plans"},
    {"name": "State Benchmark", "file": "state_benchmark.parquet", "db_table": "state_benchmark"},
    {"name": "BGS Auction Rates", "file": "bgs_auction_rates.csv", "db_table": "bgs_auction_rates"},
    {"name": "EIA-861 Master", "file": "Operational_Data_master.csv", "db_table": "eia861_master"},
    {"name": "EIA-861M Monthly", "file": "Sales_Ult_Cust_master.csv", "db_table": "eia861m_monthly"},
    {"name": "Community Energy", "file": "community_energy.csv", "db_table": "community_energy"},
    {"name": "Municipal Energy", "file": "municipal_energy.csv", "db_table": "municipal_energy"},
    {"name": "EIA-930 Daily/Hourly", "file": "eia_pjm_daily_demand.csv", "db_table": "eia930_interchange"},
    {"name": "US Census ACS", "file": "tl_2024_us_zcta520.parquet", "db_table": "raw_demographics"},
    {"name": "NOAA Weather Cache", "file": "weather_noaa_cache.csv", "db_table": "raw_weather"},
]

root_dir = Path(".")
py_files = list(root_dir.rglob("*.py"))
tsx_files = list(root_dir.rglob("*.tsx"))

print(f"Scanned {len(py_files)} Python files and {len(tsx_files)} TypeScript/React files.\n")

results = {}

for ds in datasets:
    dname = ds["name"]
    fname = ds["file"]
    tname = ds["db_table"]
    
    found_py = []
    found_tsx = []
    
    for pf in py_files:
        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
            if fname.lower() in content.lower() or tname.lower() in content.lower():
                found_py.append(str(pf.relative_to(root_dir)))
        except:
            pass
            
    for tf in tsx_files:
        try:
            content = tf.read_text(encoding="utf-8", errors="ignore")
            if fname.lower() in content.lower() or tname.lower() in content.lower():
                found_tsx.append(str(tf.relative_to(root_dir)))
        except:
            pass
            
    results[dname] = {
        "file": fname,
        "db_table": tname,
        "python_refs": sorted(list(set(found_py))),
        "tsx_refs": sorted(list(set(found_tsx)))
    }

print("=== CODEBASE MAPPING RESULTS ===")
for dname, res in results.items():
    print(f"[{dname}] (File: {res['file']} | Table: {res['db_table']})")
    print(f"  Python Files ({len(res['python_refs'])}): {res['python_refs'][:5]}")
    print(f"  React UI Files ({len(res['tsx_refs'])}): {res['tsx_refs'][:5]}")
    print()
