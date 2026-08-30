# Installing Diagnostic Center (End User)

## What you need

Just the installer file: **`DiagnosticCenter-Setup-1.0.0.exe`**.
You do **not** need to install Python, a database, or anything else first —
everything the application needs is bundled inside this installer.

## Steps

1. Copy `DiagnosticCenter-Setup-1.0.0.exe` to the Windows computer.
2. Double-click it to run the installer.
3. Windows may show a security prompt ("Windows protected your PC") because
   the installer is not yet code-signed by a recognized publisher — this is
   normal for a small, internally-distributed application. Click
   **More info**, then **Run anyway**.
4. Follow the setup wizard: choose whether to create a Desktop icon, then
   click **Install**.
5. When installation finishes, leave "Launch Diagnostic Center" checked and
   click **Finish** — the application opens automatically.

## First launch

The very first time the application runs, it silently:

- Creates its data folder at `%LOCALAPPDATA%\DiagnosticCenter\`
- Creates an empty database ready to use
- Opens straight to the Dashboard — no fake sample data is added

Go to **Settings** first to enter your company name/logo/address, then
**Master Data** to add your doctors and investigation types. See
`USER_GUIDE.md` for the full walkthrough.

## Uninstalling

Use **Windows Settings → Apps → Diagnostic Center → Uninstall**, or the
shortcut in the Start Menu folder. Uninstalling **only removes the
application program files** — your database, backups, settings, and logs
in `%LOCALAPPDATA%\DiagnosticCenter\` are left untouched, so reinstalling
later picks up right where you left off.

## Moving to a new computer

1. On the old computer: **Settings → Backup Database**, and copy the
   resulting `.db` file to a USB drive (also copy
   `%LOCALAPPDATA%\DiagnosticCenter\config\settings.json` and the
   `assets\logo.*` file if you want your branding to carry over).
2. Install the application on the new computer as above.
3. On the new computer: **Settings → Restore Database**, and select the
   `.db` file you copied over.

## Status of this installer

This installer is produced by `.github/workflows/build-windows.yml`, which
builds and smoke-tests the application on a genuine Windows machine (a
GitHub Actions Windows runner) before packaging it — see
`docs/TEST_REPORT.md` for exactly what has been verified and what a
release process should confirm before this file is handed to end users.
