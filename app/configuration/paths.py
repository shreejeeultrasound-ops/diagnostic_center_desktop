"""
Resolves where the application stores mutable data (database, config,
logs, backups, logo) as opposed to where the application binaries live.

Business data must NEVER live next to the executable, because Windows
program-files style install locations are frequently not user-writable,
and because application updates must not be able to destroy business data
by overwriting the install directory.

Windows:   %LOCALAPPDATA%\\DiagnosticCenter
macOS:     ~/Library/Application Support/DiagnosticCenter
Linux:     $XDG_DATA_HOME/DiagnosticCenter or ~/.local/share/DiagnosticCenter

An APP_DATA_DIR environment variable can override this (used by the test
suite so tests never touch a real user's data directory).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "DiagnosticCenter"


def _base_data_dir() -> Path:
    override = os.environ.get("APP_DATA_DIR")
    if override:
        return Path(override)

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME


class AppPaths:
    """Central resolver for every writable location the app uses."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or _base_data_dir()
        self.db_dir = self.base_dir / "database"
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.backups_dir = self.base_dir / "backups"
        self.assets_dir = self.base_dir / "assets"  # e.g. uploaded logo

    def ensure_created(self) -> None:
        for d in (
            self.base_dir,
            self.db_dir,
            self.config_dir,
            self.logs_dir,
            self.backups_dir,
            self.assets_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def database_file(self) -> Path:
        return self.db_dir / "diagnostic_center.db"

    @property
    def settings_file(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def log_file(self) -> Path:
        return self.logs_dir / "app.log"


# Module-level singleton used by the application at runtime. Tests build
# their own AppPaths pointed at a temp directory instead of using this.
default_paths = AppPaths()
