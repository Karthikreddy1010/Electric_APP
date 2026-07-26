"""
backend.analytics.components — Component breakdown, fixed/variable decomposition, and tax math.
"""
from __future__ import annotations

from typing import Dict, Any, List
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import (
    ComponentBreakdownSchema,
    ComponentItemSchema,
    FixedChargesSchema,
    VariableChargesSchema,
    TaxesSchema,
    TariffCalculationsSchema,
)
from backend.config.constants import NJ_TAX_RATE, COMPONENT_TYPES, UTILITY_CUSTOMER_CHARGES


def calculate_fixed_charges(parsed_bill: ParsedBill) -> FixedChargesSchema:
    """Calculate fixed monthly charges."""
    cust_charge = (
        parsed_bill.monthly_service_charge
        if parsed_bill.monthly_service_charge > 0
        else UTILITY_CUSTOMER_CHARGES.get(parsed_bill.utility, 8.24)
    )
    return FixedChargesSchema(
        customer_charge=round(cust_charge, 2),
        meter_fee=0.0,
        total_fixed_charges=round(cust_charge, 2),
    )


def calculate_variable_charges(
    parsed_bill: ParsedBill, tariff: TariffCalculationsSchema
) -> VariableChargesSchema:
    """Calculate volumetric variable charges."""
    usage = parsed_bill.usage_kwh
    bgs_cost = (
        parsed_bill.bgs_cost
        if parsed_bill.bgs_cost is not None
        else round(usage * tariff.bgs_rate, 2)
    )
    dist_cost = (
        parsed_bill.distribution_cost
        if parsed_bill.distribution_cost is not None
        else round(usage * tariff.distribution_rate, 2)
    )
    trans_cost = (
        parsed_bill.transmission_cost
        if parsed_bill.transmission_cost is not None
        else round(usage * tariff.transmission_rate, 2)
    )
    sbc_cost = (
        parsed_bill.sbc_cost
        if parsed_bill.sbc_cost is not None
        else round(usage * tariff.sbc_rate, 2)
    )
    transition_cost = (
        parsed_bill.market_transition_cost
        if parsed_bill.market_transition_cost is not None
        else round(usage * tariff.transition_rate, 2)
    )
    rider_cost = (
        parsed_bill.rider_cost
        if parsed_bill.rider_cost is not None
        else round(usage * tariff.rider_rate, 2)
    )
    nug_cost = (
        parsed_bill.nug_cost
        if parsed_bill.nug_cost is not None
        else round(usage * tariff.nug_rate, 2)
    )

    total_var = round(
        bgs_cost + dist_cost + trans_cost + sbc_cost + transition_cost + rider_cost + nug_cost,
        2,
    )

    return VariableChargesSchema(
        usage_kwh=usage,
        bgs_supply_cost=round(bgs_cost, 2),
        distribution_cost=round(dist_cost, 2),
        transmission_cost=round(trans_cost, 2),
        sbc_cost=round(sbc_cost, 2),
        transition_cost=round(transition_cost, 2),
        rider_cost=round(rider_cost, 2),
        nug_cost=round(nug_cost, 2),
        total_variable_charges=total_var,
    )


def calculate_taxes(
    fixed: FixedChargesSchema, variable: VariableChargesSchema, billed_tax: float
) -> TaxesSchema:
    """Calculate pre-tax subtotal and tax reconciliation."""
    subtotal = round(fixed.total_fixed_charges + variable.total_variable_charges, 2)
    calculated_tax = round(subtotal * NJ_TAX_RATE, 2)
    actual_billed_tax = billed_tax if billed_tax > 0 else calculated_tax
    discrepancy = round(actual_billed_tax - calculated_tax, 2)

    return TaxesSchema(
        tax_rate=NJ_TAX_RATE,
        taxable_subtotal=subtotal,
        calculated_tax=calculated_tax,
        billed_tax=actual_billed_tax,
        tax_discrepancy=discrepancy,
    )


def calculate_component_breakdown(
    fixed: FixedChargesSchema,
    variable: VariableChargesSchema,
    taxes: TaxesSchema,
    tariff: TariffCalculationsSchema,
) -> ComponentBreakdownSchema:
    """Construct complete itemized component breakdown ledger."""
    total_bill = round(taxes.taxable_subtotal + taxes.billed_tax, 2)

    items: List[ComponentItemSchema] = []
    if total_bill > 0:
        # Fixed customer charge
        items.append(
            ComponentItemSchema(
                name="Customer Charge",
                amount=fixed.customer_charge,
                percentage=round((fixed.customer_charge / total_bill) * 100, 1),
                category="fixed",
                type="fixed",
                controllable="No",
                driver="fixed",
            )
        )
        # BGS Supply
        items.append(
            ComponentItemSchema(
                name="BGS Supply",
                amount=variable.bgs_supply_cost,
                percentage=round((variable.bgs_supply_cost / total_bill) * 100, 1),
                category="supply",
                type="variable",
                controllable="Yes",
                driver="market",
                rate_per_kwh=tariff.bgs_rate,
            )
        )
        # Distribution
        items.append(
            ComponentItemSchema(
                name="Distribution Charge",
                amount=variable.distribution_cost,
                percentage=round((variable.distribution_cost / total_bill) * 100, 1),
                category="delivery",
                type="variable",
                controllable="Partial",
                driver="infrastructure",
                rate_per_kwh=tariff.distribution_rate,
            )
        )
        # Transmission
        items.append(
            ComponentItemSchema(
                name="Transmission Charge",
                amount=variable.transmission_cost,
                percentage=round((variable.transmission_cost / total_bill) * 100, 1),
                category="delivery",
                type="variable",
                controllable="No",
                driver="market",
                rate_per_kwh=tariff.transmission_rate,
            )
        )
        # SBC
        items.append(
            ComponentItemSchema(
                name="Societal Benefits Charge",
                amount=variable.sbc_cost,
                percentage=round((variable.sbc_cost / total_bill) * 100, 1),
                category="delivery",
                type="variable",
                controllable="No",
                driver="policy",
                rate_per_kwh=tariff.sbc_rate,
            )
        )
        # Sales Tax
        items.append(
            ComponentItemSchema(
                name="Sales Tax (6.625%)",
                amount=taxes.billed_tax,
                percentage=round((taxes.billed_tax / total_bill) * 100, 1),
                category="tax",
                type="fixed",
                controllable="No",
                driver="policy",
            )
        )

    supply_tot = variable.bgs_supply_cost
    delivery_tot = round(
        variable.total_variable_charges - supply_tot + fixed.total_fixed_charges, 2
    )

    return ComponentBreakdownSchema(
        fixed_total=fixed.total_fixed_charges,
        variable_total=variable.total_variable_charges,
        supply_total=supply_tot,
        delivery_total=delivery_tot,
        taxes_total=taxes.billed_tax,
        total_bill=total_bill,
        components=items,
    )
