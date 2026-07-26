"""
backend.bill_parser.templates — Utility layout regex templates for structured bill parsing.
"""
from __future__ import annotations

from typing import Dict, Any

UTILITY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "PSE&G": {
        "customer_id_pattern": r'(?:account\s*number|acct\s*#)\s*:?\s*([a-z0-9\-]+)',
        "meter_pattern": r'(?:meter\s*number|meter\s*#)\s*:?\s*([a-z0-9\-]+)',
        "usage_pattern": r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:kwh|kilowatt\s*hours?)',
        "total_pattern": r'(?:total\s+amount|amount\s+due|total\s+due)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "service_charge_pattern": r'(?:customer\s+charge|service\s+charge)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "supply_pattern": r'(?:supply|generation|bgs)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "delivery_pattern": r'(?:delivery|distribution)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "default_zip": "07102",
        "default_rate_schedule": "RS",
    },
    "JCP&L": {
        "customer_id_pattern": r'(?:account\s*number|acct\s*#)\s*:?\s*([a-z0-9\-]+)',
        "meter_pattern": r'(?:meter\s*number|meter\s*#)\s*:?\s*([a-z0-9\-]+)',
        "usage_pattern": r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:kwh|kilowatt\s*hours?)',
        "total_pattern": r'(?:total\s+amount|amount\s+due|total\s+due)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "service_charge_pattern": r'(?:customer\s+charge|service\s+charge)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "supply_pattern": r'(?:supply|generation|bgs)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "delivery_pattern": r'(?:delivery|distribution)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "default_zip": "07701",
        "default_rate_schedule": "RS",
    },
    "Atlantic City Electric": {
        "customer_id_pattern": r'(?:account\s*number|acct\s*#)\s*:?\s*([a-z0-9\-]+)',
        "meter_pattern": r'(?:meter\s*number|meter\s*#)\s*:?\s*([a-z0-9\-]+)',
        "usage_pattern": r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:kwh|kilowatt\s*hours?)',
        "total_pattern": r'(?:total\s+amount|amount\s+due|total\s+due)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "service_charge_pattern": r'(?:customer\s+charge|service\s+charge)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "supply_pattern": r'(?:supply|generation|bgs)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "delivery_pattern": r'(?:delivery|distribution)\s+charge\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',
        "default_zip": "08401",
        "default_rate_schedule": "RS",
    },
}
