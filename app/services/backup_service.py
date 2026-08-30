"""Backup / Restore service.

Uses sqlite3's native backup API (not a raw file copy) so a backup taken
while the application has the database open (WAL mode) is always a
consistent, non-corrupt snapshot. Restore never destroys the current
database until the replacement has been verified to open successfully -
if anything goes wrong the original file is put back in place.

Because the application keeps a long-lived SQLAlchemy engine open in
WAL mode, a restore must also dispose that engine's connection pool and
clear any leftover -wal/-shm sidecar files before overwriting the main
database file - otherwise old cached pages or WAL frames from the
still-open session can make already-restored data appear to "come
back" the moment the app runs its next query. The engine is free to
reconnect lazily afterwards; SQLAlchemy does this automatically on the
next call.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.configuration.paths import AppPaths
from app.services.exceptions import BackupError, RestoreError


class BackupService:
    def __init__(self, paths: AppPaths, engine=None):
        self.paths = paths
        self.engine = engine

    def backup(self, destination: Optional[Path] = None) -> Path:
        self.paths.ensure_created()
        if not self.paths.database_file.exists():
            raise BackupError("No database file exists yet - nothing to back up.")

        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = self.paths.backups_dir / f"backup_{timestamp}.db"
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            source_conn = sqlite3.connect(str(self.paths.database_file))
            dest_conn = sqlite3.connect(str(destination))
            with dest_conn:
                source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()
        except sqlite3.Error as exc:
            raise BackupError(f"Backup failed: {exc}") from exc

        self._verify_integrity(destination, error_cls=BackupError, action="Backup")
        return destination

    def restore(self, source: Path) -> None:
        source = Path(source)
        if not source.exists():
            raise RestoreError("Selected backup file does not exist.")

        self._verify_integrity(source, error_cls=RestoreError, action="Restore")

        self.paths.ensure_created()
        safety_copy: Optional[Path] = None
        if self.paths.database_file.exists():
            safety_copy = self.paths.database_file.with_suffix(".db.before-restore")
            shutil.copyfile(self.paths.database_file, safety_copy)

        if self.engine is not None:
            # Close every pooled connection so nothing can read stale
            # pages or WAL frames from the database we are about to
            # replace on disk.
            self.engine.dispose()
        self._remove_wal_sidecars(self.paths.database_file)

        try:
            shutil.copyfile(source, self.paths.database_file)
            self._remove_wal_sidecars(self.paths.database_file)
            self._verify_integrity(self.paths.database_file, error_cls=RestoreError, action="Restore")
        except Exception:
            # Roll back to the pre-restore state rather than leaving the
            # application with a broken database.
            if safety_copy is not None:
                shutil.copyfile(safety_copy, self.paths.database_file)
                self._remove_wal_sidecars(self.paths.database_file)
            raise
        finally:
            if safety_copy is not None:
                safety_copy.unlink(missing_ok=True)

    @staticmethod
    def _remove_wal_sidecars(db_path: Path) -> None:
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            sidecar.unlink(missing_ok=True)

    @staticmethod
    def _verify_integrity(db_path: Path, *, error_cls, action: str) -> None:
        try:
            conn = sqlite3.connect(str(db_path))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
        except sqlite3.Error as exc:
            raise error_cls(f"{action} failed integrity check: {exc}") from exc
        if not result or result[0] != "ok":
            raise error_cls(f"{action} failed: database integrity check did not pass.")
