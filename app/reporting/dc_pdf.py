from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.configuration.settings import CompanySettings
from app.reporting.currency import format_date, format_inr
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
from app.services.dc_service import DCData
from app.services.exceptions import ReportGenerationError

_styles = getSampleStyleSheet()
_STYLE_META = ParagraphStyle("Meta", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14)
_STYLE_TOTAL_LABEL = ParagraphStyle(
    "TotalLabel", parent=_styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14, alignment=2
)
_STYLE_TOTAL_VALUE = ParagraphStyle(
    "TotalValue", parent=_styles["Normal"], fontSize=11, leading=14, alignment=2, fontName=FONT_BOLD
)


def generate_dc_pdf(dc: DCData, company: CompanySettings, output_path: Path) -> Path:
    usable_width = PAGE_SIZE[0] - 2 * MARGIN

    def make_doc_and_story(company: CompanySettings):
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title=f"DC - {dc.doctor_name}",
        )

        story = [
            build_header_table(company, usable_width),
            Spacer(1, 6),
            hr(usable_width),
            Spacer(1, 6),
            Paragraph("DOCTOR-WISE STATEMENT (DC)", STYLE_DOC_TITLE),
            Paragraph(f"<b>Doctor:</b> {dc.doctor_name}", _STYLE_META),
            Paragraph(
                f"<b>Period:</b> {format_date(dc.from_date)} to {format_date(dc.to_date)}",
                _STYLE_META,
            ),
            Spacer(1, 8),
        ]

        header_row = ["Date", "Patient", "Investigation", "Fee", "Discount", "Net Fee"]
        table_data = [header_row]
        for row in dc.rows:
            table_data.append(
                [
                    format_date(row.transaction_date),
                    Paragraph(row.patient_name, _STYLE_META),
                    Paragraph(row.investigation_name_snapshot, _STYLE_META),
                    format_inr(row.fee),
                    format_inr(row.discount),
                    format_inr(row.net_fee),
                ]
            )

        if dc.rows:
            col_widths = [22 * mm, 46 * mm, 40 * mm, 24 * mm, 24 * mm, 24 * mm]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("No transactions found for this doctor and period.", _STYLE_META))

        story.append(Spacer(1, 10))
        story.append(hr(usable_width))
        story.append(Spacer(1, 6))

        totals_table = Table(
            [
                ["Total Patients:", str(dc.total_patients)],
                ["Gross Fees:", format_inr(dc.gross_fees)],
                ["Discount:", format_inr(dc.total_discount)],
                ["Net Fees:", format_inr(dc.net_fees)],
            ],
            colWidths=[usable_width - 40 * mm, 40 * mm],
        )
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                    ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(totals_table)

        story.append(Spacer(1, 20))
        story.append(Paragraph(company.report_footer or "", STYLE_FOOTER))
        return doc, story

    try:
        build_with_logo_fallback(make_doc_and_story, company, output_path)
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise ReportGenerationError(f"Could not generate the DC PDF: {exc}") from exc
