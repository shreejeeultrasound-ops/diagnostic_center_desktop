"""Authentication service.

Passwords are hashed with bcrypt (via the `bcrypt` package directly -
no extra abstraction needed for a single hashing scheme) and never
stored or logged in plain text. There is no "forgot password" email
flow in V1 (no outbound email/SMTP was part of the original scope) -
a logged-in user can reset another account's password from Settings,
which is sufficient for a small office of a handful of staff.
"""
from __future__ import annotations

from typing import Optional

import bcrypt
from sqlalchemy.orm import sessionmaker

from app.database.session import session_scope
from app.domain.user import User, validate_password, validate_username
from app.repositories.user_repository import UserRepository
from app.services.exceptions import ValidationError


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # A corrupt/foreign-format hash must fail closed, not raise.
        return False


class AuthService:
    def __init__(self, session_factory: sessionmaker, repo: Optional[UserRepository] = None):
        self.session_factory = session_factory
        self.repo = repo or UserRepository()

    def has_any_user(self) -> bool:
        with session_scope(self.session_factory) as session:
            return self.repo.count(session) > 0

    def create_user(self, username: str, password: str) -> User:
        clean_username = validate_username(username)
        clean_password = validate_password(password)
        with session_scope(self.session_factory) as session:
            existing = self.repo.get_by_username(session, clean_username)
            if existing is not None:
                raise ValidationError(f"Username '{clean_username}' is already taken.")
            return self.repo.add(session, clean_username, _hash_password(clean_password))

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Returns the User on success, or None on any failure (unknown
        username, wrong password, or a deactivated account) - the
        caller shows the same generic "invalid username or password"
        message either way, so a login attempt can never be used to
        probe which usernames exist.
        """
        if not username or not password:
            return None
        with session_scope(self.session_factory) as session:
            user = self.repo.get_by_username(session, username)
            if user is None or not user.is_active:
                return None
            if not _verify_password(password, user.password_hash):
                return None
            return user

    def change_password(self, user_id: int, new_password: str) -> User:
        clean_password = validate_password(new_password)
        with session_scope(self.session_factory) as session:
            return self.repo.set_password(session, user_id, _hash_password(clean_password))

    def set_active(self, user_id: int, is_active: bool) -> User:
        with session_scope(self.session_factory) as session:
            return self.repo.set_active(session, user_id, is_active)

    def get(self, user_id: int) -> User:
        with session_scope(self.session_factory) as session:
            return self.repo.get(session, user_id)

    def list_all(self) -> list[User]:
        with session_scope(self.session_factory) as session:
            return self.repo.list_all(session)
