"""Resolves the path to bundled read-only resources (fonts, icons) that
ship inside the application package itself - as opposed to
app.configuration.paths, which resolves the per-user *writable* data
directory.

When PyInstaller freezes the app, bundled data files are extracted to a
temporary directory exposed as sys._MEIPASS; in normal `python -m
app.main` development runs, resources live under app/assets relative to
this source tree.
"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base.joinpath("app", "assets", *parts)
    base = Path(__file__).resolve().parent.parent  # .../app
    return base.joinpath("assets", *parts)
