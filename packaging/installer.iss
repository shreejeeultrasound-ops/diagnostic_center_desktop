; Inno Setup script for the Diagnostic Center desktop application.
;
; Compiles the PyInstaller onedir build (dist/DiagnosticCenter/) into a
; single Setup.exe that a non-technical Windows user can run. Must be
; compiled with the Inno Setup Compiler (ISCC.exe) ON WINDOWS - see
; packaging/BUILD_WINDOWS.md, or let .github/workflows/build-windows.yml
; do it automatically on a Windows GitHub Actions runner.
;
; Expects dist/DiagnosticCenter/DiagnosticCenter.exe (and its
; supporting _internal folder) to already exist, i.e. run PyInstaller
; first: pyinstaller packaging/diagnostic_center.spec --noconfirm --clean

#define MyAppName "Diagnostic Center"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Diagnostic Center"
#define MyAppExeName "DiagnosticCenter.exe"

[Setup]
AppId={{6B2E6F0D-6B3B-4C2E-9B34-2D9F6D9B1A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-machine install into Program Files; the application itself never
; writes business data next to the executable (see
; app/configuration/paths.py) so this location can safely be
; non-writable by the ordinary user account that runs the app day to day.
PrivilegesRequired=admin
OutputDir=..\dist_installer
OutputBaseFilename=DiagnosticCenter-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; Uninstalling must never touch the user's business data, which lives
; under %LOCALAPPDATA%\DiagnosticCenter, not under {app}. We deliberately
; do NOT add a [UninstallDelete] entry for the data directory.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\DiagnosticCenter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
