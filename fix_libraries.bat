@echo off
REM Script para arreglar versiones de librerías compatibles con Python 3.13
REM Evita el downgrade completo de Python

echo ========================================
echo ARREGLANDO VERSIONES DE LIBRERÍAS PYTHON 3.13
echo ========================================
echo.

echo PASO 1: Verificando versiones actuales...
pip list | findstr -i "scikit-learn scipy joblib aiohttp ccxt"
echo.

echo PASO 2: Respaldando requirements.txt...
if exist requirements.txt (
    copy requirements.txt requirements.txt.backup
    echo ✅ Backup creado: requirements.txt.backup
) else (
    echo ⚠️  No se encontró requirements.txt
)
echo.

echo PASO 3: Actualizando librerías problemáticas a versiones compatibles con Python 3.13...
echo.

echo Actualizando scikit-learn a version 1.5.2 (compatible con Python 3.13)...
pip install --upgrade scikit-learn==1.5.2
if %errorlevel% neq 0 (
    echo ERROR: Fallo actualizando scikit-learn
    pause
    exit /b 1
)
echo ✅ scikit-learn actualizado
echo.

echo Actualizando scipy a version 1.14.1 (compatible con Python 3.13)...
pip install --upgrade scipy==1.14.1
if %errorlevel% neq 0 (
    echo ERROR: Fallo actualizando scipy
    pause
    exit /b 1
)
echo ✅ scipy actualizado
echo.

echo Actualizando joblib a version 1.4.2 (compatible con Python 3.13)...
pip install --upgrade joblib==1.4.2
if %errorlevel% neq 0 (
    echo ERROR: Fallo actualizando joblib
    pause
    exit /b 1
)
echo ✅ joblib actualizado
echo.

echo Actualizando aiohttp a version 3.10.10 (compatible con Python 3.13)...
pip install --upgrade aiohttp==3.10.10
if %errorlevel% neq 0 (
    echo ERROR: Fallo actualizando aiohttp
    pause
    exit /b 1
)
echo ✅ aiohttp actualizado
echo.

echo PASO 4: Verificando que las actualizaciones funcionen...
echo.

echo Probando imports críticos...
python -c "
try:
    import sklearn
    print('✅ sklearn importado correctamente')
except Exception as e:
    print(f'❌ sklearn error: {e}')
    exit(1)

try:
    import scipy
    print('✅ scipy importado correctamente')
except Exception as e:
    print(f'❌ scipy error: {e}')
    exit(1)

try:
    import joblib
    print('✅ joblib importado correctamente')
except Exception as e:
    print(f'❌ joblib error: {e}')
    exit(1)

try:
    import aiohttp
    print('✅ aiohttp importado correctamente')
except Exception as e:
    print(f'❌ aiohttp error: {e}')
    exit(1)

print('🎉 Todos los imports críticos funcionan!')
"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Algunos imports fallaron
    echo.
    echo SOLUCIONES ALTERNATIVAS:
    echo 1. Intentar versiones diferentes
    echo 2. Usar el downgrade de Python como plan B
    echo 3. Verificar conflictos de dependencias
    pause
    exit /b 1
)

echo.
echo PASO 5: Probando imports del proyecto...
python -c "
try:
    from utils.normalization import DataNormalizer
    print('✅ DataNormalizer importado correctamente')
except Exception as e:
    print(f'❌ DataNormalizer error: {e}')
    exit(1)

try:
    from indicators.technical_indicators import TechnicalIndicators
    print('✅ TechnicalIndicators importado correctamente')
except Exception as e:
    print(f'❌ TechnicalIndicators error: {e}')
    exit(1)

print('🎉 Todos los imports del proyecto funcionan!')
"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Imports del proyecto fallaron
    pause
    exit /b 1
)

echo.
echo ========================================
echo VERSIONES DE LIBRERÍAS ARREGLADAS!
echo ========================================
echo.
echo VERIFICANDO VERSIONES FINALES...
pip list | findstr -i "scikit-learn scipy joblib aiohttp"
echo.

echo 🎯 PROXIMOS PASOS:
echo 1. Probar el sistema: python descarga_datos/main.py --live-ccxt
echo 2. Si funciona, ¡problema resuelto sin downgrade!
echo 3. Si falla, usar downgrade_python.bat como plan B
echo.

pause