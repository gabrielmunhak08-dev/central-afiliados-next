[Setup]
AppId={{D9B6A2E1-7F45-4D7A-9D1B-CA7F1D2B9E10}
AppName=Central de Afiliados
AppVersion=1.0.0
AppPublisher=Central de Afiliados
DefaultDirName={autopf}\Central de Afiliados
DefaultGroupName=Central de Afiliados
OutputDir=output
OutputBaseFilename=CentralDeAfiliados-Instalador
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\CentralDeAfiliados.exe

[Files]
Source: "..\dist\CentralDeAfiliados\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Central de Afiliados"; Filename: "{app}\CentralDeAfiliados.exe"
Name: "{autodesktop}\Central de Afiliados"; Filename: "{app}\CentralDeAfiliados.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
