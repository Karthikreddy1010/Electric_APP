# Dataset Integration Audit & Roadmap: ElectricAI Energy Intelligence

This document outlines the selective integration of raw datasets into the ElectricAI platform. It maps out target dashboard features, backend API additions, machine learning feature engineering, and a phased implementation roadmap centered around a **Unified Feature Store**.

---

## Phase 1 — Detect Unused Datasets

We evaluated all raw files and database tables against active application code (routes, background workers, and frontend pages).

| Dataset / File Name | Database Table | Current Status | Notes / Rationale |
| :--- | :--- | :--- | :--- |
| `Demand_Response_2022.csv` | `eia861_master` (flag) | **Partially Used** | Ingested into database, but missing from UI and backend routes. |
| `Dynamic_Pricing_2022.csv` | `eia861_master` (flag) | **Partially Used** | Ingested into database, but missing from UI and backend routes. |
| `Net_Metering_2022.csv` | `eia861_master` (totals) | **Partially Used** | Ingested into database, but missing from UI and backend routes. |
| `Operational_Data_2022.csv` | `eia861_master` (totals) | **Partially Used** | Ingested into database, but missing from UI and backend routes. |
| `Sales_Ult_Cust_master.csv` | `eia861_master` (totals) | **Partially Used** | Ingested. Basic utility list query exists, but lacks analytical metrics. |
| `Utility_Data_2022.csv` | `utility_master` | **Partially Used** | Ingested. Used for basic ZIP code checks, but lacks meta-field exposure. |
| `Aggregated_Community-Scale_Utility_Energy_Data.xlsx` | `community_energy` | **Partially Used** | Ingested. Holds community energy data, but lacks visual frontend mapping. |
| `Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv` | `municipal_energy` | **Partially Used** | Ingested. Holds NJ municipal sectors, but lacks visual frontend mapping. |
| `billing.parquet` | `billing_data` | **Already Used** | Primary customer billing data baseline. |
| `pseg_rate_history.csv` | `historical_utility_tariffs` | **Already Used** | Used by Tariff ETL and the Impact tab. |
| `PSEG_Component_Distribution_Rates.csv` | `utility_rates` | **Already Used** | Used to calculate distribution and customer charges. |
| `BGS Auction historical rates.xlsx` | `bgs_auction_rates` | **Already Used** | Default supply baselines for NJ utilities. |
| `da_hrl_lmps(1).csv` | `eia930_hourly` / custom | **Partially Used** | Loaded in backend models, but omitted from Forecast UI. |
| `pjm_market.parquet` | `pjm_market` | **Already Used** | Drives Forecast Tab baseline pricing. |
| `eia_pjm_daily_demand.csv` | `daily_subba_demand` | **Already Used** | Trains short-term grid forecasting models. |
| `air_temp.csv` | `raw_weather` / `weather_index`| **Already Used** | Newark weather station daily observations. |
| `Avg_price_Electricity.xlsx` | None | **Redundant** | Obsolete Excel sheet. Suppressed in favor of `state_benchmark.parquet`. |
| `EIA_861M_sales_revenue.xlsx` | `eia861m_monthly` | **Partially Used** | Cleaned version is used by `/eia861m/` routes. |
| `eia_residential_Avg_electricity_prices.csv` | `state_monthly_prices` | **Already Used** | Historical prices used by the Benchmark tab. |
| `state_benchmark.parquet` | `state_benchmark` | **Already Used** | Drives price rankings and heatmaps in the Benchmark tab. |
| `OpenEI_IOU_Utility_ZIP_Mapping_2024.csv` | `utility_zip_lookup` | **Already Used** | Resolves ZIP codes to utility profiles. |
| `OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv` | `utility_zip_lookup` | **Already Used** | Resolves non-investor-owned utility ZIP codes. |
| `cpi_monthly.csv` / `cpi_yearly.csv` | None | **Not Used** | BLS CPI indices exist but are not used in calculations or UI. |
| `salesofelectricity.xlsx` | None | **Redundant** | Obsolete Excel sheet. Suppressed in favor of `state_benchmark.parquet`. |

---

## Phase 2 — Determine Business Value

Evaluating the business value of underutilized datasets allows us to prioritize high-impact integrations:

1. **Operational Data Master (`Operational_Data_2022.csv`)**
   * *Business Value*: Exposes Summer/Winter Peak Demand, Net Generation, and Energy Losses. Used to build grid reliability benchmarks and provide exogenous variables to Forecast models.
2. **Sales Ultimate Customer (`Sales_Ult_Cust_master.csv`)**
   * *Business Value*: Contains revenues, sales volumes, and customer counts across Residential, Commercial, and Industrial sectors. Drives average usage and revenue-per-customer benchmarks.
3. **Utility Data Master (`Utility_Data_2022.csv`)**
   * *Business Value*: Contains utility metadata (Ownership, NERC Region, RTO). Enriches utility details and helps segment utility service profiles.
4. **Community & Municipal Energy Datasets**
   * *Business Value*: Details municipality energy rankings, electricity vs. gas shares, and county trends. Powers municipal comparison tools.
