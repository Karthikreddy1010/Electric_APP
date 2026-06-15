"""
Bill Impact Model: Component Contribution and Sensitivity Analysis.
This module enforces the core analytical objective:
'If an individual electricity bill component increases or decreases, 
how much does the total bill change?'

Incorporates weather-normalized causal analysis using Newark NOAA weather data (TAVG/TMAX/TMIN -> CDD/HDD).
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BillImpactModel:
    """
    Core logic for quantifying component contributions and simulating impacts.
    Focuses on weather-normalized causal decomposition rather than black-box models.
    """
    
    def __init__(self):
        # Component configuration: key in data -> (Label, Category, Driver)
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
        
        # Calibrated baseline coefficients for weather-driven usage
        # usage = intercept + beta_cdd * CDD + beta_hdd * HDD
        self.beta_cdd = 0.85
        self.beta_hdd = 0.45
        self.intercept = 450.0
        self.calibrated = False
        
        self._calibrate_from_history()

    def _calibrate_from_history(self):
        """Fit a robust Least-Squares regression of usage on CDD and HDD using NOAA air_temp.csv and billing history."""
        # FIX: 4 - Calibrate OLS regression from actual air_temp.csv NOAA data
        try:
            root_dir = Path(__file__).resolve().parent.parent
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
            logger.warning(f"Weather regression calibration failed, using baseline defaults: {e}")

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

        # Dynamically infer rates if missing (e.g. from cost/usage in test inputs)
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

        # Get seasonal CDD/HDD climatology fallbacks
        def get_climatology(month_num):
            cdd_map = {1:0.0, 2:0.0, 3:0.0, 4:5.0, 5:45.0, 6:180.0, 7:310.0, 8:260.0, 9:100.0, 10:15.0, 11:0.0, 12:0.0}
            hdd_map = {1:950.0, 2:820.0, 3:650.0, 4:350.0, 5:120.0, 6:10.0, 7:0.0, 8:0.0, 9:30.0, 10:220.0, 11:500.0, 12:820.0}
            return cdd_map.get(month_num, 0.0), hdd_map.get(month_num, 0.0)

        cdd_latest, hdd_latest = get_climatology(latest_date.month)
        cdd_prev, hdd_prev = get_climatology(prev_date.month)
        
        # Load precise NOAA air_temp.csv values on the fly
        try:
            root_dir = Path(__file__).resolve().parent.parent
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

        # Distinguish weather-driven usage vs discretionary behavioral usage
        from models.pjm_market_physics import DEFAULT_PJM, compute_effective_kwh
        lf = DEFAULT_PJM.total_loss_factor
        
        eff_usage = float(row.get("effective_kwh", compute_effective_kwh(usage, lf)))
        eff_prev_usage = float(prev_row.get("effective_kwh", compute_effective_kwh(prev_usage, lf)))

        weather_usage_latest = self.beta_cdd * cdd_latest + self.beta_hdd * hdd_latest
        weather_usage_prev = self.beta_cdd * cdd_prev + self.beta_hdd * hdd_prev
        
        # Keep weather caps safe using eff_usage
        weather_usage_latest = min(weather_usage_latest, 0.9 * eff_usage)
        weather_usage_prev = min(weather_usage_prev, 0.9 * eff_prev_usage)
        
        ΔWeatherUsage = weather_usage_latest - weather_usage_prev
        ΔUsage = eff_usage - eff_prev_usage
        ΔNonWeatherUsage = ΔUsage - ΔWeatherUsage

        tax_mult = 1.06625  # NJ Sales Tax factor on utility charges

        # Variables mapped as: key, label, driver
        variable_keys = [
            ("bgs_rate", "BGS Supply", "Market"),
            ("distribution_rate", "Distribution Charge", "Infrastructure"),
            ("transmission_rate", "Transmission Charge", "Market"),
            ("sbc_rate", "Societal Benefits Charge", "Policy"),
            ("nug_rate", "Non-Utility Generation", "Regulatory")
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
        
            "percent": round(((ΔFixed * tax_mult) / total_bill) * 100, 2) if total_bill else 0
        }

        # B. Weather Impact attribution - Deterministic Attribution
        avg_bgs_rate = (float(prev_row.get("bgs_rate", 0.0)) + float(row.get("bgs_rate", 0.0))) / 2.0
        avg_other_rate_total = avg_rate_total - avg_bgs_rate
        ΔBill_weather = (ΔWeatherUsage * avg_bgs_rate + (ΔWeatherUsage / (1.0 + lf)) * avg_other_rate_total) * tax_mult
        contributions["weather"] = {
            "value": round(ΔBill_weather, 2),
            "percent": round((ΔBill_weather / total_bill) * 100, 2) if total_bill else 0
        }

        # C. Behavioral Usage Impact (Discretionary usage shifts)
        ΔBill_usage = (ΔNonWeatherUsage * avg_bgs_rate + (ΔNonWeatherUsage / (1.0 + lf)) * avg_other_rate_total) * tax_mult
        contributions["behavioral_usage"] = {
            "value": round(ΔBill_usage, 2),
            "percent": round((ΔBill_usage / total_bill) * 100, 2) if total_bill else 0
        }

        # D. Component rate change impacts
        for rate_key, label, driver in variable_keys:
            rate_prev = float(prev_row.get(rate_key, 0.0))
            rate_latest = float(row.get(rate_key, 0.0))
            ΔRate = rate_latest - rate_prev
            
            # Midpoint causal price impact (bgs_rate uses effective usage)
            if rate_key == "bgs_rate":
                comp_impact = ΔRate * avg_eff_usage * tax_mult
            else:
                comp_impact = ΔRate * avg_raw_usage * tax_mult
            short_key = rate_key.replace("_rate", "")
            
            contributions[short_key] = {
                "value": round(comp_impact, 2),
                "percent": round((comp_impact / total_bill) * 100, 2) if total_bill else 0
            }

        # E. PJM Wholesale LMP Impact
        lmp_latest = float(row.get("avg_lmp", row.get("lmp", float(row.get("bgs_rate", 0.0)) * 1000.0)))
        lmp_prev = float(prev_row.get("avg_lmp", prev_row.get("lmp", float(prev_row.get("bgs_rate", 0.0)) * 1000.0)))
        ΔLmp = lmp_latest - lmp_prev
        lmp_impact = (ΔLmp / 1000.0) * avg_eff_usage * tax_mult
        contributions["lmp"] = {
            "value": round(lmp_impact, 2),
            "percent": round((lmp_impact / total_bill) * 100, 2) if total_bill else 0
        }

        # 3. Sensitivity Analysis (Dynamic and Elasticity-Based) - FIX: 7 Dynamic Elasticity
        sensitivity = {}
        for rate_key, label, driver in variable_keys:
            short_key = rate_key.replace("_rate", "")
            base_rate = float(row.get(rate_key, 0.0))
            if base_rate == 0:
                continue
                
            impacts = {}
            for pct in [10, -10]:
                delta_rate = base_rate * (pct / 100.0)
                # Rate impact
                if rate_key == "bgs_rate":
                    rate_impact = delta_rate * eff_usage * tax_mult
                else:
                    rate_impact = delta_rate * usage * tax_mult
                # Demand response (typical elasticity = -0.2)
                usage_response = usage * (pct / 100.0) * -0.2
                usage_impact = usage_response * prev_rate_total * tax_mult
                total_delta = rate_impact + usage_impact
                impacts[f"{'+' if pct > 0 else ''}{pct}%"] = round(total_delta, 2)
                
            sensitivity[short_key] = impacts

        # Weather sensitivity CDD/HDD scaling
        weather_sens = {}
        for pct in [10, -10]:
            cdd_shift = cdd_latest * (pct / 100.0)
            hdd_shift = hdd_latest * (pct / 100.0)
            usage_shift = self.beta_cdd * cdd_shift + self.beta_hdd * hdd_shift
            total_delta = usage_shift * prev_rate_total * tax_mult
            weather_sens[f"{'+' if pct > 0 else ''}{pct}%"] = round(total_delta, 2)
        sensitivity["weather"] = weather_sens

        # FIX: 8 - Add Time Awareness & Seasonal Insight Generation
        insights = self._generate_insights_causal(contributions, sensitivity, cdd_latest, hdd_latest, latest_date.month)

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

    def _generate_insights_causal(self, contributions: Dict, sensitivity: Dict, cdd: float, hdd: float, month: int, is_absolute: bool = False) -> List[str]:
        """Generate human-readable, time-aware causal insights about bill drivers."""
        insights = []
        season = "Summer" if month in [6, 7, 8] else ("Winter" if month in [12, 1, 2] else "Transition")
        
        label_map = {
            "bgs": "BGS Supply",
            "distribution": "Distribution Charge",
            "transmission": "Transmission Charge",
            "sbc": "Societal Benefits Charge",
            "nug": "Non-Utility Generation Charge"
        }

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
            return insights

        # 1. Weather Impact Insight
        weather_val = contributions.get("weather", {}).get("value", 0.0)
        if weather_val > 3.0:
            insights.append(f"🌡️ **Weather impact**: Abnormal seasonal temperatures caused a **+${weather_val:.2f}** bill increase from heating/cooling degree days.")
        elif weather_val < -3.0:
            insights.append(f"🌡️ **Weather relief**: Favorable seasonal weather reduced your bill by **-${abs(weather_val):.2f}** due to lighter HVAC loads.")
            
        # 2. Behavioral Usage Insight
        usage_val = contributions.get("behavioral_usage", {}).get("value", 0.0)
        if usage_val > 3.0:
            insights.append(f"🔌 **Behavioral shift**: Higher non-heating/cooling appliance usage added **+${usage_val:.2f}** to your monthly costs.")
        elif usage_val < -3.0:
            insights.append(f"🔌 **Energy efficiency**: Conservation efforts and reduced usage lowered your bill by **-${abs(usage_val):.2f}**.")

        # 3. Rate Adjustments Insight
        rate_contribs = {k: v["value"] for k, v in contributions.items() if k not in ["weather", "behavioral_usage", "customer", "lmp"]}
        if rate_contribs:
            sorted_rates = sorted(rate_contribs.items(), key=lambda x: abs(x[1]), reverse=True)
            top_rate_key, top_rate_val = sorted_rates[0]
            label = label_map.get(top_rate_key, top_rate_key.capitalize())
            direction = "added" if top_rate_val > 0 else "saved"
            insights.append(f"📈 **Tariff adjustment**: Rate shifts in **{label}** {direction} **${abs(top_rate_val):.2f}** on your bill.")

        # 3b. LMP Market physics insight
        lmp_val = contributions.get("lmp", {}).get("value", 0.0)
        if abs(lmp_val) > 2.0:
            direction = "spiked" if lmp_val > 0 else "declined"
            insights.append(
                f"🔌 **PJM wholesale LMP**: Wholesale energy prices {direction}, "
                f"driving a **{'+' if lmp_val > 0 else ''}${lmp_val:.2f}** change on your bill after loss adjustment."
            )

        # 4. Seasonality insight
        if season == "Summer":
            insights.append("☀️ **Season awareness**: Summer exhibit high cooling sensitivity. Every additional degree day scales your bill via distribution/supply rates.")
        elif season == "Winter":
            insights.append("❄️ **Season awareness**: Winter exhibits high space-heating demand. Keep thermostat settings optimized to control HDD-driven consumption.")
            
        return insights

def get_bill_impact(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function for API integration."""
    model = BillImpactModel()
    return model.get_analysis(row)
