from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import PatientInvestigation as TxnORM
from app.domain.patient_investigation import PatientInvestigation
from app.services.exceptions import NotFoundError


def _to_domain(row: TxnORM) -> PatientInvestigation:
    return PatientInvestigation(
        id=row.id,
        transaction_date=row.transaction_date.date(),
        patient_name=row.patient_name,
        address=row.address,
        mobile=row.mobile,
        age=row.age,
        father_husband_name=row.father_husband_name,
        doctor_id=row.doctor_id,
        doctor_name_snapshot=row.doctor_name_snapshot,
        investigation_type_id=row.investigation_type_id,
        investigation_name_snapshot=row.investigation_name_snapshot,
        fee=Decimal(str(row.fee)),
        discount=Decimal(str(row.discount)),
        net_fee=Decimal(str(row.net_fee)),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@dataclass
class TransactionFilter:
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    doctor_id: Optional[int] = None
    investigation_type_id: Optional[int] = None
    patient_name: Optional[str] = None
    mobile: Optional[str] = None


class TransactionRepository:
    def add(self, session: Session, txn: PatientInvestigation) -> PatientInvestigation:
        row = TxnORM(
            transaction_date=datetime.combine(txn.transaction_date, time.min),
            patient_name=txn.patient_name,
            address=txn.address,
            mobile=txn.mobile,
            age=txn.age,
            father_husband_name=txn.father_husband_name,
            doctor_id=txn.doctor_id,
            doctor_name_snapshot=txn.doctor_name_snapshot,
            investigation_type_id=txn.investigation_type_id,
            investigation_name_snapshot=txn.investigation_name_snapshot,
            fee=txn.fee,
            discount=txn.discount,
            net_fee=txn.net_fee,
        )
        session.add(row)
        session.flush()
        return _to_domain(row)

    def get(self, session: Session, txn_id: int) -> PatientInvestigation:
        row = session.get(TxnORM, txn_id)
        if row is None:
            raise NotFoundError(f"Transaction #{txn_id} was not found.")
        return _to_domain(row)

    def update(self, session: Session, txn_id: int, **fields) -> PatientInvestigation:
        row = session.get(TxnORM, txn_id)
        if row is None:
            raise NotFoundError(f"Transaction #{txn_id} was not found.")
        for key, value in fields.items():
            if key == "transaction_date" and isinstance(value, date):
                value = datetime.combine(value, time.min)
            setattr(row, key, value)
        session.flush()
        return _to_domain(row)

    def search(self, session: Session, filt: TransactionFilter) -> list[PatientInvestigation]:
        stmt = select(TxnORM)
        if filt.from_date:
            stmt = stmt.where(TxnORM.transaction_date >= datetime.combine(filt.from_date, time.min))
        if filt.to_date:
            stmt = stmt.where(TxnORM.transaction_date <= datetime.combine(filt.to_date, time.max))
        if filt.doctor_id:
            stmt = stmt.where(TxnORM.doctor_id == filt.doctor_id)
        if filt.investigation_type_id:
            stmt = stmt.where(TxnORM.investigation_type_id == filt.investigation_type_id)
        if filt.patient_name:
            stmt = stmt.where(TxnORM.patient_name.ilike(f"%{filt.patient_name.strip()}%"))
        if filt.mobile:
            stmt = stmt.where(TxnORM.mobile.ilike(f"%{filt.mobile.strip()}%"))
        stmt = stmt.order_by(TxnORM.transaction_date.desc(), TxnORM.id.desc())
        return [_to_domain(r) for r in session.execute(stmt).scalars().all()]

    def today(self, session: Session, today: date) -> list[PatientInvestigation]:
        return self.search(session, TransactionFilter(from_date=today, to_date=today))
