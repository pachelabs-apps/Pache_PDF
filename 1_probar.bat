@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
rem Abre Ozone PDF desde el codigo fuente, en un entorno aislado (.venv), sin instalar nada en el sistema.
rem Busca Python 3.12 exactamente igual que CREAR_INSTALADOR.bat.

call :buscar_python
if not defined PY goto sin_python

rem Si el entorno existe pero no es de Python 3.12, se rehace
if not exist ".venv\Scripts\python.exe" goto crear_venv
".venv\Scripts\python.exe" -c "import sys, tkinter; assert sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 rmdir /s /q ".venv"
:crear_venv
if exist ".venv\Scripts\python.exe" goto componentes
echo Creando el entorno de prueba...
"%PY%" -m venv ".venv"
if not exist ".venv\Scripts\python.exe" goto sin_venv

:componentes
echo Verificando componentes (la primera vez los descarga)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --quiet -r requirements.txt
if errorlevel 1 goto sin_componentes
start "" ".venv\Scripts\pythonw.exe" app.py
exit /b 0


rem ======================= subrutinas (iguales a CREAR_INSTALADOR.bat) =======================

:buscar_python
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


rem ======================= errores =======================

:sin_python
echo.
echo No se encontro Python 3.12 de 64 bits (con Tkinter).
echo Instalalo desde https://www.python.org/downloads/ (version 3.12, marca "Add Python to PATH")
echo o ejecuta CREAR_INSTALADOR.bat, que lo instala solo.
echo.
pause
exit /b 1

:sin_venv
echo.
echo No se pudo crear el entorno de prueba (.venv) con %PY%
echo.
pause
exit /b 1

:sin_componentes
echo.
echo No se pudieron descargar o verificar los componentes.
echo Revisa la conexion a internet o el proxy (pypi.org y files.pythonhosted.org).
echo Si dice que una huella (hash) no coincide, NO continues: puede ser un archivo alterado.
echo.
pause
exit /b 1
