@echo off
REM Script para downgrade de Python 3.13.7 a 3.11.x en Windows
REM Este script automatiza el proceso completo

echo ========================================
echo DOWNGRADE PYTHON 3.13.7 → 3.11.x
echo ========================================
echo.

echo PASO 1: Verificando version actual...
python --version
echo.

echo PASO 2: Descargando Python 3.11.9...
echo.
echo IMPORTANTE: Si no tienes Python 3.11 descargado, ve a:
echo https://www.python.org/downloads/release/python-3119/
echo Descarga: python-3.11.9-amd64.exe
echo.
echo Una vez descargado, ejecutalo como administrador y sigue estos pasos:
echo 1. Marcar "Add Python 3.11 to PATH"
echo 2. Seleccionar "Customize installation"
echo 3. En "Optional Features": marcar todo
echo 4. En "Advanced Options":
echo    - Install for all users
echo    - Associate files with Python
echo    - Create shortcuts
echo    - Add Python to environment variables
echo    - Precompile standard library
echo.

pause

echo.
echo PASO 3: Verificando nueva instalacion...
"C:\Users\javie\AppData\Local\Programs\Python\Python311\python.exe" --version
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11 no encontrado. Verifica la instalacion.
    echo Buscando python.exe en PATH...
    where python
    echo.
    echo Si ves python.exe en Python311 folder, continua.
    echo Si no, reinstala Python 3.11 correctamente.
    pause
    exit /b 1
)

echo ✅ Python 3.11 encontrado correctamente
"C:\Users\javie\AppData\Local\Programs\Python\Python311\python.exe" --version
echo.

echo PASO 4: Actualizando variables de entorno...
echo IMPORTANTE: Reinicia tu terminal/PowerShell despues de este script
echo para que los cambios de PATH tomen efecto.
echo.

echo PASO 5: Respaldando entorno virtual actual...
if exist .venv (
    echo Respaldando .venv actual...
    move .venv .venv_backup_313 2>nul
    echo ✅ Entorno virtual respaldado como .venv_backup_313
) else (
    echo No hay entorno virtual para respaldar
)

echo.
echo PASO 6: Creando nuevo entorno virtual con Python 3.11...
"C:\Users\javie\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo ✅ Nuevo entorno virtual creado con Python 3.11
echo.

echo PASO 7: Activando entorno virtual y actualizando pip...
call .venv\Scripts\activate.bat
python --version
pip install --upgrade pip
echo.

echo PASO 8: Instalando dependencias...
if exist requirements.txt (
    echo Instalando desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Fallo instalando dependencias
        echo Intenta: pip install --upgrade setuptools wheel
        echo Luego vuelve a ejecutar: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo ✅ Dependencias instaladas correctamente
) else (
    echo WARNING: No se encontro requirements.txt
)

echo.
echo ========================================
echo DOWNGRADE COMPLETADO EXITOSAMENTE!
echo ========================================
echo.
echo PROXIMOS PASOS:
echo 1. CIERRA esta terminal completamente
echo 2. ABRE una nueva terminal PowerShell
echo 3. Navega al proyecto: cd C:\Users\javie\copilot\botcopilot-sar
echo 4. Activa el entorno: .venv\Scripts\Activate.ps1
echo 5. Verifica: python --version (debe ser 3.11.x)
echo 6. Prueba el sistema: python descarga_datos/main.py --live-ccxt
echo.
echo Si algo falla, puedes restaurar el entorno anterior:
echo move .venv_backup_313 .venv
echo.

pause