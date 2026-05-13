"""
Flask configuration — mirrors config/settings.py values
with Flask-specific additions.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class FlaskConfig:
    """Default configuration for the Flask application."""

    # Flask core
    SECRET_KEY = "change-me-in-production"
    DEBUG = True
    TESTING = False

    # Server
    HOST = "0.0.0.0"
    PORT = 5000

    # Data directories
    RAW_DATA_DIR = str(BASE_DIR / "data" / "raw")
    PROCESSED_DATA_DIR = str(BASE_DIR / "data" / "processed")

    # Model defaults
    XGB_N_ESTIMATORS = 500
    XGB_MAX_DEPTH = 6
    XGB_LEARNING_RATE = 0.05
    SARIMA_ORDER = (1, 1, 1)
    SARIMA_SEASONAL_ORDER = (1, 1, 1, 12)
    MC_SIMULATIONS = 10_000

    # Pre-loaded data/models (populated at startup by __init__.py)
    BILLING_DF = None
    WEATHER_DF = None
    MARKET_DF = None
    BENCHMARK_DF = None
    PLANS_DF = None
    IMPACT_MODEL = None
    FORECAST_MODEL = None
    FEATURE_MATRIX = None
    FEATURE_COLS = None


class ProductionConfig(FlaskConfig):
    DEBUG = False
    SECRET_KEY = "set-via-environment-variable"


class TestConfig(FlaskConfig):
    TESTING = True
    DEBUG = True
