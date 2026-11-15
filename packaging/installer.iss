#define AppName "DownloaderVideo"
#define AppVersion "1.0.0"
[Setup]
AppId={{2CF1EB77-B15B-4A57-A9C3-C192CCEC5768}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=DownloaderVideo
DefaultDirName={localappdata}\Programs\DownloaderVideo
DefaultGroupName=DownloaderVideo
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=DownloaderVideo-1.0.0-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\DownloaderVideo.exe
CloseApplications=yes
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked
[Files]
Source: "..\dist\DownloaderVideo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\DownloaderVideo"; Filename: "{app}\DownloaderVideo.exe"
Name: "{autodesktop}\DownloaderVideo"; Filename: "{app}\DownloaderVideo.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\DownloaderVideo.exe"; Description: "Abrir DownloaderVideo"; Flags: nowait postinstall skipifsilent
; User preferences, database and downloaded media are intentionally preserved.
