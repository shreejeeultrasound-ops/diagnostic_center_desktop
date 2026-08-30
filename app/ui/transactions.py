from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
from app.reporting.currency import format_date, format_inr
from app.repositories.transaction_repository import TransactionFilter
from app.ui.widgets import show_error, today_date_edit


class TransactionsScreen(QWidget):
    edit_requested = Signal(int)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._results = []
        self._build_ui()
        self.search()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(10)

        heading = QLabel("Search / View Entries")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        filter_row = QHBoxLayout()
        self.today_only = QCheckBox("Today only")
        self.today_only.setChecked(True)
        self.today_only.stateChanged.connect(self._on_today_toggled)
        filter_row.addWidget(self.today_only)

        filter_row.addWidget(QLabel("From"))
        self.from_date = today_date_edit()
        filter_row.addWidget(self.from_date)
        filter_row.addWidget(QLabel("To"))
        self.to_date = today_date_edit()
        filter_row.addWidget(self.to_date)

        self.patient_name_filter = QLineEdit()
        self.patient_name_filter.setPlaceholderText("Patient name")
        filter_row.addWidget(self.patient_name_filter)

        self.mobile_filter = QLineEdit()
        self.mobile_filter.setPlaceholderText("Mobile")
        filter_row.addWidget(self.mobile_filter)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search)
        filter_row.addWidget(search_button)
        outer.addLayout(filter_row)

        self._on_today_toggled()

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Patient", "Mobile", "Doctor", "Investigation", "Net Fee", "Edit"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        outer.addWidget(self.table)

    def _on_today_toggled(self) -> None:
        enabled = not self.today_only.isChecked()
        self.from_date.setEnabled(enabled)
        self.to_date.setEnabled(enabled)

    def search(self) -> None:
        try:
            if self.today_only.isChecked():
                today = date.today()
                filt = TransactionFilter(from_date=today, to_date=today)
            else:
                filt = TransactionFilter(
                    from_date=self.from_date.date().toPython(),
                    to_date=self.to_date.date().toPython(),
                )
            if self.patient_name_filter.text().strip():
                filt.patient_name = self.patient_name_filter.text().strip()
            if self.mobile_filter.text().strip():
                filt.mobile = self.mobile_filter.text().strip()

            self._results = self.ctx.data_capture_service.search(filt)
        except Exception as exc:  # noqa: BLE001
            show_error(self, "Search failed", exc)
            return

        self.table.setRowCount(len(self._results))
        for row_index, txn in enumerate(self._results):
            values = [
                format_date(txn.transaction_date),
                txn.patient_name,
                txn.mobile or "-",
                txn.doctor_name_snapshot,
                txn.investigation_name_snapshot,
                format_inr(txn.net_fee),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col, item)

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda _c=False, tid=txn.id: self.edit_requested.emit(tid))
            self.table.setCellWidget(row_index, 6, edit_button)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.search()
