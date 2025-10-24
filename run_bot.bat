@echo off
REM Script para ejecutar Bot Trader Copilot en Windows
REM Asegura que se use el entorno virtual correcto

echo ========================================
echo Bot Trader Copilot - Launcher Windows
echo ========================================
echo.

REM Verificar si el entorno virtual existe
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ ERROR: No se encuentra el entorno virtual .venv
    echo    Ejecuta primero: python -m venv .venv
    echo    Luego instala dependencias: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activar entorno virtual
echo ✅ Activando entorno virtual...
call .venv\Scripts\activate.bat

REM Verificar versión de Python (acepta cualquier 3.11.x)
python -c "import sys; v=sys.version_info; print(f'Versión Python: {v.major}.{v.minor}.{v.micro}'); sys.exit(0 if v.major==3 and v.minor==11 else 1)"
if errorlevel 1 (
    echo ❌ ERROR: Se requiere Python 3.11.x
    echo    Versión actual:
    python -c "import sys; print(sys.version)"
    pause
    exit /b 1
)

echo ✅ Entorno verificado correctamente
echo.

REM Ejecutar main.py con todos los argumentos pasados
echo Ejecutando: python descarga_datos/main.py %*
python descarga_datos/main.py %*

REM Mantener ventana abierta si hay error
if errorlevel 1 (
    echo.
    echo ❌ Se produjo un error durante la ejecución
    pause
)