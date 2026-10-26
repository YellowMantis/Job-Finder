; The Windows installer for Job Finder, built with Inno Setup (https://jrsoftware.org/isinfo.php)
; by tools/build_desktop.py, which passes the version and the folders:
;   ISCC /DAppVersion=0.1.0 /DSourceDir=...\build\Job Finder /DOutputDir=...\build installer.iss
;
; It installs for the current user only (no administrator rights), into
; %LOCALAPPDATA%\Programs\Job Finder, with a Start menu entry, an optional desktop
; shortcut and an uninstaller. Your data (%LOCALAPPDATA%\Job Finder) is a different
; folder: installing a new version or uninstalling never touches it.

#define AppName "Job Finder"
; The name the app keeps while it runs (MUTEX_NAME in desktop.py).
#define MutexName "JobFinderIsRunning"

[Setup]
; The installer's identity. It must never change: it is how a new version
; recognises and replaces an installed older one.
AppId={{A8CE607A-EE01-4392-9D1C-41111B001DA6}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Job Finder
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=Job-Finder-Setup
SetupIconFile={#SourceDir}\..\icon.ico
UninstallDisplayIcon={app}\{#AppName}.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; An update while the app is open: offer to close it first.
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Put a shortcut on the desktop"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Directly in the Start menu's list, not in a folder of its own (one shortcut only).
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "Open Job Finder now"; Flags: nowait postinstall skipifsilent
; After a quiet update (the app's Update button runs this installer with
; /SILENT), open Job Finder again by itself.
Filename: "{app}\{#AppName}.exe"; Flags: nowait; Check: WizardSilent

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
    if SuppressibleMsgBox('Job Finder is open. Close it, then click OK to continue.',
        mbInformation, MB_OKCANCEL, IDCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  Result := True;
end;
