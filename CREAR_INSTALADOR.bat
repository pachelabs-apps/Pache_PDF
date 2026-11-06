@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "VERSION=1.1.0"
title Crear instalador - Ozone PDF %VERSION%
echo.
echo  ==========================================
echo     Creando el instalador de Ozone PDF %VERSION%
echo  ==========================================
echo.
echo  Este proceso tarda unos minutos. No cierres esta ventana.
echo.
echo  IMPORTANTE: no hagas clic dentro de esta ventana.
echo  Si lo haces, Windows la pausa (el titulo dice "Seleccionar").
echo  Si pasa, apreta ENTER para que continue.
echo.

rem ---------- 1. Python 3.12 (la version documentada y verificada) ----------
call :buscar_python
if not defined PY call :instalar_python
if not defined PY goto sin_python
echo  [1/5] Python 3.12 listo.

rem ---------- 2. Entorno aislado y componentes verificados por huella ----------
echo  [2/5] Preparando entorno aislado y componentes verificados...
echo        (la primera vez descarga unos 40 MB; vas a ver el avance)
rem El entorno se crea de cero en cada compilacion: asi pip verifica la huella de cada
rem componente siempre y no puede colarse ningun paquete instalado antes a mano.
rem (pip guarda lo descargado en su cache: a partir de la segunda vez es rapido.)
if exist ".venv-build" rmdir /s /q ".venv-build"
if exist ".venv-build" goto error_venv
"%PY%" -m venv ".venv-build"
if not exist ".venv-build\Scripts\python.exe" goto error
set "VPY=%~dp0.venv-build\Scripts\python.exe"
"%VPY%" -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --timeout 30 --retries 3 --progress-bar on -r requirements.txt
if errorlevel 1 goto error_red

rem ---------- 3. Programa + autoprueba ----------
echo  [3/5] Armando el programa...
rem Exclusion estricta: el ejecutable no incluye ni siquiera los modulos de red de bajo nivel.
rem El modo queda grabado dentro del programa (compilacion.txt) y se ve en "Acerca de".
set "MODO_RED=estricta (sin socket, asyncio ni multiprocessing)"
call :armar "--exclude-module socket --exclude-module _socket --exclude-module asyncio --exclude-module _asyncio --exclude-module _overlapped --exclude-module multiprocessing --exclude-module _multiprocessing" estricta
if errorlevel 1 goto error
echo        Probando el programa armado (15 herramientas y exclusion de red)...
call :autoprueba
rem Codigo 3 = la autoprueba se colgo (no tiene que ver con la exclusion de red): se detiene sin plan B
if "!PRUEBA!"=="3" goto prueba_colgada
if "!PRUEBA!"=="9" goto prueba_sin_powershell
rem Se compara el texto del codigo (no "if errorlevel"): un cuelgue de Windows da un codigo negativo
if not "!PRUEBA!"=="0" call :plan_b
if not "!PRUEBA!"=="0" goto error_prueba
echo        Autoprueba OK. Exclusion de red: !MODO_RED!

rem ---------- 4. Firma digital (opcional) ----------
rem Para firmar, guarda la huella (thumbprint) del certificado en firma_huella.txt
rem o en la variable de entorno FIRMA_HUELLA. Ver el documento tecnico, seccion 6.
set "HUELLA="
if exist "firma_huella.txt" set /p HUELLA=<"firma_huella.txt"
if defined FIRMA_HUELLA set "HUELLA=%FIRMA_HUELLA%"
if defined HUELLA set "HUELLA=!HUELLA: =!"
if not defined HUELLA goto sin_firma
call :validar_huella
if errorlevel 1 goto huella_mala
call :buscar_signtool
if not defined SIGNTOOL goto sin_signtool
echo  [4/5] Firmando el programa y todas sus bibliotecas (EXE, DLL y PYD)...
rem Se firma cada ejecutable de la carpeta del programa. Los que ya traen una firma valida
rem de su fabricante (por ejemplo, python312.dll o las DLL de Microsoft) se dejan como estan.
set /a FIRMADOS=0, YA_FIRMADOS=0
for /r "dist\Ozone PDF" %%F in (*.exe *.dll *.pyd) do (
  "!SIGNTOOL!" verify /pa /q "%%F" >nul 2>nul
  if errorlevel 1 (
    call :firmar_archivo "%%F"
    if errorlevel 1 goto error_firma
    set /a FIRMADOS+=1
  ) else (
    set /a YA_FIRMADOS+=1
  )
)
echo        Firmados: !FIRMADOS! archivos. Ya tenian firma de su fabricante: !YA_FIRMADOS!.
rem Se vuelve a probar el programa YA FIRMADO: lo que se instala es exactamente lo que se probo
echo        Probando de nuevo el programa firmado...
call :autoprueba
if "!PRUEBA!"=="9" goto prueba_sin_powershell
if not "!PRUEBA!"=="0" goto error_prueba_firmado
goto instalador
:sin_firma
echo  [4/5] Sin firma digital: no hay certificado configurado (ver LEEME).

