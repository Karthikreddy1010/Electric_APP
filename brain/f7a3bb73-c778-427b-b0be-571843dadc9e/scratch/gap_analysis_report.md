# Electric AI Web Application — Comprehensive Gap Analysis

This document provides a systematic gap analysis of the Electric AI application, investigating the alignment between the platform's strategic objectives, its technical features, the existing datasets, and the data structures necessary to transition the platform into a production-grade, AI-driven decision portal.

---

## Step 1: Understand the Application Objectives

Based on the codebase, API routes, and models, the Electric AI platform is designed to provide retail consumers, utility analysts, and municipal managers with transparency regarding electricity pricing, grid conditions, consumption behavior, and causal factors driving costs.

Below are the purposes, required inputs, and expected outputs for each of the 16 target features:

### 1. Utility Intelligence
*   **Purpose**: Track and analyze utility-level characteristics, customer count, revenues, peak load capacity, and adoption rates of net metering, demand response (DR), and dynamic pricing (DP) programs.
*   **Required Inputs**: EIA-861 annual reporting data (seeded into the `eia861_master` database table).
*   **Expected Outputs**: Utility profiles, operational peak demand metrics, state-wide utility comparisons, and program flags indicating the availability of demand-side programs.

### 2. Bill Analysis
*   **Purpose**: Decompose customer-level monthly electricity bills into constituent parts (fixed, distribution, transmission, societal benefits, default supply, and taxes) to isolate rate impacts from consumption behavior.
*   **Required Inputs**: Monthly billing dataset ([billing.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/billing.parquet)), utility-specific rate history schedules.
*   **Expected Outputs**: Absolute ($) and percentage (%) breakdowns of delivery vs. supply, effective rate per kWh, and month-over-month cost drivers.

### 3. Bill Statement Extraction
*   **Purpose**: Ingest and parse unstructured text or OCR output from scanned/PDF utility bills to construct structured digital accounts.
*   **Required Inputs**: Messy OCR text payload from a bill statement.
*   **Expected Outputs**: Normalized JSON containing utility name, billing period, total cost, usage in kWh, broken-out category charges, cost-driver indicators, and a text summary.

### 4. Rate Plan Comparison
*   **Purpose**: Contrast default utility supply pricing (Basic Generation Service - BGS) with commercial third-party retail supplier plans to optimize procurement.
*   **Required Inputs**: Retail plan parameters ([retail_plans.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/retail_plans.parquet)), customer historical load profile.
*   **Expected Outputs**: Expected annualized cost difference, Monte Carlo simulation of savings under variable rate volatility, early termination penalty notices, and green percentage scoring.

### 5. Benchmarking
*   **Purpose**: Position a customer's usage, unit price, and total bill against regional, state, and national averages.
*   **Required Inputs**: EIA monthly retail sales and revenue databases ([state_benchmark.parquet](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/state_benchmark.parquet)).
*   **Expected Outputs**: State-level rate rankings, average bill comparisons, volatility distributions, and price vs. bill scatter plots.

### 6. Geo Analytics
*   **Purpose**: Map electricity pricing, bill sizes, and annual volatility across the United States to detect geographical anomalies and local tariff differences.
*   **Required Inputs**: Cleaned monthly state prices (`state_monthly_prices` table), shapefile boundaries.
*   **Expected Outputs**: Color-coded geographic choropleths with timeline sliders, state YoY change metrics, and local GIS summaries.

### 7. Forecasting
*   **Purpose**: Forecast future electricity cost liability and usage demands to mitigate pricing spikes.
*   **Required Inputs**: Customer monthly historical billing files, weather anomalies (HDD/CDD).
*   **Expected Outputs**: Projected billing amounts, baseline adjustments, and weather-normalized expectations.

### 8. AI Insights
*   **Purpose**: Explaining bill anomalies, seasonality shifts, and rate-change impacts using natural language generation (NLG).
*   **Required Inputs**: Billing components, weather variance parameters, OCR extraction results.
*   **Expected Outputs**: Natural language narratives explaining bill drivers (e.g. identifying that a 15% bill spike was caused by a heatwave that increased CDD).

