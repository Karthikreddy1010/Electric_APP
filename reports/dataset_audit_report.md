# Enterprise Dataset Audit, Utilization Analysis & Architecture Validation

## Executive Project Overview

This document contains a comprehensive, rigorous dataset audit, utilization analysis, and architecture validation for the **ElectricAI Energy Cost Platform**. It inventories 24 core datasets (spread across 31 raw files and directories), maps them to report tabs and backend models, checks data quality, identifies gaps, and validates ML readiness.

---
## Phase 1 — Dataset Inventory

### Aggregated_Community-Scale_Utility_Energy_Data.xlsx
- **Source**: NJ Board of Public Utilities (BPU)
- **File Type**: XLSX
- **File Size**: 971.47 KB
- **Number of Rows**: 4506
- **Number of Columns**: 16
- **Column Names**: Municipality, County, Muni/County, Year, Electric Utility, Residential Electricity, Commercial Electricity, Industrial Electricity, Street Lighting Electricity, Total Electricity (kWh), Natural Gas Utility, Residential Natural Gas, Commercial Natural Gas, Industrial Natural Gas, Street Lighting Natural Gas, Total Natural Gas (Therms)
- **Primary Key(s)**: Muni/County + Electric Utility + Year
- **Foreign Key(s)**: None
- **Time Coverage**: 2011-2022
- **Geographic Coverage**: New Jersey (Municipalities)
- **Granularity**: Municipal Annual total consumption
- **Update Frequency**: Annually
- **Data Types**: {"Municipality": "object", "County": "object", "Muni/County": "object", "Year": "int64", "Electric Utility": "object", "Residential Electricity": "object", "Commercial Electricity": "object", "Industrial Electricity": "object", "Street Lighting Electricity": "object", "Total Electricity (kWh)": "object", "Natural Gas Utility": "object", "Residential Natural Gas": "object", "Commercial Natural Gas": "object", "Industrial Natural Gas": "object", "Street Lighting Natural Gas": "object", "Total Natural Gas (Therms)": "object"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **92/100**

### air_temp.csv
- **Source**: NOAA GHCND station
- **File Type**: CSV
- **File Size**: 101.03 KB
- **Number of Rows**: 1231
- **Number of Columns**: 6
- **Column Names**: STATION, NAME, DATE, TAVG, TMAX, TMIN
- **Primary Key(s)**: DATE
- **Foreign Key(s)**: None
- **Time Coverage**: 2021-2024
- **Geographic Coverage**: Local Newark Station (NJ)
- **Granularity**: Daily (TAVG, TMAX, TMIN)
- **Update Frequency**: Daily
- **Data Types**: {"STATION": "object", "NAME": "object", "DATE": "object", "TAVG": "float64", "TMAX": "int64", "TMIN": "int64"}
- **Missing Values**: 1231 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **75/100**

### Avg_price_Electricity.xlsx
- **Source**: EIA Form 861M
- **File Type**: XLSX
- **File Size**: 16.48 KB
- **Number of Rows**: 50
- **Number of Columns**: 6
- **Column Names**: Table 5.3. Average Price of Electricity to Ultimate Customers:, Unnamed: 1, Unnamed: 2, Unnamed: 3, Unnamed: 4, Unnamed: 5
- **Primary Key(s)**: Month + State Division
- **Foreign Key(s)**: None
- **Time Coverage**: 2022-2024
- **Geographic Coverage**: National (Census Divisions)
- **Granularity**: Monthly average cents/kWh by sector
- **Update Frequency**: Monthly
- **Data Types**: {"Table 5.3. Average Price of Electricity to Ultimate Customers:": "object", "Unnamed: 1": "object", "Unnamed: 2": "object", "Unnamed: 3": "object", "Unnamed: 4": "object", "Unnamed: 5": "object"}
- **Missing Values**: 40 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **60/100**

### BGS Auction historical rates.xlsx
- **Source**: NJ Board of Public Utilities
- **File Type**: XLSX
- **File Size**: 18.05 KB
- **Number of Rows**: 108
- **Number of Columns**: 4
- **Column Names**: Year, EDC, Auction / Product Type, Final Price ( /¢/kWh)
- **Primary Key(s)**: Year + EDC + Auction/Product Type
- **Foreign Key(s)**: None
- **Time Coverage**: 2002-2024
- **Geographic Coverage**: New Jersey utilities (PSE&G, JCP&L, ACE, RECO)
- **Granularity**: Annual final auction prices
- **Update Frequency**: Annually
- **Data Types**: {"Year": "int64", "EDC": "object", "Auction / Product Type": "object", "Final Price ( /\u00a2/kWh)": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **95/100**

### billing.csv
- **Source**: ElectricAI Ingestion / User Bills
- **File Type**: CSV
- **File Size**: 10.88 KB
- **Number of Rows**: 84
- **Number of Columns**: 19
- **Column Names**: date, usage_kwh, bgs_rate, bgs_cost, transmission_rate, transmission_cost, distribution_rate, distribution_cost, sbc_rate, sbc_cost, nug_rate, nug_cost, dr_credit, subtotal, sales_tax, total_bill, utility, state, customer_class
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: Local Customer Facilities
- **Granularity**: Monthly billing cycles
- **Update Frequency**: Monthly
- **Data Types**: {"date": "object", "usage_kwh": "float64", "bgs_rate": "float64", "bgs_cost": "float64", "transmission_rate": "float64", "transmission_cost": "float64", "distribution_rate": "float64", "distribution_cost": "float64", "sbc_rate": "float64", "sbc_cost": "float64", "nug_rate": "float64", "nug_cost": "float64", "dr_credit": "float64", "subtotal": "float64", "sales_tax": "float64", "total_bill": "float64", "utility": "object", "state": "object", "customer_class": "object"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **98/100**

### billing.parquet
- **Source**: ElectricAI Ingestion / User Bills
- **File Type**: PARQUET
- **File Size**: 20.24 KB
- **Number of Rows**: 84
- **Number of Columns**: 19
- **Column Names**: date, usage_kwh, bgs_rate, bgs_cost, transmission_rate, transmission_cost, distribution_rate, distribution_cost, sbc_rate, sbc_cost, nug_rate, nug_cost, dr_credit, subtotal, sales_tax, total_bill, utility, state, customer_class
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: Local Customer Facilities
- **Granularity**: Monthly billing cycles
- **Update Frequency**: Monthly
- **Data Types**: {"date": "datetime64[ns]", "usage_kwh": "float64", "bgs_rate": "float64", "bgs_cost": "float64", "transmission_rate": "float64", "transmission_cost": "float64", "distribution_rate": "float64", "distribution_cost": "float64", "sbc_rate": "float64", "sbc_cost": "float64", "nug_rate": "float64", "nug_cost": "float64", "dr_credit": "float64", "subtotal": "float64", "sales_tax": "float64", "total_bill": "float64", "utility": "object", "state": "object", "customer_class": "object"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### census_demographics_2022_cache.csv
- **Source**: US Census Bureau (ACS 5-Year Estim.)
- **File Type**: CSV
- **File Size**: 0.85 KB
- **Number of Rows**: 21
- **Number of Columns**: 6
- **Column Names**: county_fips, county_name, median_income, population, housing_units, year
- **Primary Key(s)**: county_fips
- **Foreign Key(s)**: None
- **Time Coverage**: 2022
- **Geographic Coverage**: New Jersey (Counties)
- **Granularity**: County annual averages
- **Update Frequency**: Every 5 years
- **Data Types**: {"county_fips": "int64", "county_name": "object", "median_income": "int64", "population": "int64", "housing_units": "int64", "year": "int64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **98/100**

### cpi_monthly.csv
- **Source**: US Bureau of Labor Statistics (BLS)
- **File Type**: CSV
- **File Size**: 1.79 KB
- **Number of Rows**: 120
- **Number of Columns**: 3
- **Column Names**: year, month, cpi
- **Primary Key(s)**: year + month
- **Foreign Key(s)**: None
- **Time Coverage**: 2014-2024
- **Geographic Coverage**: National
- **Granularity**: Monthly indices
- **Update Frequency**: Monthly
- **Data Types**: {"year": "int64", "month": "int64", "cpi": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### cpi_yearly.csv
- **Source**: US Bureau of Labor Statistics (BLS)
- **File Type**: CSV
- **File Size**: 0.58 KB
- **Number of Rows**: 10
- **Number of Columns**: 4
- **Column Names**: year, cpi_annual_avg, deflator, inflation_pct
- **Primary Key(s)**: year
- **Foreign Key(s)**: None
- **Time Coverage**: 2014-2023
- **Geographic Coverage**: National
- **Granularity**: Annual avg & deflator
- **Update Frequency**: Annually
- **Data Types**: {"year": "int64", "cpi_annual_avg": "float64", "deflator": "float64", "inflation_pct": "float64"}
- **Missing Values**: 1 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **95/100**

### da_hrl_lmps(1).csv
- **Source**: PJM Interconnection (RTO)
- **File Type**: CSV
- **File Size**: 42563.22 KB
- **Number of Rows**: 346800
- **Number of Columns**: 14
- **Column Names**: datetime_beginning_utc, datetime_beginning_ept, pnode_id, pnode_name, voltage, equipment, type, zone, system_energy_price_da, total_lmp_da, congestion_price_da, marginal_loss_price_da, row_is_current, version_nbr
- **Primary Key(s)**: datetime_beginning_utc + pnode_id
- **Foreign Key(s)**: None
- **Time Coverage**: 2020-2024
- **Geographic Coverage**: PJM Nodes (PSEG, JC, AE, PL etc.)
- **Granularity**: Hourly Day-Ahead LMPs
- **Update Frequency**: Hourly
- **Data Types**: {"datetime_beginning_utc": "object", "datetime_beginning_ept": "object", "pnode_id": "int64", "pnode_name": "object", "voltage": "object", "equipment": "object", "type": "object", "zone": "object", "system_energy_price_da": "float64", "total_lmp_da": "float64", "congestion_price_da": "float64", "marginal_loss_price_da": "float64", "row_is_current": "bool", "version_nbr": "int64"}
- **Missing Values**: 27744 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **90/100**

### EIA_861M_sales_revenue.xlsx
- **Source**: EIA Form 861M
- **File Type**: XLSX
- **File Size**: 2183.85 KB
- **Number of Rows**: 9999
- **Number of Columns**: 24
- **Column Names**: Unnamed: 0, Unnamed: 1, Unnamed: 2, Unnamed: 3, RESIDENTIAL, Unnamed: 5, Unnamed: 6, Unnamed: 7, COMMERCIAL, Unnamed: 9, Unnamed: 10, Unnamed: 11, INDUSTRIAL, Unnamed: 13, Unnamed: 14, Unnamed: 15, TRANSPORTATION, Unnamed: 17, Unnamed: 18, Unnamed: 19, TOTAL, Unnamed: 21, Unnamed: 22, Unnamed: 23
- **Primary Key(s)**: Unnamed: 0 + Unnamed: 1 (State + Sector)
- **Foreign Key(s)**: None
- **Time Coverage**: 2021-2024
- **Geographic Coverage**: All 50 US States
- **Granularity**: Monthly state totals by sector
- **Update Frequency**: Monthly
- **Data Types**: {"Unnamed: 0": "object", "Unnamed: 1": "object", "Unnamed: 2": "object", "Unnamed: 3": "object", "RESIDENTIAL": "object", "Unnamed: 5": "object", "Unnamed: 6": "object", "Unnamed: 7": "object", "COMMERCIAL": "object", "Unnamed: 9": "object", "Unnamed: 10": "object", "Unnamed: 11": "object", "INDUSTRIAL": "object", "Unnamed: 13": "object", "Unnamed: 14": "object", "Unnamed: 15": "object", "TRANSPORTATION": "object", "Unnamed: 17": "object", "Unnamed: 18": "object", "Unnamed: 19": "object", "TOTAL": "object", "Unnamed: 21": "object", "Unnamed: 22": "object", "Unnamed: 23": "object"}
- **Missing Values**: 27 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **50/100**

### eia_pjm_daily_demand.csv
- **Source**: EIA API v2 / PJM
- **File Type**: CSV
- **File Size**: 287.50 KB
- **Number of Rows**: 10760
- **Number of Columns**: 4
- **Column Names**: period, subba, value, parent
- **Primary Key(s)**: period + subba
- **Foreign Key(s)**: None
- **Time Coverage**: 2020-2024
- **Geographic Coverage**: PJM Sub-Balancing Areas (AE, JC, PS, RECO)
- **Granularity**: Daily sub-BA demand (MW)
- **Update Frequency**: Daily
- **Data Types**: {"period": "object", "subba": "object", "value": "float64", "parent": "object"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### eia_residential_Avg_electricity_prices.csv
- **Source**: EIA Form 861M
- **File Type**: CSV
- **File Size**: 380.45 KB
- **Number of Rows**: 13260
- **Number of Columns**: 4
- **Column Names**: Date, State, State_Name, Price_cents_per_kWh
- **Primary Key(s)**: Date + State
- **Foreign Key(s)**: None
- **Time Coverage**: 2005-2024
- **Geographic Coverage**: All 50 US States
- **Granularity**: Monthly residential average rate
- **Update Frequency**: Monthly
- **Data Types**: {"Date": "object", "State": "object", "State_Name": "object", "Price_cents_per_kWh": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 13260, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv
- **Source**: NJ Board of Public Utilities
- **File Type**: CSV
- **File Size**: 3706.97 KB
- **Number of Rows**: 30498
- **Number of Columns**: 11
- **Column Names**: OBJECTID, Municipality, County, GNIS, Utility, Year, Sector, Electricity (kWh), Natural Gas (Therms), Energy Type, GLOBALID
- **Primary Key(s)**: OBJECTID
- **Foreign Key(s)**: None
- **Time Coverage**: 2015-2021
- **Geographic Coverage**: New Jersey (Municipalities)
- **Granularity**: Annual municipal electric and gas usage by sector
- **Update Frequency**: Annually
- **Data Types**: {"OBJECTID": "int64", "Municipality": "object", "County": "object", "GNIS": "int64", "Utility": "object", "Year": "int64", "Sector": "object", "Electricity (kWh)": "float64", "Natural Gas (Therms)": "float64", "Energy Type": "object", "GLOBALID": "object"}
- **Missing Values**: 27114 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **85/100**

### nj-rs-Average_retail_price_of_electricity_monthly.csv
- **Source**: EIA Form 861M
- **File Type**: CSV
- **File Size**: 4.15 KB
- **Number of Rows**: 303
- **Number of Columns**: 2
- **Column Names**: Month, New Jersey : residential cents per kilowatthour
- **Primary Key(s)**: Month
- **Foreign Key(s)**: None
- **Time Coverage**: 1999-2024
- **Geographic Coverage**: New Jersey
- **Granularity**: Monthly residential cents/kWh
- **Update Frequency**: Monthly
- **Data Types**: {"Month": "object", "New Jersey : residential cents per kilowatthour": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 303, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **90/100**

### OpenEI_IOU_Utility_ZIP_Mapping_2024.csv
- **Source**: Open Energy Information (OpenEI)
- **File Type**: CSV
- **File Size**: 5846.46 KB
- **Number of Rows**: 49004
- **Number of Columns**: 9
- **Column Names**: zip, eiaid, utility_name, state, service_type, ownership, comm_rate, ind_rate, res_rate
- **Primary Key(s)**: zip + eiaid
- **Foreign Key(s)**: eia_utility_id
- **Time Coverage**: 2024
- **Geographic Coverage**: National (All US ZIP codes)
- **Granularity**: ZIP code level mappings
- **Update Frequency**: Annually
- **Data Types**: {"zip": "int64", "eiaid": "int64", "utility_name": "object", "state": "object", "service_type": "object", "ownership": "object", "comm_rate": "float64", "ind_rate": "float64", "res_rate": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv
- **Source**: Open Energy Information (OpenEI)
- **File Type**: CSV
- **File Size**: 3308.03 KB
- **Number of Rows**: 28009
- **Number of Columns**: 9
- **Column Names**: zip, eiaid, utility_name, state, service_type, ownership, comm_rate, ind_rate, res_rate
- **Primary Key(s)**: zip + eiaid
- **Foreign Key(s)**: eia_utility_id
- **Time Coverage**: 2024
- **Geographic Coverage**: National (All US ZIP codes)
- **Granularity**: ZIP code level mappings
- **Update Frequency**: Annually
- **Data Types**: {"zip": "int64", "eiaid": "int64", "utility_name": "object", "state": "object", "service_type": "object", "ownership": "object", "comm_rate": "float64", "ind_rate": "float64", "res_rate": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 4
- **Overall Data Quality Score**: **98/100**

### pjm_market.csv
- **Source**: PJM Interconnection (RTO)
- **File Type**: CSV
- **File Size**: 101.51 KB
- **Number of Rows**: 2557
- **Number of Columns**: 6
- **Column Names**: date, zone, lmp_da, lmp_rt, capacity_price, congestion
- **Primary Key(s)**: date + zone
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: PSEG Zone (NJ)
- **Granularity**: Daily averages
- **Update Frequency**: Daily
- **Data Types**: {"date": "object", "zone": "object", "lmp_da": "float64", "lmp_rt": "float64", "capacity_price": "float64", "congestion": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### pjm_market.parquet
- **Source**: PJM Interconnection (RTO)
- **File Type**: PARQUET
- **File Size**: 68.04 KB
- **Number of Rows**: 2557
- **Number of Columns**: 6
- **Column Names**: date, zone, lmp_da, lmp_rt, capacity_price, congestion
- **Primary Key(s)**: date + zone
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: PSEG Zone (NJ)
- **Granularity**: Daily averages
- **Update Frequency**: Daily
- **Data Types**: {"date": "datetime64[ns]", "zone": "object", "lmp_da": "float64", "lmp_rt": "float64", "capacity_price": "float64", "congestion": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### pjm_market_pseg_cache.csv
- **Source**: PJM Interconnection (RTO)
- **File Type**: CSV
- **File Size**: 108.93 KB
- **Number of Rows**: 2745
- **Number of Columns**: 6
- **Column Names**: date, zone, lmp_da, lmp_rt, capacity_price, congestion
- **Primary Key(s)**: date + zone
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: PSEG Zone (NJ)
- **Granularity**: Daily averages
- **Update Frequency**: Daily
- **Data Types**: {"date": "object", "zone": "object", "lmp_da": "float64", "lmp_rt": "float64", "capacity_price": "float64", "congestion": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### PSEG_Component_Distribution_Rates.csv
- **Source**: PSE&G Rate Filings / NJ BPU
- **File Type**: CSV
- **File Size**: 27.82 KB
- **Number of Rows**: 282
- **Number of Columns**: 6
- **Column Names**: Tariff_Version, Year, Rate_Schedule, Component_Label, Base_Rate, With_SUT
- **Primary Key(s)**: Tariff_Version + Year + Rate_Schedule + Component_Label
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: PSE&G service territory (NJ)
- **Granularity**: Component rates
- **Update Frequency**: Periodically
- **Data Types**: {"Tariff_Version": "object", "Year": "int64", "Rate_Schedule": "object", "Component_Label": "object", "Base_Rate": "float64", "With_SUT": "float64"}
- **Missing Values**: 59 cells
- **Duplicate Records**: 31 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **90/100**

### pseg_rate_history.csv
- **Source**: PSE&G Rate Books
- **File Type**: CSV
- **File Size**: 77.38 KB
- **Number of Rows**: 272
- **Number of Columns**: 23
- **Column Names**: date, year, month, season, tier, distribution_rate, riders_adj_sbc_nug_etc, total_delivery_rate, fixed_charge_per_month, bgs_rate, bgs_transmission_adj, total_bgs_rate, total_rate_per_kwh, usage_kwh, dr_credit, sales_tax_note, rs_rate_effective_from, rs_rate_effective_to, rs_source_label, bgs_rate_effective_from, bgs_rate_effective_to, bgs_source_label, data_source
- **Primary Key(s)**: date + tier + season
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: PSE&G service territory (NJ)
- **Granularity**: Monthly rate parameters
- **Update Frequency**: Monthly
- **Data Types**: {"date": "object", "year": "int64", "month": "int64", "season": "object", "tier": "object", "distribution_rate": "float64", "riders_adj_sbc_nug_etc": "float64", "total_delivery_rate": "float64", "fixed_charge_per_month": "float64", "bgs_rate": "float64", "bgs_transmission_adj": "float64", "total_bgs_rate": "float64", "total_rate_per_kwh": "float64", "usage_kwh": "float64", "dr_credit": "float64", "sales_tax_note": "object", "rs_rate_effective_from": "object", "rs_rate_effective_to": "object", "rs_source_label": "object", "bgs_rate_effective_from": "object", "bgs_rate_effective_to": "object", "bgs_source_label": "object", "data_source": "object"}
- **Missing Values**: 974 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 30, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **95/100**

### retail_plans.csv
- **Source**: NJ Power Switch Scraped Plans
- **File Type**: CSV
- **File Size**: 0.38 KB
- **Number of Rows**: 8
- **Number of Columns**: 7
- **Column Names**: provider, type, rate, term_months, etf, green_pct, volatility
- **Primary Key(s)**: provider + type + rate
- **Foreign Key(s)**: None
- **Time Coverage**: 2024 (Active)
- **Geographic Coverage**: New Jersey
- **Granularity**: Supplier plan offers
- **Update Frequency**: Daily
- **Data Types**: {"provider": "object", "type": "object", "rate": "float64", "term_months": "int64", "etf": "int64", "green_pct": "int64", "volatility": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### retail_plans.parquet
- **Source**: NJ Power Switch Scraped Plans
- **File Type**: PARQUET
- **File Size**: 4.56 KB
- **Number of Rows**: 8
- **Number of Columns**: 7
- **Column Names**: provider, type, rate, term_months, etf, green_pct, volatility
- **Primary Key(s)**: provider + type + rate
- **Foreign Key(s)**: None
- **Time Coverage**: 2024 (Active)
- **Geographic Coverage**: New Jersey
- **Granularity**: Supplier plan offers
- **Update Frequency**: Daily
- **Data Types**: {"provider": "object", "type": "object", "rate": "float64", "term_months": "int64", "etf": "int64", "green_pct": "int64", "volatility": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### salesofelectricity.xlsx
- **Source**: EIA Form 861M
- **File Type**: XLSX
- **File Size**: 18.96 KB
- **Number of Rows**: 66
- **Number of Columns**: 11
- **Column Names**: Table 5.4.A. Sales of Electricity to Ultimate Customers by End-Use Sector,, Unnamed: 1, Unnamed: 2, Unnamed: 3, Unnamed: 4, Unnamed: 5, Unnamed: 6, Unnamed: 7, Unnamed: 8, Unnamed: 9, Unnamed: 10
- **Primary Key(s)**: Table Row ID
- **Foreign Key(s)**: None
- **Time Coverage**: 2022-2024
- **Geographic Coverage**: National (Census Divisions)
- **Granularity**: Monthly totals
- **Update Frequency**: Monthly
- **Data Types**: {"Table 5.4.A. Sales of Electricity to Ultimate Customers by End-Use Sector,": "object", "Unnamed: 1": "object", "Unnamed: 2": "object", "Unnamed: 3": "object", "Unnamed: 4": "object", "Unnamed: 5": "object", "Unnamed: 6": "object", "Unnamed: 7": "object", "Unnamed: 8": "object", "Unnamed: 9": "object", "Unnamed: 10": "object"}
- **Missing Values**: 26 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **55/100**

### state_benchmark.csv
- **Source**: EIA Form 861M
- **File Type**: CSV
- **File Size**: 12.70 KB
- **Number of Rows**: 175
- **Number of Columns**: 12
- **Column Names**: state, state_name, year, avg_rate, avg_rate_cents, avg_bill, avg_usage_kwh, sales_mwh, region, rank, percentile, vs_national_pct
- **Primary Key(s)**: state + year
- **Foreign Key(s)**: None
- **Time Coverage**: 2020-2024
- **Geographic Coverage**: All 50 US States
- **Granularity**: Annual State Averages
- **Update Frequency**: Annually
- **Data Types**: {"state": "object", "state_name": "object", "year": "int64", "avg_rate": "float64", "avg_rate_cents": "float64", "avg_bill": "float64", "avg_usage_kwh": "int64", "sales_mwh": "float64", "region": "object", "rank": "int64", "percentile": "float64", "vs_national_pct": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 175, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### state_benchmark.parquet
- **Source**: EIA Form 861M
- **File Type**: PARQUET
- **File Size**: 12.90 KB
- **Number of Rows**: 175
- **Number of Columns**: 12
- **Column Names**: state, state_name, year, avg_rate, avg_rate_cents, avg_bill, avg_usage_kwh, sales_mwh, region, rank, percentile, vs_national_pct
- **Primary Key(s)**: state + year
- **Foreign Key(s)**: None
- **Time Coverage**: 2020-2024
- **Geographic Coverage**: All 50 US States
- **Granularity**: Annual State Averages
- **Update Frequency**: Annually
- **Data Types**: {"state": "object", "state_name": "object", "year": "int64", "avg_rate": "float64", "avg_rate_cents": "float64", "avg_bill": "float64", "avg_usage_kwh": "int64", "sales_mwh": "float64", "region": "object", "rank": "int64", "percentile": "float64", "vs_national_pct": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 175, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### weather.csv
- **Source**: NOAA weather station
- **File Type**: CSV
- **File Size**: 113.04 KB
- **Number of Rows**: 2557
- **Number of Columns**: 7
- **Column Names**: date, station, avg_temp_f, hdd, cdd, precip_in, humidity_pct
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: Newark Station (NJ)
- **Granularity**: Daily (TAVG, HDD, CDD)
- **Update Frequency**: Daily
- **Data Types**: {"date": "object", "station": "object", "avg_temp_f": "float64", "hdd": "float64", "cdd": "float64", "precip_in": "float64", "humidity_pct": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### weather.parquet
- **Source**: NOAA weather station
- **File Type**: PARQUET
- **File Size**: 46.03 KB
- **Number of Rows**: 2557
- **Number of Columns**: 7
- **Column Names**: date, station, avg_temp_f, hdd, cdd, precip_in, humidity_pct
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: Newark Station (NJ)
- **Granularity**: Daily (TAVG, HDD, CDD)
- **Update Frequency**: Daily
- **Data Types**: {"date": "datetime64[ns]", "station": "object", "avg_temp_f": "float64", "hdd": "float64", "cdd": "float64", "precip_in": "float64", "humidity_pct": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### weather_noaa_cache.csv
- **Source**: NOAA Weather Stations
- **File Type**: CSV
- **File Size**: 124.53 KB
- **Number of Rows**: 2922
- **Number of Columns**: 5
- **Column Names**: date, avg_temp_f, station_id, hdd, cdd
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2016-2024
- **Geographic Coverage**: Local station
- **Granularity**: Daily
- **Update Frequency**: Daily
- **Data Types**: {"date": "object", "avg_temp_f": "float64", "station_id": "object", "hdd": "float64", "cdd": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

### weather_openmeteo.csv
- **Source**: Open-Meteo API
- **File Type**: CSV
- **File Size**: 99.45 KB
- **Number of Rows**: 2744
- **Number of Columns**: 6
- **Column Names**: date, temp_max, temp_min, temp_avg, hdd, cdd
- **Primary Key(s)**: date
- **Foreign Key(s)**: None
- **Time Coverage**: 2018-2024
- **Geographic Coverage**: Local region
- **Granularity**: Daily max/min/avg, HDD, CDD
- **Update Frequency**: Daily
- **Data Types**: {"date": "object", "temp_max": "float64", "temp_min": "float64", "temp_avg": "float64", "hdd": "float64", "cdd": "float64"}
- **Missing Values**: 0 cells
- **Duplicate Records**: 0 rows
- **Invalid Records**: Date Errs: 0, State Errs: 0, ZIP Errs: 0
- **Overall Data Quality Score**: **100/100**

---
## Phase 2 — Dataset Classification

| Dataset Name | Category Classifications |
| :--- | :--- |
| `Aggregated_Community-Scale_Utility_Energy_Data.xlsx` | Utility, GIS, Benchmark, Historical, Reference Data |
| `air_temp.csv` | Weather, NOAA, Historical, Reference Data |
| `Avg_price_Electricity.xlsx` | EIA, Benchmark, Historical, Lookup, Reference Data |
| `BGS Auction historical rates.xlsx` | Tariffs, Historical, Pricing, Benchmark, Lookup |
| `billing.csv` | Billing, Customer, Historical, Lookup |
| `billing.parquet` | Billing, Customer, Historical, Lookup, Machine Learning |
| `census_demographics_2022_cache.csv` | Demographics, GIS, Benchmark, Reference Data |
| `cpi_monthly.csv` | Market, Pricing, Reference Data |
| `cpi_yearly.csv` | Market, Pricing, Reference Data |
| `da_hrl_lmps(1).csv` | PJM, Market, Pricing, Demand, Forecasting, Historical |
| `EIA_861M_sales_revenue.xlsx` | EIA, Benchmark, Market, Historical, Lookup |
| `eia_pjm_daily_demand.csv` | EIA, PJM, Demand, Forecasting, Historical |
| `eia_residential_Avg_electricity_prices.csv` | EIA, Benchmark, Historical, Pricing, Lookup |
| `Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv` | Utility, GIS, Benchmark, Historical, Lookup |
| `nj-rs-Average_retail_price_of_electricity_monthly.csv` | EIA, Benchmark, Historical, Pricing, Lookup |
| `OpenEI_IOU_Utility_ZIP_Mapping_2024.csv` | Utility, GIS, Benchmark, Lookup, Reference Data |
| `OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv` | Utility, GIS, Benchmark, Lookup, Reference Data |
| `pjm_market.csv` | PJM, Market, Pricing, Forecasting, Historical |
| `pjm_market.parquet` | PJM, Market, Pricing, Forecasting, Historical, Machine Learning |
| `pjm_market_pseg_cache.csv` | PJM, Market, Pricing, Forecasting, Historical, Lookup |
| `PSEG_Component_Distribution_Rates.csv` | Tariffs, Historical, Pricing, Lookup |
| `pseg_rate_history.csv` | Tariffs, Billing, Historical, Pricing, Lookup |
| `retail_plans.csv` | Tariffs, Pricing, Market, Lookup, Reference Data |
| `retail_plans.parquet` | Tariffs, Pricing, Market, Lookup, Reference Data, Machine Learning |
| `salesofelectricity.xlsx` | EIA, Benchmark, Market, Historical, Lookup |
| `state_benchmark.csv` | EIA, Benchmark, Market, Historical, Lookup |
| `state_benchmark.parquet` | EIA, Benchmark, Market, Historical, Lookup, Machine Learning |
| `weather.csv` | Weather, NOAA, Historical, Reference Data |
| `weather.parquet` | Weather, NOAA, Historical, Reference Data, Machine Learning |
| `weather_noaa_cache.csv` | Weather, NOAA, Historical, Reference Data |
| `weather_openmeteo.csv` | Weather, Historical, Reference Data |

---
## Phase 3 — Compare Against Enterprise Architecture Audit

The Enterprise Architecture Audit Report identifies specific relational schemas and models (such as `user_bills` and `tariffs`) for backend logic execution.

### Comparison Matrix
| Dataset Name | Mentioned in Report | Actually Used | Recommendation |
| :--- | :---: | :---: | :--- |
| `billing.csv` / `billing.parquet` | Yes | Yes (BillingData ORM) | Keep as core billing baseline |
| `air_temp.csv` | Yes | Yes (RawWeather ORM) | Unify weather files |
| `state_benchmark.csv` | Yes | Yes (StateBenchmark ORM)| Keep as retail pricing baseline |
| `retail_plans.csv` | Yes | Yes (Tariff ORM) | Keep as supplier plans directory |
| `da_hrl_lmps(1).csv` | Yes | Yes (EIA930Hourly ORM) | Link to hourly demand forecasting |
| `census_demographics_2022_cache.csv` | Yes | Yes (ACS demographics) | Build Energy Burden indices |
| `Avg_price_Electricity.xlsx` | Yes | No | Obsolete. Archive |
| `EIA_861M_sales_revenue.xlsx` | Yes | No | Replace with database loaded table |
| `salesofelectricity.xlsx` | Yes | No | Obsolete. Archive |

### Audit Inconsistencies & Contradictions
- **Contradiction 1**: The Enterprise Architecture Audit lists `customer_bills` and `customer_profiles` as the primary tables for billing history, but the active SaaS platform writes user-uploaded bills exclusively to `user_bills` (UUID keys) and uses `customer_bills` solely for regional geographic benchmarks. This database bifurcation is unmentioned in the reports.
- **Contradiction 2**: The audit mentions dynamic rate-tier overrides for seasonal distribution charges, but the actual database seeds in `historical_utility_tariffs` do not support time-varying schedules automatically (it assumes flat seasonal averages).

---
## Phase 4 — Compare Against Comprehensive End-to-End Analytics Report

### Alignment Matrix
| Dataset Name | Usage Status | alignment Details |
| :--- | :---: | :--- |
| `billing.parquet` | Used exactly as intended | Serves as the primary baseline for the Impact and Overview tabs. |
| `retail_plans.parquet` | Used exactly as intended | Serves as the TPS plan offering inventory in the Plans tab. |
| `eia_pjm_daily_demand.csv` | Used exactly as intended | Used for training short-term grid load forecasting models. |
| `utility_zip_lookup` | Used exactly as intended | Mapped in the Geo tab to resolve ZIP search fields. |
| `eia930_interchange` | Never integrated | Present in database, but never rendered in any dashboard visual. |
| `eia930_generation` | Partially utilized | Ingested in backend database, but omitted from front-end grid mix visuals. |
| `cpi_monthly.csv` | Available but never mentioned | BLS indices exist in raw folder, but are not exposed in the client UI. |

---
## Phase 5 — Report Tab Mapping

| Dataset Name | Overview | Bill Analysis | Impact | Forecast | Benchmark | Regional | Plans | Shared Backend |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Aggregated_Community-Scale_Utility_Energy_Data.xlsx` |  |  |  |  |  | X |  | X |
| `air_temp.csv` | X |  | X | X |  |  |  |  |
| `Avg_price_Electricity.xlsx` |  |  |  |  | X | X |  |  |
| `BGS Auction historical rates.xlsx` |  |  | X |  |  |  | X |  |
| `billing.csv` | X | X | X |  |  |  |  |  |
| `billing.parquet` | X | X | X |  |  |  |  | X |
| `census_demographics_2022_cache.csv` |  |  |  |  |  | X |  | X |
| `cpi_monthly.csv` |  |  |  |  |  |  |  | X |
| `cpi_yearly.csv` |  |  |  |  |  |  |  | X |
| `da_hrl_lmps(1).csv` |  |  |  | X |  |  |  | X |
| `EIA_861M_sales_revenue.xlsx` |  |  |  |  | X |  |  | X |
| `eia_pjm_daily_demand.csv` |  |  |  | X |  |  |  | X |
| `eia_residential_Avg_electricity_prices.csv` |  |  |  |  | X | X |  |  |
| `Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv` |  |  |  |  |  | X |  | X |
| `nj-rs-Average_retail_price_of_electricity_monthly.csv` |  |  |  |  | X | X |  |  |
| `OpenEI_IOU_Utility_ZIP_Mapping_2024.csv` | X |  |  |  |  | X |  | X |
| `OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv` | X |  |  |  |  | X |  | X |
| `pjm_market.csv` |  |  |  | X |  |  |  | X |
| `pjm_market.parquet` |  |  |  | X |  |  |  | X |
| `pjm_market_pseg_cache.csv` |  |  |  | X |  |  |  | X |
| `PSEG_Component_Distribution_Rates.csv` | X | X | X |  |  |  |  |  |
| `pseg_rate_history.csv` | X | X | X |  |  | X |  |  |
| `retail_plans.csv` |  |  |  |  |  |  | X | X |
| `retail_plans.parquet` |  |  |  |  |  |  | X | X |
| `salesofelectricity.xlsx` |  |  |  |  | X |  |  | X |
| `state_benchmark.csv` |  |  |  |  | X | X |  |  |
| `state_benchmark.parquet` |  |  |  |  | X | X |  | X |
| `weather.csv` | X |  | X | X |  |  |  |  |
| `weather.parquet` | X |  | X | X |  |  |  | X |
| `weather_noaa_cache.csv` | X |  | X | X |  |  |  |  |
| `weather_openmeteo.csv` | X |  | X | X |  |  |  |  |

---
## Phase 6 — Column-Level Analysis

Below is the target column analysis for our canonical datasets:

### `billing.parquet` (Fact)
- **Columns Used**: `date`, `usage_kwh`, `bgs_rate`, `bgs_cost`, `transmission_rate`, `distribution_rate`, `sbc_rate`, `total_bill`
- **Columns Ignored**: `nug_rate`, `nug_cost` (0 value for most periods)
- **KPI Columns**: `total_bill`, `usage_kwh`
- **Chart Columns**: `date`, `total_bill` (12-Month cost trend)
- **Simulations**: `distribution_rate`, `bgs_rate` (sliding multipliers)
- **LLM Columns**: `utility`, `customer_class` (context injection)

### `state_benchmark.parquet` (Fact)
- **Columns Used**: `state`, `avg_rate_cents`, `avg_bill`, `avg_usage_kwh`, `rank`, `percentile`
- **KPI Columns**: `rank`, `percentile` (state comparative rank)
- **Map Columns**: `state`, `avg_rate_cents` (Choropleth fill values)
- **Filters**: `region` (Census Divisions)

### `weather.parquet` (Dim)
- **Columns Used**: `date`, `avg_temp_f`, `hdd`, `cdd`
- **Forecasting/Simulations**: `hdd`, `cdd` (exogenous heating/cooling load drivers)
- **LLM Columns**: `avg_temp_f` (weather anomaly explanation)

---
## Phase 7 — Duplicate Dataset Detection

1. **weather.csv vs weather.parquet vs weather_noaa_cache.csv vs weather_openmeteo.csv**
   - *Why it exists*: Form GHCND station records, NOAA cached downloads, and Open-Meteo API outputs were stored independently during feature iterations.
   - *Recommendation*: **Merge**. Establish `weather.parquet` as the canonical source. Archive the remaining CSV files to reduce bundle size by ~325 KB.
2. **billing.csv vs billing.parquet**
   - *Why it exists*: Standard format backup.
   - *Recommendation*: **Keep Separately**. Rely on `billing.parquet` for ML/simulation vector loading, and keep `billing.csv` as a human-readable config baseline.
3. **pjm_market.csv vs pjm_market.parquet vs pjm_market_pseg_cache.csv**
   - *Why it exists*: Multi-nodal daily market caches.
   - *Recommendation*: **Archive CSVs**. Keep `pjm_market.parquet` as the canonical wholesale pricing sequence.

---
## Phase 8 — Business Value Assessment

| Dataset Name | Business | Technical | Forecasting | Simulation | ML | Viz | Benchmark | Regional | LLM | Maint | Overall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Aggregated_Community-Scale_Utility_Energy_Data.xlsx` | 85 | 75 | 40 | 50 | 30 | 90 | 85 | 95 | 60 | 30 | 80 |
| `air_temp.csv` | 80 | 85 | 90 | 90 | 85 | 70 | 60 | 50 | 50 | 40 | 85 |
| `Avg_price_Electricity.xlsx` | 50 | 40 | 30 | 30 | 20 | 65 | 70 | 60 | 40 | 20 | 55 |
| `BGS Auction historical rates.xlsx` | 90 | 85 | 75 | 85 | 70 | 80 | 85 | 85 | 75 | 30 | 85 |
| `billing.csv` | 95 | 95 | 90 | 95 | 90 | 95 | 85 | 80 | 95 | 20 | 95 |
| `billing.parquet` | 95 | 98 | 92 | 96 | 95 | 92 | 85 | 80 | 95 | 20 | 96 |
| `census_demographics_2022_cache.csv` | 75 | 70 | 20 | 40 | 50 | 80 | 85 | 90 | 70 | 10 | 75 |
| `cpi_monthly.csv` | 60 | 65 | 75 | 70 | 70 | 50 | 50 | 40 | 40 | 10 | 65 |
| `cpi_yearly.csv` | 55 | 60 | 70 | 65 | 65 | 45 | 45 | 35 | 40 | 10 | 60 |
| `da_hrl_lmps(1).csv` | 92 | 90 | 95 | 90 | 95 | 75 | 70 | 70 | 60 | 60 | 90 |
| `EIA_861M_sales_revenue.xlsx` | 55 | 40 | 30 | 30 | 20 | 70 | 75 | 65 | 50 | 40 | 60 |
| `eia_pjm_daily_demand.csv` | 92 | 90 | 96 | 85 | 95 | 80 | 70 | 75 | 60 | 30 | 90 |
| `eia_residential_Avg_electricity_prices.csv` | 88 | 85 | 75 | 70 | 80 | 90 | 95 | 90 | 80 | 20 | 90 |
| `Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv` | 80 | 70 | 30 | 45 | 30 | 85 | 85 | 90 | 65 | 30 | 80 |
| `nj-rs-Average_retail_price_of_electricity_monthly.csv` | 75 | 65 | 80 | 70 | 75 | 80 | 85 | 80 | 70 | 10 | 75 |
| `OpenEI_IOU_Utility_ZIP_Mapping_2024.csv` | 95 | 95 | 30 | 80 | 70 | 95 | 95 | 98 | 85 | 20 | 96 |
| `OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv` | 90 | 90 | 30 | 75 | 65 | 90 | 90 | 95 | 80 | 20 | 90 |
| `pjm_market.csv` | 85 | 80 | 90 | 85 | 90 | 70 | 60 | 60 | 60 | 20 | 85 |
| `pjm_market.parquet` | 88 | 85 | 92 | 88 | 92 | 75 | 60 | 60 | 60 | 20 | 86 |
| `pjm_market_pseg_cache.csv` | 80 | 80 | 90 | 85 | 90 | 70 | 60 | 60 | 60 | 20 | 80 |
| `PSEG_Component_Distribution_Rates.csv` | 92 | 90 | 70 | 95 | 75 | 85 | 80 | 80 | 85 | 30 | 90 |
| `pseg_rate_history.csv` | 95 | 92 | 80 | 96 | 85 | 85 | 85 | 85 | 90 | 20 | 94 |
| `retail_plans.csv` | 85 | 80 | 50 | 80 | 60 | 90 | 85 | 80 | 85 | 30 | 85 |
| `retail_plans.parquet` | 88 | 85 | 55 | 85 | 65 | 92 | 85 | 80 | 85 | 30 | 86 |
| `salesofelectricity.xlsx` | 45 | 35 | 20 | 20 | 10 | 60 | 65 | 55 | 40 | 20 | 50 |
| `state_benchmark.csv` | 90 | 85 | 70 | 75 | 80 | 95 | 98 | 92 | 85 | 10 | 92 |
| `state_benchmark.parquet` | 92 | 88 | 72 | 78 | 82 | 98 | 100 | 95 | 85 | 10 | 93 |
| `weather.csv` | 88 | 85 | 90 | 92 | 90 | 75 | 60 | 55 | 70 | 20 | 88 |
| `weather.parquet` | 90 | 88 | 92 | 94 | 92 | 78 | 60 | 55 | 70 | 10 | 90 |
| `weather_noaa_cache.csv` | 75 | 70 | 85 | 80 | 85 | 60 | 50 | 45 | 50 | 20 | 75 |
| `weather_openmeteo.csv` | 80 | 80 | 90 | 88 | 90 | 70 | 50 | 50 | 50 | 20 | 80 |

---
## Phase 9 — Data Quality Audit

### Major Data Quality Findings
1. **`PSEG_Component_Distribution_Rates.csv`** contains **31 duplicate records** and **59 null cells** where certain tariff versions do not specify transmission rates (uses fallback aggregation). Quality Score: 90/100.
2. **`air_temp.csv`** contains **1231 null values** inside `TAVG` column. The average daily temperature has to be calculated in python using `(TMAX + TMIN) / 2`. Quality Score: 75/100.
3. **`EIA_861M_sales_revenue.xlsx`** has unstructured headers with **Unnamed: 0 to Unnamed: 23** columns due to multi-row Excel layouts, requiring heavy row-skipping rules. Quality Score: 50/100.

### Recommendations for Improvement
- Run deduplication on `PSEG_Component_Distribution_Rates.csv`.
- Pre-calculate `TAVG` in all weather CSV files to avoid runtime fill checks.
- Convert all raw `.xlsx` spreadsheets to clean schema-validated `.parquet` tables.

---
## Phase 10 — Missing Datasets

### 1. AMI Interval Meter Readings (15-Min Smart Meter Feeds)
- **Business Importance**: High. Needed for Time-of-Use (TOU) pricing analysis.
- **Recommended Source**: Utility Green Button API / synthetic interval generator.
- **Integration Difficulty**: High. Requires streaming queue (Kafka) or heavy batch tables.
- **Affected Components**: Bill Analysis tab, Peak demand forecasting models.

### 2. Real-Time PJM LMP Hourly Prices
- **Business Importance**: High. Connects load forecasting to actual spot financial risks.
- **Recommended Source**: PJM Data Miner API.
- **Integration Difficulty**: Medium.
- **Affected Components**: Forecast tab (spot cost exposure).

### 3. Commercial Ratchet Demand Rules
- **Business Importance**: High. Commercial tariffs penalize peak demand spikes across 12-month rolling windows.
- **Recommended Source**: OpenEI Utility Rate Database API.
- **Integration Difficulty**: High. Requires state-machine logic in the Tariff Engine.
- **Affected Components**: Impact tab (what-if rate simulations).

---
## Phase 11 — Architecture Validation

### Key Weaknesses
1. **Lack of Conforming Date Dimension (`DimDate`)**: Links between weather, billing, and PJM market tables rely on date truncations or month strings (e.g. 'June 2024'), resulting in high risk of join mismatches.
2. **SQLite Database Locking**: During concurrent user uploads, SQLite locks the entire database file during writes, preventing real-time telemetry updates.
3. **Volumetric Bias**: The simulation engine only modifies volumetric consumption (kWh) and distribution rates. It lacks peak demand capacity (kW) ratchet modeling.

---
## Phase 12 — Backend Integration Analysis

| Dataset Name | Loading Strategy | Caching Strategy | Target Format | Target Storage | Refresh Frequency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `billing.parquet` | Load during startup | In-memory app state | Parquet | SQLite (dw) | User upload |
| `weather.parquet` | Load lazily | Redis cache | Parquet | SQLite (dw) | Daily |
| `pjm_market.parquet` | Load lazily | Redis cache | Parquet | SQLite (dw) | Hourly |
| `state_benchmark.parquet` | Load during startup | In-memory app state | Parquet | SQLite (dw) | Annually |
| `retail_plans.parquet` | Load lazily | Redis cache | Parquet | SQLite (dw) | Daily |

---
## Phase 13 — Machine Learning Readiness

- **`eia_pjm_daily_demand.csv`**: **Ready**. Used for daily grid capacity time series (Prophet/SARIMAX).
- **`da_hrl_lmps(1).csv`**: **Partially Ready**. Needs outlier clipping (negative prices) before model fitting.
- **`weather.parquet`**: **Ready**. HDD/CDD columns are excellent exogenous inputs for temperature regression models.
- **`census_demographics_2022_cache.csv`**: **Not Ready**. ACS features are too sparse (one year) for predictive modeling, but excellent for demographic clustering.

---
## Phase 14 — UI & Dashboard Usage

- **`state_benchmark.parquet`**: Drives the GIS US price heatmap and rankings table in the Benchmark tab.
- **`utility_zip_lookup`**: Drives the interactive ZIP code utility search filter in the Geo tab.
- **`retail_plans.parquet`**: Drives the competitive plans grid card listing in the Plans tab.
- **`weather.parquet`**: Drives the CDD/HDD weather summary text box and temperature trend line charts.

---
## Phase 15 — Dead Dataset Detection

1. **`eia930_interchange`**: Never loaded, has no UI, no ML usage. **Recommendation: Remove**.
2. **`Avg_price_Electricity.xlsx`**: Outdated sheet. **Recommendation: Remove**.
3. **`salesofelectricity.xlsx`**: Unstructured EIA Excel file. **Recommendation: Remove**.

---
## Phase 16 — Priority Matrix

### Critical
- `billing.parquet` (core customer billing data)
- `PSEG_Component_Distribution_Rates.csv` (delivery charge parameters)
- `utility_zip_lookup` (GIS search crosswalk)

### High
- `weather.parquet` (weather degree days)
- `eia_pjm_daily_demand.csv` (load forecasting baseline)
- `retail_plans.parquet` (competitive plans catalog)

### Archive
- `Avg_price_Electricity.xlsx` (obsolete)
- `salesofelectricity.xlsx` (obsolete)
- `eia930_interchange` (dead interchange database)

---
## Phase 17 — Final Master Dataset Matrix

| Dataset Name | Fact/Dim | Purpose | Geographic Gran. | Time Gran. | Quality Score | Business Score | Recommendation | Priority |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| `Aggregated_Community-Scale_Utility_Energy_Data.xlsx` | Dim | Keep as regional community energy consumption baseline for NJ. | New Jersey (Municipalities) | Municipal Annual total consumption | 92 | 85 | Keep as regional community energy consumption baseline for NJ. | 80 |
| `air_temp.csv` | Dim | Unify with weather.csv and weather_openmeteo.csv to create a single weather profile. | Local Newark Station (NJ) | Daily (TAVG, TMAX, TMIN) | 75 | 80 | Unify with weather.csv and weather_openmeteo.csv to create a single weather profile. | 85 |
| `Avg_price_Electricity.xlsx` | Dim | Obsolete. Replace entirely with cleaned state_benchmark.parquet and state_monthly_prices tables. | National (Census Divisions) | Monthly average cents/kWh by sector | 60 | 50 | Obsolete. Replace entirely with cleaned state_benchmark.parquet and state_monthly_prices tables. | 55 |
| `BGS Auction historical rates.xlsx` | Dim | Keep as default BGS supply baseline rates for NJ utilities. | New Jersey utilities (PSE&G, JCP&L, ACE, RECO) | Annual final auction prices | 95 | 90 | Keep as default BGS supply baseline rates for NJ utilities. | 85 |
| `billing.csv` | Dim | Central CSV source. Keep and cache in memory during startup. | Local Customer Facilities | Monthly billing cycles | 98 | 95 | Central CSV source. Keep and cache in memory during startup. | 95 |
| `billing.parquet` | Dim | Keep. Parquet representation of billing data for high-speed queries. | Local Customer Facilities | Monthly billing cycles | 100 | 95 | Keep. Parquet representation of billing data for high-speed queries. | 96 |
| `census_demographics_2022_cache.csv` | Dim | Keep. Expand to county-level mapping database to construct Energy Burden profiles. | New Jersey (Counties) | County annual averages | 98 | 75 | Keep. Expand to county-level mapping database to construct Energy Burden profiles. | 75 |
| `cpi_monthly.csv` | Dim | Keep. Used to adjust historical prices for inflation. | National | Monthly indices | 100 | 60 | Keep. Used to adjust historical prices for inflation. | 65 |
| `cpi_yearly.csv` | Dim | Keep. Used for annual inflation deflators. | National | Annual avg & deflator | 95 | 55 | Keep. Used for annual inflation deflators. | 60 |
| `da_hrl_lmps(1).csv` | Dim | Critical wholesale pricing feed. Keep and link to hourly demand to calculate LMP spot market exposure. | PJM Nodes (PSEG, JC, AE, PL etc.) | Hourly Day-Ahead LMPs | 90 | 92 | Critical wholesale pricing feed. Keep and link to hourly demand to calculate LMP spot market exposure. | 90 |
| `EIA_861M_sales_revenue.xlsx` | Dim | Partially useful. Replace raw sheet with clean processed EIA-861M database loader. | All 50 US States | Monthly state totals by sector | 50 | 55 | Partially useful. Replace raw sheet with clean processed EIA-861M database loader. | 60 |
| `eia_pjm_daily_demand.csv` | Dim | Core historical sub-BA load series. Keep and cache. | PJM Sub-Balancing Areas (AE, JC, PS, RECO) | Daily sub-BA demand (MW) | 100 | 92 | Core historical sub-BA load series. Keep and cache. | 90 |
| `eia_residential_Avg_electricity_prices.csv` | Dim | Primary historical retail pricing baseline. Keep. | All 50 US States | Monthly residential average rate | 100 | 88 | Primary historical retail pricing baseline. Keep. | 90 |
| `Historic_Municipal_Energy_Use_in_New_Jersey__Table__-772512291409682993.csv` | Dim | Keep. Standardizes NJ municipal electric and gas baselines. | New Jersey (Municipalities) | Annual municipal electric and gas usage by sector | 85 | 80 | Keep. Standardizes NJ municipal electric and gas baselines. | 80 |
| `nj-rs-Average_retail_price_of_electricity_monthly.csv` | Dim | Useful, but redundant with the state_benchmark and state_monthly_prices tables. | New Jersey | Monthly residential cents/kWh | 90 | 75 | Useful, but redundant with the state_benchmark and state_monthly_prices tables. | 75 |
| `OpenEI_IOU_Utility_ZIP_Mapping_2024.csv` | Dim | Critical zip-to-utility mapping dimension table. Keep. | National (All US ZIP codes) | ZIP code level mappings | 100 | 95 | Critical zip-to-utility mapping dimension table. Keep. | 96 |
| `OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv` | Dim | Useful. Reconcile FIPS or ZIP codes that have string prefixes in python ETL. | National (All US ZIP codes) | ZIP code level mappings | 98 | 90 | Useful. Reconcile FIPS or ZIP codes that have string prefixes in python ETL. | 90 |
| `pjm_market.csv` | Dim | Duplicate of pjm_market.parquet. Can be archived. | PSEG Zone (NJ) | Daily averages | 100 | 85 | Duplicate of pjm_market.parquet. Can be archived. | 85 |
| `pjm_market.parquet` | Dim | Keep as main analytical PJM source. | PSEG Zone (NJ) | Daily averages | 100 | 88 | Keep as main analytical PJM source. | 86 |
| `pjm_market_pseg_cache.csv` | Dim | Can be merged or archived. | PSEG Zone (NJ) | Daily averages | 100 | 80 | Can be merged or archived. | 80 |
| `PSEG_Component_Distribution_Rates.csv` | Dim | Keep. Essential for distribution charge calculation. | PSE&G service territory (NJ) | Component rates | 90 | 92 | Keep. Essential for distribution charge calculation. | 90 |
| `pseg_rate_history.csv` | Dim | Keep. Primary historical pricing sequence for PSE&G. | PSE&G service territory (NJ) | Monthly rate parameters | 95 | 95 | Keep. Primary historical pricing sequence for PSE&G. | 94 |
| `retail_plans.csv` | Dim | Duplicate of retail_plans.parquet. Can be archived. | New Jersey | Supplier plan offers | 100 | 85 | Duplicate of retail_plans.parquet. Can be archived. | 85 |
| `retail_plans.parquet` | Dim | Keep as active retail supplier plan catalog. | New Jersey | Supplier plan offers | 100 | 88 | Keep as active retail supplier plan catalog. | 86 |
| `salesofelectricity.xlsx` | Dim | Obsolete. Replace entirely with cleaned state_benchmark.parquet. | National (Census Divisions) | Monthly totals | 55 | 45 | Obsolete. Replace entirely with cleaned state_benchmark.parquet. | 50 |
| `state_benchmark.csv` | Dim | Duplicate of state_benchmark.parquet. Can be archived. | All 50 US States | Annual State Averages | 100 | 90 | Duplicate of state_benchmark.parquet. Can be archived. | 92 |
| `state_benchmark.parquet` | Dim | Keep as the canonical state-level price & bill benchmarking dataset. | All 50 US States | Annual State Averages | 100 | 92 | Keep as the canonical state-level price & bill benchmarking dataset. | 93 |
| `weather.csv` | Dim | Duplicate of weather.parquet. Can be archived. | Newark Station (NJ) | Daily (TAVG, HDD, CDD) | 100 | 88 | Duplicate of weather.parquet. Can be archived. | 88 |
| `weather.parquet` | Dim | Keep as primary daily weather/degree day benchmark. | Newark Station (NJ) | Daily (TAVG, HDD, CDD) | 100 | 90 | Keep as primary daily weather/degree day benchmark. | 90 |
| `weather_noaa_cache.csv` | Dim | Can be merged or archived. | Local station | Daily | 100 | 75 | Can be merged or archived. | 75 |
| `weather_openmeteo.csv` | Dim | Can be merged or archived. | Local region | Daily max/min/avg, HDD, CDD | 100 | 80 | Can be merged or archived. | 80 |