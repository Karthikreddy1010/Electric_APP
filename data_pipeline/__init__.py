"""
Data Pipeline Package
- config: centralized paths, dataset registry, API keys
- loaders: loads local raw CSV/XLSX files
- api_fetchers: incremental fetchers for BLS and EIA APIs
- transformers: cleaning and standardizing datasets
- validators: data quality checks
- merger: joins datasets and applies inflation adjustments
- pipeline_runner: main orchestrator
- ingestors: pull data from EIA, NOAA, PJM APIs
- cleaners: handle missing values, normalize units
- features: lag features, rolling averages, seasonal encodings
- storage: write to Parquet / Snowflake
"""
from data_pipeline.pipeline_runner import run_pipeline

__all__ = ["run_pipeline"]
