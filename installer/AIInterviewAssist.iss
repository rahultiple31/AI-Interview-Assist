#define MyAppName "AI Interview Assist"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Local"
#define MyAppExeName "AIInterviewAssist.exe"

[Setup]
AppId={{76A1A046-0D2D-4C3E-B040-BCFE7DE8892D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AI Interview Assist
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\final-product
OutputBaseFilename=AI-Interview-Assist-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\AIInterviewAssist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ProductName: String;
begin
  Result := True;
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'ProductName', ProductName) then
  begin
    if Pos('Windows Server', ProductName) > 0 then
    begin
      MsgBox('{#MyAppName} installs only on Windows 10 and Windows 11 client editions.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
