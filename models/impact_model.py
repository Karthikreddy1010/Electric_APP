"""
Bill Impact Model: Component Contribution and Sensitivity Analysis.
This module enforces the core analytical objective:
'If an individual electricity bill component increases or decreases, 
how much does the total bill change?'

Components:
- Customer Charge (fixed)
- Distribution Charge (kWh-based)
- Transition Charges
- Societal Benefits Charge (SBC)
- Transmission Charge
- Rider Charges
- Weather Normalization
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class BillImpactModel:
    """
    Core logic for quantifying component contributions and simulating impacts.
    Focuses on deterministic sensitivity rather than black-box models.
    """
    
    def __init__(self):
        # Component configuration: key in data -> (Label, Category, Driver)
        self.components_config = {
            "customer_charge": ("Customer Charge", "fixed", "fixed"),
            "distribution_cost": ("Distribution Charge", "usage-based", "infrastructure"),
            "market_transition_cost": ("Transition Charges", "usage-based", "policy-driven"),
            "sbc_cost": ("Societal Benefits Charge", "usage-based", "policy-driven"),
            "transmission_cost": ("Transmission Charge", "usage-based", "market-driven"),
            "rider_cost": ("Rider Charges", "usage-based", "policy-driven"),
            "weather_adjustment": ("Weather Normalization", "external-driven", "weather-driven"),
            "bgs_cost": ("BGS Supply", "usage-based", "market-driven"), # Included for completeness
            "sales_tax": ("Sales Tax", "external-driven", "policy-driven")
        }

    def get_analysis(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point to get contribution, sensitivity, and insights.
        Returns the specific JSON format requested.
        """
        total_bill = float(row.get("total_bill", 0))
        if total_bill == 0:
            return {}

        # 1. Contribution Calculation
        contributions = {}
        for key, (label, cat, driver) in self.components_config.items():
            val = float(row.get(key, 0))
            if val != 0:
                # Key used in JSON is the short key (e.g., 'distribution')
                json_key = key.replace("_cost", "").replace("_charge", "").replace("_adjustment", "")
                contributions[json_key] = {
                    "value": round(val, 2),
                    "percent": round((val / total_bill) * 100, 2)
                }

        # 2. Sensitivity Analysis (+/- 10%)
        sensitivity = {}
        tax_rate = 0.06625  # NJ Sales Tax
        
        for key, (label, cat, driver) in self.components_config.items():
            if key == "sales_tax": continue
            
            base_val = float(row.get(key, 0))
            if base_val == 0: continue
            
            json_key = key.replace("_cost", "").replace("_charge", "").replace("_adjustment", "")
            
            impacts = {}
            for pct in [10, -10]:
                delta = base_val * (pct / 100.0)
                # Total change includes the component change plus the proportional tax change
                total_delta = delta * (1 + tax_rate)
                impacts[f"{'+' if pct > 0 else ''}{pct}%"] = round(total_delta, 2)
            
            sensitivity[json_key] = impacts

        # 3. Insight Generation
        insights = self._generate_insights(contributions, sensitivity)

        return {
            "total_bill": round(total_bill, 2),
            "contributions": contributions,
            "sensitivity": sensitivity,
            "insights": insights
        }

    def _generate_insights(self, contributions: Dict, sensitivity: Dict) -> List[str]:
        """Generate human-readable explanations based on data drivers."""
        insights = []
        
        # Identify top driver
        sorted_contribs = sorted(contributions.items(), key=lambda x: x[1]['value'], reverse=True)
        if sorted_contribs:
            top_key, top_data = sorted_contribs[0]
            label = self.components_config.get(f"{top_key}_cost", 
                    self.components_config.get(f"{top_key}_charge", 
                    self.components_config.get(f"{top_key}_adjustment", (top_key.capitalize(), "", ""))))[0]
            insights.append(f"{label} is the primary driver, accounting for {top_data['percent']}% of the total bill.")

        # Sensitivity insight
        if "distribution" in sensitivity:
            dist_impact = sensitivity["distribution"]["+10%"]
            insights.append(f"Distribution charges have a high impact (${dist_impact:+.2f} per 10% change) due to usage dependency.")

        if "customer" in sensitivity:
            insights.append("Customer charge impact is fixed and does not scale with usage changes.")

        if "transmission" in sensitivity:
            insights.append("Transmission cost changes are market-driven and reflect regional grid congestion.")

        if "weather" in contributions:
            insights.append("Weather-related components show seasonal sensitivity and adjust based on abnormal temperatures.")

        # General policy insight
        policy_drivers = [k for k, v in self.components_config.items() if v[2] == "policy-driven"]
        policy_total = sum(contributions.get(k.replace("_cost","").replace("_charge",""), {}).get("percent", 0) for k in policy_drivers)
        if policy_total > 0:
            insights.append(f"Policy-driven components (SBC, Riders, etc.) represent {policy_total:.1f}% of the total cost structure.")

        return insights

def get_bill_impact(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function for API integration."""
    model = BillImpactModel()
    return model.get_analysis(row)
