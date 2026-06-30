import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_design_pdf():
    pdf_filename = "Kaviyadharshini_M_kaviyadharshini.works@gmail.com_Eightfold.pdf"
    
    # Setup document with compact margins (28 pt = ~0.38 inches) for a single page layout
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=28
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles to fit high density content on one page
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#475569'),
        alignment=2 # Right aligned
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=5,
        spaceAfter=3,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=3
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    list_style = ParagraphStyle(
        'DocList',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-12,
        spaceAfter=2
    )
    
    story = []
    
    # 1. Header (Candidate Info + Title)
    header_data = [
        [
            Paragraph("Multi-Source Candidate Data Transformer<br/><font size=8.5 color='#64748B'><b>Stage 1 Technical Design Document</b></font>", title_style),
            Paragraph("<b>Candidate:</b> Kaviyadharshini M<br/><b>Email:</b> kaviyadharshini.works@gmail.com<br/><b>Role:</b> Engineering Intern (Jul-Dec 2026)", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[310, 246])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    
    # 2. Section 1: Ingestion & Parsing Pipeline
    story.append(Paragraph("1. PIPELINE & SYSTEM WORKFLOW (ARCHITECTURE BREAKDOWN)", h1_style))
    pipeline_text = (
        "The system enforces a strict <b>unidirectional data flow</b> designed around the <b>Ports and Adapters</b> pattern to isolate "
        "I/O from core processing: <b>(1) Ingest</b>: Input adapters (CSV, JSON, PDF, DOCX, TXT) read raw files/streams and output a "
        "standard raw envelope. <b>(2) Extract/Parse</b>: Extracts raw semi-structured text. <b>(3) Normalize</b>: Standardizes values "
        "(phones, dates, names) into clean formats. <b>(4) Resolve Identity</b>: Deterministically matches candidates against existing profiles "
        "using indexed hashes of primary keys (emails, phones). <b>(5) Merge & Conflict Resolution</b>: Merges records field-by-field, "
        "resolving schema collisions using configured rules while building a central <b>provenance log</b>. <b>(6) Validate</b>: Business "
        "validation runs on the merged golden record (Pydantic v2). <b>(7) Project</b>: Configurable mapper reshapes output JSON dynamically."
    )
    story.append(Paragraph(pipeline_text, body_style))
    
    # 3. Section 2: Canonical Output Schema & Normalization Formats
    story.append(Paragraph("2. CANONICAL DATA SCHEMA & NORMALIZATION RULES", h1_style))
    schema_intro = (
        "The internal <b>Canonical Candidate Record</b> defines a single point of truth. All attributes are normalized upon entry:"
    )
    story.append(Paragraph(schema_intro, body_style))
    
    norms = [
        "<b>Names</b>: Stripped of honorifics (Mr., Dr.), parsed into Title Case. Concat into <i>full_name</i>.",
        "<b>Phone Numbers</b>: Parsed, stripped of symbols, and formatted strictly to <b>E.164</b> (e.g., +15551234567). Default country applied if missing.",
        "<b>Emails</b>: Trimmed, validated against RFC 5322, lowercased to ensure deterministic matching.",
        "<b>Locations</b>: Structured as 3-tuple <i>[city, region, country]</i>. Country codes mapped to <b>ISO-3166 alpha-2</b> (uppercase).",
        "<b>Dates</b>: Standardized to <b>YYYY-MM</b> or <b>YYYY-MM-DD</b>. 'Present' / 'Current' maps to null to represent active status.",
        "<b>Skills</b>: Flat strings mapped to standard taxonomy terms (e.g. 'js', 'javascript' -> 'JavaScript') to ensure clean search indexing."
    ]
    for norm in norms:
        story.append(Paragraph(f"• {norm}", list_style))
        
    # 4. Section 3: Merge Policy, Conflict Resolution & Confidence Scoring
    story.append(Paragraph("3. IDENTITY RESOLUTION, MERGE POLICY & CONFIDENCE ASSIGNMENT", h1_style))
    merge_text = (
        "<b>Identity Resolution (Matching)</b>: Records are merged if they share any normalized email or phone number. "
        "A deterministic matcher computes cryptographic hashes of emails/phones for instant lookup. "
        "<br/><b>Conflict Resolution (Field-Level Survivorship)</b>: We use a configurable, attribute-level priority cascade: "
        "<b>(1) Source Priority</b>: Admin-defined trust hierarchy (e.g., <i>recruiter_notes</i> [1.0] > <i>ats_json</i> [0.8] > <i>resume_pdf</i> [0.6]). "
        "<b>(2) Extraction Confidence</b>: Parsers supply a confidence rating. If source priority ties, higher confidence wins. "
        "<b>(3) Source Recency</b>: Later source update timestamps break ties. "
        "<br/><b>Collection Merging</b>: Flat lists (like skills) are union-deduplicated. Hierarchical lists (work/education) are matched by key "
        "(e.g., company+title) and merged internally; otherwise, they are appended. "
        "<b>Provenance</b> is tracked per-field: <i>provenance: [ { field, source, method } ]</i>. "
        "<b>Overall Confidence</b> is calculated as the weighted average of surviving attribute extraction confidences."
    )
    story.append(Paragraph(merge_text, body_style))
    
    # 5. Section 4: Configurable Output & Projection Engine
    story.append(Paragraph("4. RUNTIME CONFIGURABLE PROJECTION ENGINE", h1_style))
    proj_text = (
        "To satisfy downstream consumer schemas without modifying code, we implement a runtime JSON projection engine. The engine reads "
        "a configuration specifying: <b>(1) Subset selection</b>: Filters fields. <b>(2) Remapping (from)</b>: Paths like <i>emails[0]</i> "
        "mapped to a new key <i>primary_email</i>. <b>(3) Custom normalizations</b>: Formats fields at output time (e.g. anonymizes skills, "
        "masks names, forces E.164). <b>(4) Missing value handling</b>: Configures fallback actions (<i>null</i>, <i>omit</i> from JSON, or "
        "raise a fatal <i>error</i>). This maintains clean separation between canonical storage and API display layers."
    )
    story.append(Paragraph(proj_text, body_style))
    
    # 6. Section 5: Edge Cases, Recovery & Descope
    story.append(Paragraph("5. EDGE CASES, ERROR RECOVERY & STRATEGIC DESCOPING", h1_style))
    
    edges = [
        "<b>Garbage/Empty Sources</b>: If an adapter receives malformed/empty files, it raises an <i>IngestionWarning</i>, generates an empty record wrapper, and allows the remaining sources to run without crashing the batch.",
        "<b>Conflicting Names (e.g. Jon Doe vs Johnathan Doe)</b>: Identity resolver matches them via email. The Merge Engine retains 'Johnathan Doe' if it came from the higher-priority ATS JSON source, but records 'Jon Doe' in the provenance file notes.",
        "<b>Overlapping Work Timelines</b>: If merged dates result in overlapping jobs, a validation warning is logged, but records are preserved to prevent loss of candidate experience data.",
        "<b>Deliberate Descope (Time Pressure)</b>: We descoped: (1) Fuzzy matching names/companies via NLP/LLM (leveraging strict identifier matching instead), (2) Real-time external API calls for skill taxomony verification (using an in-memory taxonomy dictionary instead), and (3) A database layer (saving output directly to JSON files)."
    ]
    for edge in edges:
        story.append(Paragraph(f"• {edge}", list_style))
        
    doc.build(story)
    print(f"Successfully generated {pdf_filename}")

if __name__ == "__main__":
    create_design_pdf()
