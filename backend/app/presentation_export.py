"""
Welcome Nights Presentation Export Service

This module provides export functionality for presentations to PPTX and PDF formats.
"""

import io
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pptx import Presentation as PptxPresentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

from . import models, crud


# Slide dimensions (standard 16:9)
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert hex color to RGBColor"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


def export_to_pptx(
    db: Session,
    presentation_id: int,
    output_path: Optional[str] = None
) -> bytes:
    """
    Export a presentation to PPTX format.

    Args:
        db: Database session
        presentation_id: ID of the presentation to export
        output_path: Optional path to save the file (if None, returns bytes)

    Returns:
        Bytes of the PPTX file
    """
    # Get presentation data
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise ValueError(f"Presentation {presentation_id} not found")

    brand = crud.get_brand(db, presentation.brand_id)
    facility = crud.get_wn_facility(db, presentation.facility_id)
    slides = crud.get_presentation_slides(db, presentation_id)

    # Create PPTX
    pptx = PptxPresentation()
    pptx.slide_width = SLIDE_WIDTH
    pptx.slide_height = SLIDE_HEIGHT

    # Get colors
    primary_color = hex_to_rgb(brand.primary_color or "#0b7280")
    secondary_color = hex_to_rgb(brand.secondary_color or "#065a67")

    # Generate slides
    for slide_data in slides:
        add_slide_to_pptx(
            pptx,
            slide_data,
            brand,
            facility,
            primary_color,
            secondary_color
        )

    # Save to bytes
    buffer = io.BytesIO()
    pptx.save(buffer)
    buffer.seek(0)
    pptx_bytes = buffer.read()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pptx_bytes)

    return pptx_bytes


def add_slide_to_pptx(
    pptx: PptxPresentation,
    slide_data: models.PresentationSlideInstance,
    brand: models.Brand,
    facility: models.WNFacility,
    primary_color: RGBColor,
    secondary_color: RGBColor
):
    """Add a single slide to the PPTX based on slide type"""
    slide_type = slide_data.slide_type
    payload = slide_data.payload or {}

    # Use blank layout
    blank_layout = pptx.slide_layouts[6]  # Blank
    slide = pptx.slides.add_slide(blank_layout)

    if slide_type == "WelcomeIntro":
        create_welcome_pptx_slide(slide, payload, brand, facility, primary_color)
    elif slide_type == "RaffleBumper":
        create_raffle_pptx_slide(slide, payload, primary_color)
    elif slide_type == "HistoryBlock":
        create_content_pptx_slide(slide, "Our History", payload, primary_color)
    elif slide_type == "FootprintBlock":
        create_content_pptx_slide(slide, "Our Growing Footprint", payload, primary_color)
    elif slide_type == "RegionsBlock":
        create_content_pptx_slide(slide, "Our Regions", payload, primary_color)
    elif slide_type == "CultureBlock":
        create_culture_pptx_slide(slide, payload, brand, primary_color)
    elif slide_type == "GameSlide":
        create_game_pptx_slide(slide, payload, primary_color)
    elif slide_type == "PillarsClosing":
        create_pillars_pptx_slide(slide, payload, primary_color, secondary_color)
    else:
        # Generic slide
        create_generic_pptx_slide(slide, slide_type, payload, primary_color)


def create_welcome_pptx_slide(
    slide,
    payload: Dict[str, Any],
    brand: models.Brand,
    facility: models.WNFacility,
    primary_color: RGBColor
):
    """Create welcome/intro slide"""
    # Background color
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT
    )
    background.fill.solid()
    background.fill.fore_color.rgb = primary_color
    background.line.fill.background()

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2.5), Inches(12.33), Inches(1.5)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = f"Welcome to {brand.name}"
    title_para.font.size = Pt(54)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)
    title_para.alignment = PP_ALIGN.CENTER

    # Facility name
    subtitle_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(4), Inches(12.33), Inches(1)
    )
    subtitle_frame = subtitle_box.text_frame
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.text = facility.name
    subtitle_para.font.size = Pt(32)
    subtitle_para.font.color.rgb = RGBColor(255, 255, 255)
    subtitle_para.alignment = PP_ALIGN.CENTER

    # Event type
    event_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(5), Inches(12.33), Inches(0.75)
    )
    event_frame = event_box.text_frame
    event_para = event_frame.paragraphs[0]
    event_para.text = "Culture Night"
    event_para.font.size = Pt(24)
    event_para.font.color.rgb = RGBColor(255, 255, 255)
    event_para.alignment = PP_ALIGN.CENTER


def create_raffle_pptx_slide(
    slide,
    payload: Dict[str, Any],
    primary_color: RGBColor
):
    """Create raffle bumper slide"""
    # Background
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT
    )
    background.fill.solid()
    background.fill.fore_color.rgb = RGBColor(255, 215, 0)  # Gold
    background.line.fill.background()

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2.5), Inches(12.33), Inches(2)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = payload.get("title", "RAFFLE TIME!")
    title_para.font.size = Pt(72)
    title_para.font.bold = True
    title_para.font.color.rgb = primary_color
    title_para.alignment = PP_ALIGN.CENTER

    # Subtitle
    subtitle_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(4.5), Inches(12.33), Inches(1)
    )
    subtitle_frame = subtitle_box.text_frame
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.text = payload.get("subtitle", "Time to draw a winner!")
    subtitle_para.font.size = Pt(28)
    subtitle_para.font.color.rgb = primary_color
    subtitle_para.alignment = PP_ALIGN.CENTER


