from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import InvestigationType as InvestigationORM
from app.domain.investigation_type import InvestigationType, STATUS_ACTIVE
from app.services.exceptions import NotFoundError


def _to_domain(row: InvestigationORM) -> InvestigationType:
    return InvestigationType(
        id=row.id,
        name=row.name,
        default_fee=Decimal(str(row.default_fee)),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class InvestigationRepository:
    def add(self, session: Session, name: str, default_fee: Decimal) -> InvestigationType:
        row = InvestigationORM(name=name, default_fee=default_fee, status=STATUS_ACTIVE)
        session.add(row)
        session.flush()
        return _to_domain(row)

    def get(self, session: Session, investigation_id: int) -> InvestigationType:
        row = session.get(InvestigationORM, investigation_id)
        if row is None:
            raise NotFoundError(f"Investigation type #{investigation_id} was not found.")
        return _to_domain(row)

    def update(
        self, session: Session, investigation_id: int, name: str, default_fee: Decimal
    ) -> InvestigationType:
        row = session.get(InvestigationORM, investigation_id)
        if row is None:
            raise NotFoundError(f"Investigation type #{investigation_id} was not found.")
        row.name = name
        row.default_fee = default_fee
        session.flush()
        return _to_domain(row)

    def set_status(self, session: Session, investigation_id: int, status: str) -> InvestigationType:
        row = session.get(InvestigationORM, investigation_id)
        if row is None:
            raise NotFoundError(f"Investigation type #{investigation_id} was not found.")
        row.status = status
        session.flush()
        return _to_domain(row)

    def list(
        self, session: Session, *, active_only: bool = False, search: Optional[str] = None
    ) -> list[InvestigationType]:
        stmt = select(InvestigationORM)
        if active_only:
            stmt = stmt.where(InvestigationORM.status == STATUS_ACTIVE)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(InvestigationORM.name.ilike(like))
        stmt = stmt.order_by(InvestigationORM.name)
        return [_to_domain(r) for r in session.execute(stmt).scalars().all()]

    def has_transactions(self, session: Session, investigation_id: int) -> bool:
        from app.database.models import PatientInvestigation as TxnORM

        stmt = select(TxnORM.id).where(TxnORM.investigation_type_id == investigation_id).limit(1)
        return session.execute(stmt).first() is not None
