"""Customer Investigation Report PDF.

IMPORTANT: this is explicitly NOT a clinical diagnostic report (build
brief section 10). It must never contain clinical findings, observations,
measurements, diagnosis, impression, or radiology interpretation - only
patient/customer and investigation metadata, professionally formatted.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reporting.currency import format_date
from app.reporting.pdf_common import (
    FONT_BOLD,
    FONT_REGULAR,
    MARGIN,
    PAGE_SIZE,
    STYLE_DOC_TITLE,
    STYLE_FOOTER,
    build_header_table,
    build_with_logo_fallback,
    hr,
)
from app.services.exceptions import ReportGenerationError
from app.services.report_service import CustomerReportData

_styles = getSampleStyleSheet()
_STYLE_FIELD_LABEL = ParagraphStyle(
    "FieldLabel", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=15,
    textColor=colors.HexColor("#444444"),
)
_STYLE_FIELD_VALUE = ParagraphStyle(
    "FieldValue", parent=_styles["Normal"], fontSize=10, leading=15, fontName=FONT_BOLD
)
_STYLE_SECTION_HEADING = ParagraphStyle(
    "SectionHeading",
    parent=_styles["Normal"],
    fontSize=10.5,
    leading=14,
    fontName=FONT_BOLD,
    textColor=colors.white,
)


def _info_table(rows: list[tuple[str, str]], usable_width: float) -> Table:
    data = [
        [Paragraph(f"{label} :", _STYLE_FIELD_LABEL), Paragraph(value or "-", _STYLE_FIELD_VALUE)]
        for label, value in rows
    ]
    table = Table(data, colWidths=[42 * mm, usable_width - 42 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _section_bar(text: str, usable_width: float) -> Table:
    t = Table([[Paragraph(text, _STYLE_SECTION_HEADING)]], colWidths=[usable_width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#2f4f6f")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def generate_customer_report_pdf(data: CustomerReportData, output_path: Path) -> Path:
    txn = data.transaction
    usable_width = PAGE_SIZE[0] - 2 * MARGIN

    def make_doc_and_story(company):
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title=f"Customer Investigation Report - {txn.patient_name}",
        )

        story = [
            build_header_table(company, usable_width),
            Spacer(1, 6),
            hr(usable_width),
            Paragraph("CUSTOMER INVESTIGATION REPORT", STYLE_DOC_TITLE),
            Spacer(1, 4),
            _section_bar("PATIENT / CUSTOMER INFORMATION", usable_width),
            Spacer(1, 4),
            _info_table(
                [
                    ("Patient Name", txn.patient_name),
                    ("Age", str(txn.age) if txn.age is not None else "-"),
                    ("Father / Husband's Name", txn.father_husband_name or "-"),
                    ("Address", (txn.address or "-").replace("\n", "<br/>")),
                    ("Mobile", txn.mobile or "-"),
                ],
                usable_width,
            ),
            Spacer(1, 10),
            _section_bar("INVESTIGATION INFORMATION", usable_width),
            Spacer(1, 4),
            _info_table(
                [
                    ("Doctor", txn.doctor_name_snapshot),
                    ("Investigation", txn.investigation_name_snapshot),
                    ("Report / Visit Date", format_date(txn.transaction_date)),
                ],
                usable_width,
            ),
            Spacer(1, 40),
            hr(usable_width, thickness=0.6, color=colors.HexColor("#999999")),
            Spacer(1, 4),
        ]

        signature_table = Table(
            [["", "_______________________"], ["", "Authorized Signatory"]],
            colWidths=[usable_width - 60 * mm, 60 * mm],
        )
        signature_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(signature_table)

        story.append(Spacer(1, 16))
        story.append(Paragraph(company.report_footer or "", STYLE_FOOTER))
        return doc, story

    try:
        build_with_logo_fallback(make_doc_and_story, data.company, output_path)
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise ReportGenerationError(
            f"Could not generate the Customer Investigation Report PDF: {exc}"
        ) from exc
