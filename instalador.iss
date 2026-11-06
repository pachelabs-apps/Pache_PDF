; Instalador de Ozone PDF 1.2.0 (Inno Setup 6.3 o posterior)
; No hace falta abrir este archivo: CREAR_INSTALADOR.bat lo compila solo.
; Si hay certificado configurado, el .bat define FIRMAR y la herramienta "firma"
; (signtool /sha1 <huella>), y Inno firma el instalador y el desinstalador.

#define AppName "Ozone PDF"
#define AppVersion "1.2.0"

[Setup]
AppId={{5B3E59AC-D9F8-43C8-ABA7-AE1591EFB8BC}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Pache Labs (Nicolás Emanuel Pacheco)
VersionInfoVersion=1.2.0.0
VersionInfoProductName={#AppName}
VersionInfoDescription=Instalador de {#AppName} {#AppVersion}
; Programa de 64 bits: se instala en "Program Files" (no en "Program Files (x86)")
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Siempre en la carpeta por defecto: la regla de firewall y la detección de despliegue usan esa ruta
DisableDirPage=yes
; Se instala para todos los usuarios en "Program Files" (pide permisos de administrador).
; Así la regla de firewall que crea el instalador cubre siempre la ruta del programa.
; /CURRENTUSER por línea de comandos instala solo para el usuario, SIN regla de firewall
; (no recomendado).
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
OutputDir=instalador
OutputBaseFilename=Instalar_Ozone_PDF_{#AppVersion}
SetupIconFile=assets\icono.ico
UninstallDisplayIcon={app}\{#AppName}.exe
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Licencia del programa (GNU AGPL-3.0), se muestra en el asistente
InfoBeforeFile=AVISO_USO.txt
#ifdef FIRMAR
SignTool=firma
SignedUninstaller=yes
#endif
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "AVISO_USO.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENCIAS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENCIAS_TERCEROS.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Acceso directo en el escritorio y en el menú Inicio (siempre)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppName}.exe"

[Run]
; Tercera capa de protección: el firewall de Windows bloquea toda salida a red del programa.
; Primero se borra una regla anterior (actualizaciones) y después se crea la nueva.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Ozone PDF - sin red"""; Flags: runhidden waituntilterminated; Check: IsAdminInstallMode; StatusMsg: "Configurando el firewall..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Ozone PDF - sin red"" dir=out action=block enable=yes program=""{app}\{#AppName}.exe"""; Flags: runhidden waituntilterminated; Check: IsAdminInstallMode; StatusMsg: "Configurando el firewall..."
Filename: "{app}\{#AppName}.exe"; Description: "Abrir {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Ozone PDF - sin red"""; Flags: runhidden waituntilterminated; RunOnceId: "QuitarReglaFirewall"

[Code]
// Si Ozone PDF ya está instalado con el instalador .msi (GPO), no se instala encima:
// son dos instaladores distintos y quedarían dos instalaciones mezcladas.
function InitializeSetup(): Boolean;
begin
  Result := True;
  if RegValueExists(HKLM64, 'Software\Ozone PDF', 'AccesoMenu') then
  begin
    MsgBox('Ozone PDF ya está instalado con el instalador .msi (instalación por GPO).' + #13#10 + #13#10 +
           'Las actualizaciones de esa instalación se hacen con el .msi. Si querés usar este ' +
           'instalador, primero desinstalá Ozone PDF desde Configuración > Aplicaciones.',
           mbInformation, MB_OK);
    Result := False;
  end;
end;
