from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.context import AppContext
from app.services.exceptions import AppError
from app.ui.widgets import confirm, show_error, show_info


class SettingsScreen(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._new_logo_path: str | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        heading = QLabel("Settings")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(heading)

        company_heading = QLabel("Company / Branding (used on all reports and DCs)")
        company_heading.setStyleSheet("font-weight: 600;")
        outer.addWidget(company_heading)

        form = QFormLayout()
        self.company_name_edit = QLineEdit()
        form.addRow("Company Name", self.company_name_edit)

        logo_row = QHBoxLayout()
        self.logo_preview = QLabel("No logo")
        self.logo_preview.setFixedSize(80, 50)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc;")
        logo_row.addWidget(self.logo_preview)
        logo_button = QPushButton("Choose Logo...")
        logo_button.clicked.connect(self._choose_logo)
        logo_row.addWidget(logo_button)
        form.addRow("Logo", logo_row)

        self.address_edit = QPlainTextEdit()
        self.address_edit.setFixedHeight(50)
        form.addRow("Address", self.address_edit)

        self.phone_edit = QLineEdit()
        form.addRow("Phone", self.phone_edit)
        self.email_edit = QLineEdit()
        form.addRow("Email", self.email_edit)
        self.website_edit = QLineEdit()
        form.addRow("Website", self.website_edit)
        self.footer_edit = QLineEdit()
        form.addRow("Report Footer", self.footer_edit)
        outer.addLayout(form)

        save_button = QPushButton("Save Company Settings")
        save_button.clicked.connect(self._on_save)
        outer.addWidget(save_button)

        data_heading = QLabel("Data")
        data_heading.setStyleSheet("font-weight: 600;")
        outer.addWidget(data_heading)

        self.db_location_label = QLabel("")
        self.db_location_label.setWordWrap(True)
        outer.addWidget(self.db_location_label)

        data_row = QHBoxLayout()
        backup_button = QPushButton("Backup Database")
        backup_button.clicked.connect(self._on_backup)
        restore_button = QPushButton("Restore Database")
        restore_button.clicked.connect(self._on_restore)
        data_row.addWidget(backup_button)
        data_row.addWidget(restore_button)
        outer.addLayout(data_row)

        outer.addStretch(1)

    def refresh(self) -> None:
        company = self.ctx.settings_service.get()
        self.company_name_edit.setText(company.company_name)
        self.address_edit.setPlainText(company.address)
        self.phone_edit.setText(company.phone)
        self.email_edit.setText(company.email)
        self.website_edit.setText(company.website)
        self.footer_edit.setText(company.report_footer)
        self._existing_logo_path = company.logo_path
        self._update_logo_preview(company.logo_path)
        self.db_location_label.setText(f"Database file: {self.ctx.paths.database_file}")

    def _update_logo_preview(self, path: str) -> None:
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            self.logo_preview.setPixmap(
                pixmap.scaled(78, 48, aspectMode=1, mode=1) if pixmap else QPixmap()
            )
        else:
            self.logo_preview.setText("No logo")

    def _choose_logo(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Choose Logo Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path_str:
            self._new_logo_path = path_str
            self._update_logo_preview(path_str)

    def _on_save(self) -> None:
        try:
            self.ctx.settings_service.save(
                company_name=self.company_name_edit.text(),
                address=self.address_edit.toPlainText(),
                phone=self.phone_edit.text(),
                email=self.email_edit.text(),
                website=self.website_edit.text(),
                report_footer=self.footer_edit.text(),
                new_logo_source_path=self._new_logo_path,
                existing_logo_path=self._existing_logo_path,
            )
            self._new_logo_path = None
            show_info(self, "Saved", "Company settings saved.")
            self.refresh()
        except AppError as exc:
            show_error(self, "Could not save settings", exc)

    def _on_backup(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Backup Database To...", "diagnostic_center_backup.db", "SQLite DB (*.db)"
        )
        if not path_str:
            return
        try:
            self.ctx.backup_service.backup(Path(path_str))
            show_info(self, "Backup complete", f"Backup saved to:\n{path_str}")
        except AppError as exc:
            show_error(self, "Backup failed", exc)

    def _on_restore(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Restore Database From...", "", "SQLite DB (*.db)")
        if not path_str:
            return
        if not confirm(
            self,
            "Restore Database",
            "This will replace the current database with the selected backup. "
            "A safety copy of the current database is kept until the restore "
            "succeeds. Continue?",
        ):
            return
        try:
            self.ctx.backup_service.restore(Path(path_str))
            show_info(
                self,
                "Restore complete",
                "Database restored. Please restart the application to continue.",
            )
        except AppError as exc:
            show_error(self, "Restore failed", exc)
