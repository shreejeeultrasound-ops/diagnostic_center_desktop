from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Doctor as DoctorORM
from app.domain.doctor import Doctor, STATUS_ACTIVE
from app.services.exceptions import NotFoundError


def _to_domain(row: DoctorORM) -> Doctor:
    return Doctor(
        id=row.id,
        name=row.name,
        mobile=row.mobile,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class DoctorRepository:
    def add(self, session: Session, name: str, mobile: Optional[str]) -> Doctor:
        row = DoctorORM(name=name, mobile=mobile, status=STATUS_ACTIVE)
        session.add(row)
        session.flush()
        return _to_domain(row)

    def get(self, session: Session, doctor_id: int) -> Doctor:
        row = session.get(DoctorORM, doctor_id)
        if row is None:
            raise NotFoundError(f"Doctor #{doctor_id} was not found.")
        return _to_domain(row)

    def update(self, session: Session, doctor_id: int, name: str, mobile: Optional[str]) -> Doctor:
        row = session.get(DoctorORM, doctor_id)
        if row is None:
            raise NotFoundError(f"Doctor #{doctor_id} was not found.")
        row.name = name
        row.mobile = mobile
        session.flush()
        return _to_domain(row)

    def set_status(self, session: Session, doctor_id: int, status: str) -> Doctor:
        row = session.get(DoctorORM, doctor_id)
        if row is None:
            raise NotFoundError(f"Doctor #{doctor_id} was not found.")
        row.status = status
        session.flush()
        return _to_domain(row)

    def list(
        self, session: Session, *, active_only: bool = False, search: Optional[str] = None
    ) -> list[Doctor]:
        stmt = select(DoctorORM)
        if active_only:
            stmt = stmt.where(DoctorORM.status == STATUS_ACTIVE)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(DoctorORM.name.ilike(like))
        stmt = stmt.order_by(DoctorORM.name)
        return [_to_domain(r) for r in session.execute(stmt).scalars().all()]

    def has_transactions(self, session: Session, doctor_id: int) -> bool:
        from app.database.models import PatientInvestigation as TxnORM

        stmt = select(TxnORM.id).where(TxnORM.doctor_id == doctor_id).limit(1)
        return session.execute(stmt).first() is not None
