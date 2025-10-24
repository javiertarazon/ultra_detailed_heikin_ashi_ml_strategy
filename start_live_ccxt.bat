@echo off
REM Script para ejecutar Bot Trader Copilot en modo Live CCXT
REM Mantiene la ventana abierta para debugging

cd /d "C:\Users\javie\copilot\botcopilot-sar"

echo ========================================
echo Iniciando Bot Trader Copilot - Live CCXT
echo ========================================
echo.

.\.venv\Scripts\python.exe descarga_datos\main.py --live-ccxt

REM Mantener ventana abierta si hay error
if %errorlevel% neq 0 (
    echo.
    echo ERROR: El sistema falló con código %errorlevel%
    pause
)
