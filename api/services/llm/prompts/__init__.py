"""
Phase 2 — Modular Prompts Package.
Aggregates all domain-specific versioned prompt templates.
"""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.bill.explanation import bill_explanation
from api.services.llm.prompts.executive.summary import executive_summary
from api.services.llm.prompts.report.pdf_report import pdf_report
from api.services.llm.prompts.recommendation.savings import savings
from api.services.llm.prompts.forecast.narrative import forecast_narrative

__all__ = [
    "PromptTemplate",
    "bill_explanation",
    "executive_summary",
    "pdf_report",
    "savings",
    "forecast_narrative",
]
