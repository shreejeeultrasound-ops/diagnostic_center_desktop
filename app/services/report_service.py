"""Customer Investigation Report service.

Deliberately produces NO clinical content (findings, observations,
measurements, diagnosis, impression) - see build brief section 10. The
report is patient/customer + investigation metadata only, formatted
professionally, branded with the configured company details.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.configuration.settings import CompanySettings, SettingsRepository
from app.database.session import session_scope
from app.domain.patient_investigation import PatientInvestigation
from app.repositories.transaction_repository import TransactionFilter, TransactionRepository


@dataclass
class CustomerReportData:
    company: CompanySettings
    transaction: PatientInvestigation


class ReportService:
    def __init__(
        self,
        session_factory: sessionmaker,
        settings_repo: SettingsRepository,
        txn_repo: Optional[TransactionRepository] = None,
    ):
        self.session_factory = session_factory
        self.settings_repo = settings_repo
        self.txn_repo = txn_repo or TransactionRepository()

    def get_report_data(self, txn_id: int) -> CustomerReportData:
        with session_scope(self.session_factory) as session:
            txn = self.txn_repo.get(session, txn_id)
        company = self.settings_repo.load()
        return CustomerReportData(company=company, transaction=txn)

    def search_transactions(self, filt: TransactionFilter) -> list[PatientInvestigation]:
        with session_scope(self.session_factory) as session:
            return self.txn_repo.search(session, filt)
