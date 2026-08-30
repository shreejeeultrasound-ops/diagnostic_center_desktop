# Building the Windows Installer (Developer Instructions)

This produces the real, user-facing `Setup.exe`. It must be run **on Windows**
— PyInstaller does not cross-compile, so running it on Linux/macOS produces a
Linux/macOS binary, not a Windows one. If you don't have a Windows machine
handy, push to GitHub and let `.github/workflows/build-windows.yml` build it
for you on a Windows runner (see the bottom of this file).

## Prerequisites (on the Windows build machine)

- Windows 10 or 11
- [Python 3.12](https://www.python.org/downloads/) (check "Add Python to PATH"
  during install)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (free) — used to build the
  final `Setup.exe` installer
- Git (to clone the repository) — or just copy the project folder over

None of this is needed by the **end user** — only by whoever is building the
installer.

## Steps

Open PowerShell in the project's root folder (the one containing
`requirements.txt`) and run:

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Run the automated test suite - confirm everything passes on Windows
pytest tests/ -v

# 4. Build the application with PyInstaller
pyinstaller packaging\diagnostic_center.spec --noconfirm --clean

# 5. Smoke-test the packaged .exe launches correctly
dist\DiagnosticCenter\DiagnosticCenter.exe
# (close the window once you see it open correctly)

# 6. Compile the installer with Inno Setup
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

The finished installer appears at:

```
dist_installer\DiagnosticCenter-Setup-1.0.0.exe
```

That single file is what you hand to the diagnostic center — see
`docs/INSTALL_INSTRUCTIONS.md` for what happens when they run it.

## Building automatically via GitHub Actions (no Windows machine needed)

Push this repository to GitHub (or a mirror) and the workflow at
`.github/workflows/build-windows.yml` will:

1. Spin up a Windows GitHub Actions runner.
2. Install dependencies and run the full automated test suite **on Windows**.
3. Build the application with PyInstaller.
4. Launch the packaged `.exe` as a smoke test and confirm it created its
   database on first run.
5. Compile the Inno Setup installer.
6. Upload the finished `Setup.exe` (and the raw application folder) as
   downloadable build artifacts on the workflow run.

This is the recommended path if you are iterating from a non-Windows
development machine, and is the only way this project's Windows packaging
has actually been exercised so far — see `docs/TEST_REPORT.md` for exactly
what has and has not been verified.
