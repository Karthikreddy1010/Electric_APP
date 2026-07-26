"""
backend.analytics.tariff — Tariff calculations submodule.

Performs deterministic utility rate schedule lookups and calculates unbundled
volumetric components (BGS supply, distribution, transmission, SBC, transition, rider, NUG).
"""
from __future__ import annotations

from typing import Dict, Any
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import TariffCalculationsSchema
from backend.config.constants import UTILITY_RATE_REGISTRY, PSEG_RS_RATES


def calculate_tariff_details(
    parsed_bill: ParsedBill,
    rate_overrides: Dict[str, float] | None = None,
) -> TariffCalculationsSchema:
    """Calculate unbundled volumetric tariff components for the bill."""
    utility = parsed_bill.utility
    schedule = parsed_bill.rate_schedule
    base_rates = UTILITY_RATE_REGISTRY.get(utility, PSEG_RS_RATES).copy()

    # Apply optional user rate overrides
    if rate_overrides:
        base_rates.update(rate_overrides)

    bgs_rate = base_rates.get("bgs_rate", 0.1052)
    distribution_rate = base_rates.get("distribution_rate", 0.0422)
    transmission_rate = base_rates.get("transmission_rate", 0.0157)
    sbc_rate = base_rates.get("sbc_rate", 0.0036)
    transition_rate = base_rates.get("transition_rate", 0.0020)
    rider_rate = base_rates.get("rider_rate", 0.0040)
    nug_rate = base_rates.get("nug_rate", 0.0010)

    effective_volumetric_rate = (
        parsed_bill.effective_rate
        if parsed_bill.effective_rate > 0
        else sum(base_rates.values())
    )

    return TariffCalculationsSchema(
        utility_name=utility,
        rate_schedule=schedule,
        effective_volumetric_rate=round(effective_volumetric_rate, 4),
        bgs_rate=round(bgs_rate, 4),
        distribution_rate=round(distribution_rate, 4),
        transmission_rate=round(transmission_rate, 4),
        sbc_rate=round(sbc_rate, 4),
        transition_rate=round(transition_rate, 4),
        rider_rate=round(rider_rate, 4),
        nug_rate=round(nug_rate, 4),
    )
