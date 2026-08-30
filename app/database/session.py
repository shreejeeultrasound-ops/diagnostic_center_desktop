"""Engine / session management and safe first-run database initialization.

Migration strategy (documented decision): V1 ships a single schema
version. Rather than pulling in Alembic (unnecessary complexity for a
single-table-set local SQLite app), we stamp a `schema_version` table on
creation. If a future release needs to change the schema, it can check
this table and apply forward-only migration steps before opening the
app. This keeps the dependency footprint small while leaving a clear,
documented upgrade path.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Base
from app.services.exceptions import DatabaseUnavailableError

CURRENT_SCHEMA_VERSION = 2  # v2 adds the `users` table for web-hosted auth


def build_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        # Enforce FK constraints (off by default in SQLite).
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL improves durability/concurrency for a desktop app that may
        # have the UI and a background report-generation thread reading
        # at once, and reduces the chance of corruption on power loss
        # compared to the default rollback journal in many real-world
        # cases.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()

    return engine


def init_database(engine) -> None:
    """Create tables if they do not exist yet. Never destroys existing
    data: SQLAlchemy's create_all() only creates missing tables and is a
    no-op for tables that already exist.
    """
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_version ("
                    "id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL)"
                )
            )
            existing = conn.execute(text("SELECT version FROM schema_version WHERE id=1")).first()
            if existing is None:
                conn.execute(
                    text("INSERT INTO schema_version (id, version) VALUES (1, :v)"),
                    {"v": CURRENT_SCHEMA_VERSION},
                )
            elif existing[0] < CURRENT_SCHEMA_VERSION:
                # create_all() above already added any new tables (it is
                # purely additive and never touches existing ones), so
                # bumping the stamp here is just keeping the record
                # honest for an app-data folder carried over from an
                # older version.
                conn.execute(
                    text("UPDATE schema_version SET version = :v WHERE id=1"),
                    {"v": CURRENT_SCHEMA_VERSION},
                )
    except sqlite3.DatabaseError as exc:
        raise DatabaseUnavailableError(
            f"The application database could not be initialized: {exc}"
        ) from exc


def build_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker):
    """Provide a transactional scope: commits on success, rolls back and
    re-raises on any error, so a failed save can never leave a half
    written record behind.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
