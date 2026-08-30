"""Application logging.

Logs go to a rotating file in the per-user app-data logs directory so a
non-technical user never needs a console to get diagnostic information
to a developer. Only technical/error detail is logged - patient names,
addresses and mobile numbers are deliberately never written to the log
(see app.services.exceptions: UI-facing messages are friendly text, the
full exception/traceback goes to the log instead).
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_configured = False


def configure_logging(log_file: Path, *, level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
