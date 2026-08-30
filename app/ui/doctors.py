from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.context import AppContext
from app.ui.widgets import confirm, show_error, show_info


class DoctorsScreen(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._editing_id: Optional[int] = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(10)

        heading = QLabel("Doctor Master")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        form.addRow("Doctor Name", self.name_edit)
        self.mobile_edit = QLineEdit()
        form.addRow("Mobile", self.mobile_edit)
        outer.addLayout(form)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Add Doctor")
        self.save_button.clicked.connect(self._on_save)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_form)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.clear_button)
        outer.addLayout(button_row)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name")
        self.search_edit.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_edit)
        outer.addLayout(search_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Mobile", "Status", "Edit", "Toggle Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        outer.addWidget(self.table)

    def _clear_form(self) -> None:
        self._editing_id = None
        self.name_edit.clear()
        self.mobile_edit.clear()
        self.save_button.setText("Add Doctor")

    def _on_save(self) -> None:
        try:
            if self._editing_id is None:
                self.ctx.doctor_service.create_doctor(self.name_edit.text(), self.mobile_edit.text())
                show_info(self, "Added", "Doctor added successfully.")
            else:
                self.ctx.doctor_service.update_doctor(
                    self._editing_id, self.name_edit.text(), self.mobile_edit.text()
                )
                show_info(self, "Updated", "Doctor updated successfully.")
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Could not save doctor", exc)
            return
        self._clear_form()
        self.refresh()

    def _edit(self, doctor_id: int) -> None:
        doctor = self.ctx.doctor_service.get(doctor_id)
        self._editing_id = doctor.id
        self.name_edit.setText(doctor.name)
        self.mobile_edit.setText(doctor.mobile or "")
        self.save_button.setText("Update Doctor")

    def _toggle_status(self, doctor_id: int, activate: bool) -> None:
        try:
            if activate:
                self.ctx.doctor_service.activate(doctor_id)
            else:
                if not confirm(
                    self,
                    "Deactivate Doctor",
                    "Deactivated doctors no longer appear for new entries, but all "
                    "historical transactions remain unchanged. Continue?",
                ):
                    return
                self.ctx.doctor_service.deactivate(doctor_id)
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Could not update status", exc)
            return
        self.refresh()

    def refresh(self) -> None:
        doctors = self.ctx.doctor_service.list_all(search=self.search_edit.text().strip() or None)
        self.table.setRowCount(len(doctors))
        for row, doctor in enumerate(doctors):
            self.table.setItem(row, 0, self._readonly_item(doctor.name))
            self.table.setItem(row, 1, self._readonly_item(doctor.mobile or "-"))
            self.table.setItem(row, 2, self._readonly_item(doctor.status.title()))

            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _c=False, did=doctor.id: self._edit(did))
            self.table.setCellWidget(row, 3, edit_btn)

            toggle_btn = QPushButton("Deactivate" if doctor.is_active else "Activate")
            toggle_btn.clicked.connect(
                lambda _c=False, did=doctor.id, act=not doctor.is_active: self._toggle_status(did, act)
            )
            self.table.setCellWidget(row, 4, toggle_btn)

    @staticmethod
    def _readonly_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()
