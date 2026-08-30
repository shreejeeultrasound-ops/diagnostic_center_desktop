"""Application entry point.

On first launch this:
  1. creates the per-user app-data directories (database/config/logs/backups),
  2. initializes the SQLite schema if it does not already exist,
  3. opens straight to the dashboard - no fake seed data is created
     (build brief section 28: doctors/investigations/patients are never
     auto-populated).

Any unhandled exception is caught at the top level, logged with full
detail, and shown to the user as a plain-language message instead of a
crash with a raw traceback (build brief section 21).
"""
from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from app.context import AppContext
from app.logging_config import get_logger
from app.ui.main_window import MainWindow

logger = get_logger(__name__)


def _install_global_exception_hook(app: QApplication) -> None:
    def handle_exception(exc_type, exc_value, exc_tb):
        logger.error(
            "Unhandled exception: %s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        QMessageBox.critical(
            None,
            "Unexpected Error",
            "An unexpected error occurred and has been logged. "
            "Please restart the application. If this keeps happening, "
            "use Settings > Backup to protect your data and contact support.",
        )

    sys.excepthook = handle_exception


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Diagnostic Center")

    try:
        ctx = AppContext()
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(
            None,
            "Startup Error",
            f"The application could not start because the database could not "
            f"be initialized:\n\n{exc}\n\nYour data has not been affected.",
        )
        return 1

    _install_global_exception_hook(app)

    window = MainWindow(ctx)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
