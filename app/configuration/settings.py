"""
Company / branding settings used on generated reports and DCs.

Deliberately NOT hard-coded: stored as JSON in the per-user app-data
config directory so branding can be changed without touching code or
rebuilding the application. The logo file itself is copied into the
app-data assets directory so the settings survive even if the original
uploaded file is later moved or deleted.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from app.configuration.paths import AppPaths
from app.services.exceptions import ValidationError

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@dataclass
class CompanySettings:
    company_name: str = ""
    logo_path: str = ""  # absolute path inside app-data assets dir, or ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    report_footer: str = ""

    def is_configured(self) -> bool:
        return bool(self.company_name.strip())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CompanySettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class SettingsRepository:
    """Reads/writes CompanySettings as JSON in the app-data config dir."""

    def __init__(self, paths: AppPaths):
        self.paths = paths

    def load(self) -> CompanySettings:
        if not self.paths.settings_file.exists():
            return CompanySettings()
        try:
            data = json.loads(self.paths.settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Corrupt settings file must never crash the app - fall back
            # to blank settings rather than raising.
            return CompanySettings()
        return CompanySettings.from_dict(data)

    def save(self, settings: CompanySettings) -> None:
        self.paths.ensure_created()
        tmp_file = self.paths.settings_file.with_suffix(".json.tmp")
        tmp_file.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp_file.replace(self.paths.settings_file)  # atomic on same filesystem

    def import_logo(self, source_path: str) -> str:
        """Validate and copy a logo image into the app-data assets dir.

        Returns the new absolute path to store in CompanySettings.logo_path.
        """
        src = Path(source_path)
        if not src.exists() or not src.is_file():
            raise ValidationError("Selected logo file does not exist.")
        if src.suffix.lower() not in ALLOWED_LOGO_EXTENSIONS:
            raise ValidationError(
                f"Logo must be one of: {', '.join(sorted(ALLOWED_LOGO_EXTENSIONS))}"
            )
        if src.stat().st_size > MAX_LOGO_SIZE_BYTES:
            raise ValidationError("Logo file is too large (max 5 MB).")

        # Reject a corrupt/unreadable image now, with a clear message,
        # rather than silently accepting it and only surfacing the
        # problem later as a missing logo on a generated report (PDF
        # generation degrades gracefully if this check is ever bypassed
        # - see app/reporting/pdf_common.py - but catching it here gives
        # the person who uploaded it useful feedback immediately).
        try:
            from PIL import Image as PILImage

            with PILImage.open(src) as pil_img:
                pil_img.load()
        except Exception as exc:
            raise ValidationError(
                "That file doesn't appear to be a valid image. Please choose a different logo."
            ) from exc

        self.paths.ensure_created()
        dest = self.paths.assets_dir / f"logo{src.suffix.lower()}"
        try:
            shutil.copyfile(src, dest)
        except OSError as exc:
            raise ValidationError(f"Could not import logo file: {exc}") from exc
        return str(dest)
