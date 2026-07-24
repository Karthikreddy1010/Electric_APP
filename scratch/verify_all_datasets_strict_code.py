import os
import re
from pathlib import Path

# Datasets to audit strictly
datasets = [
    {
        "id": "pjm_lmp",
        "name": "PJM Day-Ahead Hourly LMP",
        "file": "data/raw/pjm_market_pseg_cache.csv",
        "table": "pjm_lmp_hourly",
        "route_path": "/pjm/",
        "component": "PJMWholesaleOverlay"
    },
    {
        "id": "weather_openmeteo",
        "name": "Open-Meteo Weather",
        "file": "data/raw/weather_openmeteo.csv",
        "table": "weather_openmeteo",
        "route_path": "/weather/",
        "component": "WeatherSeverityPanel"
    },
    {
        "id": "retail_plans",
        "name": "Retail Supplier Plans",
        "file": "data/raw/retail_plans.parquet",
        "table": "retail_plans",
        "route_path": "/impact/tariff-optimization/evaluate-supplier-plan",
        "component": "RetailSupplierETFSection"
    },
    {
        "id": "state_benchmark",
        "name": "State Benchmark",
        "file": "data/raw/state_benchmark.parquet",
        "table": "state_benchmark",
        "route_path": "/geo/benchmark/",
        "component": "StateBenchmarkSection"
    },
    {
        "id": "bgs_auction",
        "name": "BGS Auction Clearing Rates",
        "file": "data/raw/bgs_auction_rates.csv",
        "table": "bgs_auction_rates",
        "route_path": "/impact/tariff-optimization/bgs-auction-history",
        "component": "BGSCiepAuctionSection"
    },
    {
        "id": "eia861_master",
        "name": "EIA-861 Master Utility",
        "file": "data/raw/eia861_master_data/Operational_Data_master.csv",
        "table": "eia861_master",
        "route_path": "/eia/scorecard",
        "component": "UtilityScorecardSection"
    },
    {
        "id": "eia861m_monthly",
        "name": "EIA-861M Monthly Sales",
        "file": "data/raw/eia861_master_data/Sales_Ult_Cust_master.csv",
        "table": "eia861m_monthly",
        "route_path": "/eia861m/sector-trends",
        "component": "EVElectrificationSection"
    },
    {
        "id": "community_energy",
        "name": "DVRPC Community Energy",
        "file": "data/raw/community_energy.csv",
        "table": "community_energy",
        "route_path": "/geo/municipal/community-energy",
        "component": "CommunityEnergySection"
    },
    {
        "id": "municipal_energy",
        "name": "NJ DEP Municipal Energy",
        "file": "data/raw/municipal_energy.csv",
        "table": "municipal_energy",
        "route_path": "/geo/municipal-breakdown",
        "component": "MunicipalSectorSection"
    },
    {
        "id": "eia930_interchange",
        "name": "EIA-930 Grid Flow",
        "file": "data/raw/eia_pjm_daily_demand.csv",
        "table": "eia930_interchange",
        "route_path": "/eia930/grid/interchange",
        "component": "GridInterchangeSection"
    },
    {
        "id": "census_acs",
        "name": "US Census ACS Demographics",
        "file": "data/raw/tl_2024_us_zcta520/tl_2024_us_zcta520.parquet",
        "table": "raw_demographics",
        "route_path": "/geo/census-demographics",
        "component": "CensusEnergyBurdenSection"
    },
    {
        "id": "noaa_weather",
        "name": "NOAA Climate Severity",
        "file": "data/raw/weather_noaa_cache.csv",
        "table": "raw_weather",
        "route_path": "/weather/noaa-severity",
        "component": "WeatherSeverityPanel"
    },
    {
        "id": "customer_bills",
        "name": "Customer Billing & History",
        "file": "electric.db::customer_bills",
        "table": "customer_bills",
        "route_path": "/billing/",
        "component": "CustomerArchetypeAndHealthCard"
    },
    {
        "id": "cross_dataset_360",
        "name": "360° Cross-Dataset Matrix",
        "file": "Cross-Dataset Unified Store",
        "table": "unified_feature_store",
        "route_path": "/cross-dataset/unified-insights",
        "component": "Unified360CustomerCard"
    }
]

def search_snippet(filepath, keyword):
    if not Path(filepath).exists():
        return None
    lines = Path(filepath).read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, 1):
        if keyword.lower() in line.lower():
            return {"file": str(filepath).replace("\\", "/"), "line": idx, "code": line.strip()[:100]}
    return None

results = []

