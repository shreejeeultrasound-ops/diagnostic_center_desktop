"""Patient/Investigation transaction - the core transactional record.

Basic Data Capture, DC Generation and the Customer Investigation Report
all read from this single table; nothing here is ever duplicated into a
separate storage mechanism for DC/report purposes (see services/dc_service
and services/report_service, which both read the same repository).

Financial values (fee, discount, net_fee) are captured on the transaction
itself and never recomputed from the current master data, so that later
changes to an Investigation Type's default fee cannot retroactively alter
a historical transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.domain.doctor import validate_mobile
from app.services.exceptions import ValidationError

MAX_AGE = 130


@dataclass
class PatientInvestigation:
    id: Optional[int]
    transaction_date: date
    patient_name: str
    address: Optional[str]
    mobile: Optional[str]
    age: Optional[int]
    father_husband_name: Optional[str]
    doctor_id: int
    doctor_name_snapshot: str
    investigation_type_id: int
    investigation_name_snapshot: str
    fee: Decimal
    discount: Decimal
    net_fee: Decimal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def validate_patient_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Patient/customer name is mandatory.")
    if len(name) > 150:
        raise ValidationError("Patient name is too long (max 150 characters).")
    return name


def validate_age(age) -> Optional[int]:
    if age in (None, ""):
        return None
    try:
        age_int = int(age)
    except (TypeError, ValueError):
        raise ValidationError("Age must be a whole number.")
    if age_int < 0 or age_int > MAX_AGE:
        raise ValidationError(f"Age must be between 0 and {MAX_AGE}.")
    return age_int


def validate_patient_mobile(mobile: Optional[str]) -> Optional[str]:
    return validate_mobile(mobile, field_label="Mobile")


def compute_net_fee(fee: Decimal, discount: Decimal) -> Decimal:
    """Net Fees = Fees - Discount, with validation that the result of the
    transaction is a sane financial value.

    Discount greater than fee is rejected as invalid unless a documented
    business reason exists; none has been specified for V1, so it is
    treated as a hard validation error rather than allowing negative net
    fees to be silently persisted.
    """
    if fee < 0:
        raise ValidationError("Fee cannot be negative.")
    if discount < 0:
        raise ValidationError("Discount cannot be negative.")
    if discount > fee:
        raise ValidationError("Discount cannot be greater than the fee.")
    return (fee - discount).quantize(Decimal("0.01"))
