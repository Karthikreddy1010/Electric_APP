"""
Static constants and lookup structures for the Electricity Cost AI Platform.
"""
from typing import Dict, Any

# New Jersey Utility Sales Tax Rate
NJ_TAX_RATE = 0.06625

# Standard PSE&G residential service customer charge
DEFAULT_CUSTOMER_CHARGE = 8.24

# Mapping of average monthly usage by state for bill estimates (EIA averages)
STATE_AVG_MONTHLY_USAGE = {
    "AL": 1200, "AK": 570, "AZ": 1060, "AR": 1120, "CA": 530,
    "CO": 690, "CT": 730, "DE": 930, "DC": 710, "FL": 1100,
    "GA": 1120, "HI": 510, "ID": 960, "IL": 720, "IN": 940,
    "IA": 870, "KS": 930, "KY": 1130, "LA": 1220, "ME": 530,
    "MD": 1000, "MA": 600, "MI": 630, "MN": 780, "MS": 1200,
    "MO": 1060, "MT": 810, "NE": 960, "NV": 910, "NH": 590,
    "NJ": 680, "NM": 640, "NY": 570, "NC": 1060, "ND": 1110,
    "OH": 870, "OK": 1100, "OR": 910, "PA": 830, "RI": 570,
    "SC": 1130, "SD": 1020, "TN": 1210, "TX": 1140, "UT": 790,
    "VT": 540, "VA": 1120, "WA": 950, "WV": 1090, "WI": 680,
    "WY": 860,
}

# Component labels and driving classification for bill impact modeling
COMPONENT_LABELS_MAP = {
    "customer": ("Customer Charge", "Fixed"),
    "distribution": ("Distribution Charge", "Infrastructure"),
    "transition": ("Transition Charges", "Regulatory"),
    "sbc": ("Societal Benefits Charge", "Policy"),
    "transmission": ("Transmission Charge", "Market"),
    "rider": ("Rider Charges", "Regulatory"),
    "bgs": ("BGS Supply", "Market"),
    "weather": ("Weather Impact", "External"),
    "behavioral_usage": ("Discretionary Usage", "Behavioral"),
    "nug": ("Non-Utility Generation Charge", "Regulatory"),
    "tax": ("Sales Tax", "Policy")
}

# User-facing descriptions of various rate structure tariff components
COMPONENT_DESCRIPTIONS = {
    "Customer Charge": "Fixed monthly customer charge independent of usage changes.",
    "Distribution Charge": "Local distribution grid maintenance costs, weather-normalized.",
    "Transition Charges": "Stranded cost recoveries and policy transition adjustments.",
    "Societal Benefits Charge": "Funds state-mandated energy efficiency and assistance programs.",
    "Transmission Charge": "High-voltage transmission grid service cost share.",
    "Rider Charges": "Temporary regulatory tariff adjustments for utility costs.",
    "BGS Supply": "Basic Generation Service market price for wholesale supply.",
    "Weather Impact": "Attributed cooling/heating demand costs based on NOAA degree-day anomalies.",
    "Discretionary Usage": "Behavioral consumption changes unrelated to seasonal temperature anomalies.",
    "Non-Utility Generation Charge": "Historical independent power producer contract recovery.",
    "Sales Tax": "New Jersey state utility sales tax (6.625%) on all components."
}

# Presets applied to base simulation parameters
SCENARIO_PRESETS: Dict[str, Dict[str, Any]] = {
    "cold_winter": {
        "description": "Severe winter with 30% higher heating degree days and 15% higher usage",
        "weather_override": {"hdd_multiplier": 1.30, "cdd_multiplier": 0.0},
        "rate_changes": {},
        "usage_multiplier": 1.15,
    },
    "hot_summer": {
        "description": "Extreme summer with 40% higher cooling degree days and 25% higher usage",
        "weather_override": {"hdd_multiplier": 0.0, "cdd_multiplier": 1.40},
        "rate_changes": {},
        "usage_multiplier": 1.25,
    },
    "high_market": {
        "description": "Wholesale market spike: BGS +25%, transmission +15%",
        "weather_override": {},
        "rate_changes": {"bgs_rate": 25, "transmission_rate": 15},
        "usage_multiplier": 1.0,
    },
    "low_usage": {
        "description": "Energy-efficient household using 30% less electricity",
        "weather_override": {},
        "rate_changes": {},
        "usage_multiplier": 0.70,
    },
    "conservation": {
        "description": "Conservation scenario: 15% usage reduction, stable rates",
        "weather_override": {},
        "rate_changes": {},
        "usage_multiplier": 0.85,
    },
}