def create_content_pptx_slide(
    slide,
    title: str,
    payload: Dict[str, Any],
    primary_color: RGBColor
):
    """Create generic content slide"""
    # Title bar
    title_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.5)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = primary_color
    title_bar.line.fill.background()

    # Title text
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.75)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = payload.get("title", title)
    title_para.font.size = Pt(36)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)

    # Content area
    content = payload.get("content", {})
    if isinstance(content, dict):
        # If content has items, display them
        items = content.get("items", [])
        if items:
            content_box = slide.shapes.add_textbox(
                Inches(0.75), Inches(2), Inches(11.83), Inches(5)
            )
            tf = content_box.text_frame
            tf.word_wrap = True
            for i, item in enumerate(items[:6]):  # Limit to 6 items
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                if isinstance(item, dict):
                    p.text = f"  {item.get('text', str(item))}"
                else:
                    p.text = f"  {item}"
                p.font.size = Pt(24)
                p.font.color.rgb = RGBColor(50, 50, 50)
                p.space_after = Pt(12)


def create_culture_pptx_slide(
    slide,
    payload: Dict[str, Any],
    brand: models.Brand,
    primary_color: RGBColor
):
    """Create culture slide with Cascadia Way vs Common Way"""
    # Title bar
    title_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.5)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = primary_color
    title_bar.line.fill.background()

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.75)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = payload.get("title", f"The {brand.name} Way")
    title_para.font.size = Pt(36)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)

    # Subtitle
    subtitle_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2), Inches(12.33), Inches(0.75)
    )
    subtitle_frame = subtitle_box.text_frame
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.text = "We are NOT corporate"
    subtitle_para.font.size = Pt(28)
    subtitle_para.font.bold = True
    subtitle_para.font.color.rgb = primary_color
    subtitle_para.alignment = PP_ALIGN.CENTER


def create_game_pptx_slide(
    slide,
    payload: Dict[str, Any],
    primary_color: RGBColor
):
    """Create game slide"""
    # Title bar
    title_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.5)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = primary_color
    title_bar.line.fill.background()

    # Game title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.75)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = payload.get("title", "Game Time!")
    title_para.font.size = Pt(36)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)

    # Value label (if exists)
    value_label = payload.get("value_label")
    if value_label:
        label_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2), Inches(12.33), Inches(0.6)
        )
        label_frame = label_box.text_frame
        label_para = label_frame.paragraphs[0]
        label_para.text = value_label
        label_para.font.size = Pt(24)
        label_para.font.bold = True
        label_para.font.color.rgb = primary_color
        label_para.alignment = PP_ALIGN.CENTER

    # Rules
    rules = payload.get("rules", "")
    if rules:
        rules_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(3), Inches(11.83), Inches(4)
        )
        rules_frame = rules_box.text_frame
        rules_frame.word_wrap = True
        rules_para = rules_frame.paragraphs[0]
        rules_para.text = rules
        rules_para.font.size = Pt(22)
        rules_para.font.color.rgb = RGBColor(50, 50, 50)


def create_pillars_pptx_slide(
    slide,
    payload: Dict[str, Any],
    primary_color: RGBColor,
    secondary_color: RGBColor
):
    """Create 3 pillars closing slide"""
    # Background
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT
    )
    background.fill.solid()
    background.fill.fore_color.rgb = primary_color
    background.line.fill.background()

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.75), Inches(12.33), Inches(1)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = "Our 3 Pillars"
    title_para.font.size = Pt(48)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)
    title_para.alignment = PP_ALIGN.CENTER

    # Pillars
    pillars = payload.get("pillars", [
        {"name": "Clinical", "description": "Excellence in care"},
        {"name": "Cultural", "description": "Our people, our values"},
        {"name": "Financial", "description": "Sustainable success"},
    ])

    x_positions = [Inches(1.5), Inches(5.17), Inches(8.83)]
    for i, pillar in enumerate(pillars[:3]):
        # Pillar box
        box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, x_positions[i], Inches(2.5), Inches(3), Inches(4)
        )
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(255, 255, 255)
        box.line.fill.background()

        # Pillar name
        name_box = slide.shapes.add_textbox(
            x_positions[i] + Inches(0.1), Inches(3), Inches(2.8), Inches(1)
        )
        name_frame = name_box.text_frame
        name_para = name_frame.paragraphs[0]
        name_para.text = pillar.get("name", "")
        name_para.font.size = Pt(28)
        name_para.font.bold = True
        name_para.font.color.rgb = primary_color
        name_para.alignment = PP_ALIGN.CENTER

        # Pillar description
        desc_box = slide.shapes.add_textbox(
            x_positions[i] + Inches(0.1), Inches(4), Inches(2.8), Inches(2)
        )
        desc_frame = desc_box.text_frame
        desc_frame.word_wrap = True
        desc_para = desc_frame.paragraphs[0]
        desc_para.text = pillar.get("description", "")
        desc_para.font.size = Pt(18)
        desc_para.font.color.rgb = RGBColor(100, 100, 100)
        desc_para.alignment = PP_ALIGN.CENTER


