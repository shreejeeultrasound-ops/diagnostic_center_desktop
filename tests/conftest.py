from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.context import AppContext


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    """A fresh AppContext backed by a temp directory for every test, so
    tests never touch a real user's data and never interfere with each
    other.
    """
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "appdata"))
    return AppContext(tmp_path / "appdata")
