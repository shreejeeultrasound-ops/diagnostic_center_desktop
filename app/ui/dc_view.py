from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.context import AppContext
from app.reporting.currency import format_inr
from app.reporting.dc_pdf import generate_dc_pdf
from app.services.exceptions import AppError
from app.ui.widgets import show_error, show_info, today_date_edit


class DCScreen(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._current_dc = None
        self._build_ui()
        self.refresh_doctors()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(10)

        heading = QLabel("DC Generation")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Doctor"))
        self.doctor_combo = QComboBox()
        filter_row.addWidget(self.doctor_combo, 1)

        filter_row.addWidget(QLabel("From"))
        self.from_date = today_date_edit()
        self.from_date.setDate(self.from_date.date().addDays(-30))
        filter_row.addWidget(self.from_date)

        filter_row.addWidget(QLabel("To"))
        self.to_date = today_date_edit()
        filter_row.addWidget(self.to_date)

        generate_button = QPushButton("Generate / Preview")
        generate_button.clicked.connect(self._on_generate)
        filter_row.addWidget(generate_button)
        outer.addLayout(filter_row)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: 600;")
        outer.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Patient", "Investigation", "Fee", "Net Fee"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        outer.addWidget(self.table)

        action_row = QHBoxLayout()
        self.pdf_button = QPushButton("Save as PDF")
        self.pdf_button.clicked.connect(self._on_save_pdf)
        self.pdf_button.setEnabled(False)
        self.print_button = QPushButton("Print")
        self.print_button.clicked.connect(self._on_print)
        self.print_button.setEnabled(False)
        action_row.addWidget(self.pdf_button)
        action_row.addWidget(self.print_button)
        outer.addLayout(action_row)

    def refresh_doctors(self) -> None:
        current = self.doctor_combo.currentData()
        self.doctor_combo.clear()
        for doctor in self.ctx.doctor_service.list_all():
            label = doctor.name if doctor.is_active else f"{doctor.name} (inactive)"
            self.doctor_combo.addItem(label, doctor.id)
        if current is not None:
            for i in range(self.doctor_combo.count()):
                if self.doctor_combo.itemData(i) == current:
                    self.doctor_combo.setCurrentIndex(i)
                    break

    def _on_generate(self) -> None:
        doctor_id = self.doctor_combo.currentData()
        if doctor_id is None:
            show_info(self, "Select a doctor", "Please add a doctor first, then select one.")
            return
        try:
            dc = self.ctx.dc_service.generate(
                doctor_id, self.from_date.date().toPython(), self.to_date.date().toPython()
            )
        except AppError as exc:
            show_error(self, "Could not generate DC", exc)
            return

        self._current_dc = dc
        self.table.setRowCount(len(dc.rows))
        for row_index, txn in enumerate(dc.rows):
            from app.reporting.currency import format_date

            values = [
                format_date(txn.transaction_date),
                txn.patient_name,
                txn.investigation_name_snapshot,
                format_inr(txn.fee),
                format_inr(txn.net_fee),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col, item)

        self.summary_label.setText(
            f"Total Patients: {dc.total_patients}    "
            f"Gross Fees: {format_inr(dc.gross_fees)}    "
            f"Discount: {format_inr(dc.total_discount)}    "
            f"Net Fees: {format_inr(dc.net_fees)}"
        )
        has_rows = True
        self.pdf_button.setEnabled(has_rows)
        self.print_button.setEnabled(has_rows)

    def _generate_pdf(self, destination: Path) -> Path:
        company = self.ctx.settings_service.get()
        return generate_dc_pdf(self._current_dc, company, destination)

    def _on_save_pdf(self) -> None:
        if self._current_dc is None:
            return
        default_name = f"DC_{self._current_dc.doctor_name}_{self._current_dc.from_date}_{self._current_dc.to_date}.pdf"
        default_name = default_name.replace(" ", "_")
        path_str, _ = QFileDialog.getSaveFileName(self, "Save DC as PDF", default_name, "PDF Files (*.pdf)")
        if not path_str:
            return
        try:
            self._generate_pdf(Path(path_str))
            show_info(self, "Saved", f"DC saved to:\n{path_str}")
        except AppError as exc:
            show_error(self, "Could not save PDF", exc)

    def _on_print(self) -> None:
        if self._current_dc is None:
            return
        try:
            temp_path = self.ctx.paths.backups_dir.parent / "print_temp"
            temp_path.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_path / "dc_print.pdf"
            self._generate_pdf(pdf_path)
        except AppError as exc:
            show_error(self, "Could not prepare print", exc)
            return
        # Opens the PDF in the system's default PDF viewer, where the
        # user can print via the normal OS print dialog. This keeps a
        # single authoritative rendering (ReportLab) instead of building
        # and maintaining a second, separately-maintained native print
        # layout that could drift out of sync with the PDF/preview.
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