:instalador
rem ---------- 5. Instalador ----------
call :buscar_iscc
if not defined ISCC call :instalar_inno
if not defined ISCC goto sin_inno
echo  [5/5] Generando el instalador...
if defined HUELLA goto iscc_firmado
"%ISCC%" /Q "instalador.iss"
if errorlevel 1 goto error_inno
goto listo
:iscc_firmado
rem Inno firma el instalador y tambien el desinstalador
"%ISCC%" /Q /DFIRMAR "/Sfirma=$q!SIGNTOOL!$q sign /sha1 !HUELLA! /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f" "instalador.iss"
if errorlevel 1 goto error_inno

:listo
echo.
echo  ==========================================
echo     LISTO
echo  ==========================================
echo.
echo  El instalador quedo en:
echo     instalador\Instalar_Ozone_PDF_%VERSION%.exe
echo.
echo  Ese es el unico archivo que tenes que copiar o compartir.
echo  Al ejecutarlo instala Ozone PDF y crea los accesos directos
echo  en el escritorio y en el menu Inicio.
echo  Exclusion de red del programa: !MODO_RED!
if defined HUELLA (echo  Programa, bibliotecas, instalador y desinstalador quedaron firmados.) else (echo  Recorda: el instalador no esta firmado.)
echo.
"%WINDIR%\explorer.exe" "instalador"
pause
exit /b 0


rem ======================= subrutinas =======================

:armar
rem %1 = exclusiones extra, %2 = modo (estricta o reducida)
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
> "compilacion.txt" echo %~2
"%VPY%" -m PyInstaller --noconfirm --clean --windowed --log-level WARN ^
  --name "Ozone PDF" ^
  --icon "assets\icono.ico" ^
  --add-data "assets;assets" ^
  --add-data "AVISO_USO.txt;." ^
  --add-data "LICENSE.txt;." ^
  --add-data "LICENCIAS.txt;." ^
  --add-data "LICENCIAS_TERCEROS.txt;." ^
  --add-data "compilacion.txt;." ^
  --hidden-import PIL._tkinter_finder ^
  --collect-data tkinterdnd2 ^
  --exclude-module onnxruntime ^
  --exclude-module ssl ^
  --exclude-module _ssl ^
  --exclude-module http ^
  --exclude-module urllib.request ^
  --exclude-module ftplib ^
  --exclude-module smtplib ^
  --exclude-module poplib ^
  --exclude-module imaplib ^
  --exclude-module xmlrpc ^
  --exclude-module webbrowser ^
  %~1 ^
  --version-file "version_info.txt" ^
  app.py
if errorlevel 1 exit /b 1
if not exist "dist\Ozone PDF\Ozone PDF.exe" exit /b 1
rem OpenCV trae FFmpeg (lee videos y transmisiones de red); la camara no lo usa, se borra.
del /q "dist\Ozone PDF\_internal\cv2\opencv_videoio_ffmpeg*.dll" 2>nul
rem tkinterdnd2 trae tkdnd para todas las plataformas; solo se deja la de Windows x64
rem (Python 3.12 usa Tcl 8.6). La autoprueba verifica que arrastrar y soltar siga activo.
set "TKDND=dist\Ozone PDF\_internal\tkinterdnd2\tkdnd"
if not exist "%TKDND%\win-x64" exit /b 0
pushd "%TKDND%"
for /d %%D in (*) do if /i not "%%D"=="win-x64" rmdir /s /q "%%D"
popd
exit /b 0

:autoprueba
rem Deja el codigo de salida en PRUEBA: 0 = bien, 1 = fallo, 3 = se colgo,
rem 9 = no se pudo ejecutar la prueba (PowerShell ausente o bloqueado).
rem El limite de tiempo es externo (11 minutos): cubre tambien un programa que ni llega a
rem arrancar la prueba (por ejemplo, si muestra un cuadro de error al iniciar).
set "PRUEBA=9"
for /f "delims=" %%c in ('powershell -NoProfile -Command "$p = Start-Process -FilePath (Join-Path $PWD 'dist\Ozone PDF\Ozone PDF.exe') -ArgumentList '--autotest' -PassThru; $null = $p.Handle; if ($p.WaitForExit(660000)) { $p.ExitCode } else { try { $p.Kill() } catch {}; 3 }" 2^>nul') do set "PRUEBA=%%c"
exit /b 0

