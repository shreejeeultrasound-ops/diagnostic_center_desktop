# Architecture — Diagnostic Center Desktop Application

## 1. Technology choice

| Layer          | Choice                          | Why |
|-----------------|----------------------------------|-----|
| UI               | PySide6 (Qt for Python)          | Native-feeling Windows desktop widgets, mature, good keyboard/tab-order support, LGPL (no licensing cost for a small business). |
| Persistence      | SQLite via SQLAlchemy 2.0        | Zero-config, single-file, offline, transactional, well suited to a single small-business desktop app. SQLAlchemy gives a typed ORM layer and keeps a documented path to Postgres/MySQL later without a rewrite, without adding a server dependency now. |
| PDF generation   | ReportLab                        | Pure-Python, no external binary dependency (unlike wkhtmltopdf/LibreOffice), full control over layout for both the DC and the Customer Report from one shared toolkit (`app/reporting/pdf_common.py`). |
| Packaging        | PyInstaller (onedir) + Inno Setup | PyInstaller freezes the Python app into a self-contained folder (no Python/pip needed on the target machine); Inno Setup wraps that into a normal Windows `Setup.exe` with Start Menu/Desktop shortcuts. Both are free, widely used, and require no license. |

This matches the build brief's suggested default stack; nothing in the
(non-existent, greenfield) repository indicated a different stack was
required, so the default was used as-is.

## 2. Layered structure

```
app/
├── domain/          Pure business rules & validation (no DB, no Qt)
├── database/         SQLAlchemy ORM models + engine/session setup
├── repositories/      Translate between ORM rows and domain dataclasses
├── services/          Business use-cases; the ONLY place a UI screen calls into
├── reporting/          PDF generation (DC + Customer Report) + currency/date formatting
├── configuration/      App-data paths, company settings (branding), bundled resource paths
├── ui/                PySide6 screens - call services only, never touch the DB directly
├── context.py         Composition root: wires paths → DB → services → (later) UI
└── main.py            Entry point: first-run init, global error handling
```

**Dependency direction is one-way**: `ui → services → repositories → database`,
and `domain` has no dependency on anything else. A service is the only thing a
UI screen is allowed to call; a UI screen never imports SQLAlchemy or opens a
session itself. This is what keeps DC generation and Customer Report
generation both reading from the *same* `TransactionRepository` instead of
each screen inventing its own data access — see build brief section 20.

## 3. Data model

```
doctors                    investigation_types
--------                   -------------------
id (PK)                    id (PK)
name                        name
mobile                       default_fee
status (ACTIVE/INACTIVE)      status (ACTIVE/INACTIVE)
created_at / updated_at        created_at / updated_at
   |                                |
   | FK doctor_id                    | FK investigation_type_id
   v                                v
patient_investigations
-----------------------
id (PK)
transaction_date
patient_name, address, mobile, age, father_husband_name
doctor_id (FK) + doctor_name_snapshot
investigation_type_id (FK) + investigation_name_snapshot
fee, discount, net_fee
created_at / updated_at
```

**Design decision — snapshot columns**: `doctor_name_snapshot` and
`investigation_name_snapshot` duplicate the master's name onto every
transaction at the moment it is captured, in addition to the foreign key.
This was not explicitly requested for names (only for `default_fee` vs.
captured `fee`), but the build brief states as a general principle that
*"historical transaction data must remain stable even if master data
changes later"* (§1, §18), and Doctor/Investigation names are editable
(§5.1/§5.2 "Edit" capability). Without the snapshot, renaming a doctor
would silently rewrite how every old report/DC displays that doctor. The
FK is kept alongside the snapshot for filtering, joins, and reaching
current status. **This is a documented assumption, not a directly stated
requirement — it is easy to remove if it turns out to be unwanted.**

