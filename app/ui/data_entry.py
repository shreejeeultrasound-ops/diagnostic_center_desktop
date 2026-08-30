from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.context import AppContext
from app.reporting.currency import format_inr
from app.services.data_capture_service import TransactionInput
from app.services.exceptions import AppError
from app.ui.widgets import CurrencySpinBox, qdate_to_date, show_error, show_info, today_date_edit


class DataEntryScreen(QWidget):
    saved = Signal()

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._editing_id: Optional[int] = None
        self._build_ui()
        self.reset_form()

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        self.heading = QLabel("Patient / Customer Entry")
        self.heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(self.heading)

        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = today_date_edit()
        form.addRow("Date", self.date_edit)

        self.patient_name_edit = QLineEdit()
        self.patient_name_edit.setPlaceholderText("Mandatory")
        form.addRow("Patient Name", self.patient_name_edit)

        self.address_edit = QPlainTextEdit()
        self.address_edit.setFixedHeight(60)
        form.addRow("Address", self.address_edit)

        self.mobile_edit = QLineEdit()
        form.addRow("Mobile", self.mobile_edit)

        self.age_edit = QSpinBox()
        self.age_edit.setRange(0, 130)
        self.age_edit.setSpecialValueText(" ")  # 0 renders blank-ish
        form.addRow("Age", self.age_edit)

        self.father_husband_edit = QLineEdit()
        form.addRow("Father/Husband's Name", self.father_husband_edit)

        self.doctor_combo = _ActiveDropdown()
        form.addRow("Doctor", self.doctor_combo)

        self.investigation_combo = _ActiveDropdown()
        self.investigation_combo.currentIndexChanged.connect(self._on_investigation_changed)
        form.addRow("Investigation Type", self.investigation_combo)

        self.fee_edit = CurrencySpinBox()
        self.fee_edit.valueChanged.connect(self._recalculate_net)
        form.addRow("Fees", self.fee_edit)

        self.discount_edit = CurrencySpinBox()
        self.discount_edit.valueChanged.connect(self._recalculate_net)
        form.addRow("Discount", self.discount_edit)

        self.net_fee_label = QLabel(format_inr(0))
        self.net_fee_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        form.addRow("Net Fees", self.net_fee_label)

        outer.addLayout(form)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("SAVE")
        self.save_button.setMinimumHeight(38)
        self.save_button.clicked.connect(self._on_save)
        self.clear_button = QPushButton("CLEAR")
        self.clear_button.setMinimumHeight(38)
        self.clear_button.clicked.connect(self.reset_form)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.clear_button)
        outer.addLayout(button_row)
        outer.addStretch(1)

    # ---- behaviour ---------------------------------------------------
    def _on_investigation_changed(self) -> None:
        investigation_id = self.investigation_combo.current_id()
        if investigation_id is None:
            return
        investigation = self.ctx.investigation_service.get(investigation_id)
        self.fee_edit.setValue(float(investigation.default_fee))

    def _recalculate_net(self) -> None:
        fee = Decimal(str(self.fee_edit.value()))
        discount = Decimal(str(self.discount_edit.value()))
        net = fee - discount
        if net < 0:
            net = Decimal("0.00")
        self.net_fee_label.setText(format_inr(net))

    def reset_form(self) -> None:
        self._editing_id = None
        self.heading.setText("Patient / Customer Entry")
        self.save_button.setText("SAVE")
        self.date_edit.setDate(self.date_edit.date().currentDate())
        from PySide6.QtCore import QDate

        self.date_edit.setDate(QDate.currentDate())
        self.patient_name_edit.clear()
        self.address_edit.clear()
        self.mobile_edit.clear()
        self.age_edit.setValue(0)
        self.father_husband_edit.clear()
        self.fee_edit.setValue(0)
        self.discount_edit.setValue(0)
        self._reload_dropdowns()
        self._recalculate_net()
        self.patient_name_edit.setFocus()

    def _reload_dropdowns(self) -> None:
        doctors = self.ctx.doctor_service.list_active()
        self.doctor_combo.load([(d.id, d.name) for d in doctors])
        investigations = self.ctx.investigation_service.list_active()
        self.investigation_combo.load([(i.id, i.name) for i in investigations])

    def load_for_edit(self, txn_id: int) -> None:
        txn = self.ctx.data_capture_service.get(txn_id)
        self._editing_id = txn_id
        self.heading.setText(f"Edit Entry #{txn_id}")
        self.save_button.setText("UPDATE")

        from PySide6.QtCore import QDate

        self.date_edit.setDate(QDate(txn.transaction_date.year, txn.transaction_date.month, txn.transaction_date.day))
        self.patient_name_edit.setText(txn.patient_name)
        self.address_edit.setPlainText(txn.address or "")
        self.mobile_edit.setText(txn.mobile or "")
        self.age_edit.setValue(txn.age or 0)
        self.father_husband_edit.setText(txn.father_husband_name or "")

        self._reload_dropdowns()
        # An inactive doctor/investigation on a historical record must
        # still show correctly even though it is not in the active-only
        # dropdown list built above - add it back in for display.
        self.doctor_combo.ensure_present(txn.doctor_id, txn.doctor_name_snapshot)
        self.investigation_combo.ensure_present(
            txn.investigation_type_id, txn.investigation_name_snapshot
        )
        self.doctor_combo.select(txn.doctor_id)
        self.investigation_combo.select(txn.investigation_type_id)

        self.fee_edit.setValue(float(txn.fee))
        self.discount_edit.setValue(float(txn.discount))
        self._recalculate_net()

    def _on_save(self) -> None:
        doctor_id = self.doctor_combo.current_id()
        investigation_id = self.investigation_combo.current_id()
        data = TransactionInput(
            transaction_date=qdate_to_date(self.date_edit.date()),
            patient_name=self.patient_name_edit.text(),
            address=self.address_edit.toPlainText(),
            mobile=self.mobile_edit.text(),
            age=self.age_edit.value() or None,
            father_husband_name=self.father_husband_edit.text(),
            doctor_id=doctor_id,
            investigation_type_id=investigation_id,
            fee=Decimal(str(self.fee_edit.value())),
            discount=Decimal(str(self.discount_edit.value())),
        )
        try:
            if self._editing_id is None:
                self.ctx.data_capture_service.create_transaction(data)
                show_info(self, "Saved", "Entry saved successfully.")
            else:
                self.ctx.data_capture_service.update_transaction(self._editing_id, data)
                show_info(self, "Updated", "Entry updated successfully.")
        except AppError as exc:
            show_error(self, "Could not save entry", exc)
            return
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Could not save entry", exc)
            return

        self.saved.emit()
        self.reset_form()


class _ActiveDropdown(QWidget):
    """A QComboBox-like control that supports re-adding a currently
    referenced but inactive master record for display purposes, without
    letting it be picked for a brand new entry (see build brief section
    5: inactive masters should not normally appear in new-entry
    dropdowns, but historical records must still display correctly).
    """

    currentIndexChanged = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtWidgets import QComboBox

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(lambda _i: self.currentIndexChanged.emit())
        layout.addWidget(self.combo)

    def load(self, items: list[tuple[int, str]]) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        for item_id, name in items:
            self.combo.addItem(name, item_id)
        self.combo.blockSignals(False)
        if items:
            self.combo.setCurrentIndex(0)
            self.currentIndexChanged.emit()

    def ensure_present(self, item_id: int, name: str) -> None:
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == item_id:
                return
        self.combo.addItem(f"{name} (inactive)", item_id)

    def select(self, item_id: int) -> None:
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == item_id:
                self.combo.setCurrentIndex(i)
                return

    def current_id(self) -> Optional[int]:
        return self.combo.currentData()
