"""Phase 2 — Markdown Report Renderer."""
from typing import Dict, Any


class MarkdownReportRenderer:
    """Renders bill analysis narrative into clean GitHub-flavored Markdown."""

    @staticmethod
    def render(narrative_text: str, context_data: Dict[str, Any]) -> str:
        bill = context_data.get("bill", context_data)
        total = bill.get("total_bill", 0.0)
        usage = bill.get("usage_kwh", 0.0)
        period = bill.get("billing_period", "Current Period")

        header = (
            f"# Electricity Bill Analysis Report\n\n"
            f"**Billing Period**: {period}  \n"
            f"**Total Bill**: ${total:.2f}  \n"
            f"**Usage**: {usage:.1f} kWh  \n\n"
            f"---\n\n"
        )
        return header + narrative_text
