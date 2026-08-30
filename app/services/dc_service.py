"""DC Generation service.

"DC" = the doctor-wise statement/list of patient transactions mapped to a
doctor for a date range (as specified in the build brief, section 9).
No commission/payment rules are invented here since none were specified;
this only aggregates the fee/discount/net figures that already exist on
each transaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.database.session import session_scope
from app.domain.patient_investigation import PatientInvestigation
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.transaction_repository import TransactionFilter, TransactionRepository
from app.services.exceptions import ValidationError


@dataclass
class DCData:
    doctor_name: str
    from_date: date
    to_date: date
    rows: list[PatientInvestigation] = field(default_factory=list)

    @property
    def total_patients(self) -> int:
        return len(self.rows)

    @property
    def gross_fees(self) -> Decimal:
        return sum((r.fee for r in self.rows), Decimal("0.00"))

    @property
    def total_discount(self) -> Decimal:
        return sum((r.discount for r in self.rows), Decimal("0.00"))

    @property
    def net_fees(self) -> Decimal:
        return sum((r.net_fee for r in self.rows), Decimal("0.00"))


class DCService:
    def __init__(
        self,
        session_factory: sessionmaker,
        txn_repo: Optional[TransactionRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
    ):
        self.session_factory = session_factory
        self.txn_repo = txn_repo or TransactionRepository()
        self.doctor_repo = doctor_repo or DoctorRepository()

    def generate(self, doctor_id: int, from_date: date, to_date: date) -> DCData:
        if from_date > to_date:
            raise ValidationError("'From date' cannot be after 'To date'.")
        with session_scope(self.session_factory) as session:
            doctor = self.doctor_repo.get(session, doctor_id)
            rows = self.txn_repo.search(
                session,
                TransactionFilter(doctor_id=doctor_id, from_date=from_date, to_date=to_date),
            )
            # Oldest-first reads naturally as a statement/ledger.
            rows = sorted(rows, key=lambda r: (r.transaction_date, r.id))
            return DCData(
                doctor_name=doctor.name, from_date=from_date, to_date=to_date, rows=rows
            )
