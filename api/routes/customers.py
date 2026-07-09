import math
import logging
from datetime import date
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from database.connection import get_sync_session
from database.models import (
    CustomerProfile,
    CustomerBill,
    CustomerUsageHistory,
    CustomerForecast,
    CustomerSimulation,
    CustomerBillOCR
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["customers"])


@router.get("/customers")
async def get_customers():
    """List all synthetic customer profiles."""
    with get_sync_session() as session:
        rows = session.query(CustomerProfile).all()
        return [
            {
                "customer_id": r.customer_id,
                "utility": r.utility,
                "zip_code": r.zip_code,
                "rate_schedule": r.rate_schedule,
                "meter_number": r.meter_number
            }
            for r in rows
        ]


@router.get("/customers/{id}")
async def get_customer_details(id: str):
    """Retrieve details for a specific synthetic customer, including bills and history."""
    with get_sync_session() as session:
        profile = session.query(CustomerProfile).filter(CustomerProfile.customer_id == id).first()
        if not profile:
            raise HTTPException(404, f"Customer profile with ID {id} not found")
        
        bills = session.query(CustomerBill).filter(CustomerBill.customer_id == id).order_by(CustomerBill.bill_date.desc()).all()
        history = session.query(CustomerUsageHistory).filter(CustomerUsageHistory.customer_id == id).all()
        
        return {
            "profile": {
                "customer_id": profile.customer_id,
                "utility": profile.utility,
                "zip_code": profile.zip_code,
                "rate_schedule": profile.rate_schedule,
                "meter_number": profile.meter_number
            },
            "bills": [
                {
                    "id": b.id,
                    "bill_date": str(b.bill_date),
                    "billing_period": b.billing_period,
                    "days": b.days,
                    "usage_kwh": b.usage_kwh,
                    "total_bill": b.total_bill
                }
                for b in bills
            ],
            "usage_history": [
                {
                    "month_label": h.month_label,
                    "usage_kwh": h.usage_kwh,
                    "avg_temp_f": h.avg_temp_f
                }
                for h in history
            ]
        }


@router.get("/customers/{id}/bill")
async def get_customer_bill(id: str):
    """Get latest detailed bill breakdown and simulated Document AI OCR extraction metadata."""
    with get_sync_session() as session:
        bill = session.query(CustomerBill).filter(CustomerBill.customer_id == id).order_by(CustomerBill.bill_date.desc()).first()
        if not bill:
            raise HTTPException(404, f"No bill found for customer {id}")
            
        ocr_results = session.query(CustomerBillOCR).filter(
            CustomerBillOCR.customer_id == id,
            CustomerBillOCR.bill_date == bill.bill_date
        ).all()
        
        # Calculate effective rate
        effective_rate = bill.total_bill / bill.usage_kwh if bill.usage_kwh > 0 else 0
        
        return {
            "bill_details": {
                "id": bill.id,
                "bill_date": str(bill.bill_date),
                "billing_period": bill.billing_period,
                "days": bill.days,
                "previous_reading": bill.previous_reading,
                "current_reading": bill.current_reading,
                "usage_kwh": bill.usage_kwh,
                "monthly_service_charge": bill.monthly_service_charge,
                "delivery_charge": bill.delivery_charge,
                "supply_charge": bill.supply_charge,
                "tax": bill.tax,
                "total_bill": bill.total_bill,
                "average_daily_usage": bill.average_daily_usage,
                "average_daily_cost": bill.average_daily_cost,
                "utility_message": bill.utility_message,
                "weather_message": bill.weather_message,
                "energy_assistance_message": bill.energy_assistance_message,
                "net_metering_message": bill.net_metering_message,
                "ocr_text": bill.ocr_text,
                "effective_rate": round(effective_rate, 4)
            },
            "ocr_runs": [
                {
                    "field_name": o.field_name,
                    "ground_truth_value": o.ground_truth_value,
                    "extracted_value": o.extracted_value,
                    "confidence": o.confidence,
                    "ocr_error_flag": o.ocr_error_flag,
                    "bbox": o.bbox
                }
                for o in ocr_results
            ]
        }