Financial values (`fee`, `discount`, `net_fee`) are always taken from the
transaction row itself, never recomputed from the current
`investigation_types.default_fee` — this is what makes the "change the
master fee, old transactions stay the same" acceptance scenario (build
brief §31 step 7) work, and it is covered by an automated test
(`tests/test_data_capture_service.py::test_historical_fee_preserved_when_master_default_fee_changes`).

Doctors and investigation types are never physically deleted — only
`status` flips between `ACTIVE`/`INACTIVE` — because a `DELETE` would
either orphan historical transactions or (if `ON DELETE CASCADE` were
used) destroy them, both of which contradict the build brief directly.

## 4. Application data location (Windows)

Business data is kept **out of** the install folder, per build brief §27:

```
%LOCALAPPDATA%\DiagnosticCenter\
├── database\diagnostic_center.db      (SQLite, WAL mode)
├── config\settings.json               (company branding)
├── assets\logo.png                    (imported logo copy)
├── backups\backup_YYYYMMDD_HHMMSS.db
└── logs\app.log (rotating, 5 x 2 MB)
```

The installed application binaries live under `Program Files\Diagnostic
Center\` and are never written to at runtime, so an application update
(re-running the installer with a newer build) cannot touch business data.

## 5. Data safety

- SQLite runs in **WAL mode** with `synchronous=FULL` and foreign keys
  enforced, for durability and referential integrity.
- Every write goes through `session_scope()` (`app/database/session.py`),
  which commits on success and **rolls back** on any exception — no
  half-written record can ever be persisted.
- **Backup** uses SQLite's native `sqlite3.Connection.backup()` API (not a
  raw file copy), which produces a consistent snapshot even while the
  application has the database open, and is verified with
  `PRAGMA integrity_check` before being reported as successful.
- **Restore** verifies the incoming file's integrity *before* touching
  anything, keeps a safety copy of the current database until the new one
  has been proven to open cleanly, disposes the live SQLAlchemy
  connection pool and clears any WAL/SHM sidecar files so no stale cached
  data can "leak back in", and rolls back to the safety copy automatically
  if anything goes wrong.

## 6. Reports (DC & Customer Investigation Report)

Both PDFs are generated by `app/reporting/dc_pdf.py` and
`app/reporting/customer_report_pdf.py`, sharing layout building blocks
(`pdf_common.py`) and both reading through the *same* transaction
repository as Data Capture — there is no separate storage mechanism for
either document (build brief §20).

A bundled DejaVu Sans TTF (`app/assets/fonts/`, public-domain, redistributable)
is registered with ReportLab so the ₹ (Indian Rupee) glyph renders
correctly on every machine regardless of what fonts happen to be
installed on it — the built-in PDF core fonts (Helvetica etc.) do not
include this character.

The Customer Investigation Report deliberately contains **no clinical
content** — no findings, diagnosis, impression, or measurements — per
build brief §10. This is verified by an automated test that extracts the
generated PDF's text and asserts none of those terms appear
(`tests/test_report_service.py::test_customer_report_pdf_has_no_clinical_terms`).

"Print" is implemented by generating the PDF and opening it with the
operating system's default PDF viewer (`QDesktopServices.openUrl`), where
the user prints via the normal OS print dialog. This was a deliberate
simplification: building and maintaining a second, native
`QPrinter`-based rendering pipeline that duplicates the ReportLab layout
would violate the "single authoritative implementation" principle
(build brief §20) and risks the two renderings drifting apart over
time, for no real benefit in a small-business desktop app where every
Windows machine already has a PDF viewer capable of printing.

## 7. Known limitation: Windows packaging has not been run on Windows here

This project was built in a Linux sandbox with no Windows machine
available. See `docs/TEST_REPORT.md` for exactly what has been verified
(all business logic and the PySide6 UI, run headlessly on Linux; the
PyInstaller spec validated by producing a working *Linux* binary as a
proxy) versus what still needs a real Windows run
(`.github/workflows/build-windows.yml` or `packaging/BUILD_WINDOWS.md`)
before the `Setup.exe` can be handed to the diagnostic center.
