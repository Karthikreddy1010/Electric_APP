"""
backend.config.constants — Tariff rate schedules and charge constants.

All hardcoded billing rates, tax percentages, and tariff component
definitions live here so that no analytics or parser module contains
magic numbers. Imports the existing config/constants.py values where
applicable to avoid duplication.
"""
from __future__ import annotations

from typing import Dict

# ── Re-export existing project constants for backward compatibility ──────────
from config.constants import (
    NJ_TAX_RATE,
    DEFAULT_CUSTOMER_CHARGE,
    STATE_AVG_MONTHLY_USAGE,
    COMPONENT_LABELS_MAP,
    COMPONENT_DESCRIPTIONS,
    SCENARIO_PRESETS,
)

# ── PSE&G Residential Service (RS) Tariff Rates ($/kWh) ─────────────────────
# Sourced from NJ BPU-approved PSE&G rate schedules.

PSEG_RS_RATES: Dict[str, float] = {
    "bgs_rate": 0.1052,
    "distribution_rate": 0.0422,
    "transmission_rate": 0.0157,
    "sbc_rate": 0.0036,
    "transition_rate": 0.0020,
    "rider_rate": 0.0040,
    "nug_rate": 0.0010,
}

# ── JCP&L Residential Rates ─────────────────────────────────────────────────
JCPL_RS_RATES: Dict[str, float] = {
    "bgs_rate": 0.1010,
    "distribution_rate": 0.0480,
    "transmission_rate": 0.0165,
    "sbc_rate": 0.0042,
    "transition_rate": 0.0018,
    "rider_rate": 0.0035,
    "nug_rate": 0.0008,
}

# ── Atlantic City Electric Rates ─────────────────────────────────────────────
ACE_RS_RATES: Dict[str, float] = {
    "bgs_rate": 0.0980,
    "distribution_rate": 0.0510,
    "transmission_rate": 0.0170,
    "sbc_rate": 0.0038,
    "transition_rate": 0.0015,
    "rider_rate": 0.0042,
    "nug_rate": 0.0012,
}

# ── Utility Rate Registry ───────────────────────────────────────────────────
UTILITY_RATE_REGISTRY: Dict[str, Dict[str, float]] = {
    "PSE&G": PSEG_RS_RATES,
    "JCP&L": JCPL_RS_RATES,
    "Atlantic City Electric": ACE_RS_RATES,
    "RECO": PSEG_RS_RATES,  # Fallback to PSE&G rates
}

# ── Fixed Charge Registry ($ per month) ──────────────────────────────────────
UTILITY_CUSTOMER_CHARGES: Dict[str, float] = {
    "PSE&G": 8.24,
    "JCP&L": 7.91,
    "Atlantic City Electric": 8.05,
    "RECO": 8.24,
}

# ── Component Metadata ───────────────────────────────────────────────────────
COMPONENT_TYPES: Dict[str, Dict[str, str]] = {
    "customer_charge": {
        "label": "Customer Charge",
        "type": "fixed",
        "driver": "fixed",
        "controllable": "No",
    },
    "bgs_rate": {
        "label": "BGS Supply",
        "type": "variable",
        "driver": "market",
        "controllable": "Yes",
    },
    "distribution_rate": {
        "label": "Distribution Charge",
        "type": "variable",
        "driver": "infrastructure",
        "controllable": "Partial",
    },
    "transmission_rate": {
        "label": "Transmission Charge",
        "type": "variable",
        "driver": "market",
        "controllable": "No",
    },
    "sbc_rate": {
        "label": "Societal Benefits Charge",
        "type": "variable",
        "driver": "policy",
        "controllable": "No",
    },
    "transition_rate": {
        "label": "Transition Charge",
        "type": "variable",
        "driver": "regulatory",
        "controllable": "No",
    },
    "nug_rate": {
        "label": "Non-Utility Generation",
        "type": "variable",
        "driver": "regulatory",
        "controllable": "No",
    },
    "rider_rate": {
        "label": "Rider Charges",
        "type": "variable",
        "driver": "regulatory",
        "controllable": "No",
    },
}

# ── Monthly Weather Lookup Tables (NJ average) ──────────────────────────────
# Default CDD/HDD values per month for NJ when no live weather data exists.
MONTHLY_CDD_DEFAULTS: Dict[int, float] = {
    1: 0.0, 2: 0.0, 3: 0.0, 4: 5.0, 5: 45.0, 6: 180.0,
    7: 310.0, 8: 260.0, 9: 100.0, 10: 15.0, 11: 0.0, 12: 0.0,
}

MONTHLY_HDD_DEFAULTS: Dict[int, float] = {
    1: 950.0, 2: 820.0, 3: 650.0, 4: 350.0, 5: 120.0, 6: 10.0,
    7: 0.0, 8: 0.0, 9: 30.0, 10: 220.0, 11: 500.0, 12: 820.0,
}

# ── Seasonal Multipliers (for forecast inputs) ──────────────────────────────
SEASONAL_MULTIPLIERS: Dict[int, float] = {
    1: 1.15, 2: 1.10, 3: 1.00, 4: 0.90, 5: 0.95, 6: 1.10,
    7: 1.25, 8: 1.20, 9: 1.05, 10: 0.92, 11: 0.95, 12: 1.12,
}

# ── Pipeline & Versioning ───────────────────────────────────────────────────
TARIFF_VERSION = "2026.07"
WEATHER_VERSION = "2026.07"
DATASET_VERSION = "2026.07"
