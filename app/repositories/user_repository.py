from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import User as UserORM
from app.domain.user import User
from app.services.exceptions import NotFoundError


def _to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        username=row.username,
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class UserRepository:
    def add(self, session: Session, username: str, password_hash: str) -> User:
        row = UserORM(username=username, password_hash=password_hash, is_active=True)
        session.add(row)
        session.flush()
        return _to_domain(row)

    def get_by_username(self, session: Session, username: str) -> Optional[User]:
        stmt = select(UserORM).where(UserORM.username == username.strip().lower())
        row = session.execute(stmt).scalar_one_or_none()
        return _to_domain(row) if row else None

    def get(self, session: Session, user_id: int) -> User:
        row = session.get(UserORM, user_id)
        if row is None:
            raise NotFoundError(f"User #{user_id} was not found.")
        return _to_domain(row)

    def set_password(self, session: Session, user_id: int, password_hash: str) -> User:
        row = session.get(UserORM, user_id)
        if row is None:
            raise NotFoundError(f"User #{user_id} was not found.")
        row.password_hash = password_hash
        session.flush()
        return _to_domain(row)

    def set_active(self, session: Session, user_id: int, is_active: bool) -> User:
        row = session.get(UserORM, user_id)
        if row is None:
            raise NotFoundError(f"User #{user_id} was not found.")
        row.is_active = is_active
        session.flush()
        return _to_domain(row)

    def list_all(self, session: Session) -> list[User]:
        stmt = select(UserORM).order_by(UserORM.username)
        return [_to_domain(r) for r in session.execute(stmt).scalars().all()]

    def count(self, session: Session) -> int:
        stmt = select(UserORM)
        return len(session.execute(stmt).scalars().all())
