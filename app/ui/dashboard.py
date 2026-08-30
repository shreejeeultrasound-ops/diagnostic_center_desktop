from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.context import AppContext
from app.reporting.currency import format_inr


class _NavButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)


class _StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #f4f6f8; border-radius: 8px; padding: 4px; }"
        )
        layout = QVBoxLayout(self)
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #555555;")
        layout.addWidget(self.value_label)
        layout.addWidget(title_label)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


class DashboardScreen(QWidget):
    navigate = Signal(str)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.company_label = QLabel()
        self.company_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.company_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.company_label)

        nav_row = QHBoxLayout()
        buttons = [
            ("New Data Entry", "data_entry"),
            ("Customer Reports", "reports"),
            ("DC Generation", "dc"),
            ("Master Data", "doctors"),
            ("Settings", "settings"),
        ]
        for label, key in buttons:
            btn = _NavButton(label)
            btn.clicked.connect(lambda _checked=False, k=key: self.navigate.emit(k))
            nav_row.addWidget(btn)
        layout.addLayout(nav_row)

        stats_row = QHBoxLayout()
        self.patients_card = _StatCard("Today's Patients")
        self.collection_card = _StatCard("Today's Collection")
        stats_row.addWidget(self.patients_card)
        stats_row.addWidget(self.collection_card)
        layout.addLayout(stats_row)

        layout.addStretch(1)

    def refresh(self) -> None:
        company = self.ctx.settings_service.get()
        self.company_label.setText(company.company_name or "Diagnostic Center")

        today_rows = self.ctx.data_capture_service.today_entries()
        self.patients_card.set_value(str(len(today_rows)))
        total_collection = sum((r.net_fee for r in today_rows), Decimal("0.00"))
        self.collection_card.set_value(format_inr(total_collection))

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self.refresh()
