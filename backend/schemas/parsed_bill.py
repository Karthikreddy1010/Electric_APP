"""
backend.schemas.parsed_bill — Pydantic schema for structured, parsed bill data.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class BillingPeriodSchema(BaseModel):
    """Structured billing period definition."""
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    days: int = Field(30, ge=1, le=366, description="Billing cycle days")


class ParsedBill(BaseModel):
    """Validated structured bill input payload."""
    bill_hash: str = Field(..., description="SHA-256 hash of the original file")
    customer_id: str = Field("UPLOADED-BILL", description="Customer identifier")
    utility: str = Field("PSE&G", description="Utility company name")
    zip_code: str = Field("07102", description="ZIP code of service address")
    rate_schedule: str = Field("RS", description="Utility rate schedule code")
    account_number: str = Field("PSEG-1234567", description="Utility account number")
    meter_number: str = Field("MET-1000000", description="Electric meter identifier")
    
    bill_date: str = Field(..., description="Statement date YYYY-MM-DD")
    due_date: Optional[str] = Field(None, description="Payment due date YYYY-MM-DD")
    billing_period: str = Field(..., description="String range 'YYYY-MM-DD to YYYY-MM-DD'")
    days: int = Field(30, ge=1, le=366, description="Days in billing period")
    
    previous_reading: int = Field(0, ge=0, description="Previous meter reading (kWh)")
    current_reading: int = Field(0, ge=0, description="Current meter reading (kWh)")
    usage_kwh: float = Field(0.0, ge=0.0, description="Total billed electricity consumption (kWh)")
    
    # Financial line items ($)
    monthly_service_charge: float = Field(0.0, ge=0.0, description="Fixed monthly customer charge ($)")
    delivery_charge: float = Field(0.0, ge=0.0, description="Distribution & delivery charges ($)")
    supply_charge: float = Field(0.0, ge=0.0, description="Basic Generation Service (BGS) supply charge ($)")
    
    # Unbundled delivery component detail ($)
    bgs_cost: Optional[float] = Field(None, description="Commodity supply cost ($)")
    distribution_cost: Optional[float] = Field(None, description="Local distribution cost ($)")
    transmission_cost: Optional[float] = Field(None, description="High-voltage transmission cost ($)")
    sbc_cost: Optional[float] = Field(None, description="Societal benefits charge ($)")
    market_transition_cost: Optional[float] = Field(None, description="Market transition charge ($)")
    rider_cost: Optional[float] = Field(None, description="Regulatory rider charges ($)")
    nug_cost: Optional[float] = Field(None, description="Non-utility generation charge ($)")
    
    tax: float = Field(0.0, ge=0.0, description="Sales and local taxes ($)")
    total_bill: float = Field(0.0, ge=0.0, description="Total statement amount due ($)")
    
    # Calculated baseline metrics
    average_daily_usage: float = Field(0.0, ge=0.0, description="Average daily consumption (kWh/day)")
    average_daily_cost: float = Field(0.0, ge=0.0, description="Average daily spend ($/day)")
    effective_rate: float = Field(0.0, ge=0.0, description="Effective volumetric price ($/kWh)")
    
    parser_version: str = Field("1.0.0", description="Parser version string")
    parser_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Parser extraction confidence")
    raw_text_snippet: Optional[str] = Field(None, description="First 200 chars of source text")
