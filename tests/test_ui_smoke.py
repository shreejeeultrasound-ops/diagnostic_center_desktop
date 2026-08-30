"""Headless (offscreen) smoke test of the PySide6 UI layer.

Runs the QT_QPA_PLATFORM=offscreen backend so this executes in CI/dev
containers without a display. Confirms every screen constructs, wires
up to the real services, and drives one full workflow pass end to end
through the widgets themselves (not just the service layer, which the
other test files already cover thoroughly).
"""
from __future__ import annotations

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")


@pytest.fixture()
def qapp():
    from PySide6.QtWidgets import QApplication, QMessageBox

    # Modal dialogs would block a headless test run indefinitely.
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)

    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_builds_all_screens(qapp, ctx):
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    assert set(window._screens.keys()) == {
        "dashboard", "data_entry", "transactions", "doctors",
        "investigations", "dc", "reports", "settings",
    }


def test_end_to_end_workflow_through_ui(qapp, ctx):
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)

    window.settings.company_name_edit.setText("Example Diagnostic Center")
    window.settings.address_edit.setPlainText("Main Road")
    window.settings._on_save()
    assert ctx.settings_service.get().company_name == "Example Diagnostic Center"

    doctor = ctx.doctor_service.create_doctor("Dr. A", None)
    investigation = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    window.doctors.refresh()
    window.investigations.refresh()

    window.data_entry.reset_form()
    window.data_entry.patient_name_edit.setText("Rahul Kumar")
    window.data_entry.doctor_combo.select(doctor.id)
    window.data_entry.investigation_combo.select(investigation.id)
    window.data_entry.fee_edit.setValue(1000)
    window.data_entry.discount_edit.setValue(100)
    window.data_entry._on_save()

    txns = ctx.data_capture_service.today_entries()
    assert len(txns) == 1
    assert txns[0].net_fee.compare(txns[0].fee - txns[0].discount) == 0

    window.dashboard.refresh()
    assert window.dashboard.patients_card.value_label.text() == "1"

    window.dc.refresh_doctors()
    window.dc.doctor_combo.setCurrentIndex(0)
    window.dc._on_generate()
    assert window.dc._current_dc.total_patients == 1

    window.reports.refresh_dropdowns()
    window.reports._on_search()
    assert window.reports.table.rowCount() == 1
    window.reports._select(txns[0].id)
    assert "Rahul Kumar" in window.reports.preview_label.text()

    # Deactivate the doctor and confirm historical DC/report still work.
    ctx.doctor_service.deactivate(doctor.id)
    window.dc.refresh_doctors()
    dc_after = ctx.dc_service.generate(doctor.id, date(2020, 1, 1), date(2030, 1, 1))
    assert dc_after.total_patients == 1
    report_after = ctx.report_service.get_report_data(txns[0].id)
    assert report_after.transaction.doctor_name_snapshot == "Dr. A"
