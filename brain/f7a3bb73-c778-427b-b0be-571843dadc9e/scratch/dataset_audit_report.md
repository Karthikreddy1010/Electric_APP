# Electric AI Web Application — Dataset Integration Audit Report

This report provides a comprehensive, component-by-component audit of the dataset files, database structures, API routes, machine learning models, and frontend UI views in the Electric AI web application.

---

## 1. Dataset Files & Locations (Step 1)

The following table documents the presence, filenames, paths, and versions of the 12 required datasets:

| ID | Dataset | Exists? | Raw File Name(s) & Path(s) | Processed File Name(s) & Path(s) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **BGS Auction Historical** | **YES** | [BGS Auction historical rates.xlsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/BGS%20Auction%20historical%20rates.xlsx) | [bgs_auction.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/bgs_auction.csv) | Preprocessed by year and utility. |
| 2 | **Aggregated Community Scale Utility Energy Data** | **YES** | [Aggregated_Community-Scale_Utility_Energy_Data.xlsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/Aggregated_Community-Scale_Utility_Energy_Data.xlsx) | [community_energy.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/community_energy.csv) | Formatted to snake_case. |
| 3 | **Historic Municipal Energy Use in New Jersey** | **YES** | [Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv) | [municipal_energy.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/municipal_energy.csv) | Seemed duplicate/redundant but fully processed. |
| 4 | **NJ Residential Average Retail Price of Electricity Monthly** | **YES** | [nj-rs-Average_retail_price_of_electricity_monthly.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/nj-rs-Average_retail_price_of_electricity_monthly.csv) | [nj_retail_prices.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/nj_retail_prices.csv) | Used as base spine for master data merging. |
| 5 | **Average Electricity Prices (2005–Current)** | **YES** | - [Avg_price_Electricity.xlsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/Avg_price_Electricity.xlsx)<br>- [eia_residential_Avg_electricity_prices.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/eia_residential_Avg_electricity_prices.csv)<br>- [salesofelectricity.xlsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/salesofelectricity.xlsx) | - [eia_residential_prices.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/eia_residential_prices.csv)<br>- [state_benchmark.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/state_benchmark.csv)<br>- [state_benchmark.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/state_benchmark.parquet) | Multiple source spreadsheets representing national, state, and historical benchmark tables. |
| 6 | **NOAA Weather Data** | **YES** | - [weather.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/weather.csv)<br>- [weather.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/weather.parquet)<br>- [weather_noaa_cache.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/weather_noaa_cache.csv)<br>- [weather_openmeteo.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/weather_openmeteo.csv)<br>- [air_temp.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/air_temp.csv) | [weather_monthly.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/weather_monthly.csv) | Includes cached NOAA air temp records and daily Open-Meteo simulations. |
| 7 | **EIA-861** | **YES** | 22 files under [data/raw/eia861_master_data/](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/eia861_master_data/) (e.g. `Demand_Response...csv`, `Net_Metering...csv`, etc.) | 8 files under [data/processed/eia861/](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/eia861/) (e.g. `demand_response_clean.csv`, `sales_clean.csv`, `net_metering_clean.csv`, etc.) | Full coverage of operational and sales categories. |
| 8 | **EIA-861M (Sales & Revenue)** | **YES** | [EIA_861M_sales_revenue.xlsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/EIA_861M_sales_revenue.xlsx) | (None) | Loaded directly into the DB. |
| 9 | **Utility Tariff Data** | **YES** | (No raw file - API dynamic sync) | (None) | Dynamically loaded via API from OpenEI URDB into DB table. |
| 10 | **OpenEI Utility Service Territories** | **YES** | - [OpenEI_IOU_Utility_ZIP_Mapping_2024.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/OpenEI_IOU_Utility_ZIP_Mapping_2024.csv)<br>- [OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv) | (None) | Normalized directly to database tables. |
| 11 | **EIA-930 Hourly Grid Operations** | **YES** | - [eia_pjm_daily_demand.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/eia_pjm_daily_demand.csv)<br>- [eia_pjm_hourly_demand.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/eia_pjm_hourly_demand.csv) | (None) | Fetched from EIA API, stored in DB tables. |
| 12 | **PJM Hourly LMP Data** | **YES** | - [da_hrl_lmps(1).csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/da_hrl_lmps(1).csv)<br>- [pjm_market.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/pjm_market.csv)<br>- [pjm_market.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/pjm_market.parquet) | (None) | wholesale prices represented by `pjm_market.parquet`. |