@router.get("/customers/{id}/forecast")
async def get_customer_forecast(id: str):
    """Run/retrieve personalized usage and cost forecasts (30, 90, 365 days)."""
    with get_sync_session() as session:
        profile = session.query(CustomerProfile).filter(CustomerProfile.customer_id == id).first()
        if not profile:
            raise HTTPException(404, f"Customer {id} not found")
            
        history = session.query(CustomerUsageHistory).filter(CustomerUsageHistory.customer_id == id).all()
        if not history:
            raise HTTPException(404, f"No usage history available for forecasting")
            
        avg_usage = sum(h.usage_kwh for h in history) / len(history)
        
        forecast_date = date.today()
        existing = session.query(CustomerForecast).filter(
            CustomerForecast.customer_id == id,
            CustomerForecast.forecast_date == forecast_date
        ).all()
        
        if not existing:
            new_forecasts = []
            # Assume a baseline residential rate of 0.16 $/kWh for cost projections
            avg_rate = 0.16
            for days in [30, 90, 365]:
                predicted_kwh = avg_usage * (days / 30.4)
                predicted_cost = predicted_kwh * avg_rate
                
                # Confidence intervals increase with forecasting horizon
                uncertainty_pct = 0.10 + (days / 365.0) * 0.25
                margin_kwh = predicted_kwh * uncertainty_pct
                
                new_forecasts.append(CustomerForecast(
                    customer_id=id,
                    forecast_date=forecast_date,
                    days_ahead=days,
                    predicted_usage_kwh=round(predicted_kwh, 2),
                    predicted_cost=round(predicted_cost, 2),
                    confidence_lower=round(max(50, predicted_kwh - margin_kwh), 2),
                    confidence_upper=round(predicted_kwh + margin_kwh, 2)
                ))
            session.add_all(new_forecasts)
            session.commit()
            forecast_records = new_forecasts
        else:
            forecast_records = existing
            
        return [
            {
                "days_ahead": f.days_ahead,
                "predicted_usage_kwh": f.predicted_usage_kwh,
                "predicted_cost": f.predicted_cost,
                "confidence_lower": f.confidence_lower,
                "confidence_upper": f.confidence_upper,
                "forecast_date": str(f.forecast_date)
            }
            for f in forecast_records
        ]


@router.get("/customers/{id}/simulation")
async def run_customer_simulation(id: str):
    """Run what-if scenarios (e.g. rate changes or weather adjustments) using actual customer history."""
    with get_sync_session() as session:
        profile = session.query(CustomerProfile).filter(CustomerProfile.customer_id == id).first()
        if not profile:
            raise HTTPException(404, f"Customer {id} not found")
            
        history = session.query(CustomerUsageHistory).filter(CustomerUsageHistory.customer_id == id).all()
        if not history:
            raise HTTPException(404, f"No usage history found for customer {id}")
            
        annual_usage = sum(h.usage_kwh for h in history)
        # Use baseline RS rates for comparisons: Service: $4.62/month, Delivery: $0.055, Supply: $0.108, Tax: 6.625%
        base_service_charge = 4.62 * 12
        base_rate = 0.055 + 0.108
        actual_cost = (base_service_charge + annual_usage * base_rate) * 1.06625
        
        scenarios = [
            {
                "name": "Rate Increase 10%",
                "usage_multiplier": 1.0,
                "rate_multiplier": 1.10
            },
            {
                "name": "Summer Extreme Heatwave",
                "usage_multiplier": 1.15,
                "rate_multiplier": 1.0
            },
            {
                "name": "Smart Demand Response Shift",
                "usage_multiplier": 0.92,
                "rate_multiplier": 1.0
            }
        ]
        
        existing = session.query(CustomerSimulation).filter(CustomerSimulation.customer_id == id).all()
        if not existing:
            sims = []
            for sc in scenarios:
                sim_usage = annual_usage * sc["usage_multiplier"]
                sim_cost = (base_service_charge + sim_usage * base_rate * sc["rate_multiplier"]) * 1.06625
                
                sims.append(CustomerSimulation(
                    customer_id=id,
                    scenario_name=sc["name"],
                    simulated_annual_usage_kwh=round(sim_usage, 1),
                    simulated_annual_cost=round(sim_cost, 2),
                    difference_vs_actual=round(sim_cost - actual_cost, 2)
                ))
            session.add_all(sims)
            session.commit()
            sim_records = sims
        else:
            sim_records = existing
            
        return [
            {
                "scenario_name": s.scenario_name,
                "simulated_annual_usage_kwh": s.simulated_annual_usage_kwh,
                "simulated_annual_cost": s.simulated_annual_cost,
                "difference_vs_actual": s.difference_vs_actual,
                "actual_annual_cost_estimate": round(actual_cost, 2)
            }
            for s in sim_records
        ]