### 9. Causal Analysis
*   **Purpose**: Isolate the exact causal effect of a change in an individual rate component (such as BGS supply rate or wholesale LMP) on the total bill, controlling for confounding variables like weather and seasonality.
*   **Required Inputs**: Historical billing, weather CDD/HDD sums, PJM wholesale LMP series.
*   **Expected Outputs**: Causal elasticity coefficient, p-value statistics, and Double Machine Learning (DML) treatment effects.

### 10. Utility Tariff Analysis
*   **Purpose**: Evaluate local utility tariff structure schedules (such as customer fixed fees, seasonal distribution pricing, and riders).
*   **Required Inputs**: Historical utility filings ([pseg_rate_history.csv](file:///c:/Users/dukar/OneDrive/Desktop/Electric/data/raw/pseg_rate_history.csv)), synced OpenEI URDB API tables (`utility_tariffs`).
*   **Expected Outputs**: Interactive rate histories, charge type breakdowns, and volumetric/fixed rate schedules.

### 11. Electricity Demand Forecasting
*   **Purpose**: Train machine learning ensembles to predict grid-level daily load totals and peak demands.
*   **Required Inputs**: Balancing authority demand history (`daily_subba_demand`), daily temperatures/HDD/CDD.
*   **Expected Outputs**: 7-day and 30-day ahead total grid demand forecasts with confidence intervals, Prophet and SARIMA model evaluations (MAE, RMSE, MAPE).

### 12. Electricity Price Forecasting
*   **Purpose**: Estimate future price shifts in wholesale/retail electricity markets to optimize load shifting.
*   **Required Inputs**: Historical wholesale LMP price series, fuel indexes (Henry Hub Natural Gas), regional demand forecasts.
*   **Expected Outputs**: Volatility paths, peak pricing spike probabilities, and marginal pricing forecasts.

### 13. Customer Consumption Analytics
*   **Purpose**: Characterize customer-level base load, weather-sensitive cooling/heating loads, and underlying efficiency trends.
*   **Required Inputs**: Customer monthly usage (kWh), local weather indexes.
*   **Expected Outputs**: Customer base load estimate, weather sensitivity coefficients (slope values for CDD and HDD), and weather-normalized baseline usage.

### 14. Energy Efficiency Recommendations
*   **Purpose**: Suggest tailored energy retrofits, equipment upgrades, or behavior changes to minimize bill size.
*   **Required Inputs**: Customer base load, weather sensitivities, regional solar potential, and utility programs.
*   **Expected Outputs**: Personalized savings suggestions with estimated payback periods, sorted by financial impact.

### 15. Utility Service Territory Analysis
*   **Purpose**: Map geographic zones (ZIP codes) to the specific utilities operating in those areas to establish default provider availability.
*   **Required Inputs**: OpenEI IOU and Non-IOU ZIP code mapping files.
*   **Expected Outputs**: Operating utilities by ZIP code, ownership types, service types, and default residential rates.

### 16. Wholesale vs Retail Price Analysis
*   **Purpose**: Evaluate the spread between retail default supply rates (BGS) and wholesale market prices (LMPs) to identify arbitrage opportunities or markup margins.
*   **Required Inputs**: Utility BGS rates, PJM hourly LMP market data.
*   **Expected Outputs**: Monthly retail markups, wholesale volatility indexes, and dynamic demand response cost-saving potentials.

---

## Step 2: Review Existing Datasets

The platform currently hosts the following 12 datasets:

1.  **BGS Auction Historical**: Excel files of historical NJ Basic Generation Service (BGS) default supply rates pivoted by utility.
2.  **Aggregated Community Scale Utility Energy Data**: Excel data of municipal-level annual electricity consumption (kWh) split by sector (Residential, Commercial, Industrial) in NJ.
3.  **Historic Municipal Energy Use in NJ**: CSV data containing NJ municipal building-level historical energy consumption.
4.  **NJ Residential Average Retail Electricity Prices**: CSV price history representing average monthly retail rates (cents/kWh) in New Jersey.
5.  **EIA Average Electricity Prices (2005–Current)**: Spreadsheets containing annual/monthly state-level retail sales, revenue, and average electricity prices.
6.  **NOAA Weather**: Daily temperature summaries (TAVG, TMAX, TMIN) and computed monthly CDD/HDD for Newark.
7.  **EIA-861**: A 22-file raw directory containing national utility surveys on demand response, dynamic pricing, net metering, customer counts, sales, and service territories.
8.  **EIA-861M (Sales & Revenue)**: State-level monthly sales, revenue, and pricing tables for monthly benchmarking.
9.  **Utility Tariffs**: Dynacally synced database containing OpenEI Utility Rate Database (URDB) details for local utilities.
10. **OpenEI Utility Service Territories**: ZIP code mapping sheets connecting geographical zones to specific operating utilities.
11. **EIA-930 Hourly Grid Operations**: Hourly grid load, net generation, subregion flow, and generation mix (by fuel type) from PJM balancing authority.
12. **PJM Hourly LMP Data**: Hourly wholesale market prices (Locational Marginal Price) including energy, congestion, and loss components.

---

## Step 3: Dataset Gap Analysis

Evaluating the data requirements of each of the 16 features reveals the following sufficiency gaps:

| Feature | Sufficiency of Existing Datasets | Gaps & Missing Data Elements |
| :--- | :--- | :--- |
| **1. Utility Intelligence** | **Sufficient** | None. EIA-861 provides comprehensive coverage of utility details. |
| **2. Bill Analysis** | **Partially Sufficient** | Lacks actual multi-tier volumetric step tariff schedules. Currently relies on static rates or simplified averages, ignoring block pricing. |
| **3. Bill Statement Extraction** | **Sufficient** | Ingests raw OCR string data directly; no external database gap exists here. |
| **4. Rate Plan Comparison** | **Partially Sufficient** | Lacks dynamic, real-time supplier offers (uses a static synthetic parquet file of plans). |
| **5. Benchmarking** | **Sufficient** | EIA state-level and municipal aggregates are adequate for regional comparison. |
| **6. Geo Analytics** | **Sufficient** | Covered by `state_monthly_prices` and shapefiles. |
| **7. Forecasting** | **Partially Sufficient** | Missing forward-looking weather forecasts (relies on historical averages). |
| **8. AI Insights** | **Insufficient** | Lacks customer building details (building type, insulation, square footage) and smart meter data, which prevents the AI from explaining *why* consumption changes. |
| **9. Causal Analysis** | **Sufficient** | Covered by daily weather, PJM LMP, and billing data in a DML framework. |
| **10. Utility Tariff Analysis** | **Partially Sufficient** | OpenEI URDB is synced, but actual retail rate structures (like customer fixed costs, distribution tiers) are hardcoded in the routes. |
| **11. Electricity Demand Forecasting** | **Sufficient** | PJM daily load data and Open-Meteo weather history are sufficient. |
| **12. Electricity Price Forecasting** | **Insufficient** | Missing forward-looking fuel indices (e.g. natural gas futures) and transmission congestion forecasts. |
| **13. Customer Consumption Analytics** | **Partially Sufficient** | Customer billing is monthly. **Cannot perform daily or hourly consumption diagnostics** without AMI interval data. |
| **14. Energy Efficiency Recommendations**| **Insufficient** | Missing building characteristics (insulation, HVAC types), ENERGY STAR appliance baselines, and a directory of local rebate/incentive programs. |
| **15. Utility Service Territory Analysis** | **Sufficient** | OpenEI ZIP mapping provides complete coverage. |
| **16. Wholesale vs Retail Price Analysis** | **Sufficient** | Covered by PJM market LMP files and BGS auction rates. |

---

## Step 4: Recommend Additional Datasets

To resolve these gaps and enable production-grade AI recommendations, we recommend integrating the following datasets:

### 1. Electricity Market
*   **PJM Load Forecast**: 24-hour and 7-day ahead grid demand forecasts issued by the grid operator.
*   **PJM Fuel Mix / Generation Mix**: Near real-time and historical wholesale fuel source composition (nuclear, coal, gas, wind, solar) to estimate the carbon intensity of grid power.
*   **Natural Gas Futures (Henry Hub)**: Fuel cost futures indices to forecast retail and wholesale price adjustments.

### 2. Utility
*   **Residential Time-of-Use (TOU) Rates & Schedules**: Active rate schedules containing peak, off-peak, and shoulder windows for all regional utilities.
*   **State Solar Incentives & Solar Renewable Energy Certificates (SRECs)**: State-level solar subsidy directories, net-metering caps, and solar credit pricing.
*   **Low-Income Home Energy Assistance Program (LIHEAP) & USF (Universal Service Fund)**: Eligibility thresholds and credit amounts for customer assistance programs.

### 3. Weather
*   **Forward Weather Forecast Grid**: 7-day and 30-day temperature, wind, and solar radiation forecast grids (Open-Meteo or NOAA GFS).
*   **Relative Humidity and Wind Speed**: Weather variables needed to calculate the heat index and wind chill, refining the cooling/heating degree day estimates.

### 4. Buildings
*   **Building Characteristics Archetypes (NREL)**: Baseline indicators of building insulation, envelope performance, and HVAC equipment configurations.
*   **Home Energy Scores / Building Age / Building Type**: Municipal building attributes to enable regional building benchmarking.

### 5. Renewable Energy
*   **NREL Solar PVWatts / Solar Potential**: Rooftop solar generation potential based on geographical coordinates and azimuth vectors.
*   **Community Solar Projects Directory**: List of active local community solar projects, subscriber fees, and discount rates.

### 6. Demographics
*   **US Census Demographics (ACS)**: Zip-level indicators of median household income, population density, and housing structure types.

### 7. Energy Efficiency
*   **ENERGY STAR Appliance Benchmarks**: Standard consumption benchmarks for major household appliances (refrigerators, washers, heat pumps).

### 8. Grid
*   **SAIDI/SAIFI Reliability Indices**: Grid outage duration and frequency metrics per utility.

### 9. AI
*   **AMI Smart Meter Interval Data**: 15-minute or hourly customer consumption profiles to detect peak usage times and schedule appliance runs.

---

## Step 5: Prioritize Missing Datasets

The recommended datasets are ranked below by Priority, Implementation Difficulty, Expected Impact, and Data Availability:

| Dataset Name | Priority | Difficulty | Expected Impact | Availability |
| :--- | :--- | :--- | :--- | :--- |
| **AMI Smart Meter Interval Data** | **Critical** | Hard | High | Utility / Restricted |
| **Weather Forecast Grid (7-Day / 30-Day)**| **Critical** | Easy | High | Public (Open-Meteo) |
| **Residential TOU Rate Schedules** | **High** | Medium | High | Public (OpenEI / Utility) |
| **NREL PVWatts Solar Potential** | **High** | Easy | High | Public (NREL API) |
| **PJM Load Forecast** | **High** | Easy | Medium | Public (PJM API) |
| **Census Demographics (ACS)** | **Medium** | Easy | Medium | Public (Census API) |
| **Building Characteristics Archetypes** | **Medium** | Hard | High | Public (NREL / DOE) |
| **LIHEAP & USF Program Eligibility** | **Medium** | Easy | Medium | Public (State BPU) |
| **Natural Gas Futures (Henry Hub)** | **Medium** | Easy | Medium | Paid / Public API |
| **ENERGY STAR Benchmarks** | **Low** | Easy | Low | Public (DOE) |
| **SAIDI/SAIFI Reliability Indices** | **Low** | Easy | Low | Public (EIA / BPU) |

---

## Step 6: Produce a Final Matrix

The following matrix connects the application's target features to existing datasets, missing datasets, and integration priorities:

| Feature | Existing Dataset(s) | Missing Dataset(s) | Priority | Impact | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Utility Intelligence** | EIA-861 | None | Low | Low | Existing survey coverage is sufficient. |
| **Bill Analysis** | `billing.parquet` | TOU Rate Schedules | **High** | High | Customer bills cannot be properly modeled without active tariff structures. |
| **Bill Extraction** | MES / OCR Text | None | Low | Low | Operates on direct user text uploads. |
| **Rate Plan Comparison**| `retail_plans.parquet` | TOU Schedules, SREC Prices | **High** | High | Active supplier plans require real utility tariff rules for comparison. |
| **Benchmarking** | `state_benchmark` | Census Demographics, Building Age | Medium | Medium | Allows comparing usage against similar household types. |
| **Geo Analytics** | `state_monthly_prices` | None | Low | Low | Covered by monthly state price tables. |
| **Forecasting** | `billing.parquet`, NOAA | Weather Forecast Grids | **Critical** | High | Predictive billing requires forward weather forecasts, not historical averages. |
| **AI Insights** | NOAA, `billing.parquet` | Building Archetypes, AMI Data | **High** | High | Explaining changes requires knowing building systems and peak usage. |
| **Causal Analysis** | NOAA, PJM LMP, billing | Humidity, Wind Speed | Medium | Low | Controls for refined wind chill and heat index variables. |
| **Utility Tariff Analysis**| `pseg_rate_history` | TOU Rate Schedules | **High** | High | Crucial to represent tiered pricing structures. |
| **Demand Forecasting** | `daily_subba_demand` | PJM Load Forecast | **High** | Medium | Operator forecasts improve machine learning ensembles. |
| **Price Forecasting** | PJM LMP | Gas Futures (Henry Hub) | Medium | Medium | Energy costs are strongly correlated with natural gas prices. |
| **Consumption Analytics**| `billing.parquet` | AMI Smart Meter Interval Data | **Critical** | High | Daily/hourly interval data is required to identify peak load times. |
| **Energy Recommendations**| NOAA, `billing.parquet` | Building insulation details, local program directories | **High** | High | Prevents making generic recommendations (like "insulate windows") in favor of specific payback calculations. |
| **Service Territories** | OpenEI ZIP mappings | None | Low | Low | OpenEI provides sufficient ZIP mappings. |
| **Wholesale vs Retail** | BGS, PJM LMP | PJM Fuel Mix | Medium | Medium | Quantifies local carbon offset spreads. |

---

## Step 7: Overall Assessment

Evaluating the backend code, models, and current data pipelines yields the following assessment:

### 1. Data Completeness Score: 60%
*   *Justification*: The core macro-level dataset is complete (EIA pricing, NOAA weather, PJM LMP parquet, OpenEI ZIP mapping). However, we completely lack the micro-level customer and building datasets (smart meter intervals, tariff rules, and building configurations) required for consumer-facing decision logic.

### 2. Feature Completeness Score: 70%
*   *Justification*: Core analytical dashboards, ensembled grid forecasting models, and DML causal regressions are written. However, tariff-comparison engines, customized energy audit scripts, solar sizing models, and real-time supplier comparison tables are stubbed, missing, or simplified.

### 3. AI Readiness Score: 45%
*   *Justification*: The OCR bill analysis uses local LLMs (Qwen), and the causal inference model uses Gradient Boosted residuals. However, without customer building features and AMI interval data, the AI cannot generate personalized energy saving recommendations.

### 4. Forecasting Readiness Score: 80%
*   *Justification*: The ensembled grid demand forecaster (Prophet + SARIMA) works well. The score is held back by the lack of customer-level cost forecasting and forward-looking price forecasting models.

### 5. Benchmarking Readiness Score: 90%
*   *Justification*: Benchmarking uses EIA state monthly, annual, and municipal aggregates, which provides complete state-level rankings and municipal energy trendlines.

### 6. Bill Analysis Readiness Score: 85%
*   *Justification*: Deterministic bill breakdowns and OCR work correctly. The score is held back by the fact that rates are assumed to be flat monthly averages, ignoring active Time-of-Use (TOU) or multi-tiered block rate tariffs.

---

## Step 8: Roadmap

We propose a three-phase data enrichment roadmap to guide the platform towards production-level decision intelligence:

```mermaid
gantt
    title ElectricAI Data Enrichment Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Essential
    Weather Forecast Grid Integration :active, p1_1, 2026-07-10, 2026-07-20
    TOU Rate Schedule Integration     :active, p1_2, 2026-07-21, 2026-08-05
    section Phase 2: High-Value
    NREL PVWatts Integration          :ordered, p2_1, 2026-08-06, 2026-08-20
    PJM Load Forecast & Gas Futures    :ordered, p2_2, 2026-08-21, 2026-09-05
    Census Demographics Integration    :ordered, p2_3, 2026-09-06, 2026-09-15
    section Phase 3: Advanced
    AMI Interval Data Integration     :ordered, p3_1, 2026-09-16, 2026-10-15
    Building Archetypes & Efficiency   :ordered, p3_2, 2026-10-16, 2026-10-31
```

### Phase 1: Essential Datasets (Pre-Deployment)
Focuses on securing the datasets required to transition the core billing and forecasting engines from synthetic fallbacks to real-world operation:

1.  **Weather Forecast Grid**
    *   *Why Needed*: Replaces static temperature assumptions with 7-day and 30-day forecast grids to calculate projected heating (HDD) and cooling (CDD) degree days, feeding directly into the billing forecaster.
    *   *Features Supported*: Forecasting, What-If Simulations.
    *   *Official Source*: NOAA GFS / Open-Meteo Forecast API.
    *   *Update Frequency*: Daily.
2.  **Utility Time-of-Use (TOU) Rate Schedules**
    *   *Why Needed*: Allows modeling the complex peak, off-peak, and shoulder billing rates of regional utilities, resolving the flat-rate limitation of the bill analysis engine.
    *   *Features Supported*: Bill Analysis, Rate Plan Comparison, Tariff Analysis.
    *   *Official Source*: OpenEI Utility Rate Database (URDB) / Utility Tariff filings.
    *   *Update Frequency*: Annually.

### Phase 2: High-Value Datasets (Enhanced Recommendations)
Enhances the accuracy of the ensembled demand forecaster and builds basic solar/demand response simulators:

1.  **NREL PVWatts Solar Potential**
    *   *Why Needed*: Uses roof tilt, azimuth, and local solar irradiance parameters to simulate rooftop solar generation potential and estimate net metering offsets.
    *   *Features Supported*: Rate Plan Comparison, Energy Efficiency Recommendations.
    *   *Official Source*: NREL PVWatts API.
    *   *Update Frequency*: Annually (for local solar indexes).
2.  **PJM Load Forecast**
    *   *Why Needed*: Adds PJM's official load predictions as an exogenous feature to the demand forecasting ensemble, reducing forecast error (MAPE).
    *   *Features Supported*: Electricity Demand Forecasting.
    *   *Official Source*: PJM Data Miner API.
    *   *Update Frequency*: Hourly.
3.  **Natural Gas Futures (Henry Hub)**
    *   *Why Needed*: Captures forward pricing trends for natural gas, which acts as a primary fuel source for marginal generation units in PJM, improving wholesale price forecasts.
    *   *Features Supported*: Electricity Price Forecasting.
    *   *Official Source*: CME Group / NASDAQ API.
    *   *Update Frequency*: Daily.
4.  **Census Demographics (ACS)**
    *   *Why Needed*: Provides local variables (such as household income and average household size) to contextualize benchmarking (e.g. comparing a customer's usage to neighbors with similar income levels).
    *   *Features Supported*: Benchmarking.
    *   *Official Source*: US Census Bureau API.
    *   *Update Frequency*: Annually.

### Phase 3: Advanced Datasets (Predictive & Personalized Intelligence)
Enables predictive analytics, demand response suggestions, and building-level utility intelligence:

1.  **AMI Smart Meter Interval Data**
    *   *Why Needed*: Provides 15-minute or hourly customer usage profiles to isolate specific appliance load signatures (base load vs. HVAC cooling cycles) and identify peak demand reduction opportunities.
    *   *Features Supported*: Customer Consumption Analytics, AI Insights, Energy Efficiency Recommendations.
    *   *Official Source*: Utility customer portal Green Button XML/JSON API.
    *   *Update Frequency*: Daily (with 24-hour lag).
2.  **Building Characteristics Archetypes (ResStock / ComStock)**
    *   *Why Needed*: Models typical thermal performance, HVAC efficiency curves, and insulation characteristics of homes based on building age and type to estimate the financial payback of retrofits.
    *   *Features Supported*: Energy Efficiency Recommendations, AI Insights.
    *   *Official Source*: National Renewable Energy Laboratory (NREL).
    *   *Update Frequency*: Annually.
3.  **Low-Income Home Energy Assistance Program (LIHEAP) & USF Program Details**
    *   *Why Needed*: Automatically screens utility accounts against income thresholds to recommend eligibility for state subsidy programs.
    *   *Features Supported*: Energy Efficiency Recommendations, AI Insights.
    *   *Official Source*: NJ Board of Public Utilities (BPU) / Department of Community Affairs.
    *   *Update Frequency*: Annually.
