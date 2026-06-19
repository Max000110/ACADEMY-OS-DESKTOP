; AcademyOS Desktop Client Inno Setup Script
; Upgraded for Commercial Windows Distribution (v1.0.1)

#ifndef AppVersion
#define AppVersion "1.0.3"
#endif

[Setup]
AppId={{C7DE8E9D-4952-47BA-9C78-FA6808796ACD}
AppName=AcademyOS Desktop
AppVersion={#AppVersion}
AppPublisher=AcademyOS
AppPublisherURL=https://www.academyos.com
AppSupportURL=https://www.academyos.com/support
AppUpdatesURL=https://www.academyos.com/updates
DefaultDirName={autopf}\AcademyOS
DefaultGroupName=AcademyOS
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=dist
OutputBaseFilename=AcademyOS_Setup_v{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Prevent installation on old unsupported Windows versions (Min OS: Windows 10)
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Standalone Windows Executable
Source: "dist\AcademyOS.exe"; DestDir: "{app}"; Flags: ignoreversion

; Bundle Portable Tesseract OCR engine (Option A)
Source: "tesseract\*"; DestDir: "{app}\tesseract"; Flags: ignoreversion recursesubdirs createallsubdirs

; Default settings template - maps to {%USERPROFILE}\.academyos to align with python home-dir mapping
; Source: "settings.json"; DestDir: "{%USERPROFILE}\.academyos"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\AcademyOS Desktop"; Filename: "{app}\AcademyOS.exe"; IconFilename: "{app}\AcademyOS.exe"
Name: "{group}\{cm:UninstallProgram,AcademyOS Desktop}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AcademyOS Desktop"; Filename: "{app}\AcademyOS.exe"; Tasks: desktopicon; IconFilename: "{app}\AcademyOS.exe"

[Run]
Filename: "{app}\AcademyOS.exe"; Description: "{cm:LaunchProgram,AcademyOS Desktop}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up logs and temporary folders.
; CRITICAL SAFEGUARD: Do not delete backups, settings, or database automatically during uninstall.
; Wiping customer data is high risk. We only remove log files and staging buffers.
Type: files; Name: "{%USERPROFILE}\.academyos\academyos.log"
Type: files; Name: "{%USERPROFILE}\.academyos\settings.json"
