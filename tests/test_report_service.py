from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.configuration.settings import CompanySettings
from app.reporting.customer_report_pdf import generate_customer_report_pdf
from app.reporting.dc_pdf import generate_dc_pdf
from app.services.data_capture_service import TransactionInput

FORBIDDEN_CLINICAL_TERMS = [
    "impression",
    "diagnosis",
    "findings",
    "observation",
    "clinical",
]


def _make_transaction(ctx):
    doctor = ctx.doctor_service.create_doctor("Dr. ABC", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    return ctx.data_capture_service.create_transaction(
        TransactionInput(
            transaction_date=date(2026, 8, 2),
            patient_name="Rahul Kumar",
            address="123 Main Street",
            mobile="9876543210",
            age=42,
            father_husband_name="Suresh Kumar",
            doctor_id=doctor.id,
            investigation_type_id=investigation.id,
            fee=Decimal("1000"),
            discount=Decimal("100"),
        )
    )


def test_report_data_contains_expected_fields(ctx):
    txn = _make_transaction(ctx)
    ctx.settings_service.save(company_name="Example Diagnostic Center", address="Main Road")

    data = ctx.report_service.get_report_data(txn.id)
    assert data.transaction.patient_name == "Rahul Kumar"
    assert data.transaction.doctor_name_snapshot == "Dr. ABC"
    assert data.transaction.investigation_name_snapshot == "USG Abdomen"
    assert data.company.company_name == "Example Diagnostic Center"


def test_customer_report_pdf_is_generated(ctx, tmp_path):
    txn = _make_transaction(ctx)
    ctx.settings_service.save(company_name="Example Diagnostic Center", address="Main Road")
    data = ctx.report_service.get_report_data(txn.id)

    output = tmp_path / "report.pdf"
    generate_customer_report_pdf(data, output)
    assert output.exists()
    assert output.stat().st_size > 500  # a real PDF was written, not an empty file


def test_customer_report_pdf_has_no_clinical_terms(ctx, tmp_path):
    """Directly encodes build brief section 10/31: the report must never
    contain clinical findings/diagnosis/impression content.
    """
    from pypdf import PdfReader  # local import: only needed for this assertion

    txn = _make_transaction(ctx)
    ctx.settings_service.save(company_name="Example Diagnostic Center", address="Main Road")
    data = ctx.report_service.get_report_data(txn.id)

    output = tmp_path / "report.pdf"
    generate_customer_report_pdf(data, output)

    reader = PdfReader(str(output))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()
    for term in FORBIDDEN_CLINICAL_TERMS:
        assert term not in text, f"Report unexpectedly contains clinical term: {term}"
    assert "rahul kumar" in text
    assert "usg abdomen" in text.replace("\n", " ")


def test_dc_pdf_is_generated(ctx, tmp_path):
    doctor = ctx.doctor_service.create_doctor("Dr. ABC", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    ctx.data_capture_service.create_transaction(
        TransactionInput(
            date(2026, 8, 2), "Rahul Kumar", None, None, 42, None, doctor.id, investigation.id,
            Decimal("1000"), Decimal("100"),
        )
    )
    ctx.settings_service.save(company_name="Example Diagnostic Center")
    dc = ctx.dc_service.generate(doctor.id, date(2026, 8, 1), date(2026, 8, 31))

    output = tmp_path / "dc.pdf"
    generate_dc_pdf(dc, ctx.settings_service.get(), output)
    assert output.exists()
    assert output.stat().st_size > 500