@router.get("/customers/{id}/impact")
async def get_customer_impact(id: str):
    """Analyze bill cost contribution factors (fixed, delivery, supply, weather, wholesale, tax)."""
    with get_sync_session() as session:
        bill = session.query(CustomerBill).filter(CustomerBill.customer_id == id).order_by(CustomerBill.bill_date.desc()).first()
        if not bill:
            raise HTTPException(404, f"No billing records found for customer {id}")
            
        # Calculate contribution breakdown
        weather_contrib = max(0.0, bill.temperature_difference * 0.015 * bill.total_bill)
        wholesale_contrib = bill.supply_charge * 0.08
        fixed_contrib = bill.monthly_service_charge
        delivery_use_contrib = bill.delivery_charge - fixed_contrib
        supply_use_contrib = bill.supply_charge - wholesale_contrib
        tax_contrib = bill.tax
        
        return {
            "total_bill": bill.total_bill,
            "components": [
                {"name": "Fixed Customer Service Charge", "amount": round(fixed_contrib, 2), "pct": round(fixed_contrib/bill.total_bill*100, 1)},
                {"name": "Grid Delivery Infrastructure", "amount": round(delivery_use_contrib, 2), "pct": round(delivery_use_contrib/bill.total_bill*100, 1)},
                {"name": "Standard Supply Generation", "amount": round(supply_use_contrib, 2), "pct": round(supply_use_contrib/bill.total_bill*100, 1)},
                {"name": "Wholesale Market Pricing Jitter", "amount": round(wholesale_contrib, 2), "pct": round(wholesale_contrib/bill.total_bill*100, 1)},
                {"name": "Weather-Induced Demand Load", "amount": round(weather_contrib, 2), "pct": round(weather_contrib/bill.total_bill*100, 1)},
                {"name": "State Sales Taxes (6.625%)", "amount": round(tax_contrib, 2), "pct": round(tax_contrib/bill.total_bill*100, 1)}
            ]
        }


@router.get("/customers/{id}/benchmark")
async def get_customer_benchmark(id: str):
    """Compare customer performance vs State, Regional, and National benchmarks."""
    with get_sync_session() as session:
        bill = session.query(CustomerBill).filter(CustomerBill.customer_id == id).order_by(CustomerBill.bill_date.desc()).first()
        if not bill:
            raise HTTPException(404, f"No bills found for customer {id}")
            
        bench_df = app_state.get("benchmark_df")
        if bench_df is None or bench_df.empty:
            # Hardcoded fallbacks if benchmark_df is unavailable
            state_avg_bill = 120.0
            state_avg_usage = 750.0
            national_avg_bill = 135.0
            national_avg_usage = 890.0
            regional_avg_bill = 128.0
            regional_avg_usage = 800.0
        else:
            # Query recent year data (e.g. 2025 or maximum available)
            max_year = bench_df["year"].max()
            year_data = bench_df[bench_df["year"] == max_year]
            
            nj_row = year_data[year_data["state"] == "NJ"]
            state_avg_bill = float(nj_row["avg_bill"].values[0]) if not nj_row.empty else 120.0
            state_avg_usage = float(nj_row["avg_usage_kwh"].values[0]) if not nj_row.empty and "avg_usage_kwh" in nj_row.columns else 750.0
            
            national_avg_bill = float(year_data["avg_bill"].mean())
            national_avg_usage = float(year_data["avg_usage_kwh"].mean()) if "avg_usage_kwh" in year_data.columns else 890.0
            
            # Regional (Middle Atlantic / Northeast average)
            reg_data = year_data[year_data.get("region", "") == "Middle Atlantic"]
            if reg_data.empty:
                reg_data = year_data
            regional_avg_bill = float(reg_data["avg_bill"].mean())
            regional_avg_usage = float(reg_data["avg_usage_kwh"].mean()) if "avg_usage_kwh" in reg_data.columns else 800.0

        cust_usage = bill.usage_kwh
        cust_bill = bill.total_bill
        
        # Calculate percentile using standard normal distribution assumptions (std dev = 35% of mean)
        std_dev = state_avg_usage * 0.35
        def norm_cdf(x, mean, std):
            return 0.5 * (1 + math.erf((x - mean) / (std * (2**0.5))))
        percentile = round(norm_cdf(cust_usage, state_avg_usage, std_dev) * 100, 1)
        
        # Calculate savings opportunity if they reduced consumption to state average
        savings_opp = max(0.0, cust_bill - state_avg_bill)
        if savings_opp == 0:
            # If already below state average, savings from a 10% efficiency shift
            savings_opp = cust_bill * 0.10
            
        return {
            "customer": {
                "monthly_bill": cust_bill,
                "monthly_usage_kwh": cust_usage,
                "percentile": percentile
            },
            "comparisons": [
                {"name": "State Average (NJ)", "avg_bill": round(state_avg_bill, 2), "avg_usage_kwh": int(state_avg_usage), "diff_bill": round(cust_bill - state_avg_bill, 2)},
                {"name": "Regional Average (Mid-Atlantic)", "avg_bill": round(regional_avg_bill, 2), "avg_usage_kwh": int(regional_avg_usage), "diff_bill": round(cust_bill - regional_avg_bill, 2)},
                {"name": "National Average (US)", "avg_bill": round(national_avg_bill, 2), "avg_usage_kwh": int(national_avg_usage), "diff_bill": round(cust_bill - national_avg_bill, 2)}
            ],
            "savings_opportunity": round(savings_opp, 2)
        }
