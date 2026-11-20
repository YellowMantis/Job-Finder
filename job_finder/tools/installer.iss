; The Windows installer for Veri, built with Inno Setup (https://jrsoftware.org/isinfo.php)
; by tools/build_desktop.py, which passes the version and the folders:
;   ISCC /DAppVersion=0.1.0 /DSourceDir=...\build\Job Finder /DOutputDir=...\build installer.iss
;
; It installs for the current user only (no administrator rights), into
; %LOCALAPPDATA%\Programs\Job Finder, with a Start menu entry, an optional desktop
; shortcut and an uninstaller. Your data (%LOCALAPPDATA%\Job Finder) is a different
; folder: installing a new version or uninstalling never touches it.

; The name people see: the installer, the Start menu, Apps & features.
#define AppName "Veri"
; The program's folder and file keep the app's first name, Job Finder: an
; update from an older version replaces the same files instead of putting a
; second copy beside them.
#define ProgramName "Job Finder"
; The name the app keeps while it runs (MUTEX_NAME in desktop.py).
#define MutexName "JobFinderIsRunning"

[Setup]
; The installer's identity. It must never change: it is how a new version
; recognises and replaces an installed older one.
AppId={{A8CE607A-EE01-4392-9D1C-41111B001DA6}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=YellowMantis
DefaultDirName={localappdata}\Programs\{#ProgramName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=Job-Finder-Setup
SetupIconFile={#SourceDir}\..\icon.ico
UninstallDisplayIcon={app}\{#ProgramName}.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; An update while the app is open: offer to close it first.
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Put a shortcut on the desktop"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; The shortcuts from before the app was renamed (a new version adds "Veri" ones).
Type: files; Name: "{autoprograms}\Job Finder.lnk"
Type: files; Name: "{userdesktop}\Job Finder.lnk"

[Icons]
; Directly in the Start menu's list, not in a folder of its own (one shortcut only).
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#ProgramName}.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#ProgramName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ProgramName}.exe"; Description: "Open Veri now"; Flags: nowait postinstall skipifsilent
; After a quiet update (the app's Update button runs this installer with
; /SILENT), open Veri again by itself.
Filename: "{app}\{#ProgramName}.exe"; Flags: nowait; Check: WizardSilent

[Code]
// Windows keeps a running program's files locked, so the app can't be
// replaced while it's open. The app is closing itself when its Update button
// started this installer, so wait a few seconds; if it's still open after
// that, ask for it to be closed rather than fail halfway through the files.
function InitializeSetup(): Boolean;
var
  Waited: Integer;
begin
  Waited := 0;
  while CheckForMutexes('{#MutexName}') and (Waited < 10000) do
  begin
    Sleep(250);
    Waited := Waited + 250;
  end;
  while CheckForMutexes('{#MutexName}') do
    if SuppressibleMsgBox('Veri is open. Close it, then click OK to continue.',
        mbInformation, MB_OKCANCEL, IDCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  Result := True;
end;
