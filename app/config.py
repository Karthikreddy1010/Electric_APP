"""
Flask configuration — environment-aware config classes.
Usage: config = get_config("development")
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class _BaseConfig:
    """Shared defaults across all environments."""
    SECRET_KEY = "change-me-in-production"
    DEBUG = False
    TESTING = False

    # Directories
    DATA_RAW_DIR = str(BASE_DIR / "data" / "raw")
    DATA_PROCESSED_DIR = str(BASE_DIR / "data" / "processed")

    # CORS
    CORS_ORIGINS = ["*"]

    # Model hyperparams (used by existing config/settings.py modules)
    XGB_N_ESTIMATORS = 500
    XGB_MAX_DEPTH = 6
    XGB_LEARNING_RATE = 0.05
    SARIMA_ORDER = (1, 1, 1)
    SARIMA_SEASONAL_ORDER = (1, 1, 1, 12)
    MC_SIMULATIONS = 10_000


class DevelopmentConfig(_BaseConfig):
    DEBUG = True
    CORS_ORIGINS = ["*"]


class ProductionConfig(_BaseConfig):
    DEBUG = False
    SECRET_KEY = "set-via-environment-variable"
    CORS_ORIGINS = ["http://localhost:5000"]


class TestConfig(_BaseConfig):
    TESTING = True
    DEBUG = True


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = "default"):
    """Return the config class for the given environment name."""
    return _CONFIGS.get(env, DevelopmentConfig)
