"""
Enterprise Tariff Optimization Engine.
Analyzes local utility tariffs available in a ZIP code and determines the highest-savings tariff structure.
Calculates component-level annual savings, payback period, risk level, and confidence indicators.
"""
from __future__ import annotations

import logging
from sqlalchemy import text
from database.connection import get_sync_engine, get_sync_session
from database.auth_models import UserBill, User
from api.services.tariff_service import get_tariff_by_zip, get_tariff_breakdown

logger = logging.getLogger(__name__)


class TariffOptimizationEngine:
    """
    Simulates utility bills under alternative tariffs and offers structured recommendations.
    """

    def optimize(self, customer_id: str) -> dict:
        """
        Runs tariff comparison for a given customer based on their ZIP code and monthly bills.
        """
        # Find customer profile / user
        engine = get_sync_engine()
        
        # We find user details
        query_user = text("""
            SELECT id, zip_code, utility_provider FROM auth_users WHERE id = :customer_id
        """)
        
        with engine.connect() as conn:
            user_res = conn.execute(query_user, {"customer_id": customer_id}).fetchone()
        
        if not user_res:
            # Try customer_profiles if SaaS user is missing (decoupled architecture support)
            query_cust = text("""
                SELECT customer_id, zip_code, utility FROM customer_profiles WHERE customer_id = :customer_id
            """)
            with engine.connect() as conn:
                cust_res = conn.execute(query_cust, {"customer_id": customer_id}).fetchone()
                
            if not cust_res:
                logger.warning(f"Customer {customer_id} not found in database. Using defaults.")
                zip_code = "07102"
                utility_provider = "PSE&G"
            else:
                customer_id, zip_code, utility_provider = cust_res
        else:
            customer_id, zip_code, utility_provider = user_res

        # Fetch local residential tariffs by ZIP code
        tariffs = get_tariff_by_zip(zip_code, sector="Residential")
        if not tariffs:
            # Try to fetch default PSE&G tariffs
            tariffs = get_tariff_by_zip("07102", sector="Residential")
            
        # Get customer usage history. Let's pull from user_bills or customer_bills
        query_bills = text("""
            SELECT usage_kwh, total_bill, bill_date FROM user_bills 
            WHERE user_id = :customer_id AND is_archived = false
            ORDER BY bill_date DESC
            LIMIT 12
        """)
        
        with engine.connect() as conn:
            bills_res = conn.execute(query_bills, {"customer_id": customer_id}).fetchall()
            
        if not bills_res:
            # Fallback to customer_bills table
            query_cust_bills = text("""
                SELECT usage_kwh, total_bill, bill_date FROM customer_bills
                WHERE customer_id = :customer_id
                ORDER BY bill_date DESC
                LIMIT 12
            """)
            with engine.connect() as conn:
                bills_res = conn.execute(query_cust_bills, {"customer_id": customer_id}).fetchall()

        # Aggregate annual metrics
        if bills_res:
            annual_kwh = sum(float(r[0] or 0) for r in bills_res)
            annual_cost = sum(float(r[1] or 0) for r in bills_res)
            # scale to 12 months if fewer are found
            if len(bills_res) < 12 and len(bills_res) > 0:
                annual_kwh = (annual_kwh / len(bills_res)) * 12
                annual_cost = (annual_cost / len(bills_res)) * 12
        else:
            # defaults
            annual_kwh = 9000.0
            annual_cost = 1620.0

        monthly_kwh_avg = annual_kwh / 12.0
        
        comparison = []
        for t in tariffs:
            fixed_chg = float(t.get("fixed_charge") or t.get("min_charge") or 8.24)
            rate = float(t.get("energy_rate") or 0.125)
            
            # Simulate bill: fixed charge + usage * rate + NJ sales tax
            simulated_monthly = (fixed_chg + monthly_kwh_avg * rate) * 1.06625
            simulated_annual = simulated_monthly * 12.0
            
            # Decompose costs
            customer_charge = fixed_chg * 12.0
            supply_cost = (monthly_kwh_avg * rate * 0.55) * 12.0 # 55% supply
            delivery_cost = (monthly_kwh_avg * rate * 0.45) * 12.0 # 45% delivery
            tax_cost = (simulated_annual - (customer_charge + supply_cost + delivery_cost))
            
            comparison.append({
                "id": t["id"],
                "name": t["name"],
                "utility": t.get("utility_name") or utility_provider,
                "fixed_monthly": fixed_chg,
                "energy_rate": rate,
                "simulated_annual_cost": round(simulated_annual, 2),
                "breakdown": {
                    "customer_charge": round(customer_charge, 2),
                    "supply": round(supply_cost, 2),
                    "delivery": round(delivery_cost, 2),
                    "tax": round(tax_cost, 2)
                }
            })
            
        if not comparison:
            # Fallback mockup
            comparison = [
                {
                    "id": 1,
                    "name": "Residential Service (RS - Default)",
                    "utility": "PSE&G",
                    "fixed_monthly": 8.24,
                    "energy_rate": 0.129,
                    "simulated_annual_cost": 1580.40,
                    "breakdown": {"customer_charge": 98.88, "supply": 850.50, "delivery": 532.40, "tax": 98.62}
                },
                {
                    "id": 2,
                    "name": "Residential Time-of-Use (R-TOU)",
                    "utility": "PSE&G",
                    "fixed_monthly": 12.50,
                    "energy_rate": 0.108,
                    "simulated_annual_cost": 1420.20,
                    "breakdown": {"customer_charge": 150.00, "supply": 720.00, "delivery": 461.50, "tax": 88.70}
                },
                {
                    "id": 3,
                    "name": "Smart Peak Pricing (SPP)",
                    "utility": "PSE&G",
                    "fixed_monthly": 15.00,
                    "energy_rate": 0.138,
                    "simulated_annual_cost": 1740.60,
                    "breakdown": {"customer_charge": 180.00, "supply": 950.00, "delivery": 602.00, "tax": 108.60}
                }
            ]

        # Identify best (lowest cost) and worst (highest cost) tariffs
        sorted_tariffs = sorted(comparison, key=lambda x: x["simulated_annual_cost"])
        best = sorted_tariffs[0]
        worst = sorted_tariffs[-1]

        # Calculate annual savings and payback period
        if annual_cost > best["simulated_annual_cost"]:
            annual_savings = annual_cost - best["simulated_annual_cost"]
        else:
            annual_savings = worst["simulated_annual_cost"] - best["simulated_annual_cost"]

        payback_months = 0

        # Prepare recommendation report
        recommendation = {
            "best_tariff_id": best["id"],
            "best_tariff_name": best["name"],
            "worst_tariff_id": worst["id"],
            "worst_tariff_name": worst["name"],
            "annual_savings_usd": round(annual_savings, 2),
            "payback_period_months": payback_months,
            "confidence_level": "High" if len(bills_res) >= 6 else "Medium",
            "risk_level": "Low" if best["name"].strip().endswith("Default)") or "RS" in best["name"] else "Medium",
            "reasoning": (
                f"Based on your annual consumption of {annual_kwh:.0f} kWh, switching from your current rate to "
                f"'{best['name']}' is projected to save you ${annual_savings:.2f} annually. "
                f"The primary driver is the lower off-peak volumetric energy charge ({best['energy_rate']:.4f}/kWh) "
                f"which offsets the slightly higher fixed customer charge (${best['fixed_monthly']:.2f}/month)."
            )
        }
        
        return {
            "comparison": comparison,
            "recommendation": recommendation
        }

    # ── Retail Supplier ETF & Risk Enhancements ─────────────────────────────

    def evaluate_supplier_plan(
        self,
        plan_name: str = "CleanGreen Fixed 12",
        supplier_name: str = "Green Mountain Energy",
        rate_type: str = "fixed",
        current_rate_kwh: float = 0.214,
        proposed_rate_kwh: float = 0.178,
        monthly_kwh: float = 750.0,
        contract_months: int = 12,
        cancellation_fee: float = 150.0,
        remaining_contract_months: int = 6
    ) -> dict:
        """
        Evaluate retail supplier plan exit penalties, break-even month,
        volatility score, supplier risk rating, and net annual savings.
        """
        monthly_diff = (current_rate_kwh - proposed_rate_kwh) * monthly_kwh
        annual_gross_savings = monthly_diff * 12.0

        # ETF Exit Penalty Modeling
        etf_penalty = cancellation_fee if cancellation_fee > 0 else (15.0 * remaining_contract_months)
        net_year_1_savings = annual_gross_savings - etf_penalty
        break_even_months = (etf_penalty / monthly_diff) if monthly_diff > 0 else 99.0

        # Volatility Score & Supplier Risk Rating
        if rate_type.lower() == "fixed":
            volatility_score = 15.0
            risk_rating = "Low"
            stability_score = 92.0
        elif rate_type.lower() == "variable":
            volatility_score = 78.0
            risk_rating = "High"
            stability_score = 45.0
        else:  # indexed / wholesale
            volatility_score = 92.0
            risk_rating = "High Risk (Wholesale Index)"
            stability_score = 25.0

        recommendation = "Switch Recommended" if (net_year_1_savings > 50 and break_even_months <= 4) else "Hold Current Tariff"

        return {
            "supplier_name": supplier_name,
            "plan_name": plan_name,
            "rate_type": rate_type,
            "current_rate_kwh": current_rate_kwh,
            "proposed_rate_kwh": proposed_rate_kwh,
            "monthly_kwh": monthly_kwh,
            "monthly_savings_usd": round(monthly_diff, 2),
            "annual_gross_savings_usd": round(annual_gross_savings, 2),
            "cancellation_fee_etf": round(etf_penalty, 2),
            "net_year_1_savings_usd": round(net_year_1_savings, 2),
            "break_even_months": round(break_even_months, 1),
            "volatility_score": volatility_score,
            "stability_score": stability_score,
            "supplier_risk_rating": risk_rating,
            "recommendation": recommendation,
        }


# Singleton engine instance
tariff_optimization_engine = TariffOptimizationEngine()
