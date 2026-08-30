from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.database.session import session_scope
from app.domain.investigation_type import (
    InvestigationType,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    validate_amount,
    validate_investigation_name,
)
from app.repositories.investigation_repository import InvestigationRepository


class InvestigationService:
    def __init__(self, session_factory: sessionmaker, repo: Optional[InvestigationRepository] = None):
        self.session_factory = session_factory
        self.repo = repo or InvestigationRepository()

    def create_investigation(self, name: str, default_fee) -> InvestigationType:
        clean_name = validate_investigation_name(name)
        clean_fee = validate_amount(default_fee, field_label="Default fee")
        with session_scope(self.session_factory) as session:
            return self.repo.add(session, clean_name, clean_fee)

    def update_investigation(self, investigation_id: int, name: str, default_fee) -> InvestigationType:
        clean_name = validate_investigation_name(name)
        clean_fee = validate_amount(default_fee, field_label="Default fee")
        with session_scope(self.session_factory) as session:
            return self.repo.update(session, investigation_id, clean_name, clean_fee)

    def activate(self, investigation_id: int) -> InvestigationType:
        with session_scope(self.session_factory) as session:
            return self.repo.set_status(session, investigation_id, STATUS_ACTIVE)

    def deactivate(self, investigation_id: int) -> InvestigationType:
        with session_scope(self.session_factory) as session:
            return self.repo.set_status(session, investigation_id, STATUS_INACTIVE)

    def get(self, investigation_id: int) -> InvestigationType:
        with session_scope(self.session_factory) as session:
            return self.repo.get(session, investigation_id)

    def list_active(self) -> list[InvestigationType]:
        with session_scope(self.session_factory) as session:
            return self.repo.list(session, active_only=True)

    def list_all(self, search: Optional[str] = None) -> list[InvestigationType]:
        with session_scope(self.session_factory) as session:
            return self.repo.list(session, active_only=False, search=search)

    def has_transactions(self, investigation_id: int) -> bool:
        with session_scope(self.session_factory) as session:
            return self.repo.has_transactions(session, investigation_id)
