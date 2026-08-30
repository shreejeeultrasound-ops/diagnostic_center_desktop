"""Investigation Type master - domain rules independent of persistence/UI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.services.exceptions import ValidationError

STATUS_ACTIVE = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"


@dataclass
class InvestigationType:
    id: Optional[int]
    name: str
    default_fee: Decimal
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE


def validate_investigation_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Investigation type name is mandatory.")
    if len(name) > 150:
        raise ValidationError("Investigation type name is too long (max 150 characters).")
    return name


def validate_amount(value, *, field_label: str, allow_zero: bool = True) -> Decimal:
    """Shared validation for any money amount (fee, discount, default fee)."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"{field_label} must be a valid number.")
    if amount.is_nan() or not amount.is_finite():
        raise ValidationError(f"{field_label} must be a valid number.")
    if amount < 0:
        raise ValidationError(f"{field_label} cannot be negative.")
    if amount == 0 and not allow_zero:
        raise ValidationError(f"{field_label} must be greater than zero.")
    # Guard against fat-finger entry of absurd amounts.
    if amount > Decimal("10000000"):
        raise ValidationError(f"{field_label} is unrealistically large.")
    return amount.quantize(Decimal("0.01"))
