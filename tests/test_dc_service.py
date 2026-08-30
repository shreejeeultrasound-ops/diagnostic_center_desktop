from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.data_capture_service import TransactionInput
from app.services.exceptions import ValidationError


def _txn(doctor_id, investigation_id, patient_name, txn_date, fee, discount):
    return TransactionInput(
        transaction_date=txn_date,
        patient_name=patient_name,
        address=None,
        mobile=None,
        age=30,
        father_husband_name=None,
        doctor_id=doctor_id,
        investigation_type_id=investigation_id,
        fee=Decimal(fee),
        discount=Decimal(discount),
    )


@pytest.fixture()
def sample_data(ctx):
    doctor_a = ctx.doctor_service.create_doctor("Dr. A", None)
    doctor_b = ctx.doctor_service.create_doctor("Dr. B", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")

    ctx.data_capture_service.create_transaction(
        _txn(doctor_a.id, investigation.id, "Rahul Kumar", date(2026, 8, 2), "1000", "100")
    )
    ctx.data_capture_service.create_transaction(
        _txn(doctor_a.id, investigation.id, "Priya Sharma", date(2026, 8, 4), "800", "0")
    )
    ctx.data_capture_service.create_transaction(
        _txn(doctor_a.id, investigation.id, "Amit Singh", date(2026, 9, 7), "1000", "0")
    )  # outside the August date range used below
    ctx.data_capture_service.create_transaction(
        _txn(doctor_b.id, investigation.id, "Other Patient", date(2026, 8, 5), "1000", "0")
    )
    return doctor_a, doctor_b, investigation


def test_dc_filters_by_doctor_and_date(ctx, sample_data):
    doctor_a, _doctor_b, _investigation = sample_data
    dc = ctx.dc_service.generate(doctor_a.id, date(2026, 8, 1), date(2026, 8, 31))
    assert dc.total_patients == 2
    assert {r.patient_name for r in dc.rows} == {"Rahul Kumar", "Priya Sharma"}


def test_dc_aggregation(ctx, sample_data):
    doctor_a, _doctor_b, _investigation = sample_data
    dc = ctx.dc_service.generate(doctor_a.id, date(2026, 8, 1), date(2026, 8, 31))
    assert dc.gross_fees == Decimal("1800.00")
    assert dc.total_discount == Decimal("100.00")
    assert dc.net_fees == Decimal("1700.00")


def test_dc_does_not_mix_doctors(ctx, sample_data):
    _doctor_a, doctor_b, _investigation = sample_data
    dc = ctx.dc_service.generate(doctor_b.id, date(2026, 8, 1), date(2026, 8, 31))
    assert dc.total_patients == 1
    assert dc.rows[0].patient_name == "Other Patient"


def test_dc_zero_results(ctx, sample_data):
    doctor_a, _doctor_b, _investigation = sample_data
    dc = ctx.dc_service.generate(doctor_a.id, date(2020, 1, 1), date(2020, 1, 31))
    assert dc.total_patients == 0
    assert dc.gross_fees == Decimal("0.00")
    assert dc.net_fees == Decimal("0.00")


def test_dc_rejects_inverted_date_range(ctx, sample_data):
    doctor_a, _doctor_b, _investigation = sample_data
    with pytest.raises(ValidationError):
        ctx.dc_service.generate(doctor_a.id, date(2026, 8, 31), date(2026, 8, 1))
