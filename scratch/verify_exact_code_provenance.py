import os
import re
from pathlib import Path

# Master proven code map with exact file paths and search tokens
datasets_provenance = {
    "PJM Day-Ahead Hourly LMP": {
        "raw_file": "data/raw/pjm_market_pseg_cache.csv",
        "search_tokens": ["pjm_market_pseg_cache.csv", "pjm_lmp_hourly", "/pjm/", "PJMWholesaleOverlay"],
        "table_name": "pjm_lmp_hourly",
        "service_file": "api/services/pjm_market_service.py",
        "route_file": "api/routes/pjm.py",
        "ui_file": "frontend/src/components/tabs/ForecastTab.tsx"
    },
    "Open-Meteo Weather": {
        "raw_file": "data/raw/weather_openmeteo.csv",
        "search_tokens": ["weather_openmeteo.csv", "weather_openmeteo", "/weather/", "WeatherSeverityPanel"],
        "table_name": "weather_openmeteo",
        "service_file": "api/services/weather_severity_service.py",
        "route_file": "api/routes/weather.py",
        "ui_file": "frontend/src/components/tabs/ForecastTab.tsx"
    },
    "Retail Supplier Plans": {
        "raw_file": "data/raw/retail_plans.parquet",
        "search_tokens": ["retail_plans.csv", "retail_plans.parquet", "retail_plans", "evaluate-supplier-plan", "RetailSupplierETFSection"],
        "table_name": "retail_plans",
        "service_file": "api/services/tariff_optimization_engine.py",
        "route_file": "api/routes/tariff_optimization.py",
        "ui_file": "frontend/src/pages/ImpactPage.tsx"
    },
    "State Benchmark": {
        "raw_file": "data/raw/state_benchmark.parquet",
        "search_tokens": ["state_benchmark.parquet", "state_benchmark", "/geo/benchmark/", "StateBenchmarkSection"],
        "table_name": "state_benchmark",
        "service_file": "api/services/benchmark_service.py",
        "route_file": "api/routes/geo_insights.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "BGS Auction Clearing Rates": {
        "raw_file": "data/raw/bgs_auction_rates.csv",
        "search_tokens": ["bgs_auction_rates.csv", "bgs_auction_rates", "bgs-auction-history", "BGSCiepAuctionSection"],
        "table_name": "bgs_auction_rates",
        "service_file": "api/services/tariff_optimization_engine.py",
        "route_file": "api/routes/tariff_optimization.py",
        "ui_file": "frontend/src/pages/ImpactPage.tsx"
    },
    "EIA-861 Master Utility": {
        "raw_file": "data/raw/eia861_master_data/Operational_Data_master.csv",
        "search_tokens": ["Operational_Data_master.csv", "eia861_master", "/eia/scorecard", "UtilityScorecardSection"],
        "table_name": "eia861_master",
        "service_file": "api/services/eia861_analytics_service.py",
        "route_file": "api/routes/eia861.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "EIA-861M Monthly Sales": {
        "raw_file": "data/raw/eia861_master_data/Sales_Ult_Cust_master.csv",
        "search_tokens": ["Sales_Ult_Cust_master.csv", "eia861m_monthly", "/eia861m/sector-trends", "EVElectrificationSection"],
        "table_name": "eia861m_monthly",
        "service_file": "api/services/eia861m_service.py",
        "route_file": "api/routes/eia861m.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "DVRPC Community Energy": {
        "raw_file": "data/raw/community_energy.csv",
        "search_tokens": ["community_energy.csv", "community_energy", "/geo/municipal/community-energy", "CommunityEnergySection"],
        "table_name": "community_energy",
        "service_file": "api/services/community_energy_service.py",
        "route_file": "api/routes/municipal.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "NJ DEP Municipal Energy": {
        "raw_file": "data/raw/municipal_energy.csv",
        "search_tokens": ["municipal_energy.csv", "municipal_energy", "/geo/municipal-breakdown", "MunicipalSectorSection"],
        "table_name": "municipal_energy",
        "service_file": "api/services/municipal_energy_service.py",
        "route_file": "api/routes/geo_insights.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "EIA-930 Daily/Hourly Grid": {
        "raw_file": "data/raw/eia_pjm_daily_demand.csv",
        "search_tokens": ["eia_pjm_daily_demand.csv", "eia930_interchange", "/grid/interchange", "GridInterchangeSection"],
        "table_name": "eia930_interchange",
        "service_file": "api/services/eia930_service.py",
        "route_file": "api/routes/eia930.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "US Census ACS Demographics": {
        "raw_file": "data/raw/tl_2024_us_zcta520/tl_2024_us_zcta520.parquet",
        "search_tokens": ["tl_2024_us_zcta520.parquet", "raw_demographics", "/geo/census-demographics", "CensusEnergyBurdenSection"],
        "table_name": "raw_demographics",
        "service_file": "api/services/census_service.py",
        "route_file": "api/routes/geo_insights.py",
        "ui_file": "frontend/src/pages/RegionalPage.tsx"
    },
    "NOAA Climate Severity": {
        "raw_file": "data/raw/weather_noaa_cache.csv",
        "search_tokens": ["weather_noaa_cache.csv", "raw_weather", "/weather/noaa-severity", "WeatherSeverityPanel"],
        "table_name": "raw_weather",
        "service_file": "api/services/weather_severity_service.py",
        "route_file": "api/routes/weather.py",
        "ui_file": "frontend/src/components/tabs/ForecastTab.tsx"
    }
}

def find_evidence(tokens):
    root = Path(".")
    found = []
    for p in root.rglob("*"):
        if p.is_file() and not any(x in str(p) for x in ['.git', 'node_modules', 'dist', '.pytest_cache', '__pycache__', 'scratch']):
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for idx, line in enumerate(lines, 1):
                    for tok in tokens:
                        if tok.lower() in line.lower():
                            found.append({
                                "file": str(p).replace("\\", "/"),
                                "line": idx,
                                "token": tok,
                                "code": line.strip()[:100]
                            })
            except:
                pass
    return found

full_report = {}

for ds_name, meta in datasets_provenance.items():
    evidence = find_evidence(meta["search_tokens"])
    full_report[ds_name] = {
        "meta": meta,
        "total_hits": len(evidence),
        "hits": evidence[:15]
    }

print("=== EXACT EVIDENCE SEARCH RESULTS ===")
for dname, r in full_report.items():
    print(f"\nDataset: [{dname}] — Total Code Matches: {r['total_hits']}")
    for h in r["hits"][:5]:
        print(f"  {h['file']} (L{h['line']}): {h['code']}")
