"""Phase 2 — Executive Report Builder."""
from typing import Dict, Any


class ExecutiveReportBuilder:
    """Builds C-suite executive summaries from analytics context."""

    @staticmethod
    def build(narrative_text: str, context_data: Dict[str, Any]) -> str:
        stats = context_data.get("statistics", {})
        bill = context_data.get("bill", context_data)
        total = bill.get("total_bill", 0.0)

        header = (
            "# Executive Energy Intelligence Brief\n\n"
            f"**Total Monthly Expenditure**: ${total:.2f}  \n"
            f"**Report Type**: Executive Summary  \n\n"
            "---\n\n"
        )
        return header + narrative_text
