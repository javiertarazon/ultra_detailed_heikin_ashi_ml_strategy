# ========================================
# 🔍 VALIDACIÓN RÁPIDA - SISTEMA SANDBOX
# ========================================
# Script para validar configuración antes de ejecutar
# ========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔍 VALIDACIÓN DE CONFIGURACIÓN SANDBOX" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# ========================================
# 1. Verificar ubicación
# ========================================
Write-Host "[1/8] Verificando ubicación..." -ForegroundColor Yellow

if (Test-Path "main.py") {
    Write-Host "✅ Ubicación correcta: descarga_datos/" -ForegroundColor Green
} else {
    Write-Host "❌ No estás en descarga_datos/" -ForegroundColor Red
    $allGood = $false
}

# ========================================
# 2. Verificar config.yaml
# ========================================
Write-Host "[2/8] Verificando config.yaml..." -ForegroundColor Yellow

if (Test-Path "config\config.yaml") {
    $config = Get-Content "config\config.yaml" -Raw
    
    # Verificar modo sandbox
    if ($config -match "sandbox:\s*true") {
        Write-Host "✅ Modo sandbox: ACTIVADO" -ForegroundColor Green
    } else {
        Write-Host "❌ Modo sandbox: DESACTIVADO (PELIGRO)" -ForegroundColor Red
        $allGood = $false
    }
    
    # Verificar exchange activo
    if ($config -match "active_exchange:\s*(\w+)") {
        $exchange = $matches[1]
        Write-Host "✅ Exchange activo: $exchange" -ForegroundColor Green
    }
    
    # Verificar estrategia
    if ($config -match "UltraDetailedHeikinAshiML:\s*true") {
        Write-Host "✅ Estrategia UltraDetailedHeikinAshiML: ACTIVA" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Estrategia UltraDetailedHeikinAshiML: INACTIVA" -ForegroundColor Yellow
    }
    
    # Verificar símbolo
    if ($config -match "BNB/USDT") {
        Write-Host "✅ Símbolo BNB/USDT: CONFIGURADO" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Símbolo BNB/USDT: NO configurado" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ config.yaml NO encontrado" -ForegroundColor Red
    $allGood = $false
}

# ========================================
# 3. Verificar .env
# ========================================
Write-Host "[3/8] Verificando archivo .env..." -ForegroundColor Yellow

if (Test-Path ".env") {
    $env = Get-Content ".env" -Raw
    
    # Verificar API keys
    if ($env -match "BINANCE_API_KEY=(\S+)") {
        $key = $matches[1]
        if ($key -ne "your_binance_testnet_api_key_here" -and $key.Length -gt 10) {
            Write-Host "✅ BINANCE_API_KEY: CONFIGURADA" -ForegroundColor Green
        } else {
            Write-Host "⚠️  BINANCE_API_KEY: NO configurada (usar template)" -ForegroundColor Yellow
            $allGood = $false
        }
    } else {
        Write-Host "❌ BINANCE_API_KEY: NO encontrada" -ForegroundColor Red
        $allGood = $false
    }
    
    if ($env -match "BINANCE_API_SECRET=(\S+)") {
        $secret = $matches[1]
        if ($secret -ne "your_binance_testnet_secret_here" -and $secret.Length -gt 10) {
            Write-Host "✅ BINANCE_API_SECRET: CONFIGURADA" -ForegroundColor Green
        } else {
            Write-Host "⚠️  BINANCE_API_SECRET: NO configurada (usar template)" -ForegroundColor Yellow
            $allGood = $false
        }
    } else {
        Write-Host "❌ BINANCE_API_SECRET: NO encontrada" -ForegroundColor Red
        $allGood = $false
    }
    
    # Verificar modo sandbox en .env
    if ($env -match "SANDBOX_MODE=true") {
        Write-Host "✅ SANDBOX_MODE en .env: TRUE" -ForegroundColor Green
    } elseif ($env -match "SANDBOX_MODE=false") {
        Write-Host "❌ SANDBOX_MODE en .env: FALSE (PELIGRO)" -ForegroundColor Red
        $allGood = $false
    }
    
} else {
    Write-Host "⚠️  Archivo .env NO existe (se puede usar config.yaml)" -ForegroundColor Yellow
}

# ========================================
# 4. Verificar dependencias Python
# ========================================
Write-Host "[4/8] Verificando dependencias Python..." -ForegroundColor Yellow

# CCXT
$ccxtInstalled = python -c "import ccxt; print('OK')" 2>$null
if ($LASTEXITCODE -eq 0) {
    $ccxtVersion = python -c "import ccxt; print(ccxt.__version__)"
    Write-Host "✅ ccxt instalado: v$ccxtVersion" -ForegroundColor Green
} else {
    Write-Host "❌ ccxt NO instalado" -ForegroundColor Red
    $allGood = $false
}

# Pandas
$pandasInstalled = python -c "import pandas; print('OK')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ pandas instalado" -ForegroundColor Green
} else {
    Write-Host "❌ pandas NO instalado" -ForegroundColor Red
    $allGood = $false
}