:firmar_archivo
rem Firma un archivo. Si el servidor de sello de tiempo no responde, reintenta con otro
rem servidor y espera entre intentos (3 intentos en total) antes de dar error.
set "FIRMA_OK="
for %%T in (http://timestamp.digicert.com http://timestamp.sectigo.com http://timestamp.digicert.com) do (
  if not defined FIRMA_OK (
    "!SIGNTOOL!" sign /sha1 !HUELLA! /fd SHA256 /tr %%T /td SHA256 /q "%~1" >nul 2>nul
    if errorlevel 1 (timeout /t 5 /nobreak >nul) else (set "FIRMA_OK=1")
  )
)
if defined FIRMA_OK exit /b 0
echo        No se pudo firmar: %~1
exit /b 1

:plan_b
rem No se baja la proteccion sin preguntar: por defecto se detiene.
echo.
echo  ATENCION: con la exclusion ESTRICTA de red la autoprueba fallo.
echo  Detalle en: %TEMP%\ozonepdf_autotest.txt
echo  Se puede armar con la exclusion REDUCIDA (sin HTTP, SSL, correo ni FTP,
echo  pero con socket). Si lo haces, queda registrado en "Acerca de" del programa.
choice /c SN /n /t 120 /d N /m "  Armar con exclusion reducida? [S/N] (sin respuesta en 2 minutos: No) "
if errorlevel 2 exit /b 1
set "MODO_RED=REDUCIDA (sin HTTP, SSL, correo ni FTP; con socket)"
call :armar "" reducida
if errorlevel 1 exit /b 1
call :autoprueba
exit /b 0

:buscar_python
rem Solo Python 3.12 de 64 bits (los componentes verificados son para Windows x64)
set "PY="
for /f "delims=" %%i in ('py -3.12-64 -c "import sys, tkinter; assert sys.maxsize > 2**32; print(sys.executable)" 2^>nul') do set "PY=%%i"
if defined PY exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" call :probar_py "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PY exit /b 0
if exist "%ProgramFiles%\Python312\python.exe" call :probar_py "%ProgramFiles%\Python312\python.exe"
exit /b 0

:probar_py
"%~1" -c "import sys, tkinter; assert sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
exit /b 0

:instalar_python
echo  [1/5] No se encontro Python 3.12. Instalandolo (solo esta vez)...
where winget >nul 2>nul
if errorlevel 1 exit /b 0
rem Version fija y verificada; si winget ya no la ofrece, instala la ultima 3.12
winget install -e --id Python.Python.3.12 --version 3.12.10 --architecture x64 --scope user --silent --accept-package-agreements --accept-source-agreements
call :buscar_python
if defined PY exit /b 0
winget install -e --id Python.Python.3.12 --architecture x64 --scope user --silent --accept-package-agreements --accept-source-agreements
call :buscar_python
exit /b 0

:buscar_iscc
set "ISCC="
set "C1=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
set "C2=%ProgramFiles%\Inno Setup 6\ISCC.exe"
set "C3=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%C1%" set "ISCC=%C1%"
if exist "%C2%" set "ISCC=%C2%"
if exist "%C3%" set "ISCC=%C3%"
exit /b 0

:instalar_inno
echo  [5/5] Instalando Inno Setup (solo esta vez)...
where winget >nul 2>nul
if errorlevel 1 exit /b 0
winget install -e --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
call :buscar_iscc
exit /b 0


:validar_huella
rem Tienen que ser exactamente 40 caracteres hexadecimales (0-9, A-F).
rem Se borran de una copia los 16 caracteres validos: si queda algo, hay caracteres raros
rem (por ejemplo, el invisible que a veces se copia desde la ventana de certificados).
if "!HUELLA:~39,1!"=="" exit /b 1
if not "!HUELLA:~40,1!"=="" exit /b 1
set "RESTO=!HUELLA!"
for %%c in (0 1 2 3 4 5 6 7 8 9 A B C D E F) do set "RESTO=!RESTO:%%c=!"
if defined RESTO exit /b 1
exit /b 0

:buscar_signtool
set "SIGNTOOL="
for /f "delims=" %%F in ('where signtool 2^>nul') do set "SIGNTOOL=%%F"
if defined SIGNTOOL exit /b 0
set "KITS=%ProgramFiles(x86)%\Windows Kits\10\bin"
if not exist "%KITS%" exit /b 0
pushd "%KITS%"
for /f "delims=" %%F in ('dir /b /s signtool.exe 2^>nul ^| findstr /i "\\x64\\"') do set "SIGNTOOL=%%F"
popd
exit /b 0


