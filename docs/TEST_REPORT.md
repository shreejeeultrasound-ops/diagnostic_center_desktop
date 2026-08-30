# Test / Acceptance Report

## Environment this was built and tested in

A Linux container with Python 3.12, no display server (Qt runs via the
`offscreen` platform plugin for headless testing), and no Windows machine.
Network access was limited to package registries (PyPI, npm, GitHub) — no
general internet access. This shaped what could be verified directly here
versus what requires a Windows run (see §4 below).

## 1. Automated test suite

`pytest tests/ -v` — **39 / 39 passed**, run against the real SQLite
database and PySide6 UI (headless), not mocks.

| File | Covers |
|---|---|
| `test_doctor_service.py` | Doctor creation, validation, activate/deactivate, historical display after deactivation, editing a historical transaction for a now-inactive doctor |
| `test_investigation_service.py` | Investigation creation, validation, activate/deactivate, default-fee update |
| `test_data_capture_service.py` | Net-fee calculation, all validation rules (negative fee/discount, discount > fee, mandatory name, invalid age, doctor/investigation required), **historical fee preservation when the master default fee changes**, search by name/mobile, today's entries |
| `test_dc_service.py` | Doctor filtering, date-range filtering, aggregation (gross/discount/net), doctors are not mixed together, zero-result handling, inverted date range rejected |
| `test_report_service.py` | Report data assembly, PDF generation for both documents, **automated check that the Customer Report PDF contains no clinical terminology** (extracts and scans the actual PDF text) |
| `test_backup_service.py` | Backup creation & integrity, restore brings back exact prior state, corrupt/missing backup files rejected without touching the live database, financial values survive a backup/restore round trip |
| `test_ui_smoke.py` | Every PySide6 screen constructs and wires to the real services; a full workflow (settings → doctor/investigation → data entry → dashboard → DC → report preview → doctor deactivation) driven through the actual widgets, headless |

## 2. Manual acceptance-scenario run (build brief §31, steps 1–10)

Executed as a standalone script against the real service layer (not the
pytest suite, to mirror the brief's scenario as literally as possible) —
full output captured, every assertion passed:

- **Step 1–3**: company configured, 2 doctors + 2 investigation types added.
- **Step 4**: two transactions captured; net fee correctly computed
  (₹1000 − ₹100 = ₹900).
- **Step 5**: DC generated for Dr. A, 2 patients, gross ₹1800 / discount
  ₹100 / net ₹1700 — a real PDF was written.
- **Step 6**: Customer Investigation Report generated for Rahul Kumar; the
  actual PDF text was extracted and confirmed to contain every required
  field (company name, patient name, father's name, mobile, doctor,
  investigation, age) **and none** of: Impression, Diagnosis, Findings,
  Observation, Clinical (case-insensitive).
- **Step 7**: USG Abdomen's default fee changed 1000 → 1200; Rahul's
  stored transaction was re-read and confirmed **unchanged**
  (fee=1000.00, discount=100.00, net=900.00).
- **Step 8**: Dr. A deactivated; confirmed no longer in the active-doctor
  list, while the DC for Dr. A and Rahul's report both still generated
  correctly with "Dr. A" displayed.
- **Step 9**: backup file created (53 KB) and passed `PRAGMA
  integrity_check`.
- **Step 10**: an unwanted doctor was added (simulating a mistake), then
  restore was run — the doctor list came back to exactly the pre-mistake
  two doctors.

## 3. Packaging — what was verified here vs. what still needs Windows

**PyInstaller does not cross-compile.** Building on this Linux container
produces a Linux ELF binary, not a Windows `.exe`. What *was* done here as
a proxy check, to catch real packaging bugs before a Windows run:

- Ran `pyinstaller packaging/diagnostic_center.spec` on Linux — completed
  with only expected warnings (missing optional DB driver hidden-imports
  for MySQL/Postgres/pysqlite2, which this app doesn't use; and missing
  `libxcb-cursor`, a Linux-only X11 dependency irrelevant to Windows).
- Confirmed the bundled font files (`app/assets/fonts/*.ttf`, needed for
  the ₹ symbol in PDFs) were correctly copied into the packaged output.
- **Launched the packaged binary itself** (not just the dev-mode script)
  headlessly, and confirmed it created its `%LOCALAPPDATA%`-equivalent
  data directory structure and initialized the SQLite schema
  (`doctors`, `investigation_types`, `patient_investigations`,
  `schema_version` tables all present) on first run, exactly like the
  dev-mode run does.

**What has NOT been done, and must be done before shipping `Setup.exe` to
the diagnostic center**: an actual Windows build, Windows smoke-test, and
Windows-based Inno Setup compilation. `.github/workflows/build-windows.yml`
does all three automatically on a GitHub Actions Windows runner (build →
run the full pytest suite on Windows → launch the packaged `.exe` and
confirm it initializes its database → compile the installer with Inno
Setup) and uploads the resulting `Setup.exe` as a downloadable artifact.
Running that workflow once (or following `packaging/BUILD_WINDOWS.md` on
a real Windows machine) is the remaining step to have a genuinely
Windows-tested installer in hand — this report does not claim that step
has happened yet, in line with the build brief's explicit instruction not
to claim an installer works until it has actually been produced and
tested.

## 4. UAT checklist (build brief §36 — "Phase 6")

Use this on the actual Windows build once produced:

- [ ] Installer runs on a clean Windows machine (no Python/dev tools
      installed) and completes without error.
- [ ] Desktop/Start Menu shortcuts are created and launch the app.
- [ ] First launch shows an empty Dashboard — no fake data.
- [ ] Company settings (name, logo, address, phone) can be saved and
      appear on a generated report/DC.
- [ ] A doctor and an investigation type can be added.
- [ ] A patient entry can be captured, appears in Today's Patients count.
- [ ] A DC can be generated, previewed, saved as PDF, and printed.
- [ ] A Customer Investigation Report can be generated, previewed, saved
      as PDF, and printed — and visually confirmed to contain no clinical
      content.
- [ ] Changing an investigation type's default fee does not alter any
      already-saved transaction.
- [ ] Deactivating a doctor removes them from new-entry dropdowns but
      historical entries/DC/report referencing them still work.
- [ ] Backup produces a `.db` file; Restore from that file recovers data
      correctly after a simulated mistake.
- [ ] Closing and reopening the application preserves all data (confirms
      the app-data directory, not a temp location, is being used).
- [ ] Uninstalling the application leaves `%LOCALAPPDATA%\DiagnosticCenter`
      and its contents intact.