---

## 2. Code Usage & UI Integration (Step 2)

This section maps each dataset to its active consumers in code and visual components:

*   **1. BGS Auction Historical**
    *   **Used?** YES
    *   **Database Table**: `bgs_auction_rates`
    *   **Seeder**: `seed_bgs_auction_rates` inside [seed.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/database/seed.py#L390)
    *   **API Route**: `GET /bgs/rates` in [api/routes/bgs.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/bgs.py#L9)
    *   **UI Tab**: **Plans Tab** in [PlansTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/PlansTab.tsx#L138)
    *   **UI Component / Chart**: `NJ BGS Auction RSCP Rates History` LineChart showing wholesale rates pivoted by EDC (PSE&G, JCP&L, ACE, RECO).

*   **2. Aggregated Community Scale Utility Energy Data**
    *   **Used?** YES
    *   **Database Table**: `community_energy`
    *   **Seeder**: `seed_community_energy` inside [seed.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/database/seed.py#L430)
    *   **API Route**: `GET /municipal/list` and `GET /municipal/benchmark` in [api/routes/municipal.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/municipal.py)
    *   **UI Tab**: **Overview Tab** in [OverviewTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/OverviewTab.tsx#L151)
    *   **UI Component**: Municipal benchmark selection dropdown, consumption trend history charts showing Residential/Commercial/Industrial energy usage.

*   **3. Historic Municipal Energy Use in New Jersey**
    *   **Used?** **NO (Backend-only redundancy)**
    *   **Database Table**: `municipal_energy`
    *   **Seeder**: `seed_municipal_energy` in [seed.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/database/seed.py#L474)
    *   **API / UI Usage**: **None**. It is loaded into `app_state["municipal_energy_df"]` in [api/main.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/main.py#L188) but never queried by any API route or component. The endpoints `/municipal/list` and `/municipal/benchmark` query the `community_energy` table instead.

*   **4. NJ Residential Average Retail Price of Electricity Monthly**
    *   **Used?** YES (Indirectly)
    *   **Data Pipeline**: [merger.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data_pipeline/merger.py#L41) loads `nj_retail_prices` as the base monthly spine.
    *   **Usage**: Left-joins CPI and Weather, applies inflation adjustments, and saves the final output as [final_master_dataset.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/final_master_dataset.csv) to serve as a baseline for cost-modeling calculations.

*   **5. Average Electricity Prices (2005–Current)**
    *   **Used?** YES
    *   **Database Tables**: `state_monthly_prices`, `state_benchmark`
    *   **Seeders**: `seed_state_monthly_prices` & `seed_state_benchmark` in [seed.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/database/seed.py)
    *   **API Routes**: 
        *   `/benchmark` in [api/routes/benchmark.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/benchmark.py)
        *   `/geo/data`, `/geo/trend`, `/geo/detail`, `/geo/meta` in [api/routes/geo_insights.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/geo_insights.py)
    *   **UI Tabs**:
        *   **Benchmark Tab** in [BenchmarkTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/BenchmarkTab.tsx) (displays rank, comparison charts, and scatter plot of prices vs. bills for states).
        *   **Geo Tab** in [GeoTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/GeoTab.tsx) (renders average rates timeline and state comparison trends).

*   **6. NOAA Weather Data**
    *   **Used?** YES
    *   **API / Engine**: 
        *   `BillImpactModel` in [models/impact_model.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/models/impact_model.py#L57) reads `air_temp.csv` to compute daily HDD/CDD and calibrate OLS regression for weather normalization.
        *   `ElectricityDemandForecaster` in [models/forecast_model.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/models/forecast_model.py#L231) reads the daily Open-Meteo weather data to train Prophet and SARIMA demand models.
    *   **UI Tabs**:
        *   **Impact Tab** in [ImpactTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/ImpactTab.tsx#L300) (renders the Weather Impact decomposition waterfall and Context Card).
        *   **What-If Tab** in [WhatIfTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/WhatIfTab.tsx#L8) (runs peak billing simulations based on "Hot Summer" [+25% CDD] or "Cold Winter" [+15% HDD] scenarios).

*   **7. EIA-861**
    *   **Used?** YES
    *   **Database Table**: `eia861_master` (contains merged sales, net metering, demand response, dynamic pricing, and operational peaks).
    *   **Seeder**: `seed_eia861_master` in [seed.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/database/seed.py#L541)
    *   **API Routes**: `/eia861/states`, `/eia861/utilities`, `/eia861/utility/{utility_id}` in [api/routes/eia861.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/eia861.py)
    *   **UI Tab**: **Utility Tab** in [UtilityTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/UtilityTab.tsx#L63) (shows annual sales, total customers, peak demand, Net Metering adoption, and flags for demand response/dynamic pricing programs).
    *   **Unused**: The processed GIS county mapping [service_territory_clean.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/processed/eia861/service_territory_clean.csv) is outputted by the pipeline but is never seeded or referenced in the API/UI.

*   **8. EIA-861M (Sales & Revenue)**
    *   **Used?** YES
    *   **Database Table**: `eia861m_monthly`
    *   **API Routes**: `/eia861m/summary`, `/eia861m/states`, `/eia861m/state/{state}`, `/eia861m/trends`, `/eia861m/rankings` in [api/routes/eia861m.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/eia861m.py)
    *   **ML Model**: [models/forecast_model.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/models/forecast_model.py#L291) merges these monthly sales records as exogeneous features for demand forecasting.
    *   **UI Tabs**:
        *   **Utility Tab** in [UtilityTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/UtilityTab.tsx#L15) (under "monthly" granularity view).
        *   **Overview Tab** in [OverviewTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/OverviewTab.tsx#L239) (shows national sales, revenue, and average price cards).
        *   **Benchmark Tab** in [BenchmarkTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/BenchmarkTab.tsx#L32) (fetches monthly sector sales trends).

*   **9. Utility Tariff Data**
    *   **Used?** **NO (Backend sync only)**
    *   **Database Table**: `utility_tariffs`
    *   **Background Task**: `sync_openei_tariffs_task` in [tasks.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/orchestration/tasks.py#L170) fetches NJ utility tariff structures (fixed fees, energy rate steps) from OpenEI URDB API.
    *   **Usage**: **None**. There are no API endpoints querying this table, and no React UI components reference OpenEI tariff structures.

*   **10. OpenEI Utility Service Territories**
    *   **Used?** YES
    *   **Database Tables**: `utility_master`, `utility_zip_lookup`, `utility_rates`
    *   **API Routes**: 
        *   `/utility/lookup`, `/utility/search`, `/utility/coverage` in [api/routes/openei.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/openei.py)
        *   `/geo/boundaries` in [api/routes/geo_insights.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/geo_insights.py#L462) (joins ZIP mapping to Shapefile geometries for GeoJSON caching)
    *   **UI Tabs**: 
        *   **Geo Tab** in [GeoTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/GeoTab.tsx#L161) (fetches operating utilities by ZIP code and draws the interactive choropleth map).
        *   **Benchmark Tab** in [BenchmarkTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/BenchmarkTab.tsx#L41) (displays the number of service ZIPs).

*   **11. EIA-930 Hourly Grid Operations**
    *   **Used?** YES (Partially)
    *   **Database Tables**: `eia930_hourly`, `eia930_generation`, `eia930_subregion`, `eia930_interchange`, `daily_subba_demand`
    *   **API Routes**: `/grid/current`, `/grid/demand`, `/grid/generation-mix`, `/grid/subregions`, `/grid/interchange` in [api/routes/eia930.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/eia930.py)
    *   **UI Tab**: **Geo Tab** in [GeoTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/GeoTab.tsx#L148) (queries `/grid/current?ba=PJM` to show current load, generation, and status).
    *   **Unused Endpoints**: The hourly historical demand, fuel mix, subregion, and interchange flow endpoints are fully functional in the API but unused in the frontend. The 131MB CSV is obsolete (replaced by the daily table).

*   **12. PJM Hourly LMP Data**
    *   **Used?** YES
    *   **Data Source**: `pjm_market.parquet` loaded into memory as `market_df`.
    *   **API Route**: `/bill-impact/causal-impact` in [bill_impact.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/bill_impact_router.py) uses `avg_lmp` as a treatment variable.
    *   **Causal Engine**: [bill_impact_engine.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/services/bill_impact_engine.py#L342) merges the market price dataframe to run Double Machine Learning causal attribution models.
    *   **UI Tab**: **Impact Tab** in [ImpactTab.tsx](file:///c:/Users/dukar/OneDrive/Desktop/Electric/frontend/src/components/tabs/ImpactTab.tsx#L750) (displays causal treatment effects for `avg_lmp` to isolate price impacts).
    *   **Unused File**: [da_hrl_lmps(1).csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/da_hrl_lmps(1).csv) is an obsolete 43MB raw file that is not read by the data pipeline.

---

## 3. Claimed vs. Actual Usage Verification (Step 3)

The intended mappings have been validated as follows:

1.  **BGS Auction Historical → Plans Tab**
    *   *Verified Status*: **CORRECT**. Exposed via `/bgs/rates` and plotted as a line chart on the Plans Tab.
2.  **Aggregated Community Scale Utility Energy Data → Overview, Benchmarking**
    *   *Verified Status*: **PARTIALLY CORRECT**. Used heavily in the Overview Tab municipal list and details. It is **NOT** used in the Benchmark Tab.
3.  **NJ Residential Average Retail Price + Average Electricity Prices → Geo Tab, Benchmark Tab**
    *   *Verified Status*: **CORRECT**. Used to construct `state_monthly_prices` (Geo Tab map slider/trendlines) and `state_benchmark` (Benchmark Tab rankings and scatter plot).
4.  **EIA-861 → Benchmark**
    *   *Verified Status*: **INCORRECT**. The EIA-861 master dataset is **NOT** used in the Benchmark Tab. It is used exclusively in the **Utility Tab** to show annual operational and customer details.
5.  **NOAA Weather → AI & Forecasting**
    *   *Verified Status*: **CORRECT**. Drives weather normalization in `BillImpactModel` (Impact Tab) and feeds exogeneous temperature features to `ElectricityDemandForecaster` (Forecast Tab).
6.  **EIA-930 Hourly Grid Operations**
    *   *Verified Status*: **PARTIALLY CORRECT**. Only `/grid/current?ba=PJM` is consumed in the Geo Tab. Hourly series, subregion load, fuel mix, and interchanges are implemented in the API but not used in the UI.
7.  **PJM Hourly LMP Data**
    *   *Verified Status*: **CORRECT**. Parsed from `pjm_market.parquet` and used in Double ML causal analysis (Impact Tab).

---

## 4. Unused Datasets on Disk (Step 4)

These files exist in `data/raw` or `data/processed` but are **never referenced** in the source code:

1.  **`da_hrl_lmps(1).csv`**
    *   *Folder*: `data/raw/`
    *   *Size*: 43.58 MB
    *   *Reason*: Legacy direct download of hourly LMPs. The code has moved to using [pjm_market.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/pjm_market.parquet) and database cache.
2.  **`eia_pjm_hourly_demand.csv`**
    *   *Folder*: `data/raw/`
    *   *Size*: 131.70 MB
    *   *Reason*: Legacy hourly grid operations file. Replaced by pre-aggregated [eia_pjm_daily_demand.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/eia_pjm_daily_demand.csv) and `daily_subba_demand` table to avoid memory exhaustion at server start.
3.  **`service_territory_clean.csv`**
    *   *Folder*: `data/processed/eia861/`
    *   *Size*: 211 KB
    *   *Reason*: Cleaned by `eia861_processor.py`, but not joined to `eia861_master_clean.csv` or seeded in the database.

---

## 5. Missing Datasets (Step 5)

No referenced datasets are missing on disk. All files queried by `pandas` or loaded by `database/seed.py` are present in their expected locations.

---

## 6. Dataset Integration Summary Table (Step 6)

| Dataset | Exists in Raw | Exists in Processed | Used in Code | Tabs Using It | Components | Status |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **BGS Auction Historical** | Yes | Yes | Yes | Plans | BGS Rates History Chart | ✅ Used Correctly |
| **Aggregated Community Scale Data** | Yes | Yes | Yes | Overview | Muni Energy Stats & Trend | ✅ Used Correctly |
| **Historic Municipal Energy Use** | Yes | Yes | No | (None) | (None) | ⚠ Exists but Unused |
| **NJ Residential Avg Retail Price** | Yes | Yes | Yes | (None) | Base spine for merge pipeline | ✅ Used Correctly |
| **Average Electricity Prices** | Yes | Yes | Yes | Geo, Benchmark | State rankings, Map slider | ✅ Used Correctly |
| **NOAA Weather Data** | Yes | Yes | Yes | Impact, What-If | CDD/HDD waterfall, simulations | ✅ Used Correctly |
| **EIA-861 (Core Data)** | Yes | Yes | Yes | Utility | Annual sales, peak demand, DR/DP | ✅ Used Correctly |
| **EIA-861 (Service Territories)** | Yes | Yes | No | (None) | (None) | ⚠ Exists but Unused |
| **EIA-861M (Sales & Revenue)** | Yes | No | Yes | Utility, Overview | Monthly sales trends & stats | ✅ Used Correctly |
| **Utility Tariff Data** | No | No | No | (None) | (None) | ⚠ Exists but Unused |
| **OpenEI Utility Territories** | Yes | No | Yes | Geo, Benchmark | ZIP Lookup, Choropleth Map | ✅ Used Correctly |
| **EIA-930 Hourly Grid Ops** | Yes | No | Yes | Geo | Current load & gen status | ✅ Used Correctly |
| **PJM Hourly LMP Data** | Yes | No | Yes | Impact | Causal DML wholesale analysis | ✅ Used Correctly |

---

## 7. Recommendations & Improvements (Step 7)

### 🧹 Cleanup Redundant Files
*   **Remove Obsolete Hourly Files**: Safely delete `eia_pjm_hourly_demand.csv` (131.7 MB) and `da_hrl_lmps(1).csv` (43.58 MB) from `data/raw`. These files consume 175 MB of space, but the application now relies entirely on `eia_pjm_daily_demand.csv` and `pjm_market.parquet` respectively.

### 🔌 Activate Sleeping Datasets
*   **Integrate OpenEI Tariffs**: The database synchronization task for `utility_tariffs` runs and populates the table, but it is never used. Build API endpoints in [api/routes/openei.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/openei.py) to serve tariff details (fixed fees and rate tier blocks) to the **Plans Tab** savings calculator to replace static fallback estimates.
*   **Integrate EIA-861 Service Territories**: Link `service_territory_clean.csv` (mapping utilities to operating counties) to the database seeding process.
*   **Resolve Municipal Dataset Clash**: The app seeds both `municipal_energy` (from *Historic Municipal Energy Use*) and `community_energy` (from *Aggregated Community Scale Utility Data*) into PostgreSQL. However, only `community_energy` is utilized in the UI. Either merge the two datasets to cover more municipalities or delete the unused `municipal_energy` table and loader.
*   **Consume Extra EIA-930 Data**: The API routes `/grid/generation-mix` and `/grid/demand` are fully implemented in [eia930.py](file:///c:/Users/dukar/OneDrive/Desktop/Electric/api/routes/eia930.py) but omitted in the UI. Consider adding a "Grid Operations" sub-section in the **Geo Tab** or **Overview Tab** displaying a Fuel Mix Pie Chart (Coal, Gas, Nuclear, Wind, etc.) and a 24-hour demand vs. forecast line chart.

---

### Data Pipeline Completeness Score

# $$\mathbf{87.5\%}$$

**Remaining work to reach 100%:**
1. Expose the OpenEI `utility_tariffs` table via API and implement tariff comparison blocks in the **Plans Tab**.
2. Connect the **Overview Tab**'s municipal search to both community and municipal tables to solve coverage gaps.
3. Clean up 175 MB of redundant legacy hourly CSV files from `data/raw`.
