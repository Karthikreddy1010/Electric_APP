import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1e293b"))
        # Header
        self.drawString(54, 11 * 72 - 36, "ElectricAI - Complete End-to-End Analytics Report")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)
        
        # Footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 36, "CONFIDENTIAL - ELECTRICITY COST INTELLIGENCE & ANALYTICS PLATFORM")
        self.drawRightString(8.5 * 72 - 54, 36, f"Page {self._pageNumber} of {page_count}")
        self.line(54, 48, 8.5 * 72 - 54, 48)
        self.restoreState()

def build_pdf(md_file, pdf_file):
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'DocH3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=12,
        spaceAfter=3
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=7.5,
        leading=9.5,
        spaceAfter=0
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        spaceAfter=0
    )

    story = []

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    in_table = False
    table_data = []

    def clean_text(txt):
        txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', txt)
        txt = re.sub(r'\*(.*?)\*', r'<i>\1</i>', txt)
        txt = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', txt)
        return txt

    for line in lines:
        raw_line = line.strip()

        # Handle Table
        if raw_line.startswith('|') and raw_line.endswith('|'):
            if '---' in raw_line:
                continue
            cells = [clean_text(c.strip()) for c in raw_line.split('|')[1:-1]]
            table_data.append(cells)
            in_table = True
            continue
        elif in_table:
            # End of table
            if table_data:
                # Build reportlab table
                formatted_table = []
                for idx, row in enumerate(table_data):
                    r_formatted = []
                    for cell in row:
                        st = table_header_style if idx == 0 else table_cell_style
                        r_formatted.append(Paragraph(cell, st))
                    formatted_table.append(r_formatted)

                t = Table(formatted_table, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
            table_data = []
            in_table = False

        if not raw_line:
            story.append(Spacer(1, 3))
            continue

        if raw_line.startswith('# '):
            story.append(Paragraph(clean_text(raw_line[2:]), title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=8))
        elif raw_line.startswith('## '):
            story.append(Paragraph(clean_text(raw_line[3:]), h1_style))
        elif raw_line.startswith('### '):
            story.append(Paragraph(clean_text(raw_line[4:]), h2_style))
        elif raw_line.startswith('#### '):
            story.append(Paragraph(clean_text(raw_line[5:]), h3_style))
        elif raw_line.startswith('* ') or raw_line.startswith('- ') or re.match(r'^\d+\.\s', raw_line):
            prefix = "• " if (raw_line.startswith('* ') or raw_line.startswith('- ')) else ""
            txt = re.sub(r'^\d+\.\s', r'', raw_line) if not prefix else raw_line[2:]
            story.append(Paragraph(prefix + clean_text(txt), bullet_style))
        elif raw_line.startswith('> '):
            quote_text = clean_text(raw_line[2:])
            p = Paragraph(quote_text, ParagraphStyle('Quote', parent=body_style, textColor=colors.HexColor('#0f766e'), fontName='Helvetica-Oblique'))
            t_quote = Table([[p]], colWidths=[7.0*72])
            t_quote.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#86efac')),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(Spacer(1, 4))
            story.append(t_quote)
            story.append(Spacer(1, 6))
        elif raw_line == '---':
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=6, spaceAfter=6))
        else:
            story.append(Paragraph(clean_text(raw_line), body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF at {pdf_file}")

if __name__ == "__main__":
    md = r'c:\Users\dukar\OneDrive\Desktop\Electric\reports\comprehensive_end_to_end_analysis_report.md'
    pdf = r'c:\Users\dukar\OneDrive\Desktop\Electric\reports\comprehensive_end_to_end_analysis_report.pdf'
    build_pdf(md, pdf)
