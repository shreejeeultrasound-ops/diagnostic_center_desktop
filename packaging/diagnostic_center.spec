# PyInstaller spec for the Diagnostic Center desktop application.
#
# IMPORTANT: PyInstaller does not cross-compile. Running this spec on
# Linux produces a Linux ELF binary; running it on Windows produces a
# genuine Windows .exe. This project's CI workflow
# (.github/workflows/build-windows.yml) runs PyInstaller on a
# windows-latest GitHub Actions runner specifically so a real, testable
# Windows build comes out the other end - see packaging/BUILD_WINDOWS.md
# for how to do the same thing on a local Windows machine.
#
# Usage (from the repository root, inside an activated venv with
# requirements-dev.txt installed):
#     pyinstaller packaging/diagnostic_center.spec --noconfirm --clean
#
# Output: dist/DiagnosticCenter/DiagnosticCenter.exe (plus its
# supporting files in the same folder - this is a "one-folder" build,
# which starts faster and is easier to troubleshoot than a single .exe;
# the Inno Setup installer (packaging/installer.iss) wraps this whole
# folder into a normal Setup.exe for end users).

import sys
from pathlib import Path

block_cipher = None

# When invoked as `pyinstaller packaging/diagnostic_center.spec`, PyInstaller
# sets SPECPATH to the folder containing this file.
PROJECT_ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(PROJECT_ROOT / "app" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "app" / "assets"), "app/assets"),
    ],
    hiddenimports=[
        "sqlalchemy.dialects.sqlite",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DiagnosticCenter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app - no console popup for the end user
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # add an .ico path here once branding assets are available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DiagnosticCenter",
)
