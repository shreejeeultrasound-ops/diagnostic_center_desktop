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
from app.reporting.currency import format_inr
from app.ui.widgets import CurrencySpinBox, confirm, show_error, show_info


class InvestigationsScreen(QWidget):
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

        heading = QLabel("Investigation Type Master")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        form.addRow("Investigation Type Name", self.name_edit)
        self.fee_edit = CurrencySpinBox()
        form.addRow("Default Fee", self.fee_edit)
        outer.addLayout(form)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Add Investigation Type")
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
        self.table.setHorizontalHeaderLabels(
            ["Name", "Default Fee", "Status", "Edit", "Toggle Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        outer.addWidget(self.table)

    def _clear_form(self) -> None:
        self._editing_id = None
        self.name_edit.clear()
        self.fee_edit.setValue(0)
        self.save_button.setText("Add Investigation Type")

    def _on_save(self) -> None:
        try:
            if self._editing_id is None:
                self.ctx.investigation_service.create_investigation(
                    self.name_edit.text(), self.fee_edit.value()
                )
                show_info(self, "Added", "Investigation type added successfully.")
            else:
                self.ctx.investigation_service.update_investigation(
                    self._editing_id, self.name_edit.text(), self.fee_edit.value()
                )
                show_info(
                    self,
                    "Updated",
                    "Investigation type updated. Existing historical transactions "
                    "keep their originally captured fee.",
                )
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Could not save investigation type", exc)
            return
        self._clear_form()
        self.refresh()

    def _edit(self, investigation_id: int) -> None:
        investigation = self.ctx.investigation_service.get(investigation_id)
        self._editing_id = investigation.id
        self.name_edit.setText(investigation.name)
        self.fee_edit.setValue(float(investigation.default_fee))
        self.save_button.setText("Update Investigation Type")

    def _toggle_status(self, investigation_id: int, activate: bool) -> None:
        try:
            if activate:
                self.ctx.investigation_service.activate(investigation_id)
            else:
                if not confirm(
                    self,
                    "Deactivate Investigation Type",
                    "Deactivated investigation types no longer appear for new entries, "
                    "but all historical transactions remain unchanged. Continue?",
                ):
                    return
                self.ctx.investigation_service.deactivate(investigation_id)
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Could not update status", exc)
            return
        self.refresh()

    def refresh(self) -> None:
        investigations = self.ctx.investigation_service.list_all(
            search=self.search_edit.text().strip() or None
        )
        self.table.setRowCount(len(investigations))
        for row, investigation in enumerate(investigations):
            self.table.setItem(row, 0, self._readonly_item(investigation.name))
            self.table.setItem(row, 1, self._readonly_item(format_inr(investigation.default_fee)))
            self.table.setItem(row, 2, self._readonly_item(investigation.status.title()))

            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _c=False, iid=investigation.id: self._edit(iid))
            self.table.setCellWidget(row, 3, edit_btn)

            toggle_btn = QPushButton("Deactivate" if investigation.is_active else "Activate")
            toggle_btn.clicked.connect(
                lambda _c=False, iid=investigation.id, act=not investigation.is_active: self._toggle_status(
                    iid, act
                )
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
