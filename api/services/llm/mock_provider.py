"""
Mock LLM Provider for unit testing and deterministic simulation mode.
Does not require any network connection or background Ollama process.
"""
from typing import AsyncGenerator, Optional, Any
from api.services.llm.base_provider import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model: str = "mock-model", base_url: Optional[str] = None):
        super().__init__(model=model, base_url=base_url)

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        user_msg = prompt
        prompt_lower = prompt.lower()
        if "user question:" in prompt_lower:
            parts = prompt_lower.split("user question:")
            user_msg = parts[1].split("\n")[0].strip()
        q_lower = user_msg.lower()

        # Check for RAG context
        rag_section = ""
        if "Relevant Knowledge Base:" in prompt:
            parts = prompt.split("Relevant Knowledge Base:")
            if len(parts) > 1:
                rag_section = parts[1].split("\n\nData Source Notes:")[0].strip()

        # Out-of-scope restriction check
        if any(term in q_lower for term in ["world cup", "cats", "football", "joke"]):
            return ("I am specialized specifically for electricity bill analysis, utility tariffs, "
                    "energy conservation, and cost optimization. Please ask me any question about "
                    "your electricity bill or utility costs!")

        # Parse bill context fields
        total_bill = None
        usage_kwh = None
        utility = "PSE&G"
        effective_rate = 0.1860
        period = "Jun 2026"
        delivery_charge = 46.75
        supply_charge = 91.80
        fixed_charge = 8.24
        tax = 11.31
        cdd = 245
        has_bill = False

        import json, re
        context_match = re.search(r'Active Structured Context:\s*(\{[\s\S]*?\})\s*$', prompt) or \
                        re.search(r'Context Data:\s*(\{[\s\S]*?\})\s*$', prompt)
        if context_match:
            try:
                data = json.loads(context_match.group(1))
                bill = data.get("bill") or data.get("uploadedBill") or {}
                if isinstance(bill, dict) and bill.get("total_bill"):
                    total_bill = float(bill.get("total_bill"))
                    usage_kwh = float(bill.get("usage_kwh"))
                    utility = bill.get("utility") or "PSE&G"
                    effective_rate = float(bill.get("effective_rate") or (total_bill / usage_kwh if usage_kwh > 0 else 0.1860))
                    period = bill.get("billing_period") or "Jun 2026"
                    delivery_charge = float(bill.get("delivery_charge") or 46.75)
                    fixed_charge = float(bill.get("monthly_service_charge") or bill.get("fixed_charge") or 8.24)
                    tax = float(bill.get("tax") or 11.31)
                    supply_charge = float(bill.get("supply_charge") or (total_bill - delivery_charge - fixed_charge - tax))
                    has_bill = True
            except Exception:
                pass

        # Check if customer bill is missing for personal bill queries
        is_personal = any(term in q_lower for term in ["my bill", "my usage", "my cost", "my account", "my electricity", "my rate", "did my", "is my"])
        if is_personal and not has_bill:
            return (
                f"### Executive Summary\n"
                f"This is a validated mock response. To provide a precise analysis of your electricity usage and costs, could you please specify your "
                f"monthly kWh consumption, billing period, or upload your current bill statement?"
            )

        # Defaults for general bill synthesis if not explicitly missing
        if not total_bill:
            total_bill = 158.10
            usage_kwh = 850.0

        # Distinct tailored responses for specific user questions
        if "delivery" in q_lower or "transmission" in q_lower or "distribution" in q_lower:
            return (
                f"### 🚚 Grid Delivery & Transmission Component Breakdown\n"
                f"Your delivery charges total **${delivery_charge:.2f}** under your active {utility} rate schedule.\n\n"
                f"**Grid Infrastructure Breakdown:**\n"
                f"- **Distribution System**: Fee for high-voltage transformers, local distribution feeder lines, and pole maintenance.\n"
                f"- **Transmission Network**: High-voltage grid transmission regulated by FERC and PJM Interconnection.\n"
                f"- **Fixed Customer Charge**: Base monthly service fee of **${fixed_charge:.2f}** for account administration and metering."
            )
        elif "supply" in q_lower or "driver" in q_lower or "commodity" in q_lower:
            return (
                f"### ⚡ Supply Generation & Commodity Cost Analysis ({utility})\n"
                f"Your supply charge for {period} is **${supply_charge:.2f}**, representing approximately **58%** of your total **${total_bill:.2f}** bill.\n\n"
                f"**Key Cost Drivers Identified:**\n"
                f"1. **PJM Wholesale Market**: Basic Generation Service (BGS) auction rates reflect regional PJM Locational Marginal Pricing (LMP).\n"
                f"2. **Fuel Commodity Prices**: Generation commodity rates track natural gas pipeline pricing and capacity auction clearing prices.\n"
                f"3. **Volumetric Consumption**: You consumed **{usage_kwh:.1f} kWh** at an effective rate of **${effective_rate:.4f}/kWh**."
            )
        elif "weather" in q_lower or "temp" in q_lower or "heat" in q_lower or "degree" in q_lower or "climate" in q_lower:
            return (
                f"### 🌤️ Weather & Climate Impact Analysis ({utility})\n"
                f"Meteorological telemetry shows cooling degree-days (CDD: {cdd}) directly impacted your usage of **{usage_kwh:.1f} kWh**.\n\n"
                f"**Weather Factor Findings:**\n"
                f"- **HVAC Thermal Load**: Summer cooling degree-days increased air conditioning compressor run-times during peak afternoon hours.\n"
                f"- **Bill Financial Impact**: Seasonal temperature spikes accounted for an estimated **15% to 25%** of your monthly volumetric usage."
            )
        elif "customer" in q_lower and "charge" in q_lower:
            return (
                f"### 🏢 Fixed Monthly Customer Charge Analysis\n"
                f"Your fixed customer charge is **${fixed_charge:.2f}** per month on your {utility} statement.\n\n"
                f"This is a non-volumetric fixed baseline fee that covers account administration, meter maintenance, billing infrastructure, and 24/7 customer support regardless of how many kWh of electricity you consume."
            )
        elif "forecast" in q_lower or "predict" in q_lower or "next month" in q_lower or "projected" in q_lower:
            pred_kwh = usage_kwh * 1.03
            pred_cost = total_bill * 1.04
            return (
                f"### 🔮 Predictive Demand & Cost Forecast ({utility})\n"
                f"Based on historical billing regression and seasonal degree-day projections:\n\n"
                f"- **Projected Consumption**: **{pred_kwh:.1f} kWh** (P10: {pred_kwh * 0.9:.1f} kWh | P90: {pred_kwh * 1.15:.1f} kWh)\n"
                f"- **Estimated Monthly Bill**: **${pred_cost:.2f}**\n"
                f"- **Demand Stressors**: Seasonal HVAC cooling loads during upcoming mid-afternoon peak hours."
            )
        elif "benchmark" in q_lower or "compare" in q_lower or "average" in q_lower or "rank" in q_lower:
            return (
                f"### 🏙️ Utility & Regional Rate Benchmarking\n"
                f"Comparative analysis for **{utility}** (effective rate: **${effective_rate:.4f}/kWh**):\n\n"
                f"- **NJ State Average**: $0.1840/kWh — {utility} rate is competitive within standard state clearing margins.\n"
                f"- **National Average**: $0.1680/kWh — NJ regional rates reflect higher PJM capacity auction costs and transmission congestion surcharges.\n"
                f"- **Peer Utility Comparison**: Rates track closely with regional peers (JCP&L and Atlantic City Electric)."
            )
        elif "15%" in q_lower or "reduce" in q_lower or "save" in q_lower or "cut" in q_lower or "tip" in q_lower:
            savings = total_bill * 0.15
            kwh_saved = usage_kwh * 0.15
            return (
                f"### 🌱 Energy Optimization & Cost Reduction Strategy\n"
                f"Reducing your electricity consumption by 15% saves approximately **{kwh_saved:.1f} kWh**, reducing your monthly bill by **${savings:.2f}**.\n\n"
                f"**Top Recommended Actions:**\n"
                f"1. **Off-Peak Load Shifting**: Shift EV charging, laundry, and dishwasher runs to off-peak hours (10 PM to 8 AM).\n"
                f"2. **Thermostat Pre-Cooling**: Pre-cool your space prior to peak afternoon cooling hours (2 PM to 6 PM).\n"
                f"3. **Phantom Load Control**: Use smart power strips to eliminate standby power draw from electronics."
            )
        elif "why" in q_lower or "high" in q_lower or "increase" in q_lower or "more" in q_lower or "different" in q_lower:
            return (
                f"### ⚡ Multi-Factor Bill Variance Analysis ({utility})\n"
                f"Your bill of **${total_bill:.2f}** for **{usage_kwh:.1f} kWh** is driven by three primary factors:\n\n"
                f"1. **Volumetric Supply ({usage_kwh:.1f} kWh)**: Supply charges of **${supply_charge:.2f}** represent ~58% of total expenditure.\n"
                f"2. **Grid Delivery Fees**: Volumetric delivery and transmission charges total **${delivery_charge:.2f}**.\n"
                f"3. **Degree-Day Weather Shifts**: Seasonal temperature degree days increased cooling/heating compressor cycles."
            )

        # Fallback to RAG knowledge if no specific bill intent matched
        if rag_section:
            return f"Based on verified state energy documentation:\n\n{rag_section}"

        return (
            "### Executive Summary\n"
            "This is a validated mock response and synthesized multi-source analysis based on active utility tariffs, PJM market benchmarks, and NOAA weather indices."
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        full_text = await self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
        # Yield in chunks
        chunk_size = 40
        for i in range(0, len(full_text), chunk_size):
            yield full_text[i:i + chunk_size]

