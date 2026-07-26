"""Phase 2 — Business Report Builder (placeholder for utility & market benchmarks)."""
from typing import Dict, Any


class BusinessReportBuilder:
    """Builds utility benchmark and market analysis reports."""

    @staticmethod
    def build(narrative_text: str, context_data: Dict[str, Any]) -> str:
        header = (
            "# Utility Market Benchmark Report\n\n"
            "**Report Type**: Business Intelligence  \n\n"
            "---\n\n"
        )
        return header + narrative_text
