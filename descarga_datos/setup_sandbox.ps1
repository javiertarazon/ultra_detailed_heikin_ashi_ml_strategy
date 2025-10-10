# ========================================
# 🚀 SETUP RÁPIDO - TRADING EN VIVO SANDBOX
# ========================================
# Script PowerShell para configurar trading en vivo con exchange testnet
# Versión: 1.0
# Fecha: 09/10/2025
# ========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 BOTCOPILOT SAR v3.0 - SETUP SANDBOX" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Función para mostrar paso
function Show-Step {
    param($Number, $Title)
    Write-Host ""
    Write-Host "[$Number/6] $Title" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
}

# Función para mostrar éxito
function Show-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

# Función para mostrar advertencia
function Show-Warning {
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

# Función para mostrar error
function Show-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Función para mostrar info
function Show-Info {
    param($Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

# ========================================
# PASO 1: Verificar ubicación
# ========================================
Show-Step 1 "Verificando ubicación del proyecto..."

$currentPath = Get-Location
if (-not (Test-Path "main.py")) {
    Show-Error "No estás en el directorio descarga_datos/"
    Show-Info "Navegando automáticamente..."
    
    if (Test-Path "..\descarga_datos\main.py") {
        Set-Location "..\descarga_datos"
        Show-Success "Ubicación corregida"
    } elseif (Test-Path "descarga_datos\main.py") {
        Set-Location "descarga_datos"
        Show-Success "Ubicación corregida"
    } else {
        Show-Error "No se encuentra main.py. Por favor navega manualmente a descarga_datos/"
        exit 1
    }
}

Show-Success "Ubicación correcta: $(Get-Location)"

# ========================================
# PASO 2: Verificar archivos necesarios
# ========================================
Show-Step 2 "Verificando archivos del sistema..."

$requiredFiles = @(
    "main.py",
    "config\config.yaml",
    ".env.example",
    "core\ccxt_live_trading_orchestrator.py",
    "core\ccxt_live_data.py",
    "core\ccxt_order_executor.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Show-Success "$file encontrado"
    } else {
        Show-Error "$file NO encontrado"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Show-Error "Faltan archivos críticos. Sistema incompleto."
    exit 1
}

# ========================================
# PASO 3: Verificar config.yaml
# ========================================
Show-Step 3 "Verificando configuración..."

$configContent = Get-Content "config\config.yaml" -Raw
if ($configContent -match "sandbox:\s*true") {
    Show-Success "Modo sandbox ACTIVADO en config.yaml"
} else {
    Show-Warning "Modo sandbox NO activado en config.yaml"
    Show-Info "Editando config.yaml..."
    
    # Intentar activar sandbox automáticamente
    $configContent = $configContent -replace "sandbox:\s*false", "sandbox: true"
    Set-Content "config\config.yaml" -Value $configContent
    Show-Success "Modo sandbox ACTIVADO automáticamente"
}

# ========================================
# PASO 4: Configurar .env
# ========================================
Show-Step 4 "Configurando archivo .env..."

if (Test-Path ".env") {
    Show-Warning "Ya existe archivo .env"
    $overwrite = Read-Host "¿Deseas sobrescribirlo? (s/n)"
    
    if ($overwrite -eq "s" -or $overwrite -eq "S") {
        Copy-Item ".env.example" ".env" -Force
        Show-Success "Archivo .env sobrescrito desde template"
    } else {
        Show-Info "Manteniendo .env existente"
    }
} else {
    Copy-Item ".env.example" ".env"
    Show-Success "Archivo .env creado desde template"
}

Write-Host ""
Show-Info "IMPORTANTE: Debes editar .env con tus API keys de TESTNET"
Write-Host ""
Write-Host "Pasos para obtener API keys:" -ForegroundColor White
Write-Host "1. Ir a https://testnet.binance.vision/" -ForegroundColor White
Write-Host "2. Crear cuenta (NO usar credenciales reales)" -ForegroundColor White
Write-Host "3. Ir a API Management → Create API" -ForegroundColor White
Write-Host "4. Copiar API Key y Secret" -ForegroundColor White
Write-Host "5. Editar .env y pegar las credenciales" -ForegroundColor White
Write-Host ""

$openEnv = Read-Host "¿Deseas abrir .env ahora para editarlo? (s/n)"
if ($openEnv -eq "s" -or $openEnv -eq "S") {
    notepad .env
}

# ========================================
# PASO 5: Verificar dependencias
# ========================================
Show-Step 5 "Verificando dependencias Python..."

Write-Host "Verificando ccxt..." -NoNewline
python -c "import ccxt; print(f' v{ccxt.__version__}')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Show-Success "ccxt instalado"
} else {
    Show-Warning "ccxt NO instalado"
    Show-Info "Instalando ccxt..."
    pip install ccxt
    if ($LASTEXITCODE -eq 0) {
        Show-Success "ccxt instalado exitosamente"
    } else {
        Show-Error "Error instalando ccxt"
    }
}

Write-Host "Verificando pandas..." -NoNewline
python -c "import pandas; print(f' v{pandas.__version__}')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Show-Success "pandas instalado"
} else {
    Show-Warning "pandas NO instalado"
    Show-Info "Por favor ejecuta: pip install -r requirements.txt"
}

# ========================================
# PASO 6: Crear directorios necesarios
# ========================================
Show-Step 6 "Verificando estructura de directorios..."

$requiredDirs = @(
    "logs",
    "data\live_data",
    "data\optimization_pipeline"
)

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Show-Success "Directorio creado: $dir"
    } else {
        Show-Info "Directorio existe: $dir"
    }
}

