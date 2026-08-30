from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.database.session import session_scope
from app.domain.doctor import Doctor, STATUS_ACTIVE, STATUS_INACTIVE, validate_doctor_name, validate_mobile
from app.repositories.doctor_repository import DoctorRepository


class DoctorService:
    def __init__(self, session_factory: sessionmaker, repo: Optional[DoctorRepository] = None):
        self.session_factory = session_factory
        self.repo = repo or DoctorRepository()

    def create_doctor(self, name: str, mobile: Optional[str] = None) -> Doctor:
        clean_name = validate_doctor_name(name)
        clean_mobile = validate_mobile(mobile)
        with session_scope(self.session_factory) as session:
            return self.repo.add(session, clean_name, clean_mobile)

    def update_doctor(self, doctor_id: int, name: str, mobile: Optional[str] = None) -> Doctor:
        clean_name = validate_doctor_name(name)
        clean_mobile = validate_mobile(mobile)
        with session_scope(self.session_factory) as session:
            return self.repo.update(session, doctor_id, clean_name, clean_mobile)

    def activate(self, doctor_id: int) -> Doctor:
        with session_scope(self.session_factory) as session:
            return self.repo.set_status(session, doctor_id, STATUS_ACTIVE)

    def deactivate(self, doctor_id: int) -> Doctor:
        # Deactivating (not deleting) is the only supported way to retire
        # a doctor - historical transactions keep referencing this row
        # and keep displaying correctly (see repositories/doctor_repository
        # and domain/doctor for why we never physically delete).
        with session_scope(self.session_factory) as session:
            return self.repo.set_status(session, doctor_id, STATUS_INACTIVE)

    def get(self, doctor_id: int) -> Doctor:
        with session_scope(self.session_factory) as session:
            return self.repo.get(session, doctor_id)

    def list_active(self) -> list[Doctor]:
        with session_scope(self.session_factory) as session:
            return self.repo.list(session, active_only=True)

    def list_all(self, search: Optional[str] = None) -> list[Doctor]:
        with session_scope(self.session_factory) as session:
            return self.repo.list(session, active_only=False, search=search)

    def has_transactions(self, doctor_id: int) -> bool:
        with session_scope(self.session_factory) as session:
            return self.repo.has_transactions(session, doctor_id)
