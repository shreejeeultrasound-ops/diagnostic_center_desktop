# Diagnostic Center — Desktop Edition

A small, offline Windows desktop application for a diagnostic/ultrasound
center covering three capabilities: **Basic Data Capture**, **DC
Generation**, and the **Customer Investigation Report**.

This is the desktop-only package (PySide6 UI, PyInstaller/Inno Setup
Windows packaging). For the internet-hosted version, see the separate
web edition package instead.

- End users: `docs/INSTALL_INSTRUCTIONS.md` and `docs/USER_GUIDE.md`.
- Developers: `docs/ARCHITECTURE.md`, `docs/ASSUMPTIONS.md`,
  `packaging/BUILD_WINDOWS.md`.
- What has actually been tested: `docs/TEST_REPORT.md`.

## Quick start (development, any OS)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

pytest tests/ -v                  # automated tests
python -m app.main                 # run the app (needs a display; use
                                    # QT_QPA_PLATFORM=offscreen for headless)
```

## Building the Windows installer

PyInstaller does not cross-compile — a real Windows `.exe` must be built
*on Windows*. Either:

- push this to GitHub and let `.github/workflows/build-windows.yml`
  build, test, and package it on a Windows runner automatically, or
- follow `packaging/BUILD_WINDOWS.md` on a real Windows machine.

## Project layout

```
app/            Application source (domain / database / repositories /
                services / reporting / configuration / ui)
tests/          Automated tests (pytest)
packaging/      PyInstaller spec, Inno Setup installer script, Windows
                build instructions
.github/workflows/  CI that builds a real, tested Windows installer
docs/           Architecture, user guide, install instructions, test
                report, documented assumptions
```

## Note on shared code

`app/services/auth_service.py`, `app/domain/user.py`,
`app/repositories/user_repository.py`, and the `users` table in
`app/database/models.py` exist here too, unused by this edition's UI.
They were added for the separate web edition (which needs login
accounts) and left in place rather than surgically removed from the
shared business-logic layer, since removing them would mean
maintaining two divergent copies of `app/database/models.py` and
related files. They add one unused table to the database and no
runtime behavior change for the desktop app.
