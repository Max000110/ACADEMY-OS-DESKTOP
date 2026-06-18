; AcademyOS Desktop Client Inno Setup Script
; This script compiles the PyInstaller-bundled executable into a single Windows installer setup.

[Setup]
AppId={{C7DE8E9D-4952-47BA-9C78-FA6808796ACD}
AppName=AcademyOS Desktop
AppVersion=1.0.0
AppPublisher=AcademyOS
AppPublisherURL=https://www.academyos.com
AppSupportURL=https://www.academyos.com/support
AppUpdatesURL=https://www.academyos.com/updates
DefaultDirName={autopf}\AcademyOS
DefaultGroupName=AcademyOS
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
; Output options
OutputDir=dist
OutputBaseFilename=AcademyOS_Setup_v1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AcademyOS.exe"; DestDir: "{app}"; Flags: ignoreversion
; Default configuration structures (if packaging folders)
Source: "settings.json"; DestDir: "{userappdata}\AcademyOS"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\AcademyOS"; Filename: "{app}\AcademyOS.exe"
Name: "{group}\{cm:UninstallProgram,AcademyOS}"; Filename: "{uninstval}"
Name: "{autodesktop}\AcademyOS"; Filename: "{app}\AcademyOS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AcademyOS.exe"; Description: "{cm:LaunchProgram,AcademyOS}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\AcademyOS\backups"
Type: files; Name: "{userappdata}\AcademyOS\settings.json"
Type: files; Name: "{userappdata}\AcademyOS\academyos.db"
Type: files; Name: "{userappdata}\AcademyOS\academyos.log"