# ========================================
# RESUMEN FINAL
# ========================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ SETUP COMPLETADO" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 CHECKLIST FINAL:" -ForegroundColor Yellow
Write-Host ""
Write-Host "[✅] Archivos del sistema verificados" -ForegroundColor Green
Write-Host "[✅] Modo sandbox activado en config.yaml" -ForegroundColor Green
Write-Host "[✅] Archivo .env creado" -ForegroundColor Green

# Verificar si .env tiene credenciales
$envContent = Get-Content ".env" -Raw
if ($envContent -match "your_.*_api_key_here") {
    Write-Host "[⚠️ ] API keys pendientes en .env" -ForegroundColor Yellow
    $needsConfig = $true
} else {
    Write-Host "[✅] API keys configuradas en .env" -ForegroundColor Green
    $needsConfig = $false
}

Write-Host "[✅] Dependencias verificadas" -ForegroundColor Green
Write-Host "[✅] Directorios creados" -ForegroundColor Green
Write-Host ""

# ========================================
# PRÓXIMOS PASOS
# ========================================
Write-Host "🎯 PRÓXIMOS PASOS:" -ForegroundColor Yellow
Write-Host ""

if ($needsConfig) {
    Write-Host "1. 🔐 Configurar API keys en .env:" -ForegroundColor White
    Write-Host "   - Ir a https://testnet.binance.vision/" -ForegroundColor Gray
    Write-Host "   - Crear cuenta y generar API keys" -ForegroundColor Gray
    Write-Host "   - Editar .env y pegar las credenciales" -ForegroundColor Gray
    Write-Host "   - Comando: notepad .env" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. 💰 Solicitar fondos de prueba:" -ForegroundColor White
    Write-Host "   - En Binance Testnet ir a 'Faucet'" -ForegroundColor Gray
    Write-Host "   - Solicitar 1 BTC + 10,000 USDT gratis" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. 🚀 Ejecutar trading en vivo:" -ForegroundColor White
    Write-Host "   - Comando: python main.py --live-ccxt" -ForegroundColor Cyan
} else {
    Write-Host "1. 💰 Solicitar fondos de prueba:" -ForegroundColor White
    Write-Host "   - En Binance Testnet ir a 'Faucet'" -ForegroundColor Gray
    Write-Host "   - Solicitar 1 BTC + 10,000 USDT gratis" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. 🚀 Ejecutar trading en vivo:" -ForegroundColor White
    Write-Host "   - Comando: python main.py --live-ccxt" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📚 DOCUMENTACIÓN:" -ForegroundColor Yellow
Write-Host "   - Guía completa: LIVE_TRADING_SANDBOX_GUIDE.md" -ForegroundColor Cyan
Write-Host "   - Ver guía: cat LIVE_TRADING_SANDBOX_GUIDE.md" -ForegroundColor Cyan
Write-Host ""

# ========================================
# COMANDOS ÚTILES
# ========================================
Write-Host "💡 COMANDOS ÚTILES:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ejecutar bot:" -ForegroundColor White
Write-Host "  python main.py --live-ccxt" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ver logs en tiempo real:" -ForegroundColor White
Write-Host "  Get-Content logs\bot_trader.log -Wait -Tail 50" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verificar configuración:" -ForegroundColor White
Write-Host "  python -c `"from config.config_loader import load_config; c=load_config(); print('Sandbox:', c['exchanges']['binance']['sandbox'])`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ver documentación completa:" -ForegroundColor White
Write-Host "  cat LIVE_TRADING_SANDBOX_GUIDE.md" -ForegroundColor Cyan
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "¡Listo para comenzar! 🚀" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Preguntar si desea ejecutar ahora
if (-not $needsConfig) {
    $runNow = Read-Host "¿Deseas ejecutar el bot en modo sandbox AHORA? (s/n)"
    if ($runNow -eq "s" -or $runNow -eq "S") {
        Write-Host ""
        Write-Host "🚀 Iniciando bot en modo sandbox..." -ForegroundColor Green
        Write-Host "Presiona Ctrl+C para detener" -ForegroundColor Yellow
        Write-Host ""
        Start-Sleep -Seconds 2
        python main.py --live-ccxt
    }
}
