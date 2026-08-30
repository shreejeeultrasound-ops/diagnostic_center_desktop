"""Application composition root.

Builds the database engine/session factory and every service exactly
once, so UI screens receive ready-to-use services rather than
constructing their own persistence objects. Keeping this wiring in one
place is what lets services stay unaware of PySide6, and lets tests
build an AppContext pointed at a temp directory instead of the real
per-user app-data folder.
"""
from __future__ import annotations

from pathlib import Path

from app.configuration.paths import AppPaths
from app.configuration.settings import SettingsRepository
from app.database.session import build_engine, build_session_factory, init_database
from app.logging_config import configure_logging, get_logger
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.data_capture_service import DataCaptureService
from app.services.dc_service import DCService
from app.services.doctor_service import DoctorService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService

logger = get_logger(__name__)


class AppContext:
    def __init__(self, base_dir: Path | None = None):
        self.paths = AppPaths(base_dir)
        self.paths.ensure_created()
        configure_logging(self.paths.log_file)

        self.engine = build_engine(self.paths.database_file)
        init_database(self.engine)
        self.session_factory = build_session_factory(self.engine)

        self.settings_repo = SettingsRepository(self.paths)

        self.doctor_service = DoctorService(self.session_factory)
        self.investigation_service = InvestigationService(self.session_factory)
        self.data_capture_service = DataCaptureService(self.session_factory)
        self.dc_service = DCService(self.session_factory)
        self.report_service = ReportService(self.session_factory, self.settings_repo)
        self.settings_service = SettingsService(self.settings_repo)
        self.backup_service = BackupService(self.paths, engine=self.engine)
        self.auth_service = AuthService(self.session_factory)

        logger.info("Application context initialized (db=%s)", self.paths.database_file)
