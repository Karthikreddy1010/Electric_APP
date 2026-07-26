"""
backend.config.environment — Application environment detection.

Determines the runtime environment (DEVELOPMENT, STAGING, PRODUCTION)
from the APP_ENV environment variable, with safe defaults.
"""
from __future__ import annotations

import enum
import os


class Environment(str, enum.Enum):
    """Application runtime environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


def get_environment() -> Environment:
    """Detect the current application environment from APP_ENV variable."""
    raw = os.environ.get("APP_ENV", "development").lower().strip()
    try:
        return Environment(raw)
    except ValueError:
        return Environment.DEVELOPMENT


def is_development() -> bool:
    """Check if running in development mode."""
    return get_environment() == Environment.DEVELOPMENT


def is_production() -> bool:
    """Check if running in production mode."""
    return get_environment() == Environment.PRODUCTION


def is_testing() -> bool:
    """Check if running in test mode."""
    return get_environment() == Environment.TESTING


current_environment = get_environment()
