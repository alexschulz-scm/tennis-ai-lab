import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

# --- Configuration: Brand Assets ---
BRAND_COLOR = "#2C3E50"  # Deep Navy
ACCENT_COLOR = "#E67E22" # Tennis Clay Orange

def clean_text(text):
    """
    Removes emojis and unsupported characters from text to prevent PDF errors.
    """
    if not text: return ""
    
    # 1. Encode to ASCII, ignoring errors (strips emojis), then decode back
    clean = text.encode('ascii', 'ignore').decode('ascii')
    
    # 2. Strip extra whitespace
    return clean.strip()

def create_branded_styles():
    """Defines the custom paragraph styles for the report."""
    styles = getSampleStyleSheet()
    
    # 1. Main Title (H1)
    styles.add(ParagraphStyle(
        name='BrandTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor(BRAND_COLOR),
        spaceAfter=12,
        alignment=1 # Center
    ))

    # 2. Section Headers (H2)
    styles.add(ParagraphStyle(
        name='BrandHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor(BRAND_COLOR),
        borderColor=colors.HexColor(ACCENT_COLOR),
        borderPadding=5,
        borderWidth=0,
        spaceBefore=20,
        spaceAfter=10
    ))
    
    # 3. Normal Body Text
    styles.add(ParagraphStyle(
        name='BrandNormal',
        parent=styles['Normal'],
        fontSize=11,
        leading=14, # Line spacing
        spaceAfter=6
    ))

    # 4. Bullet Points
    styles.add(ParagraphStyle(
        name='BrandBullet',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=6
    ))

    # 5. Blockquotes / Highlights
    styles.add(ParagraphStyle(
        name='BrandQuote',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.darkgray,
        leftIndent=30,
        fontName='Helvetica-Oblique',
        spaceAfter=12
    ))

    return styles

def parse_markdown_to_flowables(md_content, styles):
    """
    Parses Markdown text line-by-line into ReportLab Flowables.
    """
    story = []
    lines = md_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # CLEAN THE LINE FIRST
        line = clean_text(line)
        
        # -- 1. Inline Formatting (Bold/Italic) --
        # Convert **text** to <b>text</b> for ReportLab
        line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        # Convert *text* to <i>text</i>
        line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)

        # -- 2. Block Element Detection --
        if line.startswith('# '):
            # H1 Title
            title_text = line[2:].strip()
            story.append(Paragraph(title_text, styles['BrandTitle']))
            story.append(Spacer(1, 12))

        elif line.startswith('## '):
            # H2 Heading
            heading_text = line[3:].strip()
            story.append(Spacer(1, 12))
            story.append(Paragraph(heading_text, styles['BrandHeading']))

        elif line.startswith('* ') or line.startswith('- '):
            # Bullet list
            bullet_text = f"• {line[2:].strip()}"
            story.append(Paragraph(bullet_text, styles['BrandBullet']))

        elif line.startswith('> '):
            # Blockquote
            quote_text = line[2:].strip()
            story.append(Paragraph(quote_text, styles['BrandQuote']))
            
        else:
            # Standard Paragraph
            story.append(Paragraph(line, styles['BrandNormal']))

    return story

def add_header_footer(canvas, doc):
    """
    Draws the fixed Header and Footer on every page.
    """
    canvas.saveState()
    
    # --- Header ---
    canvas.setFont('Helvetica-Bold', 10)
    canvas.setFillColor(colors.HexColor(BRAND_COLOR))
    canvas.drawString(inch, 10.5 * inch, "Tennis AI Lab")
    
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(colors.HexColor(ACCENT_COLOR))
    canvas.drawString(inch, 10.35 * inch, "Biomechanical Analysis Report")
    
    # Draw Orange Line
    canvas.setStrokeColor(colors.HexColor(BRAND_COLOR))
    canvas.setLineWidth(1)
    canvas.line(inch, 10.25 * inch, 7.5 * inch, 10.25 * inch)
    
    # --- Footer ---
    canvas.setStrokeColor(colors.lightgrey)
    canvas.line(inch, 0.75 * inch, 7.5 * inch, 0.75 * inch)
    
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.gray)
    footer_text = f"© {datetime.now().year} Schulz Creative Media | Automated AI Analysis"
    canvas.drawCentredString(4.25 * inch, 0.5 * inch, footer_text)
    
    canvas.restoreState()

def convert_md_to_pdf(input_md_path, output_pdf_path):
    """
    Main entry point to convert MD file to PDF.
    """
    if not os.path.exists(input_md_path):
        print(f"Error: File not found at {input_md_path}")
        return

    # 1. Read Markdown
    with open(input_md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 2. Setup Document
    doc = SimpleDocTemplate(
        output_pdf_path, 
        pagesize=letter,
        rightMargin=inch, leftMargin=inch,
        topMargin=1.5*inch, bottomMargin=1*inch # Extra top margin for Header
    )

    # 3. Create Styles & Content
    styles = create_branded_styles()
    story = parse_markdown_to_flowables(md_content, styles)

    # 4. Build with Header/Footer Callback
    print(f"Generating PDF from: {input_md_path}")
    try:
        doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
        print(f"Success! PDF saved to: {output_pdf_path}")
    except Exception as e:
        print(f"Error building PDF: {e}")

# --- Execution Block ---
if __name__ == "__main__":
    # Test file paths
    INPUT_FILE = "analyses/report_backhand_2025_12_21.md"
    OUTPUT_FILE = "reports/final_backhand_report.pdf"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    convert_md_to_pdf(INPUT_FILE, OUTPUT_FILE)
