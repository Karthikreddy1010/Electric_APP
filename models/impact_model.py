"""
Bill Impact Model wrapper around the unified BillImpactEngine.
Maintains backward compatibility and prevents duplicate model engines.
"""
from typing import Dict, Any, Optional
from api.services.bill_impact_engine import bill_impact_engine

class BillImpactModel:
    """
    Wrapper for backward compatibility.
    Delegates to the unified BillImpactEngine.
    """
    def __init__(self):
        # Match variables for any direct accesses
        self.beta_cdd = bill_impact_engine.beta_cdd
        self.beta_hdd = bill_impact_engine.beta_hdd
        self.intercept = bill_impact_engine.intercept
        self.calibrated = bill_impact_engine.calibrated
        self.components_config = {
            "customer_charge": ("Customer Charge", "fixed", "Fixed"),
            "distribution_cost": ("Distribution Charge", "usage-based", "Infrastructure"),
            "market_transition_cost": ("Transition Charges", "usage-based", "Regulatory"),
            "sbc_cost": ("Societal Benefits Charge", "usage-based", "Policy"),
            "transmission_cost": ("Transmission Charge", "usage-based", "Market"),
            "rider_cost": ("Rider Charges", "usage-based", "Regulatory"),
            "bgs_cost": ("BGS Supply", "usage-based", "Market"),
            "sales_tax": ("Sales Tax", "external-driven", "Policy")
        }

    def get_analysis(self, row: Dict[str, Any], prev_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return bill_impact_engine.get_analysis(row, prev_row)

def get_bill_impact(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function for API integration."""
    return bill_impact_engine.get_analysis(row)
