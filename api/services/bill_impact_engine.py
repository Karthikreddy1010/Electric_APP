"""
Bill Impact Engine — Deterministic, Statistical, and Causal Analysis of Electricity Costs.

This module implements:
1. Deterministic Layer (Accounting Identity): Bill = Sum(Components)
2. Statistical Layer (Regression): Partial correlations and elasticity
3. Causal Layer (DoWhy/DML): True impact of rate changes controlling for usage/weather.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

from api.state import app_state

logger = logging.getLogger(__name__)

# Constants
NJ_SALES_TAX_RATE = 0.06625

COMPONENT_TYPES = {
    "customer_charge": {
        "label": "Customer Charge",
        "type": "fixed",
        "cost_col": "customer_charge",
        "driver": "fixed",
        "reasoning": "Fixed impact independent of consumption; reflects the cost of maintaining the account and meter connection.",
        "controllable": "No",
    },
    "bgs_rate": {
        "label": "BGS Supply",
        "type": "variable",
        "cost_col": "bgs_cost",
        "driver": "market",
        "reasoning": "High impact because scales with usage (kWh). Reflects wholesale electricity supply prices.",
        "controllable": "Yes",
    },
    "distribution_rate": {
        "label": "Distribution Charge",
        "type": "variable",
        "cost_col": "distribution_cost",
        "driver": "infrastructure",
        "reasoning": "Significant impact scaling with usage; funds local delivery infrastructure.",
        "controllable": "Partial",
    },
    "transmission_rate": {
        "label": "Transmission Charge",
        "type": "variable",
        "cost_col": "transmission_cost",
        "driver": "market",
        "reasoning": "Scales with usage; reflects regional high-voltage grid costs.",
        "controllable": "No",
    },
    "sbc_rate": {
        "label": "Societal Benefits Charge",
        "type": "variable",
        "cost_col": "sbc_cost",
        "driver": "policy",
        "reasoning": "Lower impact scaling with usage; funds energy efficiency and social programs.",
        "controllable": "No",
    },
    "transition_rate": {
        "label": "Transition Charge",
        "type": "variable",
        "cost_col": "market_transition_cost",
        "driver": "regulatory",
        "reasoning": "Transition charge from deregulation of electricity markets.",
        "controllable": "No",
    },
    "nug_rate": {
        "label": "Non-Utility Generation Charge",
        "type": "variable",
        "cost_col": "nug_cost",
        "driver": "regulatory",
        "reasoning": "Charges related to legacy non-utility generation contracts.",
        "controllable": "No",
    },
    "rider_rate": {
        "label": "Rider Charges",
        "type": "variable",
        "cost_col": "rider_cost",
        "driver": "regulatory",
        "reasoning": "Supplemental charges for infrastructure recovery and programs.",
        "controllable": "No",
    },
}


class BillImpactEngine:
    def __init__(self):
        self.tax_rate = NJ_SALES_TAX_RATE
        self.beta_cdd = 0.85
        self.beta_hdd = 0.45
        self.intercept = 450.0
        self.calibrated = False
        self._calibrate_from_history()

    def get_elasticity(self) -> float:
        demand_model = app_state.get("demand_model")
        if demand_model and demand_model.is_trained:
            return demand_model.get_learned_elasticity()
        return -0.20

    def _calibrate_from_history(self):
        """Fit a robust Least-Squares regression of usage on CDD and HDD using NOAA air_temp.csv and billing history."""
        try:
            root_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = root_dir / "data" / "raw"
            air_temp_path = data_dir / "air_temp.csv"
            billing_path = data_dir / "billing.csv"
            if not billing_path.exists():
                billing_path = data_dir / "billing.parquet"
                
            if air_temp_path.exists() and billing_path.exists():
                logger.info(f"Calibrating weather attribution from {air_temp_path.name} and {billing_path.name}...")
                
                # 1. Parse weather data and compute daily CDD & HDD
                weather_df = pd.read_csv(air_temp_path)
                weather_df["DATE"] = pd.to_datetime(weather_df["DATE"])
                
                # Compute TAVG if missing
                if "TAVG" not in weather_df.columns or weather_df["TAVG"].isna().all():
                    weather_df["TAVG"] = (weather_df["TMAX"].astype(float) + weather_df["TMIN"].astype(float)) / 2
                else:
                    weather_df["TAVG"] = weather_df["TAVG"].astype(float).fillna(
                        (weather_df["TMAX"].astype(float) + weather_df["TMIN"].astype(float)) / 2
                    )
                
                weather_df["CDD"] = np.maximum(0, weather_df["TAVG"] - 65)
                weather_df["HDD"] = np.maximum(0, 65 - weather_df["TAVG"])
                weather_df["month_str"] = weather_df["DATE"].dt.strftime("%Y-%m")
                
                # Aggregate CDD/HDD to monthly sums
                weather_monthly = weather_df.groupby("month_str")[["CDD", "HDD"]].sum()
                
                # 2. Parse billing data
                if billing_path.suffix == ".csv":
                    bill_df = pd.read_csv(billing_path)
                else:
                    bill_df = pd.read_parquet(billing_path)
                
                bill_df["month_str"] = pd.to_datetime(bill_df["date"]).dt.strftime("%Y-%m")
                
                # 3. Merge billing and weather datasets
                merged = bill_df.merge(weather_monthly, on="month_str", how="left")
                
                # Climatological averages for NJ missing months fallback
                def get_climatology(month_num):
                    cdd_map = {1:0.0, 2:0.0, 3:0.0, 4:5.0, 5:45.0, 6:180.0, 7:310.0, 8:260.0, 9:100.0, 10:15.0, 11:0.0, 12:0.0}
                    hdd_map = {1:950.0, 2:820.0, 3:650.0, 4:350.0, 5:120.0, 6:10.0, 7:0.0, 8:0.0, 9:30.0, 10:220.0, 11:500.0, 12:820.0}
                    return cdd_map.get(month_num, 0.0), hdd_map.get(month_num, 0.0)
                
                for idx, row in merged.iterrows():
                    m_num = pd.to_datetime(row["date"]).month
                    clim_cdd, clim_hdd = get_climatology(m_num)
                    if pd.isna(row["CDD"]):
                        merged.at[idx, "CDD"] = clim_cdd
                    if pd.isna(row["HDD"]):
                        merged.at[idx, "HDD"] = clim_hdd
                
                # 4. Solve Least-Squares Regression (effective_kwh = intercept + beta_cdd * CDD + beta_hdd * HDD)
                from models.pjm_market_physics import DEFAULT_PJM
                X = np.column_stack([
                    np.ones(len(merged)),
                    merged["CDD"].values,
                    merged["HDD"].values
                ])
                y = (merged["usage_kwh"] * (1.0 + DEFAULT_PJM.total_loss_factor)).values
                
                coefs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                
                self.intercept = float(max(coefs[0], 100.0))
                self.beta_cdd = float(max(coefs[1], 0.05))
                self.beta_hdd = float(max(coefs[2], 0.05))
                self.calibrated = True
                logger.info(f"Weather OLS Regression Calibrated on Effective kWh: Int={self.intercept:.1f}, CDD={self.beta_cdd:.3f}, HDD={self.beta_hdd:.3f}")
        except Exception as e:
            logger.warning(f"Weather regression calibration failed, using defaults: {e}")

    def _enrich_components_with_tariff(self, components: dict[str, float]) -> dict[str, float]:
        """Enrich components dict with real tariff-derived values if lookup succeeds."""
        enriched = components.copy()
        try:
            from api.services.tariff_service import get_default_residential_tariff, _parse_rate_structure
            eia_utility_id = int(components.get("eia_utility_id") or 15477)
            tariff = get_default_residential_tariff(eia_utility_id)
            if tariff:
                if tariff.get("fixed_charge") is not None:
                    enriched["customer_charge"] = float(tariff["fixed_charge"])
                
                rate_struct = _parse_rate_structure(tariff.get("energy_rate_structure"))
                if rate_struct and isinstance(rate_struct, list) and len(rate_struct) > 0:
                    period = rate_struct[0]
                    if isinstance(period, list) and len(period) > 0:
                        tier = period[0]
                        base_rate = float(tier.get("rate", 0.0))
                        adj = float(tier.get("adj", 0.0))
                        
                        # Isolate BGS and Delivery
                        if base_rate > 0.09:
                            bgs = 0.10279
                            delivery = base_rate - bgs
                        else:
                            bgs = 0.12
                            delivery = base_rate
                        
                        # Populate if not explicitly provided (keep explicit overrides)
                        if "bgs_rate" not in components:
                            enriched["bgs_rate"] = bgs
                        if "distribution_rate" not in components:
                            enriched["distribution_rate"] = round(delivery * 0.8, 5)
                        if "transmission_rate" not in components:
                            enriched["transmission_rate"] = round(delivery * 0.2, 5)
                        if "sbc_rate" not in components:
                            enriched["sbc_rate"] = round(adj * 0.75, 5)
                        if "transition_rate" not in components:
                            enriched["transition_rate"] = round(adj * 0.25, 5)
                        if "nug_rate" not in components:
                            enriched["nug_rate"] = 0.002
                        if "rider_rate" not in components:
                            enriched["rider_rate"] = 0.005
        except Exception as e:
            logger.warning(f"Failed to enrich billing components with tariff: {e}")
        return enriched

    def parse_and_estimate_uploaded_bill(self, bill_data: dict) -> dict:
        """
        Creates a standardized uploaded bill component object.
        Estimates any missing components using the applicable PSE&G tariff structure ratios.
        """
        usage = float(bill_data.get("usage_kwh", bill_data.get("kWh", 750.0)))
        total = float(bill_data.get("total_bill", bill_data.get("Total Bill", 138.90)))
        
        # Extract direct inputs if present
        customer_charge_val = float(bill_data.get("monthly_service_charge", bill_data.get("customer_charge", 0.0)))
        if customer_charge_val == 0.0:
            customer_charge_val = 8.24
            cc_src, cc_conf = "Estimated using tariff", "Estimated"
        else:
            cc_src, cc_conf = "OCR", "99%"

        tax_val = float(bill_data.get("tax", bill_data.get("sales_tax", 0.0)))
        if tax_val == 0.0:
            tax_val = round((total - total / 1.06625), 2)
            tax_src, tax_conf = "Estimated using tariff", "Estimated"
        else:
            tax_src, tax_conf = "OCR", "99%"

        supply_val = float(bill_data.get("supply_charge", bill_data.get("bgs_cost", 0.0)))
        if supply_val == 0.0:
            subtotal = total / 1.06625
            supply_val = round((subtotal - customer_charge_val) * 0.58, 2)
            bgs_src, bgs_conf = "Estimated using tariff", "Estimated"
        else:
            bgs_src, bgs_conf = "OCR", "99%"
        bgs_rate = round(supply_val / usage, 5) if usage > 0 else 0.1052

        delivery_val = float(bill_data.get("delivery_charge", 0.0))
        if delivery_val == 0.0:
            delivery_val = round(total - tax_val - supply_val, 2)
            
        var_deliv = max(0.0, delivery_val - customer_charge_val)

        # Standard PSE&G RS variable delivery component allocation ratios
        components_to_estimate = {
            "distribution_cost": ("distribution_rate", 0.55, 0.0422),
            "transmission_cost": ("transmission_rate", 0.22, 0.0157),
            "sbc_cost": ("sbc_rate", 0.08, 0.0036),
            "market_transition_cost": ("transition_rate", 0.04, 0.002),
            "rider_cost": ("rider_rate", 0.06, 0.004),
            "nug_cost": ("nug_rate", 0.05, 0.001)
        }

        computed_components = {}
        sources = {
            "customer_charge": cc_src,
            "bgs_cost": bgs_src,
            "sales_tax": tax_src
        }
        confidences = {
            "customer_charge": cc_conf,
            "bgs_cost": bgs_conf,
            "sales_tax": tax_conf
        }

        for comp_key, (rate_key, ratio, fallback_rate) in components_to_estimate.items():
            if comp_key in bill_data and float(bill_data[comp_key]) > 0:
                comp_val = float(bill_data[comp_key])
                sources[comp_key] = "OCR"
                confidences[comp_key] = "99%"
            else:
                comp_val = round(var_deliv * ratio, 2)
                sources[comp_key] = "Estimated using tariff"
                confidences[comp_key] = "Estimated"
            computed_components[comp_key] = comp_val
            computed_components[rate_key] = round(comp_val / usage, 5) if usage > 0 else fallback_rate

        standard_obj = {
            "usage_kwh": usage,
            "total_bill": total,
            "sales_tax": tax_val,
            "date": str(bill_data.get("bill_date", bill_data.get("date", "2026-06-30"))),
            "utility": str(bill_data.get("utility", "PSE&G")),
            "rates": {
                "customer_charge": customer_charge_val,
                "bgs_rate": bgs_rate,
                "distribution_rate": computed_components["distribution_rate"],
                "transmission_rate": computed_components["transmission_rate"],
                "sbc_rate": computed_components["sbc_rate"],
                "transition_rate": computed_components["transition_rate"],
                "nug_rate": computed_components["nug_rate"],
                "rider_rate": computed_components["rider_rate"]
            },
            "costs": {
                "customer_charge": customer_charge_val,
                "bgs_cost": supply_val,
                "distribution_cost": computed_components["distribution_cost"],
                "transmission_cost": computed_components["transmission_cost"],
                "sbc_cost": computed_components["sbc_cost"],
                "market_transition_cost": computed_components["market_transition_cost"],
                "rider_cost": computed_components["rider_cost"],
                "nug_cost": computed_components["nug_cost"],
                "sales_tax": tax_val
            },
            "metadata": {
                "sources": sources,
                "confidences": confidences
            }
        }

        # Build list representing breakdown for immediate rendering in UI
        breakdown_items = [
            {
                "key": "customer_charge",
                "name": COMPONENT_TYPES["customer_charge"]["label"],
                "value": customer_charge_val,
                "pct": round(customer_charge_val / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["customer_charge"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["customer_charge"]["controllable"],
                "source": sources["customer_charge"],
                "confidence": confidences["customer_charge"]
            },
            {
                "key": "bgs_cost",
                "name": COMPONENT_TYPES["bgs_rate"]["label"],
                "value": supply_val,
                "pct": round(supply_val / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["bgs_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["bgs_rate"]["controllable"],
                "source": sources["bgs_cost"],
                "confidence": confidences["bgs_cost"]
            },
            {
                "key": "distribution_cost",
                "name": COMPONENT_TYPES["distribution_rate"]["label"],
                "value": computed_components["distribution_cost"],
                "pct": round(computed_components["distribution_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["distribution_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["distribution_rate"]["controllable"],
                "source": sources["distribution_cost"],
                "confidence": confidences["distribution_cost"]
            },
            {
                "key": "transmission_cost",
                "name": COMPONENT_TYPES["transmission_rate"]["label"],
                "value": computed_components["transmission_cost"],
                "pct": round(computed_components["transmission_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["transmission_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["transmission_rate"]["controllable"],
                "source": sources["transmission_cost"],
                "confidence": confidences["transmission_cost"]
            },
            {
                "key": "sbc_cost",
                "name": COMPONENT_TYPES["sbc_rate"]["label"],
                "value": computed_components["sbc_cost"],
                "pct": round(computed_components["sbc_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["sbc_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["sbc_rate"]["controllable"],
                "source": sources["sbc_cost"],
                "confidence": confidences["sbc_cost"]
            },
            {
                "key": "market_transition_cost",
                "name": COMPONENT_TYPES["transition_rate"]["label"],
                "value": computed_components["market_transition_cost"],
                "pct": round(computed_components["market_transition_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["transition_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["transition_rate"]["controllable"],
                "source": sources["market_transition_cost"],
                "confidence": confidences["market_transition_cost"]
            },
            {
                "key": "rider_cost",
                "name": COMPONENT_TYPES["rider_rate"]["label"],
                "value": computed_components["rider_cost"],
                "pct": round(computed_components["rider_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["rider_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["rider_rate"]["controllable"],
                "source": sources["rider_cost"],
                "confidence": confidences["rider_cost"]
            },
            {
                "key": "nug_cost",
                "name": COMPONENT_TYPES["nug_rate"]["label"],
                "value": computed_components["nug_cost"],
                "pct": round(computed_components["nug_cost"] / total * 100, 2) if total > 0 else 0,
                "type": COMPONENT_TYPES["nug_rate"]["type"].capitalize(),
                "controllable": COMPONENT_TYPES["nug_rate"]["controllable"],
                "source": sources["nug_cost"],
                "confidence": confidences["nug_cost"]
            },
            {
                "key": "sales_tax",
                "name": "Sales Tax",
                "value": tax_val,
                "pct": round(tax_val / total * 100, 2) if total > 0 else 0,
                "type": "Tax",
                "controllable": "No",
                "source": sources["sales_tax"],
                "confidence": confidences["sales_tax"]
            }
        ]
        standard_obj["breakdown"] = breakdown_items
        return standard_obj

    def _calculate_total_bill_from_costs(self, costs: dict) -> float:
        subtotal = sum(v for k, v in costs.items() if k != "sales_tax")
        tax = round(subtotal * self.tax_rate, 2)
        return round(subtotal + tax, 2)

    def contribution_analysis(self, components_obj: dict) -> dict:
        """Contribution analysis mapping each component to its cost and percentage."""
        return {
            "total_bill": components_obj["total_bill"],
            "usage_kwh": components_obj["usage_kwh"],
            "breakdown": components_obj["breakdown"]
        }

    def automatic_sensitivity_analysis(self, components_obj: dict) -> list[dict]:
        """Automatically simulate impact of ±10% variation per component."""
        base_total = components_obj["total_bill"]
        costs = components_obj["costs"]
        
        results = []
        comp_labels = {
            "customer_charge": "Customer Charge",
            "bgs_cost": "BGS Supply",
            "distribution_cost": "Distribution Charge",
            "transmission_cost": "Transmission Charge",
            "sbc_cost": "Societal Benefits Charge",
            "market_transition_cost": "Transition Charge",
            "rider_cost": "Rider Charges",
            "nug_cost": "Non-Utility Generation Charge",
        }
        
        for key, label in comp_labels.items():
            base_val = costs.get(key, 0.0)
            
            # +10%
            new_val_up = base_val * 1.10
            new_costs_up = costs.copy()
            new_costs_up[key] = new_val_up
            new_total_up = self._calculate_total_bill_from_costs(new_costs_up)
            diff_up = round(new_total_up - base_total, 2)
            diff_pct_up = round((diff_up / base_total * 100), 2) if base_total > 0 else 0.0

            # -10%
            new_val_down = base_val * 0.90
            new_costs_down = costs.copy()
            new_costs_down[key] = new_val_down
            new_total_down = self._calculate_total_bill_from_costs(new_costs_down)
            diff_down = round(new_total_down - base_total, 2)
            diff_pct_down = round((diff_down / base_total * 100), 2) if base_total > 0 else 0.0
            
            results.append({
                "key": key,
                "label": label,
                "base_value": base_val,
                "increase_10_val": round(new_val_up, 2),
                "increase_10_bill": new_total_up,
                "increase_10_diff": diff_up,
                "increase_10_pct": diff_pct_up,
                "decrease_10_val": round(new_val_down, 2),
                "decrease_10_bill": new_total_down,
                "decrease_10_diff": diff_down,
                "decrease_10_pct": diff_pct_down,
            })
        return results

    def rank_components_from_bill(self, components_obj: dict) -> list[dict]:
        """Rank components according to their impact on the uploaded customer's bill."""
        costs = components_obj["costs"]
        total = components_obj["total_bill"]
        
        ranks = []
        comp_labels = {
            "customer_charge": "Customer Charge",
            "bgs_cost": "BGS Supply",
            "distribution_cost": "Distribution Charge",
            "transmission_cost": "Transmission Charge",
            "sbc_cost": "Societal Benefits Charge (SBC)",
            "market_transition_cost": "Transition Charge",
            "rider_cost": "Rider Charges",
            "nug_cost": "Non-Utility Generation Charge"
        }
        
        for key, label in comp_labels.items():
            val = costs.get(key, 0.0)
            share = (val * (1 + self.tax_rate)) / total if total > 0 else 0
            ranks.append({
                "key": key,
                "label": label,
                "value": val,
                "share_pct": round(share * 100, 2),
                "type": "fixed" if key == "customer_charge" else "variable"
            })
        return sorted(ranks, key=lambda x: x["value"], reverse=True)

    def bill_driver_analysis(self, components_obj: dict) -> dict:
        """Explains key bill drivers, fixed/usage-based partitions, market or regulatory drivers."""
        costs = components_obj["costs"]
        total = components_obj["total_bill"]
        
        sorted_ranks = self.rank_components_from_bill(components_obj)
        highest_comp = sorted_ranks[0] if sorted_ranks else {"label": "None", "share_pct": 0.0}
        
        fixed_sum = costs.get("customer_charge", 0.0)
        variable_sum = sum(v for k, v in costs.items() if k not in ["customer_charge", "sales_tax"])
        tax_sum = costs.get("sales_tax", 0.0)
        
        return {
            "highest_contributor": highest_comp["label"],
            "highest_pct": highest_comp["share_pct"],
            "fixed_cost": round(fixed_sum, 2),
            "fixed_pct": round((fixed_sum * (1 + self.tax_rate)) / total * 100, 1) if total > 0 else 0.0,
            "variable_cost": round(variable_sum, 2),
            "variable_pct": round((variable_sum * (1 + self.tax_rate)) / total * 100, 1) if total > 0 else 0.0,
            "tax_cost": round(tax_sum, 2),
            "tax_pct": round(tax_sum / total * 100, 1) if total > 0 else 0.0,
            "market_controlled": "BGS Supply, Transmission Charge (sensitive to wholesale price peaks & PJM grid congestion)",
            "policy_regulatory": "Societal Benefits Charge (SBC), Transition Charge, Rider Charges, Non-Utility Generation Charge"
        }

    def generate_personalized_insights(self, components_obj: dict, weather_cdd: float, weather_hdd: float) -> list[str]:
        """Generate dynamic personalized insights based on uploaded bill components and climate data."""
        insights = []
        costs = components_obj["costs"]
        total = components_obj["total_bill"]
        usage = components_obj["usage_kwh"]
        
        dist_pct = round((costs.get("distribution_cost", 0.0) * (1 + self.tax_rate)) / total * 100, 1) if total > 0 else 0.0
        dist_10_impact = round(costs.get("distribution_cost", 0.0) * 0.10 * (1 + self.tax_rate), 2)
        
        insights.append(f"🔌 **Distribution Charge** contributes **{dist_pct}%** of your total bill.")
        insights.append(f"📈 A 10% increase in Distribution Charges would increase your monthly bill by approximately **${dist_10_impact:.2f}**.")
        insights.append("🔒 **Customer Charge** is fixed ($8.24) and will not change with electricity usage.")
        insights.append("💡 Reducing electricity usage mainly lowers usage-based charges: **Supply, Distribution, Transmission, and SBC**.")
        
        # Weather impact estimation using OLS coefficients
        weather_kwh = self.beta_cdd * weather_cdd + self.beta_hdd * weather_hdd
        expected_usage = self.intercept + weather_kwh
        actual_weather_portion = min(weather_kwh, usage)
        weather_pct = round(actual_weather_portion / usage * 100, 1) if usage > 0 else 0.0
        
        insights.append(f"🌡️ Weather (heating/cooling loads) accounts for approximately **{actual_weather_portion:.1f} kWh** ({weather_pct}%) of your actual consumption.")
        
        usage_diff = usage - expected_usage
        if usage_diff > 10.0:
            insights.append(
                f"📈 **Behavioral Shift**: Your actual usage of **{usage:.1f} kWh** is **{abs(usage_diff):.1f} kWh higher** than the weather-adjusted expected baseline ({expected_usage:.1f} kWh). "
                f"This indicates significant potential savings from behavioral changes or appliance efficiency upgrades."
            )
        elif usage_diff < -10.0:
            insights.append(
                f"🌿 **Energy Efficiency**: Your actual usage of **{usage:.1f} kWh** is **{abs(usage_diff):.1f} kWh lower** than the weather-adjusted expected baseline ({expected_usage:.1f} kWh). "
                f"Great job! Your household is exhibiting strong energy conservation practices."
            )
        else:
            insights.append(
                f"🎯 Your actual usage closely matches the weather-adjusted expected baseline ({expected_usage:.1f} kWh), indicating typical load patterns."
            )
            
        insights.append("📊 Wholesale **PJM market prices** directly determine your standard energy BGS supply cost.")
        
        return insights

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. DETERMINISTIC LAYER (Ground Truth)
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate_total_bill(self, components: dict[str, float], kwh: float) -> dict[str, Any]:
        """
        DETERMINISTIC LAYER: Accounting Identity.
        Total_Bill = sum(fixed) + sum(variable * kwh)
        Upgraded to use loss-adjusted consumption for the energy/supply (bgs_rate) component.
        """
        from models.pjm_market_physics import DEFAULT_PJM, compute_effective_kwh

        components = self._enrich_components_with_tariff(components)
        line_items = {}
        subtotal = 0.0

        for key, meta in COMPONENT_TYPES.items():
            val = components.get(key, 0.0)
            if meta["type"] == "variable":
                if key == "bgs_rate":
                    # Loss-adjusted consumption for energy supply
                    eff_kwh = compute_effective_kwh(kwh, DEFAULT_PJM.total_loss_factor)
                    cost = round(val * eff_kwh, 2)
                else:
                    cost = round(val * kwh, 2)
            else:
                cost = round(val, 2)
            
            line_items[meta["cost_col"]] = cost
            subtotal += cost

        # Add tax
        tax = round(subtotal * self.tax_rate, 2)
        total = round(subtotal + tax, 2)

        return {
            "total_bill": total,
            "subtotal": subtotal,
            "sales_tax": tax,
            "line_items": line_items,
            "usage_kwh": kwh
        }

    def calculate_total_bill_pjm(
        self,
        components: dict[str, float],
        kwh: float,
        lmp_da_mwh: Optional[float] = None,
        lmp_rt_mwh: Optional[float] = None,
        congestion_mwh: Optional[float] = None,
        loss_factor: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        PJM M28/M15 Settlement Accounting Bill.
        Uses two-settlement energy charge and loss-adjusted consumption.
        """
        from models.pjm_market_physics import (
            DEFAULT_PJM,
            compute_effective_kwh,
            compute_energy_charge_two_settlement,
            compute_transmission_rate,
            compute_total_bill,
        )

        components = self._enrich_components_with_tariff(components)
        lf = loss_factor if loss_factor is not None else DEFAULT_PJM.total_loss_factor
        effective_kwh = compute_effective_kwh(kwh, lf)

        # Base rates from components dictionary
        customer_charge = components.get("customer_charge", 0.0)
        distribution_rate = components.get("distribution_rate", 0.0)
        base_transmission = components.get("transmission_rate", 0.0)
        sbc_rate = components.get("sbc_rate", 0.0)
        transition_rate = components.get("transition_rate", 0.0)
        nug_rate = components.get("nug_rate", 0.0)
        rider_rate = components.get("rider_rate", 0.0)
        
        # Policy charges
        policy_rate = sbc_rate + transition_rate + nug_rate + rider_rate
        policy_charges = policy_rate * kwh

        # LMP or bgs_rate as proxy (if no LMP provided)
        bgs_rate = components.get("bgs_rate", 0.0)
        da_price = lmp_da_mwh if lmp_da_mwh is not None else (bgs_rate * 1000.0)
        rt_price = lmp_rt_mwh if lmp_rt_mwh is not None else da_price
        
        # Two-settlement energy charge
        settlement = compute_energy_charge_two_settlement(
            effective_kwh=effective_kwh,
            da_price_mwh=da_price,
            rt_price_mwh=rt_price,
            da_fraction=DEFAULT_PJM.da_settlement_fraction
        )
        energy_charge = settlement["total_energy_charge"]

        # Transmission with congestion pass-through
        cong_component = (congestion_mwh / 1000.0) if congestion_mwh is not None else 0.0
        transmission_rate = compute_transmission_rate(base_transmission, cong_component)
        transmission_cost = transmission_rate * kwh

        # Distribution cost
        distribution_cost = distribution_rate * kwh

        # Assemble the bill
        bill_res = compute_total_bill(
            customer_charge=customer_charge,
            energy_charge=energy_charge,
            distribution_cost=distribution_cost,
            transmission_cost=transmission_cost,
            policy_charges=policy_charges,
            tax_rate=self.tax_rate
        )

        # Prepare line items matching expected shape in COMPONENT_TYPES
        line_items = {
            "customer_charge": round(customer_charge, 2),
            "bgs_cost": round(energy_charge, 2),
            "distribution_cost": round(distribution_cost, 2),
            "transmission_cost": round(transmission_cost, 2),
            "sbc_cost": round(sbc_rate * kwh, 2),
            "market_transition_cost": round(transition_rate * kwh, 2),
            "nug_cost": round(nug_rate * kwh, 2),
            "rider_cost": round(rider_rate * kwh, 2),
        }

        return {
            "total_bill": round(bill_res["total_bill"], 2),
            "subtotal": round(bill_res["subtotal"], 2),
            "sales_tax": round(bill_res["tax"], 2),
            "line_items": line_items,
            "usage_kwh": kwh,
            "effective_kwh": round(effective_kwh, 2),
            "da_energy_charge": round(settlement["da_charge"], 2),
            "rt_deviation_charge": round(settlement["rt_charge"], 2),
            "loss_factor": lf,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def sensitivity_analysis(self, component: str, change_pct: float, kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Deterministic + Statistical Sensitivity Analysis using Monte Carlo simulation.
        """
        sim_res = self.what_if_simulation({component: change_pct}, kwh)
        
        if "error" in sim_res:
            return sim_res

        return {
            "component": component,
            "label": COMPONENT_TYPES[component]["label"],
            "base_bill": sim_res["base_bill"],
            "new_bill": sim_res["new_bill"],
            "absolute_impact": sim_res["total_impact"],
            "percent_impact": round((sim_res["total_impact"] / sim_res["base_bill"]) * 100, 4) if sim_res["base_bill"] else 0.0,
            "elasticity": round((sim_res["total_impact"] / sim_res["base_bill"]) / (change_pct / 100.0), 4) if change_pct != 0 and sim_res["base_bill"] else 0.0,
            "confidence_interval": sim_res["confidence_interval"],
            "component_type": COMPONENT_TYPES[component]["type"],
            "reasoning": COMPONENT_TYPES[component]["reasoning"],
            "details": {
                "change_pct": change_pct,
                "usage_adjustment": sim_res["usage_response"]
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. WHAT-IF SIMULATION (V1 and V2)
    # ═══════════════════════════════════════════════════════════════════════════

    def what_if_simulation(self, modifications: dict[str, float], kwh: Optional[float] = None) -> dict[str, Any]:
        """Scenario Simulation V1 - backward compatible."""
        return self.what_if_simulation_v2(modifications, kwh=kwh)

    def what_if_simulation_v2(self, modifications: dict[str, float], kwh: Optional[float] = None,
                               scenario: Optional[str] = None, n_sim: int = 2000) -> dict[str, Any]:
        """
        Scenario Simulation V2 with learned demand model, weather variations,
        and full multivariate Monte Carlo simulation.
        """
        from api.services.simulation_service_v2 import simulate_v2, build_weather_stats

        billing_df = app_state.get("billing_df")
        if billing_df is None or len(billing_df) == 0:
            return {"error": "Billing data not loaded"}

        feature_df = app_state.get("feature_matrix")
        demand_model = app_state.get("demand_model")
        rate_cov = app_state.get("rate_cov_matrix")
        
        weather_stats = None
        if feature_df is not None:
            weather_stats = build_weather_stats(feature_df)

        try:
            res = simulate_v2(
                modifications=modifications,
                billing_df=billing_df,
                feature_df=feature_df,
                demand_model=demand_model,
                rate_cov=rate_cov,
                weather_stats=weather_stats,
                scenario=scenario,
                kwh_override=kwh,
                n_sim=n_sim
            )
            return res
        except Exception as e:
            logger.exception("Simulation V2 failed")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════════
    #  4. IMPACT RANKING
    # ═══════════════════════════════════════════════════════════════════════════

    def rank_components(self, components_obj: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Rank components by share of total bill and elasticity."""
        if components_obj:
            return self.rank_components_from_bill(components_obj)
            
        df = app_state.get("billing_df")
        latest = df.iloc[-1].to_dict()
        total = float(latest.get("total_bill", 1.0))
        
        ranks = []
        for key, meta in COMPONENT_TYPES.items():
            cost = float(latest.get(meta["cost_col"], 0.0))
            share = (cost * (1 + self.tax_rate)) / total
            ranks.append({
                "component": key,
                "label": meta["label"],
                "share_pct": round(share * 100, 2),
                "elasticity": round(share, 4),
                "type": meta["type"],
                "reasoning": meta["reasoning"]
            })
            
        return sorted(ranks, key=lambda x: x["share_pct"], reverse=True)

    # ═══════════════════════════════════════════════════════════════════════════
    #  5. CAUSAL INFERENCE (Advanced Layer)
    # ═══════════════════════════════════════════════════════════════════════════

    def get_causal_impact(self, treatment: str) -> dict[str, Any]:
        """Estimate causal effect of a rate component on total bill."""
        actual_treatment = "avg_lmp" if treatment == "lmp" else treatment
        causal_service = app_state.get("causal_service")
        
        if causal_service and causal_service.is_fitted:
            res = causal_service.get_causal_impact_legacy(actual_treatment)
            res["treatment"] = treatment
            return res
            
        try:
            from dowhy import CausalModel
            
            df = app_state.get("billing_df").copy()
            if df is None or len(df) < 24:
                return {"error": "Insufficient data for causal inference (min 24 months)"}

            if actual_treatment == "avg_lmp" and "avg_lmp" not in df.columns:
                market_df = app_state.get("market_df")
                if market_df is not None:
                    from data_pipeline.features import merge_market_monthly
                    df = merge_market_monthly(df, market_df)

            if actual_treatment not in df.columns:
                return {"error": f"Treatment variable {treatment} not found in billing data"}

            if 'month' in df.columns:
                df['month_num'] = pd.to_datetime(df['month']).dt.month if df['month'].dtype == 'object' else df['month']
            
            model = CausalModel(
                data=df,
                treatment=actual_treatment,
                outcome="total_bill",
                common_causes=["usage_kwh", "month_num"] if 'month_num' in df.columns else ["usage_kwh"]
            )
            
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression",
                test_significance=True
            )
            
            return {
                "treatment": treatment,
                "causal_effect_estimate": round(float(estimate.value), 4),
                "p_value": round(float(estimate.test_stat_significance().get("p_value", 0.0)), 4),
                "interpretation": f"Controlling for usage and seasonality, a $1 unit increase in {treatment} causes an average bill increase of ${round(float(estimate.value), 2)}.",
                "caveat": "Estimated using observational data; results assume no unobserved confounders."
            }
        except ImportError:
            return {"error": "Causal inference services not available"}
        except Exception as e:
            logger.warning(f"Causal inference failed for {treatment}: {e}")
            return {"error": str(e)}

    def get_causal_impact_v2(self, treatment: str) -> dict[str, Any]:
        actual_treatment = "avg_lmp" if treatment == "lmp" else treatment
        causal_service = app_state.get("causal_service")
        if causal_service and causal_service.is_fitted:
            res = causal_service.estimate(actual_treatment)
            res = dict(res)
            res["treatment"] = treatment
            return res
        return {"error": "Causal model not fitted"}

    def get_analysis(self, row: Dict[str, Any], prev_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point to get contribution, sensitivity, and insights.
        Performs weather-normalized causal split to isolate rate/behavior changes from weather shifts.
        """
        is_absolute = False
        if prev_row is None or prev_row == row:
            is_absolute = True
            prev_row = row.copy()
            
        total_bill = float(row.get("total_bill", 0))
        prev_bill = float(prev_row.get("total_bill", 0))
        if total_bill == 0 or prev_bill == 0:
            return {}

        usage = float(row.get("usage_kwh", 0))
        prev_usage = float(prev_row.get("usage_kwh", 0))

        # Dynamically infer rates if missing
        row = row.copy()
        prev_row = prev_row.copy()
        for k_rate, k_cost in [("bgs_rate", "bgs_cost"), ("distribution_rate", "distribution_cost"), 
                               ("transmission_rate", "transmission_cost"), ("sbc_rate", "sbc_cost"), 
                               ("nug_rate", "nug_cost")]:
            if k_rate not in row and k_cost in row and usage > 0:
                row[k_rate] = float(row[k_cost]) / usage
            if k_rate not in prev_row and k_cost in prev_row and prev_usage > 0:
                prev_row[k_rate] = float(prev_row[k_cost]) / prev_usage

        latest_date = pd.to_datetime(row.get("date", pd.Timestamp.now()))
        prev_date = pd.to_datetime(prev_row.get("date", pd.Timestamp.now()))

        def get_climatology(month_num):
            cdd_map = {1:0.0, 2:0.0, 3:0.0, 4:5.0, 5:45.0, 6:180.0, 7:310.0, 8:260.0, 9:100.0, 10:15.0, 11:0.0, 12:0.0}
            hdd_map = {1:950.0, 2:820.0, 3:650.0, 4:350.0, 5:120.0, 6:10.0, 7:0.0, 8:0.0, 9:30.0, 10:220.0, 11:500.0, 12:820.0}
            return cdd_map.get(month_num, 0.0), hdd_map.get(month_num, 0.0)

        cdd_latest, hdd_latest = get_climatology(latest_date.month)
        cdd_prev, hdd_prev = get_climatology(prev_date.month)
        
        try:
            root_dir = Path(__file__).resolve().parent.parent.parent
            air_temp_path = root_dir / "data" / "raw" / "air_temp.csv"
            if air_temp_path.exists():
                weather_df = pd.read_csv(air_temp_path)
                weather_df["DATE"] = pd.to_datetime(weather_df["DATE"])
                if "TAVG" not in weather_df.columns or weather_df["TAVG"].isna().all():
                    weather_df["TAVG"] = (weather_df["TMAX"].astype(float) + weather_df["TMIN"].astype(float)) / 2
                weather_df["CDD"] = np.maximum(0, weather_df["TAVG"] - 65)
                weather_df["HDD"] = np.maximum(0, 65 - weather_df["TAVG"])
                weather_df["month_str"] = weather_df["DATE"].dt.strftime("%Y-%m")
                weather_monthly = weather_df.groupby("month_str")[["CDD", "HDD"]].sum().to_dict(orient="index")
                
                m_str_latest = latest_date.strftime("%Y-%m")
                m_str_prev = prev_date.strftime("%Y-%m")
                if m_str_latest in weather_monthly:
                    cdd_latest = weather_monthly[m_str_latest]["CDD"]
                    hdd_latest = weather_monthly[m_str_latest]["HDD"]
                if m_str_prev in weather_monthly:
                    cdd_prev = weather_monthly[m_str_prev]["CDD"]
                    hdd_prev = weather_monthly[m_str_prev]["HDD"]
        except Exception:
            pass

        from models.pjm_market_physics import DEFAULT_PJM, compute_effective_kwh
        lf = DEFAULT_PJM.total_loss_factor
        
        eff_usage = float(row.get("effective_kwh", compute_effective_kwh(usage, lf)))
        eff_prev_usage = float(prev_row.get("effective_kwh", compute_effective_kwh(prev_usage, lf)))

        weather_usage_latest = self.beta_cdd * cdd_latest + self.beta_hdd * hdd_latest
        weather_usage_prev = self.beta_cdd * cdd_prev + self.beta_hdd * hdd_prev
        
        weather_usage_latest = min(weather_usage_latest, 0.9 * eff_usage)
        weather_usage_prev = min(weather_usage_prev, 0.9 * eff_prev_usage)
        
        ΔWeatherUsage = weather_usage_latest - weather_usage_prev
        ΔUsage = eff_usage - eff_prev_usage
        ΔNonWeatherUsage = ΔUsage - ΔWeatherUsage

        tax_mult = 1.06625

        variable_keys = [
            ("bgs_rate", "BGS Supply", "Market"),
            ("distribution_rate", "Distribution Charge", "Infrastructure"),
            ("transmission_rate", "Transmission Charge", "Market"),
            ("sbc_rate", "Societal Benefits Charge", "Policy"),
            ("nug_rate", "Non-Utility Generation Charge", "Regulatory"),
            ("rider_rate", "Rider Charges", "Regulatory")
        ]

        prev_rate_total = 0.0
        latest_rate_total = 0.0
        for rate_key, _, _ in variable_keys:
            prev_rate_total += float(prev_row.get(rate_key, 0.0))
            latest_rate_total += float(row.get(rate_key, 0.0))

        avg_rate_total = (prev_rate_total + latest_rate_total) / 2.0
        avg_raw_usage = (prev_usage + usage) / 2.0
        avg_eff_usage = (eff_prev_usage + eff_usage) / 2.0

        contributions = {}
        
        if is_absolute:
            bgs_val = float(row.get("bgs_cost", 0.0))
            dist_val = float(row.get("distribution_cost", 0.0))
            trans_val = float(row.get("transmission_cost", 0.0))
            sbc_val = float(row.get("sbc_cost", 0.0))
            nug_val = float(row.get("nug_cost", 0.0))
            rider_val = float(row.get("rider_cost", 0.0))
            fixed_val = float(row.get("customer_charge", 8.24))
            tax_val = float(row.get("sales_tax", 0.0))
            
            contributions["bgs"] = {"value": round(bgs_val, 2), "percent": round((bgs_val / total_bill * 100), 2) if total_bill else 0}
            contributions["distribution"] = {"value": round(dist_val, 2), "percent": round((dist_val / total_bill * 100), 2) if total_bill else 0}
            contributions["transmission"] = {"value": round(trans_val, 2), "percent": round((trans_val / total_bill * 100), 2) if total_bill else 0}
            contributions["sbc"] = {"value": round(sbc_val, 2), "percent": round((sbc_val / total_bill * 100), 2) if total_bill else 0}
            contributions["nug"] = {"value": round(nug_val, 2), "percent": round((nug_val / total_bill * 100), 2) if total_bill else 0}
            contributions["rider"] = {"value": round(rider_val, 2), "percent": round((rider_val / total_bill * 100), 2) if total_bill else 0}
            contributions["customer"] = {"value": round(fixed_val, 2), "percent": round((fixed_val / total_bill * 100), 2) if total_bill else 0}
            contributions["tax"] = {"value": round(tax_val, 2), "percent": round((tax_val / total_bill * 100), 2) if total_bill else 0}
            contributions["weather"] = {"value": 0.0, "percent": 0.0}
            contributions["behavioral_usage"] = {"value": 0.0, "percent": 0.0}
            contributions["lmp"] = {"value": 0.0, "percent": 0.0}
        else:
            fixed_prev = float(prev_row.get("customer_charge", 8.24))
            fixed_latest = float(row.get("customer_charge", 8.24))
            ΔFixed = fixed_latest - fixed_prev
            contributions["customer"] = {
                "value": round(ΔFixed * tax_mult, 2),
                "percent": round(((ΔFixed * tax_mult) / total_bill) * 100, 2) if total_bill else 0
            }

            avg_bgs_rate = (float(prev_row.get("bgs_rate", 0.0)) + float(row.get("bgs_rate", 0.0))) / 2.0
            avg_other_rate_total = avg_rate_total - avg_bgs_rate
            ΔBill_weather = (ΔWeatherUsage * avg_bgs_rate + (ΔWeatherUsage / (1.0 + lf)) * avg_other_rate_total) * tax_mult
            contributions["weather"] = {
                "value": round(ΔBill_weather, 2),
                "percent": round((ΔBill_weather / total_bill) * 100, 2) if total_bill else 0
            }

            ΔBill_usage = (ΔNonWeatherUsage * avg_bgs_rate + (ΔNonWeatherUsage / (1.0 + lf)) * avg_other_rate_total) * tax_mult
            contributions["behavioral_usage"] = {
                "value": round(ΔBill_usage, 2),
                "percent": round((ΔBill_usage / total_bill) * 100, 2) if total_bill else 0
            }

            for rate_key, label, driver in variable_keys:
                rate_prev = float(prev_row.get(rate_key, 0.0))
                rate_latest = float(row.get(rate_key, 0.0))
                ΔRate = rate_latest - rate_prev
                
                if rate_key == "bgs_rate":
                    comp_impact = ΔRate * avg_eff_usage * tax_mult
                else:
                    comp_impact = ΔRate * avg_raw_usage * tax_mult
                short_key = rate_key.replace("_rate", "")
                
                contributions[short_key] = {
                    "value": round(comp_impact, 2),
                    "percent": round((comp_impact / total_bill) * 100, 2) if total_bill else 0
                }

            lmp_latest = float(row.get("avg_lmp", row.get("lmp", float(row.get("bgs_rate", 0.0)) * 1000.0)))
            lmp_prev = float(prev_row.get("avg_lmp", prev_row.get("lmp", float(prev_row.get("bgs_rate", 0.0)) * 1000.0)))
            ΔLmp = lmp_latest - lmp_prev
            lmp_impact = (ΔLmp / 1000.0) * avg_eff_usage * tax_mult
            contributions["lmp"] = {
                "value": round(lmp_impact, 2),
                "percent": round((lmp_impact / total_bill) * 100, 2) if total_bill else 0
            }

        sensitivity = {}
        for rate_key, label, driver in variable_keys:
            short_key = rate_key.replace("_rate", "")
            base_rate = float(row.get(rate_key, 0.0))
            if base_rate == 0:
                continue
                
            impacts = {}
            for pct in [10, -10]:
                delta_rate = base_rate * (pct / 100.0)
                if rate_key == "bgs_rate":
                    rate_impact = delta_rate * eff_usage * tax_mult
                else:
                    rate_impact = delta_rate * usage * tax_mult
                impacts[f"{'+' if pct > 0 else ''}{pct}%"] = round(rate_impact, 2)
                
            sensitivity[short_key] = impacts

        weather_sens = {}
        for pct in [10, -10]:
            cdd_shift = cdd_latest * (pct / 100.0)
            hdd_shift = hdd_latest * (pct / 100.0)
            usage_shift = self.beta_cdd * cdd_shift + self.beta_hdd * hdd_shift
            total_delta = usage_shift * prev_rate_total * tax_mult
            weather_sens[f"{'+' if pct > 0 else ''}{pct}%"] = round(total_delta, 2)
        sensitivity["weather"] = weather_sens

        label_map = {
            "bgs": "BGS Supply",
            "distribution": "Distribution Charge",
            "transmission": "Transmission Charge",
            "sbc": "Societal Benefits Charge",
            "nug": "Non-Utility Generation Charge",
            "rider": "Rider Charges"
        }
        
        insights = []
        season = "Summer" if latest_date.month in [6, 7, 8] else ("Winter" if latest_date.month in [12, 1, 2] else "Transition")
        
        if is_absolute:
            max_driver_key = "bgs"
            max_val = -1.0
            for k, v in contributions.items():
                if k in ["weather", "behavioral_usage", "lmp", "tax", "customer"]:
                    continue
                if v["value"] > max_val:
                    max_val = v["value"]
                    max_driver_key = k
            
            driver_label = label_map.get(max_driver_key, max_driver_key.capitalize())
            pct = contributions.get(max_driver_key, {}).get('percent', 0.0)
            insights.append(f"🔌 **Primary cost driver**: {driver_label} is the primary driver of your bill, accounting for {pct:.1f}% of the total cost.")
        else:
            weather_val = contributions.get("weather", {}).get("value", 0.0)
            if weather_val > 3.0:
                insights.append(f"🌡️ **Weather impact**: Abnormal seasonal temperatures caused a **+${weather_val:.2f}** bill increase from heating/cooling degree days.")
            elif weather_val < -3.0:
                insights.append(f"🌡️ **Weather relief**: Favorable seasonal weather reduced your bill by **-${abs(weather_val):.2f}** due to lighter HVAC loads.")
                
            usage_val = contributions.get("behavioral_usage", {}).get("value", 0.0)
            if usage_val > 3.0:
                insights.append(f"🔌 **Behavioral shift**: Higher non-heating/cooling appliance usage added **+${usage_val:.2f}** to your monthly costs.")
            elif usage_val < -3.0:
                insights.append(f"🔌 **Energy efficiency**: Conservation efforts and reduced usage lowered your bill by **-${abs(usage_val):.2f}**.")

            rate_contribs = {k: v["value"] for k, v in contributions.items() if k not in ["weather", "behavioral_usage", "customer", "lmp"]}
            if rate_contribs:
                sorted_rates = sorted(rate_contribs.items(), key=lambda x: abs(x[1]), reverse=True)
                top_rate_key, top_rate_val = sorted_rates[0]
                label = label_map.get(top_rate_key, top_rate_key.capitalize())
                direction = "added" if top_rate_val > 0 else "saved"
                insights.append(f"📈 **Tariff adjustment**: Rate shifts in **{label}** {direction} **${abs(top_rate_val):.2f}** on your bill.")

            lmp_val = contributions.get("lmp", {}).get("value", 0.0)
            if abs(lmp_val) > 2.0:
                direction = "spiked" if lmp_val > 0 else "declined"
                insights.append(
                    f"🔌 **PJM wholesale LMP**: Wholesale energy prices {direction}, "
                    f"driving a **{'+' if lmp_val > 0 else ''}${lmp_val:.2f}** change on your bill after loss adjustment."
                )

            if season == "Summer":
                insights.append("☀️ **Season awareness**: Summer exhibits high cooling sensitivity. Every additional degree day scales your bill via distribution/supply rates.")
            elif season == "Winter":
                insights.append("❄️ **Season awareness**: Winter exhibits high space-heating demand. Keep thermostat settings optimized to control HDD-driven consumption.")

        return {
            "total_bill": round(total_bill, 2),
            "contributions": contributions,
            "sensitivity": sensitivity,
            "insights": insights,
            "weather_cdd": cdd_latest,
            "weather_hdd": hdd_latest,
            "alpha": self.beta_cdd,
            "beta": self.beta_hdd,
            "base_usage": self.intercept,
            "confidence": "High" if self.calibrated else "Medium"
        }


bill_impact_engine = BillImpactEngine()