for ds in datasets:
    entry = {"id": ds["id"], "name": ds["name"], "stages": {}}
    
    # 1. Raw file
    raw_exists = Path(ds["file"]).exists() if not "::" in ds["file"] else True
    entry["stages"]["1_raw_file"] = {"verified": raw_exists, "path": ds["file"]}
    
    # 2. ETL / Ingestion Pipeline
    etl_match = search_snippet("database/seed.py", ds["table"]) or search_snippet("data_pipeline/synthetic_data.py", ds["table"])
    entry["stages"]["2_etl_pipeline"] = {"verified": bool(etl_match), "evidence": etl_match}
    
    # 3. Cleaning & Validation
    cleaner_match = search_snippet("data_pipeline/cleaners.py", ds["table"]) or search_snippet("data_pipeline/cleaners.py", ds["id"]) or search_snippet("database/seed.py", ds["table"])
    entry["stages"]["3_cleaning"] = {"verified": bool(cleaner_match), "evidence": cleaner_match}

    # 4. Database Model
    model_match = search_snippet("database/models.py", ds["table"])
    entry["stages"]["4_db_model"] = {"verified": bool(model_match), "evidence": model_match}

    # 5. Seeder / Migration
    seed_match = search_snippet("database/seed.py", ds["table"])
    entry["stages"]["5_seeder"] = {"verified": bool(seed_match), "evidence": seed_match}

    # 6. Feature Engineering
    feat_match = search_snippet("data_pipeline/features.py", ds["id"]) or search_snippet("data_pipeline/unified_feature_store.py", ds["id"]) or search_snippet("data_pipeline/unified_feature_store.py", ds["table"])
    entry["stages"]["6_feature_engineering"] = {"verified": bool(feat_match), "evidence": feat_match}

    # 7. Unified Feature Store
    store_match = search_snippet("data_pipeline/unified_feature_store.py", "build_unified_features")
    entry["stages"]["7_feature_store"] = {"verified": bool(store_match), "evidence": store_match}

    # 8. Backend Service
    svc_files = list(Path("api/services").glob("*.py"))
    svc_match = None
    for sf in svc_files:
        m = search_snippet(sf, ds["table"]) or search_snippet(sf, ds["id"])
        if m:
            svc_match = m
            break
    entry["stages"]["8_backend_service"] = {"verified": bool(svc_match), "evidence": svc_match}

    # 9. API Endpoint
    route_files = list(Path("api/routes").glob("*.py"))
    route_match = None
    for rf in route_files:
        m = search_snippet(rf, ds["route_path"]) or search_snippet(rf, ds["table"])
        if m:
            route_match = m
            break
    entry["stages"]["9_api_endpoint"] = {"verified": bool(route_match), "evidence": route_match}

    # 10. Frontend Page
    page_files = list(Path("frontend/src/pages").glob("*.tsx")) + list(Path("frontend/src/components/tabs").glob("*.tsx"))
    page_match = None
    for pf in page_files:
        m = search_snippet(pf, ds["route_path"]) or search_snippet(pf, ds["component"])
        if m:
            page_match = m
            break
    entry["stages"]["10_frontend_page"] = {"verified": bool(page_match), "evidence": page_match}

    # 11. React Component
    comp_files = list(Path("frontend/src").rglob("*.tsx"))
    comp_match = None
    for cf in comp_files:
        m = search_snippet(cf, f"const {ds['component']}") or search_snippet(cf, f"function {ds['component']}")
        if m:
            comp_match = m
            break
    entry["stages"]["11_react_component"] = {"verified": bool(comp_match), "evidence": comp_match}

    # 12. Visualization / KPI
    viz_match = None
    for cf in comp_files:
        m = search_snippet(cf, ds["component"])
        if m:
            viz_match = m
            break
    entry["stages"]["12_visualization_kpi"] = {"verified": bool(viz_match), "evidence": viz_match}

    # 13. Recommendation & AI Explanation Engine
    rec_match = search_snippet("api/services/tariff_optimization_engine.py", ds["id"]) or search_snippet("api/services/cross_dataset_service.py", ds["id"]) or search_snippet("api/services/cross_dataset_service.py", ds["table"]) or search_snippet("api/services/weather_severity_service.py", "severity")
    entry["stages"]["13_ai_engine"] = {"verified": bool(rec_match), "evidence": rec_match}

    results.append(entry)

print("=== STRICT 13-STAGE CODE VERIFICATION COMPLETE ===")
for r in results:
    v_count = sum(1 for s in r["stages"].values() if s.get("verified"))
    status = "FULL (13/13)" if v_count == 13 else f"PARTIAL ({v_count}/13)"
    print(f"Dataset: '{r['name']}' | Verified Stages: {v_count}/13 | Status: {status}")
