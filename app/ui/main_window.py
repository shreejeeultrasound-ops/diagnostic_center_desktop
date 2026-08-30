from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from app.context import AppContext
from app.ui.dashboard import DashboardScreen
from app.ui.data_entry import DataEntryScreen
from app.ui.dc_view import DCScreen
from app.ui.doctors import DoctorsScreen
from app.ui.investigations import InvestigationsScreen
from app.ui.reports_view import ReportsScreen
from app.ui.settings_view import SettingsScreen
from app.ui.transactions import TransactionsScreen

NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("data_entry", "New Data Entry"),
    ("transactions", "View / Search Entries"),
    ("doctors", "Doctor Master"),
    ("investigations", "Investigation Master"),
    ("dc", "DC Generation"),
    ("reports", "Customer Reports"),
    ("settings", "Settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("Diagnostic Center")
        self.resize(1100, 720)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setStyleSheet(
            "QListWidget { background: #22313f; color: white; border: none; font-size: 13px; }"
            "QListWidget::item { padding: 12px 14px; }"
            "QListWidget::item:selected { background: #2f4f6f; }"
        )
        for key, label in NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.nav_list)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.dashboard = DashboardScreen(ctx)
        self.dashboard.navigate.connect(self._navigate_by_key)
        self.data_entry = DataEntryScreen(ctx)
        self.transactions = TransactionsScreen(ctx)
        self.transactions.edit_requested.connect(self._edit_transaction)
        self.doctors = DoctorsScreen(ctx)
        self.investigations = InvestigationsScreen(ctx)
        self.dc = DCScreen(ctx)
        self.reports = ReportsScreen(ctx)
        self.settings = SettingsScreen(ctx)

        self._screens = {
            "dashboard": self.dashboard,
            "data_entry": self.data_entry,
            "transactions": self.transactions,
            "doctors": self.doctors,
            "investigations": self.investigations,
            "dc": self.dc,
            "reports": self.reports,
            "settings": self.settings,
        }
        for key, _label in NAV_ITEMS:
            self.stack.addWidget(self._screens[key])

        self.nav_list.setCurrentRow(0)

    def _on_nav_changed(self, row: int) -> None:
        key, _label = NAV_ITEMS[row]
        self.stack.setCurrentWidget(self._screens[key])
        # Doctors/Investigations/Reports already refresh themselves in
        # their own showEvent() whenever they become visible, so nothing
        # extra is needed here for them (calling refresh() a second time
        # in the same tick was redundant - an unnecessary duplicate
        # database query on every nav click, and it briefly recreates
        # table row widgets twice in a row for no benefit). DC Generation
        # and Data Entry don't hook showEvent, so they still need an
        # explicit nudge here.
        if key == "dc":
            self.dc.refresh_doctors()
        elif key == "data_entry":
            self.data_entry.reset_form()

    def _navigate_by_key(self, key: str) -> None:
        for row, (item_key, _label) in enumerate(NAV_ITEMS):
            if item_key == key:
                self.nav_list.setCurrentRow(row)
                return

    def _edit_transaction(self, txn_id: int) -> None:
        self._navigate_by_key("data_entry")
        self.data_entry.load_for_edit(txn_id)
