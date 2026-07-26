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
    """Database connection settings supporting PostgreSQL, Snowflake, and SQLite."""
    postgres_host: str = ""
    postgres_port: str = "5432"
    postgres_user: str = "electric"
    postgres_password: str = "electric"
    postgres_db: str = "electricity_dw"
    database_url: str = ""
    
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
        extra = "ignore"


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
        extra = "ignore"


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
        extra = "ignore"


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
        extra = "ignore"


class LLMSettings(BaseSettings):
    """LLM service configuration supporting multi-provider routing and enterprise AI capabilities."""
    provider: str = "mock"
    model: str = "auto"
    base_url: str = "http://127.0.0.1:11434"
    
    # Provider endpoints & keys
    vllm_base_url: str = "http://localhost:8000/v1"
    sglang_base_url: str = "http://localhost:30000/v1"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    
    # Model defaults per tier
    free_tier_model: str = "qwen2.5-1.5b-instruct"
    pro_tier_model: str = "gpt-4o-mini"
    enterprise_tier_model: str = "claude-3-5-sonnet-20241022"
    
    # Vector store / RAG configuration
    vector_db_provider: str = "in_memory" # pgvector | qdrant | in_memory
    vector_db_url: str = "postgresql://electric:electric@localhost:5432/electricity_dw"
    
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 10.0
    total_timeout: float = 45.0
    max_retries: int = 2
    backoff_factor: float = 1.5
    keep_alive: str = "5m"
    stream: bool = False

    # ── AI Feature Flags ───────────────────────────────────────────────
    feature_streaming: bool = True
    feature_rag: bool = True
    feature_claude: bool = True
    feature_gpt: bool = True
    feature_gemini: bool = True
    feature_vllm: bool = True
    feature_sglang: bool = True
    feature_reports: bool = True

    class Config:
        env_prefix = "LLM_"
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"



# Singleton instances
db_settings = DatabaseSettings()
api_settings = APISettings()
model_settings = ModelSettings()
data_settings = DataSourceSettings()
llm_settings = LLMSettings()

