@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
rem Arma el paquete MSIX de Ozone PDF para publicarlo en la Microsoft Store.
rem Usa el programa que ya armo y probo CREAR_INSTALADOR.bat (carpeta dist\Ozone PDF):
rem ejecuta primero CREAR_INSTALADOR.bat. Necesita el Windows SDK (MakeAppx y MakePri).
rem La Store firma el paquete al publicarlo: no hace falta certificado.

set "VERSION="
for /f "tokens=2 delims==" %%v in ('findstr /r /b /c:"APP_VERSION *=" app.py') do set "VERSION=%%~v"
set "VERSION=!VERSION: =!"
set "VERSION=!VERSION:"=!"
if not defined VERSION (
  echo  No se pudo leer la version de app.py.
  goto fin_error
)
title Crear paquete MSIX - Ozone PDF %VERSION%
echo.
echo  ==========================================
echo     Paquete MSIX de Ozone PDF %VERSION%
echo  ==========================================
echo.

if not exist "dist\Ozone PDF\Ozone PDF.exe" (
  echo  Falta el programa compilado. Ejecuta primero CREAR_INSTALADOR.bat.
  goto fin_error
)

rem ---------- 1. Identidad de la Store ----------
rem msix_identidad.txt: linea 1 = Package/Identity/Name, linea 2 = Package/Identity/Publisher
rem (Partner Center > tu app > Administracion de productos > Identidad del producto)
if not exist "msix_identidad.txt" (
  > "msix_identidad.txt" echo PEGAR-ACA-Package-Identity-Name
  >> "msix_identidad.txt" echo CN=PEGAR-ACA-Package-Identity-Publisher
  echo  Se creo msix_identidad.txt. Abrilo y pega los dos datos que muestra Partner Center
  echo  en "Identidad del producto" ^(Package/Identity/Name y Package/Identity/Publisher^).
  echo  Despues volve a ejecutar este script.
  goto fin_error
)
set "NOMBRE="
set "EDITOR="
for /f "usebackq delims=" %%L in ("msix_identidad.txt") do (
  if not defined NOMBRE (set "NOMBRE=%%L") else if not defined EDITOR set "EDITOR=%%L"
)
echo !NOMBRE!!EDITOR! | findstr /c:"PEGAR-ACA" >nul
if not errorlevel 1 (
  echo  Completa msix_identidad.txt con los datos de Partner Center y volve a ejecutar.
  goto fin_error
)
echo  [1/4] Identidad: !NOMBRE!

rem ---------- 2. Windows SDK ----------
set "SDKBIN="
for /d %%D in ("%ProgramFiles(x86)%\Windows Kits\10\bin\10.*") do (
  if exist "%%D\x64\makeappx.exe" set "SDKBIN=%%D\x64"
)
if not defined SDKBIN (
  echo  No se encontro MakeAppx. Instala el Windows SDK:
  echo  https://developer.microsoft.com/windows/downloads/windows-sdk/
  echo  ^(alcanza con la opcion "Windows SDK Signing Tools for Desktop Apps" y
  echo  "Windows SDK for UWP Managed Apps"^).
  goto fin_error
)
echo  [2/4] Windows SDK: !SDKBIN!

rem ---------- 3. Carpeta del paquete ----------
echo  [3/4] Preparando los archivos...
set "PAQ=build\msix"
if exist "%PAQ%" rmdir /s /q "%PAQ%"
mkdir "%PAQ%"
robocopy "dist\Ozone PDF" "%PAQ%" /e /nfl /ndl /njh /njs /np >nul
if errorlevel 8 goto error
robocopy "msix\Assets" "%PAQ%\Assets" /e /nfl /ndl /njh /njs /np >nul
if errorlevel 8 goto error
set "VERSION4=%VERSION%.0"
powershell -NoProfile -Command "$m = Get-Content -Raw -Encoding UTF8 'msix\AppxManifest.xml'; $m = $m.Replace('$NOMBRE$', $env:NOMBRE).Replace('$EDITOR$', $env:EDITOR).Replace('$VERSION$', $env:VERSION4); [IO.File]::WriteAllText((Join-Path $PWD '%PAQ%\AppxManifest.xml'), $m, (New-Object Text.UTF8Encoding $false))"
if errorlevel 1 goto error
rem Recursos de los iconos (tamanos de la barra de tareas y del menu Inicio)
"!SDKBIN!\makepri.exe" createconfig /cf "build\priconfig.xml" /dq es-AR /o >nul
if errorlevel 1 goto error
"!SDKBIN!\makepri.exe" new /pr "%PAQ%" /cf "build\priconfig.xml" /of "%PAQ%\resources.pri" /o >nul
if errorlevel 1 goto error

rem ---------- 4. Empaquetar ----------
echo  [4/4] Generando el paquete...
if not exist "instalador" mkdir "instalador"
set "MSIX=instalador\Ozone_PDF_%VERSION%.msix"
"!SDKBIN!\makeappx.exe" pack /d "%PAQ%" /p "!MSIX!" /o
if errorlevel 1 goto error

echo.
echo  ==========================================
echo     LISTO: !MSIX!
echo  ==========================================
echo.
echo  Subilo en Partner Center ^> tu app ^> Envio ^> Paquetes.
echo  Para probarlo antes en esta PC ^(requiere "Modo de desarrollador" activado en
echo  Configuracion ^> Sistema ^> Para programadores^):
echo    powershell Add-AppxPackage -Register "%CD%\%PAQ%\AppxManifest.xml"
echo  y para quitarlo:  powershell "Get-AppxPackage *OzonePDF* ^| Remove-AppxPackage"
echo.
pause
exit /b 0

:error
echo.
echo  Hubo un error al armar el paquete. Revisa los mensajes de arriba.
:fin_error
echo.
pause
exit /b 1
