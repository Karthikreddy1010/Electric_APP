"""
backend.analytics.savings — Savings estimation submodule.

Calculates deterministic rate schedule tier optimizations, behavioral conservation
savings, and load shift potential without machine learning.
"""
from __future__ import annotations

from typing import List
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import SavingsEstimationSchema, SavingsOpportunitySchema
from backend.config.settings import analytics_settings


def calculate_savings_estimation(parsed_bill: ParsedBill) -> SavingsEstimationSchema:
    """Calculate deterministic cost reduction opportunities and ROI payback."""
    opportunities: List[SavingsOpportunitySchema] = []
    tot = parsed_bill.total_bill
    use = parsed_bill.usage_kwh
    rate = parsed_bill.effective_rate if parsed_bill.effective_rate > 0 else 0.1852

    # 1. Behavioral Conservation (10% usage reduction)
    cons_pct = analytics_settings.savings_conservation_pct
    cons_kwh_sav = round(use * cons_pct * 12, 1)
    cons_dollar_sav = round(cons_kwh_sav * rate, 2)
    opportunities.append(
        SavingsOpportunitySchema(
            category="Conservation",
            title="10% Energy Conservation Target",
            estimated_annual_savings=cons_dollar_sav,
            estimated_kwh_reduction=cons_kwh_sav,
            feasibility="EASY",
            payback_months=0,
        )
    )

    # 2. Demand Shift (Off-Peak Load Shifting)
    shift_kwh_sav = round(use * 0.05 * 12, 1)
    shift_dollar_sav = round(shift_kwh_sav * rate * 0.40, 2)
    opportunities.append(
        SavingsOpportunitySchema(
            category="Demand Shift",
            title="Off-Peak Load Shifting",
            estimated_annual_savings=shift_dollar_sav,
            estimated_kwh_reduction=shift_kwh_sav,
            feasibility="EASY",
            payback_months=0,
        )
    )

    # 3. Smart Thermostat Optimization
    thermo_kwh_sav = round(use * 0.08 * 12, 1)
    thermo_dollar_sav = round(thermo_kwh_sav * rate, 2)
    opportunities.append(
        SavingsOpportunitySchema(
            category="Equipment",
            title="Programmable Thermostat Setpoints",
            estimated_annual_savings=thermo_dollar_sav,
            estimated_kwh_reduction=thermo_kwh_sav,
            feasibility="MODERATE",
            payback_months=6,
        )
    )

    total_sav = round(sum(o.estimated_annual_savings for o in opportunities), 2)
    annual_bill_est = tot * 12
    sav_pct = round((total_sav / annual_bill_est) * 100, 1) if annual_bill_est > 0 else 0.0

    return SavingsEstimationSchema(
        total_potential_annual_savings=total_sav,
        potential_savings_pct=sav_pct,
        opportunities=opportunities,
    )
