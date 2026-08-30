"""Small reusable Qt building blocks shared by every screen, so error
handling, currency entry, and date entry look/behave consistently across
the whole application.
"""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit, QDoubleSpinBox, QMessageBox, QWidget

from app.services.exceptions import AppError
from app.logging_config import get_logger

logger = get_logger(__name__)


def show_error(parent: QWidget, title: str, error: Exception) -> None:
    """Every unexpected error is logged with full detail and shown to
    the user as a short, friendly message - never a raw stack trace.
    """
    if isinstance(error, AppError):
        message = str(error)
    else:
        message = "Something went wrong. Please try again or contact support."
        logger.exception("Unexpected error in UI: %s", error)
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def confirm(parent: QWidget, title: str, message: str) -> bool:
    result = QMessageBox.question(
        parent, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    return result == QMessageBox.Yes


class CurrencySpinBox(QDoubleSpinBox):
    """A money-entry field: 2 decimals, non-negative, sane upper bound,
    and a rupee prefix so the unit is always obvious to a non-technical
    user.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setDecimals(2)
        self.setMinimum(0.0)
        self.setMaximum(10_000_000.0)
        self.setPrefix("\u20b9 ")
        self.setSingleStep(50.0)

    def decimal_value(self) -> Decimal:
        return Decimal(str(round(self.value(), 2)))


def today_date_edit(parent: QWidget | None = None) -> QDateEdit:
    edit = QDateEdit(parent)
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd-MMM-yyyy")
    edit.setDate(QDate.currentDate())
    return edit


def qdate_to_date(qdate: QDate):
    return qdate.toPython()
