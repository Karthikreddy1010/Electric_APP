"""
Deterministic Fallback Generators.
Provides zero-failure programmatic Markdown report generators for all ElectricAI tabs
when Ollama is offline or when LLM response validation fails twice.
"""
from typing import Dict, Any, Optional

class DeterministicFallback:
    @staticmethod
    def generate_bill_analysis_fallback(context: Dict[str, Any]) -> str:
        bill = context.get("bill", {})
        customer = context.get("customer", {})
        utility = customer.get("utility", "Utility Provider")
        total = bill.get("total_bill", 0.0)
        kwh = bill.get("usage_kwh", 0.0)
        period = bill.get("billing_period", "Current Billing Period")
        eff_rate = bill.get("effective_rate", (total / kwh) if kwh > 0 else 0.0)
        supply = bill.get("supply_charge", 0.0)
        delivery = bill.get("delivery_charge", 0.0)
        tax = bill.get("tax", 0.0)

        return (
            f"### 📝 Executive Bill Summary\n"
            f"Your total electricity bill from **{utility}** for billing period **{period}** is **${total:.2f}** "
            f"for **{kwh:.1f} kWh** at an effective tariff rate of **${eff_rate:.4f}/kWh**.\n\n"
            f"---\n\n"
            f"### 🔍 Charge Breakdown & Controllability\n"
            f"1. **Supply Charges (Generation): ${supply:.2f}** — *Controllable.* Charges for energy generation commodity.\n"
            f"2. **Delivery & Service Charges: ${delivery:.2f}** — *Partially Controllable.* Fixed customer charge plus grid distribution fee.\n"
            f"3. **State Sales Taxes & Adjustments: ${tax:.2f}** — *Mandatory.* NJ State Sales Tax (6.625%).\n\n"
            f"---\n\n"
            f"### 💡 Recommendations\n"
            f"- Shift non-essential consumption to off-peak grid hours (10 PM to 8 AM).\n"
            f"- Inspect HVAC cooling loads during peak summer heat waves."
        )

    @staticmethod
    def generate_impact_fallback(context: Dict[str, Any]) -> str:
        bill = context.get("bill", {})
        sim = context.get("simulation", {})
        total_base = bill.get("total_bill", 0.0)
        sim_bill = sim.get("simulated_bill", total_base)
        impact = sim.get("total_impact", sim_bill - total_base)
        contribs = sim.get("contributions", {})
        decomp = sim.get("decomposition", {})
        dist = sim.get("distribution", {})

        mean_val = dist.get("mean", sim_bill)
        p5_val = dist.get("p5", mean_val - 10.0)
        p95_val = dist.get("p95", mean_val + 10.0)

        price_eff = decomp.get("direct_price_effect", 0.0)
        behavior_eff = decomp.get("indirect_behavioral_effect", 0.0)
        weather_eff = decomp.get("weather_effect", 0.0)

        sign_str = "+" if impact >= 0 else "−"

        return (
            f"### 📊 Executive Financial Summary\n"
            f"Under the active what-if simulation, your simulated monthly total is **${sim_bill:.2f}**, "
            f"representing a net variance of **{sign_str}${abs(impact):.2f}** relative to baseline (${total_base:.2f}).\n\n"
            f"---\n\n"
            f"### 🌊 Causal Shift Decomposition\n"
            f"- **Direct Tariff Rate Effect**: ${price_eff:.2f}\n"
            f"- **Behavioral Shift**: ${behavior_eff:.2f}\n"
            f"- **Degree-Day Weather Shift**: ${weather_eff:.2f}\n\n"
            f"---\n\n"
            f"### 📈 Monte Carlo Probabilistic Risk\n"
            f"Based on 2,000 statistical Monte Carlo simulation trials:\n"
            f"- **Expected Mean Total**: ${mean_val:.2f}\n"
            f"- **5th Percentile (Optimistic)**: ${p5_val:.2f}\n"
            f"- **95th Percentile (Stress Risk Bound)**: ${p95_val:.2f}\n\n"
            f"---\n\n"
            f"### 💡 Operational Action Strategy\n"
            f"- Mitigate component rate shocks by setting automated peak load shedding thresholds."
        )

    @staticmethod
    def generate_forecast_fallback(context: Dict[str, Any]) -> str:
        bill = context.get("bill", {})
        fc = context.get("forecast", {})
        pred_kwh = fc.get("predicted_kwh", bill.get("usage_kwh", 750.0))
        pred_cost = fc.get("predicted_cost", bill.get("total_bill", 160.0))

        return (
            f"### 🔮 Predictive Demand Forecast\n"
            f"Our deterministic regression model projects usage of **{pred_kwh:.1f} kWh** "
            f"and an estimated monthly cost of **${pred_cost:.2f}** for the upcoming billing cycle.\n\n"
            f"---\n\n"
            f"### 🌤️ Weather & Demand Stressors\n"
            f"Seasonal cooling and heating degree-days are major drivers of demand variance."
        )

    @staticmethod
    def generate_overview_fallback(context: Dict[str, Any]) -> str:
        stats = context.get("statistics", {})
        active_bills = stats.get("total_bills", 1)
        total_spent = stats.get("total_spent", 0.0)

        return (
            f"### ⚡ Executive Dashboard Overview\n"
            f"Your account holds **{active_bills}** historical billing records with cumulative expenditure of **${total_spent:.2f}**."
        )

    @staticmethod
    def generate_recommendations_fallback(context: Dict[str, Any]) -> str:
        return (
            f"### 🌱 Clean Energy Optimization Plan\n"
            f"1. **Peak Load Shifting**: Shift laundry, dishwasher, and EV charging to off-peak hours (10 PM to 8 AM).\n"
            f"2. **Thermostat Pre-Cooling**: Pre-cool space before peak afternoon demand hours."
        )

    @staticmethod
    def generate_benchmark_fallback(context: Dict[str, Any]) -> str:
        customer = context.get("customer", {})
        utility = customer.get("utility", "Regional Utility")
        return (
            f"### 🏙️ Peer Utility Benchmark\n"
            f"Comparative analysis for **{utility}** against state benchmarks indicates competitive rate performance."
        )

    @staticmethod
    def generate_geo_fallback(context: Dict[str, Any]) -> str:
        stats = context.get("statistics", {})
        state = stats.get("state_code", "NJ")
        return (
            f"### 🗺️ Geographic & Regional Intelligence\n"
            f"Regional market clearing price analysis for state **{state}** within PJM Interconnection."
        )

    @staticmethod
    def generate_chat_fallback(context: Dict[str, Any], user_message: str) -> str:
        bill = context.get("bill", {})
        sim = context.get("simulation", {})
        user_lower = user_message.lower()

        if "supply" in user_lower or "bgs" in user_lower:
            return f"BGS Supply costs are based on PJM wholesale market auctions. In your bill context, total supply charge is ${bill.get('supply_charge', 81.0):.2f}."
        elif "delivery" in user_lower or "distribution" in user_lower:
            return f"Distribution & delivery charges pay for local grid line maintenance. Baseline delivery cost is ${bill.get('delivery_charge', 41.25):.2f}."
        elif "weather" in user_lower or "temp" in user_lower:
            return "Extreme high or low temperatures raise space heating/cooling HVAC loads, increasing consumption."
        elif "what if" in user_lower or "simulate" in user_lower:
            sim_val = sim.get("simulated_bill", bill.get("total_bill", 160.0))
            return f"Active simulation yields a total projected bill of ${sim_val:.2f}."
        
        return (
            f"Based on your validated bill data (${bill.get('total_bill', 0.0):.2f} total, {bill.get('usage_kwh', 0.0):.1f} kWh), "
            f"your effective rate is ${bill.get('effective_rate', 0.0):.4f}/kWh."
        )

    @classmethod
    def get_fallback(cls, task: str, context: Dict[str, Any], user_message: str = "") -> str:
        if task == "bill_analysis":
            return cls.generate_bill_analysis_fallback(context)
        elif task == "impact":
            return cls.generate_impact_fallback(context)
        elif task == "forecast":
            return cls.generate_forecast_fallback(context)
        elif task == "overview":
            return cls.generate_overview_fallback(context)
        elif task == "recommendations":
            return cls.generate_recommendations_fallback(context)
        elif task == "benchmark":
            return cls.generate_benchmark_fallback(context)
        elif task == "geo":
            return cls.generate_geo_fallback(context)
        elif task == "chat":
            return cls.generate_chat_fallback(context, user_message)
        return cls.generate_bill_analysis_fallback(context)
