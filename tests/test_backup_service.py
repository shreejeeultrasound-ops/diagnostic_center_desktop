from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.data_capture_service import TransactionInput
from app.services.exceptions import BackupError, RestoreError


def _add_sample_doctor(ctx, name="Dr. Backup"):
    return ctx.doctor_service.create_doctor(name, None)


def test_backup_creates_valid_file(ctx, tmp_path):
    _add_sample_doctor(ctx)
    dest = tmp_path / "manual_backup.db"
    result_path = ctx.backup_service.backup(dest)
    assert result_path.exists()
    assert result_path.stat().st_size > 0


def test_backup_with_no_database_data_still_works_after_init(ctx, tmp_path):
    # AppContext already initializes an (empty) database on construction,
    # so a backup immediately after startup must succeed.
    dest = tmp_path / "empty_backup.db"
    result_path = ctx.backup_service.backup(dest)
    assert result_path.exists()


def test_restore_brings_back_data(ctx, tmp_path):
    doctor = _add_sample_doctor(ctx, "Dr. Original")
    backup_path = ctx.backup_service.backup(tmp_path / "backup.db")

    # Simulate data loss / a mistaken change after the backup was taken.
    ctx.doctor_service.create_doctor("Dr. AddedLater", None)
    assert len(ctx.doctor_service.list_all()) == 2

    ctx.backup_service.restore(backup_path)

    doctors_after_restore = ctx.doctor_service.list_all()
    assert len(doctors_after_restore) == 1
    assert doctors_after_restore[0].name == "Dr. Original"


def test_restore_rejects_missing_file(ctx, tmp_path):
    with pytest.raises(RestoreError):
        ctx.backup_service.restore(tmp_path / "does_not_exist.db")


def test_restore_rejects_corrupt_file(ctx, tmp_path):
    bad_file = tmp_path / "corrupt.db"
    bad_file.write_bytes(b"this is not a sqlite database")
    with pytest.raises(RestoreError):
        ctx.backup_service.restore(bad_file)

    # The original (good) database must be untouched after a rejected
    # restore attempt.
    assert ctx.doctor_service.list_all() == []


def test_backup_preserves_transaction_financial_values(ctx, tmp_path):
    doctor = _add_sample_doctor(ctx)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    ctx.data_capture_service.create_transaction(
        TransactionInput(
            date(2026, 8, 2), "Rahul Kumar", None, None, 42, None, doctor.id, investigation.id,
            Decimal("1000"), Decimal("100"),
        )
    )

    backup_path = ctx.backup_service.backup(tmp_path / "backup.db")
    ctx.backup_service.restore(backup_path)

    txns = ctx.data_capture_service.today_entries(today=date(2026, 8, 2))
    assert len(txns) == 1
    assert txns[0].net_fee == Decimal("900.00")
