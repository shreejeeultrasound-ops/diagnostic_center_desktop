"""Shared ReportLab building blocks for both the DC and the Customer
Investigation Report, so branding/layout stays consistent and logic is
not duplicated between the two documents (build brief section 20).
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, Table, TableStyle

from app.configuration.resources import resource_path
from app.configuration.settings import CompanySettings

PAGE_SIZE = A4
MARGIN = 16 * mm
MAX_LOGO_WIDTH = 30 * mm
MAX_LOGO_HEIGHT = 18 * mm

# ReportLab's built-in Helvetica/Times fonts do not include the Indian
# Rupee glyph (U+20B9). We bundle DejaVu Sans (Bitstream Vera / public
# domain license, redistributable) inside app/assets/fonts so every PDF
# renders the currency symbol correctly on any machine, regardless of
# what fonts happen to be installed on it.
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
try:
    _regular_path = resource_path("fonts", "DejaVuSans.ttf")
    _bold_path = resource_path("fonts", "DejaVuSans-Bold.ttf")
    if _regular_path.exists() and _bold_path.exists():
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(_regular_path)))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(_bold_path)))
        pdfmetrics.registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
            italic="DejaVuSans",
            boldItalic="DejaVuSans-Bold",
        )
        FONT_REGULAR = "DejaVuSans"
        FONT_BOLD = "DejaVuSans-Bold"
except Exception:
    # Falls back to core Helvetica (Rupee amounts will show "Rs." instead
    # of the symbol via format_inr's ASCII-safe behaviour) rather than
    # ever failing report generation because of a font problem.
    pass

_styles = getSampleStyleSheet()

STYLE_COMPANY_NAME = ParagraphStyle(
    "CompanyName", parent=_styles["Title"], fontName=FONT_BOLD, fontSize=16, leading=19, spaceAfter=2,
)
STYLE_COMPANY_DETAIL = ParagraphStyle(
    "CompanyDetail", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12,
    textColor=colors.HexColor("#333333"),
)
STYLE_DOC_TITLE = ParagraphStyle(
    "DocTitle", parent=_styles["Heading2"], fontName=FONT_BOLD, fontSize=13, alignment=1,
    spaceBefore=6, spaceAfter=6,
)
STYLE_LABEL = ParagraphStyle("Label", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14)
STYLE_VALUE = ParagraphStyle("Value", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14)
STYLE_FOOTER = ParagraphStyle(
    "Footer", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=8,
    textColor=colors.HexColor("#666666"), alignment=1,
)


def _scaled_logo(logo_path: str):
    path = Path(logo_path) if logo_path else None
    if not path or not path.exists():
        return None
    try:
        # reportlab's Image flowable does NOT fully decode pixel data at
        # construction time - it defers that until the document is
        # actually drawn, deep inside doc.build(), by which point there
        # is no try/except left to catch a corrupt file gracefully. Force
        # a full decode with PIL right now instead, so corruption is
        # caught here and degrades to a text-only header, rather than
        # crashing the whole report/DC partway through generation.
        from PIL import Image as PILImage

        with PILImage.open(path) as pil_img:
            pil_img.load()
        img = Image(str(path))
    except Exception:
        # A corrupt/invalid logo must never prevent report generation -
        # fall back to a text-only header instead.
        return None
    ratio = min(MAX_LOGO_WIDTH / img.imageWidth, MAX_LOGO_HEIGHT / img.imageHeight)
    img.drawWidth = img.imageWidth * ratio
    img.drawHeight = img.imageHeight * ratio
    return img


def build_header_table(company: CompanySettings, usable_width: float) -> Table:
    """Logo (if any) on the left, company name/address/contact stacked
    on the right - degrades gracefully to a text-only header when no
    logo has been configured yet.
    """
    contact_bits = [b for b in (company.phone, company.email, company.website) if b]
    detail_lines = [company.address] if company.address else []
    if contact_bits:
        detail_lines.append(" | ".join(contact_bits))

    name_and_detail = [Paragraph(company.company_name or "Diagnostic Center", STYLE_COMPANY_NAME)]
    for line in detail_lines:
        name_and_detail.append(Paragraph(line.replace("\n", "<br/>"), STYLE_COMPANY_DETAIL))

    logo = _scaled_logo(company.logo_path)
    if logo is not None:
        data = [[logo, name_and_detail]]
        col_widths = [MAX_LOGO_WIDTH + 4 * mm, usable_width - MAX_LOGO_WIDTH - 4 * mm]
    else:
        data = [[name_and_detail]]
        col_widths = [usable_width]

    table = Table(data, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def hr(width: float, thickness: float = 1.1, color=colors.HexColor("#222222")):
    from reportlab.platypus import Table as _T

    t = _T([[""]], colWidths=[width], rowHeights=[thickness])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    return t


def build_with_logo_fallback(make_doc_and_story, company: CompanySettings, output_path) -> None:
    """Builds the PDF, and if that fails while a logo is configured,
    retries once with a text-only header before giving up.

    _scaled_logo() above already eagerly decodes the logo so most
    corruption is caught before the document is ever built - this is
    the second, belt-and-suspenders layer: even an unanticipated
    failure during the actual drawing pass (not just image decoding)
    must not be able to block staff from producing a report or DC for
    a patient. `make_doc_and_story(company)` must build fresh
    SimpleDocTemplate/story objects each call (a doc that already
    failed to build cannot be safely reused for a retry).
    """
    from dataclasses import replace

    doc, story = make_doc_and_story(company)
    try:
        doc.build(story)
        return
    except Exception as exc:
        if not company.logo_path:
            raise
        fallback_company = replace(company, logo_path="")
        doc, story = make_doc_and_story(fallback_company)
        try:
            doc.build(story)
        except Exception:
            raise exc from exc
