"""
Central configuration for the Electricity Cost AI platform.
Uses pydantic-settings for validation and .env file support.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class DatabaseSettings(BaseSettings):
    """Snowflake / local SQLite settings."""
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_database: str = "ELECTRICITY_DW"
    snowflake_schema: str = "PUBLIC"
    snowflake_warehouse: str = "COMPUTE_WH"
    # Fallback: local SQLite for dev
    sqlite_path: str = str(BASE_DIR / "data" / "electricity.db")

    class Config:
        env_prefix = "DB_"
        env_file = str(BASE_DIR / ".env")


class APISettings(BaseSettings):
    """FastAPI service configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300  # 5 min default cache

    class Config:
        env_prefix = "API_"
        env_file = str(BASE_DIR / ".env")


class ModelSettings(BaseSettings):
    """ML model paths and hyperparameters."""
    model_dir: str = str(BASE_DIR / "models" / "artifacts")
    mlflow_tracking_uri: str = str(BASE_DIR / "mlruns")
    mlflow_experiment_name: str = "electricity_cost_analysis"
    # XGBoost impact model
    xgb_n_estimators: int = 500
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    # SARIMA defaults
    sarima_order: tuple = (1, 1, 1)
    sarima_seasonal_order: tuple = (1, 1, 1, 12)
    # Prophet
    prophet_changepoint_prior: float = 0.05
    # LSTM
    lstm_epochs: int = 100
    lstm_batch_size: int = 32
    lstm_sequence_length: int = 12
    lstm_hidden_size: int = 64
    # Monte Carlo
    mc_simulations: int = 10_000

    class Config:
        env_prefix = "MODEL_"
        env_file = str(BASE_DIR / ".env")


class DataSourceSettings(BaseSettings):
    """External data source API keys and URLs."""
    eia_api_key: str = ""
    eia_base_url: str = "https://api.eia.gov/v2"
    noaa_token: str = ""
    noaa_base_url: str = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    pjm_base_url: str = "https://api.pjm.com/api/v1"
    pjm_api_key: str = ""
    # Local data fallback
    raw_data_dir: str = str(BASE_DIR / "data" / "raw")
    processed_data_dir: str = str(BASE_DIR / "data" / "processed")
    parquet_dir: str = str(BASE_DIR / "data" / "parquet")

    class Config:
        env_prefix = "DATA_"
        env_file = str(BASE_DIR / ".env")


# Singleton instances
db_settings = DatabaseSettings()
api_settings = APISettings()
model_settings = ModelSettings()
data_settings = DataSourceSettings()
