from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
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
from app.reporting.currency import format_date
from app.reporting.customer_report_pdf import generate_customer_report_pdf
from app.repositories.transaction_repository import TransactionFilter
from app.services.exceptions import AppError
from app.ui.widgets import show_error, show_info, today_date_edit


class ReportsScreen(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._results = []
        self._selected_txn_id: int | None = None
        self._build_ui()
        self.refresh_dropdowns()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(10)

        heading = QLabel("Customer Investigation Report")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        filter_row = QHBoxLayout()
        self.patient_filter = QLineEdit()
        self.patient_filter.setPlaceholderText("Patient name")
        filter_row.addWidget(self.patient_filter)
        self.mobile_filter = QLineEdit()
        self.mobile_filter.setPlaceholderText("Mobile")
        filter_row.addWidget(self.mobile_filter)
        self.doctor_filter = QComboBox()
        self.doctor_filter.addItem("Any doctor", None)
        filter_row.addWidget(self.doctor_filter)
        self.investigation_filter = QComboBox()
        self.investigation_filter.addItem("Any investigation", None)
        filter_row.addWidget(self.investigation_filter)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self._on_search)
        filter_row.addWidget(search_button)
        outer.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Patient", "Mobile", "Doctor", "Investigation", "Select"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        outer.addWidget(self.table)

        self.preview_frame = QFrame()
        self.preview_frame.setFrameShape(QFrame.StyledPanel)
        self.preview_frame.setStyleSheet("QFrame { background: #f8f8f8; }")
        preview_layout = QVBoxLayout(self.preview_frame)
        self.preview_label = QLabel("Select a result above to preview the report.")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        outer.addWidget(self.preview_frame)

        action_row = QHBoxLayout()
        self.pdf_button = QPushButton("Generate PDF")
        self.pdf_button.clicked.connect(self._on_save_pdf)
        self.pdf_button.setEnabled(False)
        self.print_button = QPushButton("Print")
        self.print_button.clicked.connect(self._on_print)
        self.print_button.setEnabled(False)
        action_row.addWidget(self.pdf_button)
        action_row.addWidget(self.print_button)
        outer.addLayout(action_row)

    def refresh_dropdowns(self) -> None:
        self.doctor_filter.clear()
        self.doctor_filter.addItem("Any doctor", None)
        for doctor in self.ctx.doctor_service.list_all():
            self.doctor_filter.addItem(doctor.name, doctor.id)

        self.investigation_filter.clear()
        self.investigation_filter.addItem("Any investigation", None)
        for investigation in self.ctx.investigation_service.list_all():
            self.investigation_filter.addItem(investigation.name, investigation.id)

    def _on_search(self) -> None:
        filt = TransactionFilter(
            patient_name=self.patient_filter.text().strip() or None,
            mobile=self.mobile_filter.text().strip() or None,
            doctor_id=self.doctor_filter.currentData(),
            investigation_type_id=self.investigation_filter.currentData(),
        )
        self._results = self.ctx.report_service.search_transactions(filt)
        self.table.setRowCount(len(self._results))
        for row_index, txn in enumerate(self._results):
            values = [
                format_date(txn.transaction_date),
                txn.patient_name,
                txn.mobile or "-",
                txn.doctor_name_snapshot,
                txn.investigation_name_snapshot,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col, item)
            select_button = QPushButton("Preview")
            select_button.clicked.connect(lambda _c=False, tid=txn.id: self._select(tid))
            self.table.setCellWidget(row_index, 5, select_button)

    def _select(self, txn_id: int) -> None:
        self._selected_txn_id = txn_id
        data = self.ctx.report_service.get_report_data(txn_id)
        txn = data.transaction
        self.preview_label.setText(
            f"<b>Patient:</b> {txn.patient_name} &nbsp; <b>Age:</b> {txn.age or '-'}<br/>"
            f"<b>Father/Husband:</b> {txn.father_husband_name or '-'}<br/>"
            f"<b>Address:</b> {(txn.address or '-').replace(chr(10), '<br/>')}<br/>"
            f"<b>Mobile:</b> {txn.mobile or '-'}<br/>"
            f"<b>Doctor:</b> {txn.doctor_name_snapshot} &nbsp; "
            f"<b>Investigation:</b> {txn.investigation_name_snapshot}<br/>"
            f"<b>Report Date:</b> {format_date(txn.transaction_date)}"
        )
        self.pdf_button.setEnabled(True)
        self.print_button.setEnabled(True)

    def _generate_pdf(self, destination: Path) -> Path:
        data = self.ctx.report_service.get_report_data(self._selected_txn_id)
        return generate_customer_report_pdf(data, destination)

    def _on_save_pdf(self) -> None:
        if self._selected_txn_id is None:
            return
        default_name = f"Report_{self._selected_txn_id}.pdf"
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Save Customer Investigation Report", default_name, "PDF Files (*.pdf)"
        )
        if not path_str:
            return
        try:
            self._generate_pdf(Path(path_str))
            show_info(self, "Saved", f"Report saved to:\n{path_str}")
        except AppError as exc:
            show_error(self, "Could not save report", exc)

    def _on_print(self) -> None:
        if self._selected_txn_id is None:
            return
        try:
            temp_dir = self.ctx.paths.backups_dir.parent / "print_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_dir / "report_print.pdf"
            self._generate_pdf(pdf_path)
        except AppError as exc:
            show_error(self, "Could not prepare print", exc)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh_dropdowns()
