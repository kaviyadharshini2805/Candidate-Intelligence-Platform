import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from src.models.canonical import CanonicalCandidate

class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas to calculate total page count dynamically and draw clean
    headers and footers on all pages.
    """
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
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6C6666"))
        
        # Header
        self.setStrokeColor(colors.HexColor("#E9D8D8"))
        self.setLineWidth(0.5)
        self.line(36, 756, 576, 756)
        self.drawString(36, 762, "Eightfold Candidate Ingestion Pipeline Report")
        
        # Footer
        self.line(36, 45, 576, 45)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 32, page_text)
        self.drawString(36, 32, "CONFIDENTIAL - Enterprise HR Analytics Platform")
        self.restoreState()

class CandidatePDFExporter:
    """
    Generates a professional multi-page ReportLab PDF report for a CanonicalCandidate.
    """
    def __init__(self, candidate: CanonicalCandidate):
        self.candidate = candidate
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        # Rose Glow Theme Palette
        self.primary_text = colors.HexColor('#3F3A3A')
        self.secondary_text = colors.HexColor('#6C6666')
        self.accent_title = colors.HexColor('#C98E93')
        self.border_color = colors.HexColor('#E9D8D8')
        
        self.title_style = ParagraphStyle(
            'CandidateTitle',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=self.primary_text,
            spaceAfter=4
        )
        
        self.section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=self.accent_title,
            spaceBefore=12,
            spaceAfter=4,
            keepWithNext=True
        )
        
        self.body_style = ParagraphStyle(
            'CandidateBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=self.primary_text,
            spaceAfter=3
        )
        
        self.body_bold = ParagraphStyle(
            'CandidateBodyBold',
            parent=self.body_style,
            fontName='Helvetica-Bold'
        )

        self.body_secondary = ParagraphStyle(
            'CandidateBodySecondary',
            parent=self.body_style,
            textColor=self.secondary_text
        )

        self.table_header_style = ParagraphStyle(
            'TableHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=self.primary_text
        )

        self.table_cell_style = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=self.primary_text
        )

    def export(self, output_filepath: str):
        # Page size: Letter (612 x 792 pt). Margin: 0.5 in (36 pt)
        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=54,
            bottomMargin=54
        )

        story = []

        # 1. Page 1: Candidate Overview & Summary
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"{self.candidate.full_name or 'Unknown Candidate'}", self.title_style))
        story.append(Paragraph("Canonical Candidate Profile Golden Record Overview", self.body_secondary))
        story.append(Spacer(1, 8))

        # Metrics overview block
        overall_conf = getattr(self.candidate, 'overall_confidence', 0.0)
        quality_score = getattr(self.candidate, 'data_quality_score', 0.0)
        yexp = self.candidate.years_experience
        
        yexp_str = f"{yexp} Years" if yexp is not None else "N/A"
        metrics_data = [
            [
                Paragraph("<b>Years Experience:</b>", self.body_style),
                Paragraph(yexp_str, self.body_style),
                Paragraph("<b>Ingestion Confidence:</b>", self.body_style),
                Paragraph(f"{int(overall_conf * 100)}%", self.body_style),
            ],
            [
                Paragraph("<b>Data Quality Score:</b>", self.body_style),
                Paragraph(f"{int(quality_score * 100)}%", self.body_style),
                Paragraph("<b>Location:</b>", self.body_style),
                Paragraph(", ".join([x for x in self.candidate.location if x]) or "N/A", self.body_style)
            ]
        ]
        metrics_table = Table(metrics_data, colWidths=[120, 150, 120, 150])
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 1, self.border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.5, self.border_color),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFFDFC")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 10))

        # Contact Info & Links
        story.append(Paragraph("Contact Information & Digital Profiles", self.section_header_style))
        emails_str = ", ".join(self.candidate.emails) or "None"
        phones_str = ", ".join(self.candidate.phones) or "None"
        
        linkedin = self.candidate.links.linkedin or "None"
        github = self.candidate.links.github or "None"
        portfolio = self.candidate.links.portfolio or "None"
        
        contact_data = [
            [Paragraph("<b>Emails:</b>", self.body_style), Paragraph(emails_str, self.body_style)],
            [Paragraph("<b>Phones:</b>", self.body_style), Paragraph(phones_str, self.body_style)],
            [Paragraph("<b>LinkedIn:</b>", self.body_style), Paragraph(linkedin, self.body_style)],
            [Paragraph("<b>GitHub:</b>", self.body_style), Paragraph(github, self.body_style)],
            [Paragraph("<b>Portfolio:</b>", self.body_style), Paragraph(portfolio, self.body_style)],
        ]
        contact_table = Table(contact_data, colWidths=[90, 450])
        contact_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(contact_table)
        story.append(Spacer(1, 10))

        # Professional Summary / Headline
        story.append(Paragraph("Professional Summary", self.section_header_style))
        story.append(Paragraph(self.candidate.headline or "No professional summary provided.", self.body_style))
        story.append(Spacer(1, 10))

        # Skills Table
        story.append(Paragraph("Canonical Skills", self.section_header_style))
        skills_data = [[Paragraph("Skill", self.table_header_style), Paragraph("Confidence", self.table_header_style), Paragraph("Contributing Sources", self.table_header_style)]]
        
        for skill in self.candidate.skills:
            sources_str = ", ".join(skill.sources)
            skills_data.append([
                Paragraph(skill.name, self.table_cell_style),
                Paragraph(f"{int(skill.confidence * 100)}%", self.table_cell_style),
                Paragraph(sources_str, self.table_cell_style)
            ])
            
        skills_table = Table(skills_data, colWidths=[150, 100, 290])
        skills_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8E3E5')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, self.border_color),
        ]))
        story.append(skills_table)

        # Page Break
        story.append(PageBreak())

        # 2. Page 2: Work History & Education
        story.append(Spacer(1, 10))
        story.append(Paragraph("Professional Experience", self.section_header_style))
        if self.candidate.experience:
            for exp in self.candidate.experience:
                timeline = f"{exp.start or 'N/A'} — {exp.end or 'Present'}"
                exp_header = f"<b>{exp.title}</b> at <b>{exp.company}</b> ({timeline})"
                story.append(Paragraph(exp_header, self.body_style))
                story.append(Paragraph(exp.summary or "", self.body_secondary))
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No employment experience registered.", self.body_secondary))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Academic Qualifications", self.section_header_style))
        if self.candidate.education:
            for edu in self.candidate.education:
                deg = f"{edu.degree or 'Degree'}"
                if edu.field:
                    deg += f" in {edu.field}"
                edu_line = f"<b>{edu.institution}</b> — {deg} (Class of {edu.end_year or 'N/A'})"
                story.append(Paragraph(edu_line, self.body_style))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("No education history registered.", self.body_secondary))

        # Page Break
        story.append(PageBreak())

        # 3. Page 3: Provenance & System Pipeline Metadata
        story.append(Spacer(1, 10))
        story.append(Paragraph("Field Ingestion Provenance Trace", self.section_header_style))
        story.append(Paragraph("Full audit log tracing which ingestion source resolved and populated each golden record attribute.", self.body_secondary))
        story.append(Spacer(1, 6))

        prov_data = [[
            Paragraph("Field", self.table_header_style),
            Paragraph("Source File", self.table_header_style),
            Paragraph("Parsing Method", self.table_header_style),
            Paragraph("Survivorship Decision / Priority Rule", self.table_header_style)
        ]]
        
        for item in self.candidate.provenance:
            prov_data.append([
                Paragraph(f"<b>{item.field}</b>", self.table_cell_style),
                Paragraph(item.source, self.table_cell_style),
                Paragraph(item.method or "N/A", self.table_cell_style),
                Paragraph(item.decision_reason or "Source priority map tie-breaker", self.table_cell_style)
            ])
            
        prov_table = Table(prov_data, colWidths=[100, 110, 90, 240])
        prov_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8E3E5')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, self.border_color),
        ]))
        story.append(prov_table)
        story.append(Spacer(1, 10))

        # System Pipeline Validation Warnings
        story.append(Paragraph("Pipeline Integrity Warnings", self.section_header_style))
        warnings = getattr(self.candidate, 'validation_warnings', [])
        if warnings:
            for warn in warnings:
                story.append(Paragraph(f"• <font color='#C85B5B'>{warn}</font>", self.body_style))
        else:
            story.append(Paragraph("<font color='#5C9E6E'>✓ Ingestion validation succeeded. No integrity conflicts detected.</font>", self.body_style))

        story.append(Spacer(1, 15))
        story.append(Paragraph("Ingestion Report Metadata", self.section_header_style))
        meta_data = [
            [Paragraph("<b>Report Generated:</b>", self.body_style), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.body_style)],
            [Paragraph("<b>Ingestion System Version:</b>", self.body_style), Paragraph("2.0 Stable Build", self.body_style)],
            [Paragraph("<b>Candidate ID:</b>", self.body_style), Paragraph(self.candidate.candidate_id or "N/A", self.body_style)]
        ]
        meta_table = Table(meta_data, colWidths=[150, 390])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)

        # Build document with multi-page NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
