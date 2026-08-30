"""Basic Data Capture service.

This is the single authoritative place a Patient/Investigation
transaction is created or edited. DC Generation and the Customer
Investigation Report both read the same stored transaction through
TransactionRepository - there is no separate/duplicate storage for
those two downstream documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.database.session import session_scope
from app.domain.investigation_type import validate_amount
from app.domain.patient_investigation import (
    PatientInvestigation,
    compute_net_fee,
    validate_age,
    validate_patient_mobile,
    validate_patient_name,
)
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.transaction_repository import TransactionFilter, TransactionRepository
from app.services.exceptions import ValidationError


@dataclass
class TransactionInput:
    transaction_date: date
    patient_name: str
    address: Optional[str]
    mobile: Optional[str]
    age: Optional[int]
    father_husband_name: Optional[str]
    doctor_id: int
    investigation_type_id: int
    fee: Decimal
    discount: Decimal


class DataCaptureService:
    def __init__(
        self,
        session_factory: sessionmaker,
        txn_repo: Optional[TransactionRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
        investigation_repo: Optional[InvestigationRepository] = None,
    ):
        self.session_factory = session_factory
        self.txn_repo = txn_repo or TransactionRepository()
        self.doctor_repo = doctor_repo or DoctorRepository()
        self.investigation_repo = investigation_repo or InvestigationRepository()

    def _clean(self, data: TransactionInput) -> dict:
        if not data.doctor_id:
            raise ValidationError("Please select a doctor.")
        if not data.investigation_type_id:
            raise ValidationError("Please select an investigation type.")
        fee = validate_amount(data.fee, field_label="Fee")
        discount = validate_amount(data.discount, field_label="Discount")
        net_fee = compute_net_fee(fee, discount)
        return dict(
            transaction_date=data.transaction_date or date.today(),
            patient_name=validate_patient_name(data.patient_name),
            address=(data.address or "").strip() or None,
            mobile=validate_patient_mobile(data.mobile),
            age=validate_age(data.age),
            father_husband_name=(data.father_husband_name or "").strip() or None,
            fee=fee,
            discount=discount,
            net_fee=net_fee,
        )

    def create_transaction(self, data: TransactionInput) -> PatientInvestigation:
        clean = self._clean(data)
        with session_scope(self.session_factory) as session:
            doctor = self.doctor_repo.get(session, data.doctor_id)
            if not doctor.is_active:
                raise ValidationError(
                    f"Doctor '{doctor.name}' is inactive and cannot be used for a new entry."
                )
            investigation = self.investigation_repo.get(session, data.investigation_type_id)
            if not investigation.is_active:
                raise ValidationError(
                    f"Investigation type '{investigation.name}' is inactive and cannot be "
                    "used for a new entry."
                )
            txn = PatientInvestigation(
                id=None,
                doctor_id=doctor.id,
                doctor_name_snapshot=doctor.name,
                investigation_type_id=investigation.id,
                investigation_name_snapshot=investigation.name,
                **clean,
            )
            return self.txn_repo.add(session, txn)

    def update_transaction(self, txn_id: int, data: TransactionInput) -> PatientInvestigation:
        clean = self._clean(data)
        with session_scope(self.session_factory) as session:
            doctor = self.doctor_repo.get(session, data.doctor_id)
            investigation = self.investigation_repo.get(session, data.investigation_type_id)
            # Correcting an existing entry is allowed even if the doctor
            # or investigation type has since been deactivated, so staff
            # can fix a typo in an old record without having to
            # reactivate retired master data.
            return self.txn_repo.update(
                session,
                txn_id,
                doctor_id=doctor.id,
                doctor_name_snapshot=doctor.name,
                investigation_type_id=investigation.id,
                investigation_name_snapshot=investigation.name,
                **clean,
            )

    def get(self, txn_id: int) -> PatientInvestigation:
        with session_scope(self.session_factory) as session:
            return self.txn_repo.get(session, txn_id)

    def search(self, filt: TransactionFilter) -> list[PatientInvestigation]:
        with session_scope(self.session_factory) as session:
            return self.txn_repo.search(session, filt)

    def today_entries(self, today: Optional[date] = None) -> list[PatientInvestigation]:
        with session_scope(self.session_factory) as session:
            return self.txn_repo.today(session, today or date.today())
