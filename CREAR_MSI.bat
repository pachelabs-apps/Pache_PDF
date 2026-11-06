@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
rem Arma el instalador .msi de Ozone PDF (para instalar por GPO) con WiX Toolset 3.
rem Usa el programa que ya armo y probo CREAR_INSTALADOR.bat (carpeta dist\Ozone PDF):
rem ejecuta primero CREAR_INSTALADOR.bat. Si hay certificado configurado, el programa
rem ya viene firmado y este script firma tambien el .msi.

rem La version se toma de app.py (APP_VERSION), para no tener que cambiarla en otro lugar
set "VERSION="
for /f "tokens=2 delims==" %%v in ('findstr /r /b /c:"APP_VERSION *=" app.py') do set "VERSION=%%~v"
set "VERSION=!VERSION: =!"
set "VERSION=!VERSION:"=!"
if not defined VERSION goto sin_version
title Crear instalador MSI - Ozone PDF %VERSION%
echo.
echo  ==========================================
echo     Creando el instalador MSI de Ozone PDF %VERSION%
echo  ==========================================
echo.

if not exist "dist\Ozone PDF\Ozone PDF.exe" goto sin_programa

rem ---------- 1. WiX Toolset 3 ----------
call :buscar_wix
if not defined WIXBIN call :instalar_wix
if not defined WIXBIN goto sin_wix
echo  [1/4] WiX Toolset listo: !WIXBIN!

rem ---------- 2. Lista de archivos del programa ----------
echo  [2/4] Preparando la lista de archivos...
if exist "obj_msi" rmdir /s /q "obj_msi"
mkdir "obj_msi"
rem (los componentes quedan de 64 bits porque candle compila con -arch x64)
"!WIXBIN!\heat.exe" dir "dist\Ozone PDF" -nologo -cg ArchivosPrograma -dr INSTALLFOLDER -srd -sreg -scom -ag -var var.Origen -out "obj_msi\archivos.wxs"
if errorlevel 1 goto error

rem ---------- 3. Compilar el .msi ----------
echo  [3/4] Generando el .msi...
if not exist "instalador" mkdir "instalador"
set "MSI=instalador\Ozone_PDF_%VERSION%.msi"
"!WIXBIN!\candle.exe" -nologo -arch x64 -dVersion=%VERSION% "-dOrigen=dist\Ozone PDF" -dRaiz=. -dAssets=assets -out obj_msi\ "instalador_msi.wxs" "obj_msi\archivos.wxs"
if errorlevel 1 goto error
rem Se omiten avisos de validacion que no aplican a una instalacion por equipo
rem (accesos directos con clave en HKLM).
"!WIXBIN!\light.exe" -nologo -spdb -sice:ICE38 -sice:ICE43 -sice:ICE57 -sice:ICE91 -out "!MSI!" "obj_msi\instalador_msi.wixobj" "obj_msi\archivos.wixobj"
if errorlevel 1 goto error

rem ---------- 4. Firma (opcional, la misma huella que CREAR_INSTALADOR.bat) ----------
set "HUELLA="
if exist "firma_huella.txt" set /p HUELLA=<"firma_huella.txt"
if defined FIRMA_HUELLA set "HUELLA=%FIRMA_HUELLA%"
if defined HUELLA set "HUELLA=!HUELLA: =!"
if not defined HUELLA (
  echo  [4/4] Sin firma digital: no hay certificado configurado.
  goto listo
)
set "SIGNTOOL="
for /f "delims=" %%F in ('where signtool 2^>nul') do set "SIGNTOOL=%%F"
if not defined SIGNTOOL (
  for /f "delims=" %%F in ('dir /b /s "%ProgramFiles(x86)%\Windows Kits\10\bin\signtool.exe" 2^>nul ^| findstr /i "\\x64\\"') do set "SIGNTOOL=%%F"
)
if not defined SIGNTOOL goto sin_signtool
echo  [4/4] Firmando el .msi...
set "FIRMA_OK="
for %%T in (http://timestamp.digicert.com http://timestamp.sectigo.com http://timestamp.digicert.com) do (
  if not defined FIRMA_OK (
    "!SIGNTOOL!" sign /sha1 !HUELLA! /fd SHA256 /tr %%T /td SHA256 /d "Ozone PDF" /q "!MSI!" >nul 2>nul
    if errorlevel 1 (timeout /t 5 /nobreak >nul) else (set "FIRMA_OK=1")
  )
)
if not defined FIRMA_OK goto error_firma

:listo
rmdir /s /q "obj_msi" 2>nul
echo.
echo  ==========================================
echo     LISTO
echo  ==========================================
echo.
echo  El instalador MSI quedo en:
echo     !MSI!
echo.
echo  Para instalarlo por GPO: copialo a una carpeta compartida de solo lectura
echo  (\\servidor\carpeta) y asignalo en Configuracion del equipo ^> Directivas ^>
echo  Configuracion de software ^> Instalacion de software. Detalle en el
echo  documento tecnico.
echo.
"%WINDIR%\explorer.exe" "instalador"
pause
exit /b 0


rem ======================= subrutinas =======================

:buscar_wix
set "WIXBIN="
if defined WIX if exist "%WIX%bin\candle.exe" set "WIXBIN=%WIX%bin"
if defined WIXBIN exit /b 0
for /d %%D in ("%ProgramFiles(x86)%\WiX Toolset v3*") do if exist "%%D\bin\candle.exe" set "WIXBIN=%%D\bin"
exit /b 0

:instalar_wix
echo  [1/4] No se encontro WiX Toolset 3. Instalandolo (solo esta vez)...
where winget >nul 2>nul
if errorlevel 1 exit /b 0
winget install -e --id WiXToolset.WiXToolset --silent --accept-package-agreements --accept-source-agreements
call :buscar_wix
exit /b 0


rem ======================= errores =======================

:sin_version
echo.
echo  No se pudo leer la version (APP_VERSION) de app.py.
echo.
pause
exit /b 1

:sin_programa
echo.
echo  No esta el programa armado (dist\Ozone PDF\Ozone PDF.exe).
echo  Ejecuta primero CREAR_INSTALADOR.bat y despues este archivo.
echo.
pause
exit /b 1

:sin_wix
echo.
echo  No se pudo instalar WiX Toolset 3 automaticamente.
echo  Descargalo de https://github.com/wixtoolset/wix3/releases (wix314.exe),
echo  instalalo y volve a ejecutar este archivo. Si pide .NET Framework 3.5,
echo  activalo en "Activar o desactivar las caracteristicas de Windows".
echo.
pause
exit /b 1

:sin_signtool
echo.
echo  Hay una huella de certificado configurada, pero no se encontro signtool.exe.
echo  El .msi quedo generado SIN firmar en: !MSI!
echo.
pause
exit /b 1

:error_firma
echo.
echo  No se pudo firmar el .msi (certificado, token o sello de tiempo).
echo  El .msi quedo generado SIN firmar en: !MSI!
echo.
pause
exit /b 1

:error
echo.
echo  Hubo un error. Revisa los mensajes de arriba.
echo.
pause
exit /b 1
