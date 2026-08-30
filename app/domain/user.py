"""Staff login accounts - domain rules independent of persistence/UI.

See app/database/models.py::User for why this exists at all (it is new
compared to the desktop build - only needed once the app is reachable
over the internet).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.exceptions import ValidationError

MIN_PASSWORD_LENGTH = 8


@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def validate_username(username: str) -> str:
    username = (username or "").strip().lower()
    if not username:
        raise ValidationError("Username is mandatory.")
    if len(username) < 3 or len(username) > 50:
        raise ValidationError("Username must be between 3 and 50 characters.")
    if not all(ch.isalnum() or ch in "._-" for ch in username):
        raise ValidationError(
            "Username can only contain letters, numbers, dots, hyphens, and underscores."
        )
    return username


def validate_password(password: str) -> str:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return password