# NumPy
$numpyInstalled = python -c "import numpy; print('OK')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ numpy instalado" -ForegroundColor Green
} else {
    Write-Host "❌ numpy NO instalado" -ForegroundColor Red
    $allGood = $false
}

# ========================================
# 5. Verificar archivos core
# ========================================
Write-Host "[5/8] Verificando archivos core..." -ForegroundColor Yellow

$coreFiles = @(
    "core\ccxt_live_trading_orchestrator.py",
    "core\ccxt_live_data.py",
    "core\ccxt_order_executor.py",
    "strategies\ultra_detailed_heikin_ashi_ml_strategy.py"
)

foreach ($file in $coreFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file NO encontrado" -ForegroundColor Red
        $allGood = $false
    }
}

# ========================================
# 6. Verificar directorios
# ========================================
Write-Host "[6/8] Verificando directorios..." -ForegroundColor Yellow

$dirs = @("logs", "data", "models")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "✅ Directorio $dir/ existe" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Directorio $dir/ NO existe (se creará automáticamente)" -ForegroundColor Yellow
    }
}

# ========================================
# 7. Test de conexión (opcional)
# ========================================
Write-Host "[7/8] Probando conexión a exchange..." -ForegroundColor Yellow

$testConnection = @"
import ccxt
import sys
try:
    exchange = ccxt.binance({'sandbox': True, 'enableRateLimit': True})
    markets = exchange.load_markets()
    print(f'OK:{len(markets)}')
except Exception as e:
    print(f'ERROR:{str(e)}')
    sys.exit(1)
"@

$result = python -c $testConnection 2>&1
if ($result -match "OK:(\d+)") {
    $marketCount = $matches[1]
    Write-Host "✅ Conexión a Binance Testnet exitosa ($marketCount mercados)" -ForegroundColor Green
} elseif ($result -match "ERROR:(.+)") {
    $error = $matches[1]
    Write-Host "⚠️  No se pudo conectar: $error" -ForegroundColor Yellow
    Write-Host "   (Normal si aún no configuraste API keys)" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Test de conexión no concluyente" -ForegroundColor Yellow
}

# ========================================
# 8. Verificar modelo ML
# ========================================
Write-Host "[8/8] Verificando modelo ML..." -ForegroundColor Yellow

if (Test-Path "models\BNB_USDT") {
    $modelFiles = Get-ChildItem "models\BNB_USDT" -Filter "*.joblib" -ErrorAction SilentlyContinue
    if ($modelFiles.Count -gt 0) {
        $latestModel = $modelFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Host "✅ Modelo ML encontrado: $($latestModel.Name)" -ForegroundColor Green
        Write-Host "   Fecha: $($latestModel.LastWriteTime)" -ForegroundColor Gray
    } else {
        Write-Host "⚠️  No hay modelos ML entrenados" -ForegroundColor Yellow
        Write-Host "   Ejecuta: python main.py --train-ml" -ForegroundColor Cyan
    }
} else {
    Write-Host "⚠️  Directorio de modelos no existe" -ForegroundColor Yellow
    Write-Host "   Ejecuta: python main.py --train-ml" -ForegroundColor Cyan
}

# ========================================
# RESUMEN
# ========================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "✅ VALIDACIÓN EXITOSA" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 El sistema está listo para ejecutar:" -ForegroundColor Green
    Write-Host ""
    Write-Host "   python main.py --live-ccxt" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📊 Monitorear logs:" -ForegroundColor Yellow
    Write-Host "   Get-Content logs\bot_trader.log -Wait -Tail 50" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "⚠️  VALIDACIÓN CON ERRORES" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "❌ Hay problemas que deben resolverse:" -ForegroundColor Red
    Write-Host ""
    Write-Host "1. Si falta configurar API keys:" -ForegroundColor White
    Write-Host "   - Editar .env con credenciales de testnet" -ForegroundColor Gray
    Write-Host "   - O configurar en config\config.yaml" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Si falta activar sandbox:" -ForegroundColor White
    Write-Host "   - Editar config\config.yaml" -ForegroundColor Gray
    Write-Host "   - Cambiar 'sandbox: false' a 'sandbox: true'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Si faltan dependencias:" -ForegroundColor White
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Ejecuta setup automático:" -ForegroundColor Yellow
    Write-Host "   .\setup_sandbox.ps1" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "📚 Documentación completa:" -ForegroundColor Yellow
Write-Host "   cat LIVE_TRADING_SANDBOX_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
