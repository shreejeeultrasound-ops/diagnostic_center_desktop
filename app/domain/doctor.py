"""Doctor master - domain rules independent of persistence/UI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.exceptions import ValidationError

STATUS_ACTIVE = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"


@dataclass
class Doctor:
    id: Optional[int]
    name: str
    mobile: Optional[str]
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE


def validate_doctor_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Doctor name is mandatory.")
    if len(name) > 150:
        raise ValidationError("Doctor name is too long (max 150 characters).")
    return name


def validate_mobile(mobile: Optional[str], *, field_label: str = "Mobile") -> Optional[str]:
    """Mobile is optional everywhere it appears; if provided it must look
    like a plausible phone number. Kept intentionally permissive (Indian
    mobiles are 10 digits, but landlines/STD codes and country codes are
    also legitimately entered by staff), but rejects obvious junk.
    """
    if mobile is None:
        return None
    mobile = mobile.strip()
    if not mobile:
        return None
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if len(digits) < 6 or len(digits) > 15:
        raise ValidationError(f"{field_label} does not look like a valid phone number.")
    return mobile
