#define AppName "Tysm"
#define AppVersion "1.2.0"
[Setup]
AppId={{EAE5C70A-3CC9-4D4F-8D1A-3AFD69D58B43}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Tysm
DefaultDirName={localappdata}\Programs\Tysm
DefaultGroupName=Tysm
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=Tysm_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Tysm.exe
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
; Never overwrite existing user data during updates; preserve it on uninstall.
; User data is now stored in {localappdata}\Tysm and migrated on first launch.
; No bundled database defaults are installed over user data.
Source: "dist\Tysm\*"; DestDir: "{app}"; Excludes: "*.json,*.sqlite3"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Tysm"; Filename: "{app}\Tysm.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Tysm"; Filename: "{app}\Tysm.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Tysm.exe"; Description: "Launch Tysm"; Flags: nowait postinstall skipifsilent
