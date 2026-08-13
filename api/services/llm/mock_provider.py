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
        # Extract user question from grounded prompt format ("USER QUESTION:\n...") or legacy format
        if "user question:" in prompt_lower:
            parts = prompt.split("USER QUESTION:")
            if len(parts) < 2:
                parts = prompt_lower.split("user question:")
            raw_q = parts[1].strip().split("\n")[0].strip()
            if raw_q:
                user_msg = raw_q
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
        # IMPORTANT: Ordered from most-specific to least-specific to avoid broad patterns swallowing specific questions

        # --- ELI5 / Simple explanation ---
        if any(w in q_lower for w in ["like i'm five", "eli5", "simple terms", "layman", "simplify", "in simple"]):
            supply_pct = round((supply_charge / total_bill) * 100) if total_bill > 0 else 56
            delivery_pct = round((delivery_charge / total_bill) * 100) if total_bill > 0 else 29
            return (
                f"### 💡 Your Bill in Simple Terms\n"
                f"Think of your electricity bill like a pizza order:\n\n"
                f"1. **The Pizza (Supply: ${supply_charge:.2f})** — This is the actual electricity you used ({usage_kwh:.1f} kWh). It's about **{supply_pct}%** of your total.\n"
                f"2. **The Delivery Fee (${delivery_charge:.2f})** — This pays for the wires, poles, and transformers that bring power to your home. About **{delivery_pct}%** of your total.\n"
                f"3. **The Tip & Extras** — Fixed service charge (${fixed_charge:.2f}), taxes (${tax:.2f}), and small regulatory fees.\n\n"
                f"**Bottom line**: You paid **${total_bill:.2f}** total. Most of that cost ({supply_pct}%) is for the electricity itself."
            )

        # --- Component / breakdown ranking ---
        elif any(w in q_lower for w in ["component", "breakdown", "break down", "which charge", "biggest charge",
                                         "largest charge", "most expensive", "highest charge", "what makes up",
                                         "increased the most", "biggest increase"]):
            components = [
                ("Supply (BGS)", supply_charge),
                ("Delivery", delivery_charge),
                ("Tax", tax),
                ("Fixed Customer Charge", fixed_charge),
            ]
            components.sort(key=lambda x: x[1], reverse=True)
            lines = [f"### 📊 Bill Component Ranking ({utility}, {period})\n"]
            lines.append(f"Your total bill of **${total_bill:.2f}** breaks down as follows (largest to smallest):\n")
            for rank, (name, amt) in enumerate(components, 1):
                pct = round((amt / total_bill) * 100, 1) if total_bill > 0 else 0
                bar = "█" * max(1, int(pct / 5))
                lines.append(f"{rank}. **{name}**: ${amt:.2f} ({pct}%) {bar}")
            lines.append(f"\n**Largest charge**: {components[0][0]} at ${components[0][1]:.2f} ({round((components[0][1]/total_bill)*100,1)}% of total).")
            return "\n".join(lines)

        # --- Tariff / rate schedule / specific charge explanations ---
        elif any(w in q_lower for w in ["tariff", "rate schedule", "sbc", "bgs", "rggi",
                                         "societal benefits", "charge mean"]):
            if "sbc" in q_lower or "societal" in q_lower:
                return (
                    f"### 📜 Societal Benefits Charge (SBC) Explained\n"
                    f"The SBC on your {utility} bill is a NJ BPU-mandated surcharge that funds:\n\n"
                    f"- **Clean Energy Programs**: Solar incentives, energy efficiency rebates, and renewable energy certificates.\n"
                    f"- **Low-Income Assistance**: Universal Service Fund (USF) and LIHEAP heating assistance.\n"
                    f"- **Environmental Remediation**: Nuclear decommissioning and contaminated site cleanup.\n\n"
                    f"**On your bill**: This charge is currently **$4.12** per month. It is set by the NJ Board of Public Utilities under N.J.S.A. 48:3-60."
                )
            elif "bgs" in q_lower:
                return (
                    f"### ⚡ Basic Generation Service (BGS) Explained\n"
                    f"BGS is the default electricity supply rate for {utility} customers who have not chosen a third-party supplier.\n\n"
                    f"- **How it's set**: Through an annual statewide auction administered by the NJ BPU.\n"
                    f"- **What drives it**: PJM wholesale market prices, natural gas costs, and capacity auction results.\n"
                    f"- **Your supply charge**: **${supply_charge:.2f}** for {usage_kwh:.1f} kWh this period."
                )
            elif "rggi" in q_lower:
                return (
                    f"### 🌍 Regional Greenhouse Gas Initiative (RGGI) Rider\n"
                    f"The RGGI rider recovers costs from NJ's participation in the multi-state carbon cap-and-trade program.\n\n"
                    f"- **Purpose**: Funds clean energy investments and greenhouse gas emission reduction programs.\n"
                    f"- **Your charge**: Approximately **$1.25** per month on your {utility} bill.\n"
                    f"- **Jurisdiction**: NJ Department of Environmental Protection and BPU."
                )
            else:
                return (
                    f"### 📋 {utility} Rate Schedule & Tariff Overview\n"
                    f"Your tariff is the official rate structure governing how {utility} calculates your bill.\n\n"
                    f"**Key tariff components on your bill:**\n"
                    f"- **Customer Charge**: ${fixed_charge:.2f}/month (fixed, usage-independent)\n"
                    f"- **Delivery Rate**: Volumetric charge for grid infrastructure → ${delivery_charge:.2f}\n"
                    f"- **BGS Supply Rate**: Electricity generation cost per kWh → ${supply_charge:.2f}\n"
                    f"- **Regulatory Riders**: SBC, RGGI, and other NJ BPU-mandated surcharges\n"
                    f"- **Tax**: NJ Sales & Use Tax at 6.625% → ${tax:.2f}"
                )

        # --- General bill explanation ---
        elif any(w in q_lower for w in ["explain my bill", "explain bill", "explain my electricity",
                                         "understand my bill", "tell me about my bill",
                                         "how is my bill", "what does my bill"]):
            supply_pct = round((supply_charge / total_bill) * 100, 1) if total_bill > 0 else 56
            delivery_pct = round((delivery_charge / total_bill) * 100, 1) if total_bill > 0 else 29
            return (
                f"### 📋 Complete Bill Explanation ({utility}, {period})\n"
                f"Your total bill is **${total_bill:.2f}** for **{usage_kwh:.1f} kWh** of electricity consumed.\n\n"
                f"**Charge Breakdown:**\n"
                f"| Component | Amount | % of Total |\n"
                f"|-----------|--------|------------|\n"
                f"| BGS Supply | ${supply_charge:.2f} | {supply_pct}% |\n"
                f"| Delivery | ${delivery_charge:.2f} | {delivery_pct}% |\n"
                f"| Customer Charge | ${fixed_charge:.2f} | {round((fixed_charge/total_bill)*100,1) if total_bill > 0 else 5}% |\n"
                f"| Tax | ${tax:.2f} | {round((tax/total_bill)*100,1) if total_bill > 0 else 6}% |\n\n"
                f"**Effective Rate**: ${effective_rate:.4f}/kWh — your all-in cost including delivery, supply, and fees."
            )

        # --- History / trend ---
        elif any(w in q_lower for w in ["history", "trend", "over time", "past months", "historical",
                                         "last few months", "previous months"]):
            return (
                f"### 📈 Billing History & Trend Analysis ({utility})\n"
                f"Your 6-month billing trajectory shows seasonal variation:\n\n"
                f"| Month | Usage (kWh) | Total Bill | Avg Temp (°F) |\n"
                f"|-------|-------------|------------|---------------|\n"
                f"| Jan 2026 | 820.0 | $156.40 | 32.4 |\n"
                f"| Feb 2026 | 790.0 | $150.70 | 34.1 |\n"
                f"| Mar 2026 | 680.0 | $131.20 | 45.2 |\n"
                f"| Apr 2026 | 610.0 | $118.50 | 54.8 |\n"
                f"| May 2026 | 650.0 | $126.14 | 63.5 |\n"
                f"| **Jun 2026** | **{usage_kwh:.1f}** | **${total_bill:.2f}** | **74.2** |\n\n"
                f"**Trend**: Your usage bottomed out in April (610 kWh) and has been rising as temperatures increase. The June bill is up **$18.13** from May, driven by summer cooling loads."
            )

        # --- Delivery / transmission / distribution ---
        elif any(w in q_lower for w in ["delivery", "transmission", "distribution"]):
            return (
                f"### 🚚 Grid Delivery & Transmission Component Breakdown\n"
                f"Your delivery charges total **${delivery_charge:.2f}** under your active {utility} rate schedule.\n\n"
                f"**Grid Infrastructure Breakdown:**\n"
                f"- **Distribution System**: Fee for high-voltage transformers, local distribution feeder lines, and pole maintenance.\n"
                f"- **Transmission Network**: High-voltage grid transmission regulated by FERC and PJM Interconnection.\n"
                f"- **Fixed Customer Charge**: Base monthly service fee of **${fixed_charge:.2f}** for account administration and metering."
            )

        # --- Supply / driver / commodity ---
        elif any(w in q_lower for w in ["supply", "driver", "commodity"]):
            return (
                f"### ⚡ Supply Generation & Commodity Cost Analysis ({utility})\n"
                f"Your supply charge for {period} is **${supply_charge:.2f}**, representing approximately **58%** of your total **${total_bill:.2f}** bill.\n\n"
                f"**Key Cost Drivers Identified:**\n"
                f"1. **PJM Wholesale Market**: Basic Generation Service (BGS) auction rates reflect regional PJM Locational Marginal Pricing (LMP).\n"
                f"2. **Fuel Commodity Prices**: Generation commodity rates track natural gas pipeline pricing and capacity auction clearing prices.\n"
                f"3. **Volumetric Consumption**: You consumed **{usage_kwh:.1f} kWh** at an effective rate of **${effective_rate:.4f}/kWh**."
            )

        # --- Weather / temperature / climate ---
        elif any(w in q_lower for w in ["weather", "temp", "heat", "degree", "climate"]):
            return (
                f"### 🌤️ Weather & Climate Impact Analysis ({utility})\n"
                f"Meteorological telemetry shows cooling degree-days (CDD: {cdd}) directly impacted your usage of **{usage_kwh:.1f} kWh**.\n\n"
                f"**Weather Factor Findings:**\n"
                f"- **HVAC Thermal Load**: Summer cooling degree-days increased air conditioning compressor run-times during peak afternoon hours.\n"
                f"- **Bill Financial Impact**: Seasonal temperature spikes accounted for an estimated **15% to 25%** of your monthly volumetric usage."
            )

        # --- Customer charge ---
        elif "customer" in q_lower and "charge" in q_lower:
            return (
                f"### 🏢 Fixed Monthly Customer Charge Analysis\n"
                f"Your fixed customer charge is **${fixed_charge:.2f}** per month on your {utility} statement.\n\n"
                f"This is a non-volumetric fixed baseline fee that covers account administration, meter maintenance, billing infrastructure, and 24/7 customer support regardless of how many kWh of electricity you consume."
            )

        # --- Forecast / predict ---
        elif any(w in q_lower for w in ["forecast", "predict", "next month", "projected"]):
            pred_kwh = usage_kwh * 1.03
            pred_cost = total_bill * 1.04
            return (
                f"### 🔮 Predictive Demand & Cost Forecast ({utility})\n"
                f"Based on historical billing regression and seasonal degree-day projections:\n\n"
                f"- **Projected Consumption**: **{pred_kwh:.1f} kWh** (P10: {pred_kwh * 0.9:.1f} kWh | P90: {pred_kwh * 1.15:.1f} kWh)\n"
                f"- **Estimated Monthly Bill**: **${pred_cost:.2f}**\n"
                f"- **Demand Stressors**: Seasonal HVAC cooling loads during upcoming mid-afternoon peak hours."
            )

        # --- Benchmark / compare / average / rank ---
        elif any(w in q_lower for w in ["benchmark", "compare", "average", "rank"]):
            return (
                f"### 🏙️ Utility & Regional Rate Benchmarking\n"
                f"Comparative analysis for **{utility}** (effective rate: **${effective_rate:.4f}/kWh**):\n\n"
                f"- **NJ State Average**: $0.1840/kWh — {utility} rate is competitive within standard state clearing margins.\n"
                f"- **National Average**: $0.1680/kWh — NJ regional rates reflect higher PJM capacity auction costs and transmission congestion surcharges.\n"
                f"- **Peer Utility Comparison**: Rates track closely with regional peers (JCP&L and Atlantic City Electric)."
            )

        # --- Save / reduce / optimize / tips ---
        elif any(w in q_lower for w in ["15%", "reduce", "save", "cut", "tip", "optimize",
                                         "lower my bill", "decrease", "how can i", "recommendations"]):
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

        # --- Why is bill high (NARROWED: requires bill-related context) ---
        elif ("why" in q_lower and any(w in q_lower for w in ["bill", "cost", "charge", "expensive", "usage"])) or \
             ("high" in q_lower and any(w in q_lower for w in ["bill", "cost", "charge", "usage"])) or \
             ("increase" in q_lower and any(w in q_lower for w in ["bill", "cost", "charge", "rate"])):
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
            f"### 📊 Bill Summary ({utility}, {period})\n"
            f"This is a validated mock response and bill summary. Your electricity bill totals **${total_bill:.2f}** for **{usage_kwh:.1f} kWh** at an effective rate of **${effective_rate:.4f}/kWh**.\n\n"
            f"Supply charges (${supply_charge:.2f}) make up the largest portion, followed by delivery (${delivery_charge:.2f}), "
            f"taxes (${tax:.2f}), and the fixed customer charge (${fixed_charge:.2f}).\n\n"
            f"Ask me about specific charges, savings strategies, forecasts, or comparisons for a detailed analysis!"
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

