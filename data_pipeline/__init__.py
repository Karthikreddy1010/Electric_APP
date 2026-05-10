"""
Data Pipeline Package
- ingestors: pull data from EIA, NOAA, PJM APIs
- cleaners: handle missing values, normalize units
- features: lag features, rolling averages, seasonal encodings
- storage: write to Parquet / Snowflake
"""
