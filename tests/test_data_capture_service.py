from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.data_capture_service import TransactionInput
from app.services.exceptions import ValidationError


def _base_input(doctor_id, investigation_id, **overrides):
    data = dict(
        transaction_date=date(2026, 8, 2),
        patient_name="Rahul Kumar",
        address="123 Street",
        mobile="9876543210",
        age=42,
        father_husband_name="Suresh Kumar",
        doctor_id=doctor_id,
        investigation_type_id=investigation_id,
        fee=Decimal("1000"),
        discount=Decimal("100"),
    )
    data.update(overrides)
    return TransactionInput(**data)


@pytest.fixture()
def doctor_and_investigation(ctx):
    doctor = ctx.doctor_service.create_doctor("Dr. A", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    return doctor, investigation


def test_create_transaction_computes_net_fee(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    txn = ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, fee=Decimal("1000"), discount=Decimal("100"))
    )
    assert txn.net_fee == Decimal("900.00")


def test_discount_greater_than_fee_rejected(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, investigation.id, fee=Decimal("100"), discount=Decimal("200"))
        )


def test_negative_fee_rejected(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, investigation.id, fee=Decimal("-100"), discount=Decimal("0"))
        )


def test_negative_discount_rejected(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, investigation.id, fee=Decimal("100"), discount=Decimal("-10"))
        )


def test_patient_name_mandatory(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, investigation.id, patient_name="   ")
        )


def test_invalid_age_rejected(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, investigation.id, age=999)
        )


def test_doctor_must_be_selected(ctx, doctor_and_investigation):
    _doctor, investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(None, investigation.id)
        )


def test_investigation_must_be_selected(ctx, doctor_and_investigation):
    doctor, _investigation = doctor_and_investigation
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            _base_input(doctor.id, None)
        )


def test_historical_fee_preserved_when_master_default_fee_changes(ctx, doctor_and_investigation):
    """This is the acceptance-test scenario from the build brief (section
    31, step 7): changing an Investigation Type's default fee must never
    retroactively alter an already-captured transaction's fee/discount/net.
    """
    doctor, investigation = doctor_and_investigation
    txn = ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, fee=Decimal("1000"), discount=Decimal("100"))
    )
    assert txn.net_fee == Decimal("900.00")

    ctx.investigation_service.update_investigation(investigation.id, "USG Abdomen", "1200")

    unchanged = ctx.data_capture_service.get(txn.id)
    assert unchanged.fee == Decimal("1000.00")
    assert unchanged.discount == Decimal("100.00")
    assert unchanged.net_fee == Decimal("900.00")


def test_search_by_patient_name_and_mobile(ctx, doctor_and_investigation):
    from app.repositories.transaction_repository import TransactionFilter

    doctor, investigation = doctor_and_investigation
    ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, patient_name="Priya Sharma", mobile="9812345670")
    )
    ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, patient_name="Rahul Kumar", mobile="9876543210")
    )

    by_name = ctx.data_capture_service.search(TransactionFilter(patient_name="priya"))
    assert len(by_name) == 1
    assert by_name[0].patient_name == "Priya Sharma"

    by_mobile = ctx.data_capture_service.search(TransactionFilter(mobile="9876543210"))
    assert len(by_mobile) == 1
    assert by_mobile[0].patient_name == "Rahul Kumar"


def test_today_entries(ctx, doctor_and_investigation):
    doctor, investigation = doctor_and_investigation
    ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, transaction_date=date.today())
    )
    ctx.data_capture_service.create_transaction(
        _base_input(doctor.id, investigation.id, transaction_date=date(2020, 1, 1))
    )
    today_rows = ctx.data_capture_service.today_entries()
    assert len(today_rows) == 1
