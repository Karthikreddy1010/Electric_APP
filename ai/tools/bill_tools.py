"""
Deterministic Customer Bill Tools wrapping bill data, components, and period comparisons.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default active customer bill state (aligned with application defaults)
DEFAULT_BILL = {
    "customer_id": "CUST-07102-PSE&G",
    "utility": "PSE&G",
    "rate_schedule": "RS (Residential Service)",
    "bill_date": "2026-06-30",
    "billing_period": "2026-06-01 to 2026-06-30",
    "days": 30,
    "usage_kwh": 750.0,
    "monthly_service_charge": 8.24,
    "delivery_charge": 41.25,
    "supply_charge": 81.00,
    "societal_benefits_charge": 4.12,
    "rggi_charge": 1.25,
    "tax": 8.41,
    "total_bill": 144.27,
    "effective_rate_cents_per_kwh": 19.24,
    "average_daily_kwh": 25.0
}

DEFAULT_PREVIOUS_BILL = {
    "customer_id": "CUST-07102-PSE&G",
    "utility": "PSE&G",
    "bill_date": "2026-05-31",
    "billing_period": "2026-05-01 to 2026-05-31",
    "days": 31,
    "usage_kwh": 650.0,
    "monthly_service_charge": 8.24,
    "delivery_charge": 35.75,
    "supply_charge": 70.20,
    "societal_benefits_charge": 3.57,
    "rggi_charge": 1.08,
    "tax": 7.30,
    "total_bill": 126.14,
    "effective_rate_cents_per_kwh": 19.41,
    "average_daily_kwh": 20.97
}


class EmptyInput(BaseModel):
    pass


class ComponentExplanationInput(BaseModel):
    component_name: str = Field(description="Name of the bill component (e.g. SBC, BGS, Delivery Charge, Supply Charge, Monthly Service Charge)")


class PeriodComparisonInput(BaseModel):
    current_period: str = Field(default="current", description="Current period identifier")
    previous_period: str = Field(default="previous", description="Previous period identifier")


class BillCalculationInput(BaseModel):
    usage_kwh: float = Field(description="Total electricity consumption in kWh")
    supply_rate_cents: float = Field(description="Supply rate in cents per kWh")
    delivery_rate_cents: float = Field(description="Delivery rate in cents per kWh")
    fixed_charge: float = Field(default=8.24, description="Monthly fixed customer service charge")
    tax_rate: float = Field(default=0.06625, description="Sales tax rate")


@tool(args_schema=EmptyInput)
def get_bill_details() -> Dict[str, Any]:
    """
    Retrieves current active customer bill details including usage_kwh, total_bill, utility, bill_date, and effective_rate.
    """
    return {
        "success": True,
        "tool_name": "get_bill_details",
        "data": DEFAULT_BILL,
        "source": "customer_uploaded_bill"
    }


@tool(args_schema=EmptyInput)
def get_bill_components() -> Dict[str, Any]:
    """
    Retrieves component-level breakdown of the current bill (service charge, delivery charge, supply charge, SBC, RGGI, taxes).
    """
    components = [
        {"name": "Monthly Customer Service Charge", "amount": DEFAULT_BILL["monthly_service_charge"], "unit": "$", "type": "fixed"},
        {"name": "Electric Delivery Charge", "amount": DEFAULT_BILL["delivery_charge"], "unit": "$", "type": "delivery"},
        {"name": "Basic Generation Service (BGS) Supply Charge", "amount": DEFAULT_BILL["supply_charge"], "unit": "$", "type": "supply"},
        {"name": "Societal Benefits Charge (SBC)", "amount": DEFAULT_BILL["societal_benefits_charge"], "unit": "$", "type": "rider"},
        {"name": "RGGI Recovery Rider", "amount": DEFAULT_BILL["rggi_charge"], "unit": "$", "type": "rider"},
        {"name": "NJ Sales & Use Tax", "amount": DEFAULT_BILL["tax"], "unit": "$", "type": "tax"}
    ]
    return {
        "success": True,
        "tool_name": "get_bill_components",
        "data": {
            "total_bill": DEFAULT_BILL["total_bill"],
            "usage_kwh": DEFAULT_BILL["usage_kwh"],
            "components": components
        },
        "source": "customer_uploaded_bill"
    }


@tool(args_schema=EmptyInput)
def get_bill_history() -> Dict[str, Any]:
    """
    Retrieves historical billing cycles (usage kWh and total charges) for the past 6 months.
    """
    history = [
        {"period": "2026-01", "usage_kwh": 820.0, "total_bill": 156.40, "avg_temp_f": 32.4},
        {"period": "2026-02", "usage_kwh": 790.0, "total_bill": 150.70, "avg_temp_f": 34.1},
        {"period": "2026-03", "usage_kwh": 680.0, "total_bill": 131.20, "avg_temp_f": 45.2},
        {"period": "2026-04", "usage_kwh": 610.0, "total_bill": 118.50, "avg_temp_f": 54.8},
        {"period": "2026-05", "usage_kwh": 650.0, "total_bill": 126.14, "avg_temp_f": 63.5},
        {"period": "2026-06", "usage_kwh": 750.0, "total_bill": 144.27, "avg_temp_f": 74.2}
    ]
    return {
        "success": True,
        "tool_name": "get_bill_history",
        "data": {
            "count": len(history),
            "history": history
        },
        "source": "customer_billing_database"
    }


@tool(args_schema=BillCalculationInput)
def calculate_bill_total(usage_kwh: float, supply_rate_cents: float, delivery_rate_cents: float, fixed_charge: float = 8.24, tax_rate: float = 0.06625) -> Dict[str, Any]:
    """
    Deterministically calculates the exact total bill for a given usage and rate breakdown.
    Formula: Total = (Fixed + (Usage * Delivery Rate) + (Usage * Supply Rate)) * (1 + Tax Rate)
    """
    supply_subtotal = round(usage_kwh * (supply_rate_cents / 100.0), 2)
    delivery_subtotal = round(usage_kwh * (delivery_rate_cents / 100.0), 2)
    subtotal = round(fixed_charge + supply_subtotal + delivery_subtotal, 2)
    tax_amount = round(subtotal * tax_rate, 2)
    total_bill = round(subtotal + tax_amount, 2)
    effective_rate = round((total_bill / usage_kwh) * 100.0, 2) if usage_kwh > 0 else 0.0

    return {
        "success": True,
        "tool_name": "calculate_bill_total",
        "data": {
            "usage_kwh": usage_kwh,
            "supply_subtotal": supply_subtotal,
            "delivery_subtotal": delivery_subtotal,
            "fixed_charge": fixed_charge,
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total_bill": total_bill,
            "effective_rate_cents_per_kwh": effective_rate
        },
        "deterministic_engine": "calculate_bill_total_v1"
    }


@tool(args_schema=EmptyInput)
def calculate_component_change() -> Dict[str, Any]:
    """
    Deterministically computes the month-over-month dollar and percentage change between the current bill and previous bill.
    """
    curr = DEFAULT_BILL
    prev = DEFAULT_PREVIOUS_BILL

    usage_diff_kwh = curr["usage_kwh"] - prev["usage_kwh"]
    usage_pct_change = round((usage_diff_kwh / prev["usage_kwh"]) * 100.0, 2)

    bill_diff_dollars = round(curr["total_bill"] - prev["total_bill"], 2)
    bill_pct_change = round((bill_diff_dollars / prev["total_bill"]) * 100.0, 2)

    supply_diff = round(curr["supply_charge"] - prev["supply_charge"], 2)
    delivery_diff = round(curr["delivery_charge"] - prev["delivery_charge"], 2)

    return {
        "success": True,
        "tool_name": "calculate_component_change",
        "data": {
            "current_period": curr["billing_period"],
            "previous_period": prev["billing_period"],
            "bill_diff_dollars": bill_diff_dollars,
            "bill_pct_change": bill_pct_change,
            "usage_diff_kwh": usage_diff_kwh,
            "usage_pct_change": usage_pct_change,
            "supply_diff_dollars": supply_diff,
            "delivery_diff_dollars": delivery_diff,
            "main_driver": "Increased kWh usage (+100 kWh, +15.38%) during warmer June weather"
        },
        "deterministic_engine": "calculate_component_change_v1"
    }


@tool(args_schema=ComponentExplanationInput)
def explain_bill_component(component_name: str) -> Dict[str, Any]:
    """
    Returns official utility/regulatory definitions for specific electricity bill charges (SBC, BGS, Delivery Charge, etc.).
    """
    key = component_name.lower()
    explanations = {
        "sbc": {
            "full_name": "Societal Benefits Charge (SBC)",
            "description": "Mandated state charge that funds clean energy programs, energy efficiency incentives, low-income assistance (USF/LIHEAP), and environmental remediation.",
            "statutory_basis": "N.J.S.A. 48:3-60",
            "jurisdiction": "New Jersey Board of Public Utilities (NJ BPU)"
        },
        "bgs": {
            "full_name": "Basic Generation Service (BGS)",
            "description": "The cost of electricity generation (supply) procured via the annual NJ BPU auction for customers who do not switch to a third-party supplier.",
            "jurisdiction": "NJ BPU / PJM Market"
        },
        "delivery": {
            "full_name": "Electric Delivery Charge",
            "description": "The cost of maintaining high-voltage transmission lines, local distribution poles, wires, transformers, and meter infrastructure to deliver power to your building.",
            "jurisdiction": "Utility Rate Schedule"
        },
        "rggi": {
            "full_name": "Regional Greenhouse Gas Initiative (RGGI) Rider",
            "description": "State carbon allowance cost recovery mechanism supporting clean energy and greenhouse gas mitigation in participating northeastern states.",
            "jurisdiction": "NJ DEP / BPU"
        }
    }

    matched = None
    for k, v in explanations.items():
        if k in key:
            matched = v
            break

    if not matched:
        matched = {
            "full_name": component_name,
            "description": f"Standard tariff line item under utility tariff schedule.",
            "jurisdiction": "State Public Utility Commission"
        }

    return {
        "success": True,
        "tool_name": "explain_bill_component",
        "data": matched,
        "source": "nj_bpu_tariff_definitions"
    }


@tool(args_schema=PeriodComparisonInput)
def compare_bill_periods(current_period: str = "current", previous_period: str = "previous") -> Dict[str, Any]:
    """
    Compares current billing cycle side-by-side with previous cycle across usage, rates, fixed charges, and total cost.
    """
    return {
        "success": True,
        "tool_name": "compare_bill_periods",
        "data": {
            "current": DEFAULT_BILL,
            "previous": DEFAULT_PREVIOUS_BILL,
            "delta": {
                "usage_kwh_delta": DEFAULT_BILL["usage_kwh"] - DEFAULT_PREVIOUS_BILL["usage_kwh"],
                "total_bill_delta": round(DEFAULT_BILL["total_bill"] - DEFAULT_PREVIOUS_BILL["total_bill"], 2),
                "effective_rate_delta_cents": round(DEFAULT_BILL["effective_rate_cents_per_kwh"] - DEFAULT_PREVIOUS_BILL["effective_rate_cents_per_kwh"], 2)
            }
        },
        "source": "billing_comparator_engine"
    }
