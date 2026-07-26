"""Phase 2 — Customer Report Builder."""
from typing import Dict, Any


class CustomerReportBuilder:
    """Builds consumer-facing bill interpretation reports."""

    @staticmethod
    def build(narrative_text: str, context_data: Dict[str, Any]) -> str:
        bill = context_data.get("bill", context_data)
        total = bill.get("total_bill", 0.0)
        usage = bill.get("usage_kwh", 0.0)
        utility = bill.get("utility", context_data.get("customer", {}).get("utility", "Your Utility"))

        header = (
            "# Your Monthly Electricity Bill Report\n\n"
            f"**Utility**: {utility}  \n"
            f"**Total Bill**: ${total:.2f}  \n"
            f"**Usage**: {usage:.1f} kWh  \n\n"
            "---\n\n"
        )
        return header + narrative_text
