"""SQLAlchemy ORM models. This is the ONLY place table structure lives.

Design notes (documented assumptions):
  * Master records (Doctor, InvestigationType) are never physically
    deleted - only deactivated - because historical transactions
    reference them by foreign key.
  * PatientInvestigation additionally stores a *snapshot* of the doctor
    name and investigation type name at the time of capture. This is a
    deliberate denormalization: the spec requires historical transaction
    data to "remain stable even if master data changes later" (section 1
    and section 18), and a Doctor's name field is editable per section
    5.1. Storing FK-only would let a later name edit silently change how
    old transactions render. The FK is kept too, for filtering/joins and
    to reach current status; the snapshot is what reports/DCs display.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Staff login accounts.

    Not needed by the original single-PC desktop app (whoever is
    physically at that computer already has access), but required once
    the application is reachable over the internet - patient data must
    not be visible to anyone who simply has the URL. Deliberately flat:
    every account has the same access (no role hierarchy), matching the
    "no complex role-based access control" principle from the desktop
    build - this is authentication (who can get in), not authorization
    tiers (what they can do once inside).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (Index("ix_users_username", "username", unique=True),)


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    transactions: Mapped[list["PatientInvestigation"]] = relationship(
        back_populates="doctor"
    )

    __table_args__ = (
        CheckConstraint("status in ('ACTIVE','INACTIVE')", name="ck_doctor_status"),
        Index("ix_doctors_name", "name"),
        Index("ix_doctors_status", "status"),
    )


class InvestigationType(Base):
    __tablename__ = "investigation_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    default_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    transactions: Mapped[list["PatientInvestigation"]] = relationship(
        back_populates="investigation_type"
    )

    __table_args__ = (
        CheckConstraint("status in ('ACTIVE','INACTIVE')", name="ck_investigation_status"),
        CheckConstraint("default_fee >= 0", name="ck_investigation_default_fee_nonneg"),
        Index("ix_investigation_types_name", "name"),
        Index("ix_investigation_types_status", "status"),
    )


class PatientInvestigation(Base):
    __tablename__ = "patient_investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    patient_name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    father_husband_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    doctor_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)

    investigation_type_id: Mapped[int] = mapped_column(
        ForeignKey("investigation_types.id"), nullable=False
    )
    investigation_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)

    fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    doctor: Mapped["Doctor"] = relationship(back_populates="transactions")
    investigation_type: Mapped["InvestigationType"] = relationship(
        back_populates="transactions"
    )

    __table_args__ = (
        CheckConstraint("fee >= 0", name="ck_txn_fee_nonneg"),
        CheckConstraint("discount >= 0", name="ck_txn_discount_nonneg"),
        CheckConstraint("discount <= fee", name="ck_txn_discount_le_fee"),
        CheckConstraint("net_fee >= 0", name="ck_txn_net_fee_nonneg"),
        Index("ix_txn_patient_name", "patient_name"),
        Index("ix_txn_mobile", "mobile"),
        Index("ix_txn_date", "transaction_date"),
        Index("ix_txn_doctor_date", "doctor_id", "transaction_date"),
    )