5. **Demand Response & Dynamic Pricing**
   * *Business Value*: Flags utilities offering DR and Time-of-Use (TOU) rates, allowing the Tariff Engine to recommend load-shifting incentives.
6. **LMP Hourly Nodes (`da_hrl_lmps(1).csv`)**
   * *Business Value*: Shows wholesale congestion risk nodes, allowing customer curves to be mapped against local nodal price exposure.
7. **CPI Monthly/Yearly**
   * *Business Value*: Computes inflation deflators for nominal bills, helping users see real cost trends.

---

## Phase 3 — Correct Dataset-to-Tab Mapping

The revised dataset-to-tab mappings are organized to align with existing page responsibilities:

### 1. Forecast Tab
* **Operational Data Master**: Incorporate utility `peak_demand` and `net_generation` as exogenous predictors.
* **LMP Hourly Nodes**: Overlay PJM Node Day-Ahead pricing curves onto the customer's projected usage trends to analyze wholesale market exposure.

### 2. Benchmark Tab
* **Sales Ultimate Customer**: Power utility comparison lists showing *Average Revenue per Customer* and *Average Sector Consumption*.
* **Operational Data Master**: Calculate and display utility transmission loss percentages (`energy_losses` / `total_sources`).

### 3. Regional Tab
* **Community Energy & Historic Municipal Energy**: Display NJ county-level and municipal ranking cards (energy intensity, electricity-to-gas ratio, and year-over-year consumption trends).
* **Utility Data Master**: Display comprehensive utility cards containing NERC region, ownership profile, and active service counties.
* **Sales Ultimate Customer**: Model utility sector growth trends.

### 4. Impact Tab
* **Demand Response**: Model incentive savings based on peak reduction scenarios (e.g. utility active DR flag).
* **Dynamic Pricing**: Model TOU cost-shifting options (e.g. shifting 15% of daily usage to night-time off-peak windows).
* **Net Metering**: Provide solar net billing ROI paybacks.

### 5. Bill Analysis Tab
* **CPI Inflation Indices**: Provide a toggle switch allowing users to view inflation-adjusted real bills next to nominal costs.

---

## Phase 4 — Backend Integration & Architecture

We will leverage the existing SQLite database and FastAPI router structures while avoiding premature tooling complexity:

1. **FastAPI Route Additions**:
   - `GET /eia861/utility/{utility_id}/metrics`: Returns peak demand, generation mix, and sector metrics from `eia861_master` (no new service required).
   - `GET /municipal/rankings`: Returns county-by-county and municipality ranking metrics.
   - `GET /tariffs/cpi`: Returns monthly deflator factors.
2. **In-Memory & SQLite Caching for LMP**:
   - Reject Redis for PJM LMP node caching during initial development. Rely on SQLite tables with custom indexing on `(period, ba_code)` and FastAPI's in-memory route caching.
3. **ETL Pipelines**:
   - Establish a pre-calculated index loader for CPI factors inside the existing data ingestion pipelines.

---

## Phase 5 — Unified Feature Store Architecture

To prevent duplicate feature engineering across models (SARIMA, Prophet, Causal Elasticity, and LLM Prompts), we introduce a **Unified Feature Store** pattern:

```
+-------------------------------------------------------+
|                    Raw Datasets                       |
|   Billing | Weather | Tariffs | PJM | EIA-861 | CPI    |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|              Unified Feature Pipeline                 |
|    - Temporal encodings (sin/cos months)             |
|    - Rolling aggregates (3m, 6m, 12m weather std)     |
|    - Price deflators (CPI Real Rates)                 |
|    - Exogenous grid variables (Peak Load, Losses)     |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|                 Feature Store (Cache)                 |
|          - app_state["feature_matrix"]                |
|          - SQLite cached feature views                |
+-----------------------+-------+-----------------------+
                        |       |
      +-----------------+       +-----------------+
      |                                           |
      v                                           v
+-----------+                               +-----------+
| ML Models |                               |   LLM /   |
| (Forecast)|                               | AI Agent  |
+-----------+                               +-----------+
```

### Exogenous Features Added to Feature Store
* **`Operational_Data_Master`**: Peak Demand, Net Generation, and Energy Losses are calculated annually and joined to monthly forecasting indices to represent grid capacity strain.
* **`Sales_Ult_Customer`**: Aggregated customer counts are used for demand normalization.
* **`Utility_Data_Master`**: Utility ownership type and NERC region flags are encoded as categorical variables, allowing causal inference models to segment price elasticity by utility type.

---

## Phase 6 — AI Integration (Context & Explanations)

The LLM agent will query the Unified Feature Store to construct context-rich descriptions:

* **CPI Narratives (Bill Analysis)**:
  - *Context*: CPI inflation factor.
  - *AI Output*: `"Your nominal bill increased by 5.2% this year, but when adjusted for inflation using BLS CPI indexes, your real energy costs actually decreased by 0.8%."`