rem ======================= errores =======================

:sin_python
echo.
echo  No se pudo instalar Python 3.12 automaticamente.
echo  Instalalo a mano desde https://www.python.org/downloads/ (version 3.12,
echo  marca "Add Python to PATH") y volve a ejecutar este archivo.
echo.
pause
exit /b 1

:sin_inno
echo.
echo  El programa se armo bien en:  dist\Ozone PDF\Ozone PDF.exe
echo  pero no se pudo instalar Inno Setup automaticamente.
echo  Descargalo de https://jrsoftware.org/isdl.php, instalalo
echo  y volve a ejecutar este archivo.
echo.
pause
exit /b 1

:error_inno
echo.
echo  El programa se armo bien, pero Inno Setup no pudo generar el instalador.
echo  Revisa el mensaje de arriba. Si menciona "x64compatible", el Inno Setup
echo  instalado es anterior a la 6.3: instala la ultima version desde
echo  https://jrsoftware.org/isdl.php y volve a ejecutar este archivo.
echo.
pause
exit /b 1

:huella_mala
echo.
echo  La huella del certificado no es valida: tienen que ser 40 caracteres
echo  hexadecimales (0-9 y A-F), sin espacios.
echo  Si la copiaste de la ventana de certificados, puede traer un caracter
echo  invisible al principio. Escribila a mano en firma_huella.txt o obtenela
echo  en PowerShell con:
echo     (Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert).Thumbprint
echo.
pause
exit /b 1

:sin_signtool
echo.
echo  Hay una huella de certificado configurada, pero no se encontro signtool.exe.
echo  Instala el Windows SDK (componente "Signing Tools for Desktop Apps")
echo  o borra firma_huella.txt para generar el instalador sin firma.
echo.
pause
exit /b 1

:error_firma
echo.
echo  No se pudo firmar el programa. Verifica que el certificado este instalado
echo  en este usuario (o el token conectado) y que la huella sea correcta.
echo  Para el sello de tiempo hace falta acceso a timestamp.digicert.com o
echo  timestamp.sectigo.com (se probaron los dos, con reintentos).
echo.
pause
exit /b 1

:prueba_sin_powershell
echo.
echo  Compilacion detenida: no se pudo ejecutar la autoprueba porque PowerShell no
echo  esta disponible o esta bloqueado en este equipo (AppLocker, WDAC o directivas).
echo  No es una falla del programa. Compila en un equipo donde se pueda usar PowerShell.
echo.
pause
exit /b 1

:prueba_colgada
echo.
echo  Compilacion detenida: la autoprueba no termino en 10 minutos (se colgo).
echo  No tiene que ver con la exclusion de red, por eso no se ofrece armar de otra forma.
echo  El detalle quedo en: %TEMP%\ozonepdf_autotest.txt
echo  Volve a intentarlo; si se repite, envia ese archivo a quien mantiene el proyecto.
echo.
pause
exit /b 1

:error_prueba_firmado
echo.
echo  Compilacion detenida: el programa paso la autoprueba antes de firmarlo,
echo  pero fallo despues de firmarlo. No se genero el instalador.
echo  El detalle quedo en: %TEMP%\ozonepdf_autotest.txt
echo.
pause
exit /b 1

:error_prueba
echo.
echo  Compilacion detenida: la autoprueba fallo (o no se acepto la exclusion reducida).
echo  El detalle quedo en: %TEMP%\ozonepdf_autotest.txt
echo  Envia ese archivo a quien mantiene el proyecto.
echo.
pause
exit /b 1

:error_venv
echo.
echo  No se pudo borrar el entorno anterior (.venv-build). Cerra cualquier ventana o
echo  programa que lo este usando y volve a ejecutar este archivo.
echo.
pause
exit /b 1

:error_red
echo.
echo  No se pudieron descargar o verificar los componentes.
echo  Suele pasar en redes con proxy o firewall que bloquean pypi.org.
echo  Proba desde otra red o pedile al area de sistemas habilitar pypi.org y files.pythonhosted.org
echo  Si dice que una huella (hash) no coincide, NO continues: puede ser un archivo alterado.
echo.
pause
exit /b 1

:error
echo.
echo  Hubo un error. Revisa los mensajes de arriba.
echo  Si no se entiende, sacale una captura a esta ventana y consultalo.
echo.
pause
exit /b 1