def create_generic_pptx_slide(
    slide,
    title: str,
    payload: Dict[str, Any],
    primary_color: RGBColor
):
    """Create a generic slide for unknown types"""
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(12.33), Inches(1)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(36)
    title_para.font.bold = True
    title_para.font.color.rgb = primary_color


def export_to_pdf(
    db: Session,
    presentation_id: int,
    output_path: Optional[str] = None
) -> bytes:
    """
    Export a presentation to PDF format.

    This creates a simple PDF from the slides. For production use,
    consider using a headless browser to render HTML slides to PDF.

    Args:
        db: Database session
        presentation_id: ID of the presentation to export
        output_path: Optional path to save the file

    Returns:
        Bytes of the PDF file
    """
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, white, black

    # Get presentation data
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise ValueError(f"Presentation {presentation_id} not found")

    brand = crud.get_brand(db, presentation.brand_id)
    facility = crud.get_wn_facility(db, presentation.facility_id)
    slides = crud.get_presentation_slides(db, presentation_id)

    # Create PDF
    buffer = io.BytesIO()
    page_size = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    primary_color = HexColor(brand.primary_color or "#0b7280")
    secondary_color = HexColor(brand.secondary_color or "#065a67")

    for slide_data in slides:
        add_slide_to_pdf(c, slide_data, brand, facility, width, height, primary_color)
        c.showPage()

    c.save()
    buffer.seek(0)
    pdf_bytes = buffer.read()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def add_slide_to_pdf(
    c,
    slide_data: models.PresentationSlideInstance,
    brand: models.Brand,
    facility: models.WNFacility,
    width: float,
    height: float,
    primary_color
):
    """Add a single slide to the PDF"""
    from reportlab.lib.colors import white, black, HexColor

    slide_type = slide_data.slide_type
    payload = slide_data.payload or {}

    if slide_type == "WelcomeIntro":
        # Background
        c.setFillColor(primary_color)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(width/2, height - 200, f"Welcome to {brand.name}")
        # Facility
        c.setFont("Helvetica", 28)
        c.drawCentredString(width/2, height - 280, facility.name)
        # Event
        c.setFont("Helvetica", 22)
        c.drawCentredString(width/2, height - 340, "Culture Night")

    elif slide_type == "RaffleBumper":
        # Gold background
        c.setFillColor(HexColor("#FFD700"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        # Title
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 64)
        c.drawCentredString(width/2, height - 250, payload.get("title", "RAFFLE TIME!"))
        c.setFont("Helvetica", 24)
        c.drawCentredString(width/2, height - 320, payload.get("subtitle", ""))

    elif slide_type == "GameSlide":
        # Header
        c.setFillColor(primary_color)
        c.rect(0, height - 80, width, 80, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 32)
        c.drawString(30, height - 55, payload.get("title", "Game Time!"))
        # Value label
        if payload.get("value_label"):
            c.setFillColor(primary_color)
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(width/2, height - 130, payload.get("value_label"))
        # Rules
        c.setFillColor(black)
        c.setFont("Helvetica", 18)
        rules = payload.get("rules", "")
        y = height - 200
        for line in rules.split('\n')[:8]:
            c.drawString(50, y, line[:80])
            y -= 25

    elif slide_type == "PillarsClosing":
        # Background
        c.setFillColor(primary_color)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 42)
        c.drawCentredString(width/2, height - 80, "Our 3 Pillars")
        # Pillars
        pillars = payload.get("pillars", [
            {"name": "Clinical"}, {"name": "Cultural"}, {"name": "Financial"}
        ])
        x_positions = [width/4 - 50, width/2, 3*width/4 + 50]
        for i, pillar in enumerate(pillars[:3]):
            # Box
            c.setFillColor(white)
            c.roundRect(x_positions[i] - 100, 150, 200, 280, 10, fill=1, stroke=0)
            # Name
            c.setFillColor(primary_color)
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(x_positions[i], 360, pillar.get("name", ""))
            # Description
            c.setFillColor(black)
            c.setFont("Helvetica", 14)
            desc = pillar.get("description", "")
            c.drawCentredString(x_positions[i], 310, desc[:30])

    else:
        # Generic slide
        # Header
        c.setFillColor(primary_color)
        c.rect(0, height - 80, width, 80, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 32)
        title = payload.get("title", slide_type.replace("Block", ""))
        c.drawString(30, height - 55, title)


def get_export_filename(presentation: models.Presentation, extension: str) -> str:
    """Generate a filename for export"""
    safe_title = "".join(c for c in presentation.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title.replace(' ', '_')[:50]
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return f"{safe_title}_{timestamp}.{extension}"