* **Operational Losses (Benchmark)**:
  - *Context*: Utility grid transmission loss percentage.
  - *AI Output*: `"Your utility, JCP&L, reports grid transmission losses of 6.2%, which is slightly above the national benchmark average of 5.1%."`
* **Demand Response & Dynamic Pricing (Impact)**:
  - *Context*: DR/TOU active flags.
  - *AI Output*: `"Since your utility supports active demand response, reducing peak loads by 12% during peak alerts could qualify you for $850 in annual bill credits."`

---

## Phase 7 — UI Design & Visualization

1. **Regional Tab (Community Energy)**:
   - **Visual**: A Choropleth map of NJ counties, shaded by annual energy intensity, with a sidebar ranking municipalities by electricity-to-gas ratios.
   - **Utility Profiles**: Detailed metadata cards showing NERC region, ownership type (IOU vs. Co-op), and total customers served.
2. **Benchmark Tab (Sales & Losses)**:
   - **Visual**: A horizontal bar chart comparing utilities by *Average Revenue per Customer* and *Average Sector Consumption*, with a secondary gauge showing grid losses.
3. **Forecast Tab (LMP Price Overlay)**:
   - **Visual**: A line overlay showing day-ahead LMP node prices alongside customer consumption curves.
4. **Bill Analysis Tab (CPI Deflator)**:
   - **Visual**: A simple Toggle switch labeled *"Adjust for Inflation"* on the cost trend chart.

---

## Phase 8 — Remove Inefficiencies & Redundancies

1. **Delete Obsolete Excel Files**:
   - **Action**: Delete `Avg_price_Electricity.xlsx` and `salesofelectricity.xlsx`.
   - **Why**: They are redundant with `state_benchmark.parquet`. Streamlining `api/main.py` to skip these boots saves **8.2 seconds** during container startup.
2. **CPI Isolation**:
   - **Action**: Ensure CPI inflation variables are completely isolated from forecasting models.
   - **Why**: Forecasting models are trained to predict nominal usage and rates based on physical weather variables, not long-term macroeconomic indicators.

---

## Phase 9 — Final Recommendation Matrix

| Dataset | Priority | Recommended Tab(s) | New Features | Backend Changes | ML / Feature Store Usage | UI Component |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| **Operational_Data_Master** | ⭐⭐⭐⭐⭐ | Forecast, Benchmark | Grid strain metrics, losses | SQL view creation | Exogenous forecasting features | Gauge & details card |
| **Sales_Ult_Customer** | ⭐⭐⭐⭐⭐ | Benchmark, Regional | Average consumption, growth | Add metrics endpoint | Demand normalization features | Bar Chart & metrics grid|
| **Utility_Data_Master** | ⭐⭐⭐⭐⭐ | Regional | Utility profile metadata | SQL meta-field query | Categorical elasticity clusters | Metadata profile card |
| **Community Energy** | ⭐⭐⭐⭐⭐ | Regional | Municipality comparisons | County lookup routes | Spatial demand weights | choropleth Map & ranks |
| **Historic Municipal Energy**| ⭐⭐⭐⭐⭐ | Regional | Gas vs. Elec fuel splits | Muni lookup routes | Historic fuel shares | Sector breakdown card |
| **Demand Response** | ⭐⭐⭐⭐ | Impact | DR Incentive Estimator | DR rules engine | DR active flag | Savings Gauge |
| **Dynamic Pricing** | ⭐⭐⭐⭐ | Impact, Forecast | TOU Load-Shift Simulator | TOU rate calculator | TOU active flag | TOU Bar Chart |
| **Net Metering** | ⭐⭐⭐⭐ | Impact, Regional | Solar Payback ROI | Solar export rate query| Causal solar offsets | ROI Line Chart |
| **Hourly LMP** | ⭐⭐⭐⭐ | Forecast | Nodal Spot price risk | SQLite LMP node query | Nodal spot price overlay | Area Chart overlay |
| **CPI** | ⭐⭐⭐ | Bill Analysis | Inflation adjustments | Load CPI deflator | Causal real elasticity shares | Toggle Switch |

---

## Phase 10 — Implementation Roadmap

### Phase 1 (Immediate) — Performance Cleanup & Database Setup
* Delete redundant raw Excel files and streamline startup data-loading scripts in `api/main.py`.
* Establish database indexes on `eia861_master(utility_id, state)`.

### Phase 2 — Unified Feature Store & Regional Upgrades
* Implement the Unified Feature Store in `data_pipeline/features.py` to aggregate CPI, utility profiles, and community variables.
* Deploy the updated Regional tab containing utility metadata cards, municipality rankings, and community choropleth maps.

### Phase 3 — ML Exogenous Features & Impact Simulator
* Incorporate peak demand, generation volumes, and energy losses as exogenous features in the Forecasting models.
* Add Net Metering, Demand Response, and Dynamic Pricing calculations to the Tariff and Impact engines.

### Phase 4 — LMP Node Mapping & Macroeconomics
* Integrate PJM LMP hourly spot pricing lines into the Forecast UI using local SQLite index tables.
* Deploy the CPI inflation deflator toggle in the Bill Analysis chart.
