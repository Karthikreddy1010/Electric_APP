"""Phase 2 — PDF Report Renderer using reportlab."""
import io
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PDFReportRenderer:
    """Generates formatted PDF reports using reportlab."""

    @staticmethod
    def render(narrative_text: str, context_data: Dict[str, Any]) -> io.BytesIO:
        """Render narrative text into a PDF document. Returns BytesIO buffer."""
        from reportlab.lib.pagesizes import LETTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        bill = context_data.get("bill", context_data)
        period = bill.get("billing_period", bill.get("current_month", "Current Period"))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Electricity Bill Analysis Report", styles["Title"]))
        elements.append(Spacer(1, 12))

        for line in narrative_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("### "):
                elements.append(Spacer(1, 8))
                elements.append(Paragraph(stripped[4:], styles["Heading3"]))
            elif stripped.startswith("## "):
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(stripped[3:], styles["Heading2"]))
            elif stripped.startswith("# "):
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(stripped[2:], styles["Heading1"]))
            else:
                elements.append(Paragraph(stripped, styles["Normal"]))
            elements.append(Spacer(1, 4))

        try:
            doc.build(elements)
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            # Return minimal PDF on error
            buffer = io.BytesIO()
            doc2 = SimpleDocTemplate(buffer, pagesize=LETTER)
            doc2.build([
                Paragraph("Electricity Bill Analysis Report", styles["Title"]),
                Paragraph("Report generation encountered an error.", styles["Normal"]),
            ])

        buffer.seek(0)
        return buffer
