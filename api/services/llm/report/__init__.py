"""
Phase 2 — Modular Report Generator Package.
Generates Markdown, HTML, and PDF reports from AnalyticsResult context and narrative text.
"""
from api.services.llm.report.markdown import MarkdownReportRenderer
from api.services.llm.report.html import HTMLReportRenderer
from api.services.llm.report.pdf import PDFReportRenderer
from api.services.llm.report.executive import ExecutiveReportBuilder
from api.services.llm.report.customer import CustomerReportBuilder

__all__ = [
    "MarkdownReportRenderer",
    "HTMLReportRenderer",
    "PDFReportRenderer",
    "ExecutiveReportBuilder",
    "CustomerReportBuilder",
]
