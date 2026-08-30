from __future__ import annotations

from app.configuration.settings import CompanySettings, SettingsRepository
from app.services.exceptions import ValidationError


class SettingsService:
    def __init__(self, settings_repo: SettingsRepository):
        self.settings_repo = settings_repo

    def get(self) -> CompanySettings:
        return self.settings_repo.load()

    def save(
        self,
        *,
        company_name: str,
        address: str = "",
        phone: str = "",
        email: str = "",
        website: str = "",
        report_footer: str = "",
        new_logo_source_path: str | None = None,
        existing_logo_path: str = "",
    ) -> CompanySettings:
        clean_name = (company_name or "").strip()
        if not clean_name:
            raise ValidationError("Company name is mandatory.")

        logo_path = existing_logo_path
        if new_logo_source_path:
            logo_path = self.settings_repo.import_logo(new_logo_source_path)

        settings = CompanySettings(
            company_name=clean_name,
            logo_path=logo_path,
            address=(address or "").strip(),
            phone=(phone or "").strip(),
            email=(email or "").strip(),
            website=(website or "").strip(),
            report_footer=(report_footer or "").strip(),
        )
        self.settings_repo.save(settings)
        return settings
