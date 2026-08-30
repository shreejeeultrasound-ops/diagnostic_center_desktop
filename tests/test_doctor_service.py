from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.data_capture_service import TransactionInput
from app.services.exceptions import NotFoundError, ValidationError


def test_create_doctor(ctx):
    doctor = ctx.doctor_service.create_doctor("Dr. ABC", "9999999999")
    assert doctor.id is not None
    assert doctor.name == "Dr. ABC"
    assert doctor.is_active


def test_create_doctor_requires_name(ctx):
    with pytest.raises(ValidationError):
        ctx.doctor_service.create_doctor("   ", None)


def test_create_doctor_rejects_bad_mobile(ctx):
    with pytest.raises(ValidationError):
        ctx.doctor_service.create_doctor("Dr. X", "abc")


def test_doctor_activate_deactivate(ctx):
    doctor = ctx.doctor_service.create_doctor("Dr. Toggle", None)
    inactive = ctx.doctor_service.deactivate(doctor.id)
    assert not inactive.is_active
    active_list = ctx.doctor_service.list_active()
    assert doctor.id not in [d.id for d in active_list]

    reactivated = ctx.doctor_service.activate(doctor.id)
    assert reactivated.is_active
    active_list = ctx.doctor_service.list_active()
    assert doctor.id in [d.id for d in active_list]


def test_deactivated_doctor_still_shows_on_historical_transactions(ctx):
    doctor = ctx.doctor_service.create_doctor("Dr. Retire", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")

    txn = ctx.data_capture_service.create_transaction(
        TransactionInput(
            transaction_date=date(2026, 8, 2),
            patient_name="Rahul Kumar",
            address=None,
            mobile=None,
            age=42,
            father_husband_name=None,
            doctor_id=doctor.id,
            investigation_type_id=investigation.id,
            fee=Decimal("1000"),
            discount=Decimal("0"),
        )
    )

    ctx.doctor_service.deactivate(doctor.id)

    fetched = ctx.data_capture_service.get(txn.id)
    assert fetched.doctor_name_snapshot == "Dr. Retire"

    # Cannot be used for a brand NEW transaction while inactive.
    with pytest.raises(ValidationError):
        ctx.data_capture_service.create_transaction(
            TransactionInput(
                transaction_date=date(2026, 8, 3),
                patient_name="Another Patient",
                address=None,
                mobile=None,
                age=30,
                father_husband_name=None,
                doctor_id=doctor.id,
                investigation_type_id=investigation.id,
                fee=Decimal("1000"),
                discount=Decimal("0"),
            )
        )

    # But an existing transaction for that (now inactive) doctor can
    # still be corrected/edited.
    updated = ctx.data_capture_service.update_transaction(
        txn.id,
        TransactionInput(
            transaction_date=date(2026, 8, 2),
            patient_name="Rahul Kumar",
            address="Corrected Address",
            mobile=None,
            age=42,
            father_husband_name=None,
            doctor_id=doctor.id,
            investigation_type_id=investigation.id,
            fee=Decimal("1000"),
            discount=Decimal("0"),
        ),
    )
    assert updated.address == "Corrected Address"


def test_doctor_not_found(ctx):
    with pytest.raises(NotFoundError):
        ctx.doctor_service.get(9999)
