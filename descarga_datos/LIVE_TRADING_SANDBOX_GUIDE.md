# 🚀 GUÍA COMPLETA: Trading en Vivo con Exchange en Modo Sandbox/Demo

**Fecha**: 09/10/2025  
**Sistema**: BotCopilot SAR v3.0  
**Estrategia**: UltraDetailedHeikinAshiML (81.66% win rate)  
**Modo**: Sandbox/Testnet (Sin dinero real)

---

## 📋 ÍNDICE

1. [Exchanges Soportados con Testnet](#exchanges-soportados)
2. [Configuración Paso a Paso](#configuración-paso-a-paso)
3. [Obtener API Keys de Testnet](#obtener-api-keys)
4. [Configurar config.yaml](#configurar-config)
5. [Configurar .env (Recomendado)](#configurar-env)
6. [Ejecutar Trading en Vivo](#ejecutar-trading)
7. [Monitorear y Verificar](#monitorear)
8. [Solución de Problemas](#troubleshooting)

---

## 🏦 EXCHANGES SOPORTADOS CON TESTNET/SANDBOX {#exchanges-soportados}

### ✅ **BINANCE TESTNET** (RECOMENDADO)
- **Testnet URL**: https://testnet.binance.vision/
- **Faucet**: https://testnet.binance.vision/
- **Ventajas**:
  - Dinero de prueba ilimitado
  - API idéntica a producción
  - Mejor para BNB/USDT (nuestra estrategia)
- **Fondos Iniciales**: 1 BTC + 10,000 USDT gratis

### ✅ **BYBIT TESTNET**
- **Testnet URL**: https://testnet.bybit.com/
- **Faucet**: Fondos automáticos al crear cuenta testnet
- **Ventajas**:
  - Muy similar a producción
  - Buena estabilidad
- **Fondos Iniciales**: 100,000 USDT gratis

### ⚠️ **OTROS EXCHANGES**
- **OKX**: Tiene testnet pero menos documentado
- **Kraken**: NO tiene testnet público
- **Coinbase**: NO tiene testnet público

---

## 🛠️ CONFIGURACIÓN PASO A PASO {#configuración-paso-a-paso}

### OPCIÓN 1: BINANCE TESTNET (RECOMENDADO)

#### Paso 1: Crear Cuenta en Binance Testnet

1. **Ir a Binance Testnet**:
   ```
   https://testnet.binance.vision/
   ```

2. **Crear cuenta** (NO usar credenciales reales de Binance):
   - Email: Usar email temporal o de prueba
   - Contraseña: Crear contraseña segura
   - **⚠️ IMPORTANTE**: Esta cuenta es SOLO para testing, NO usar credenciales reales

3. **Obtener fondos de prueba**:
   - Ir a "Faucet" o "Get Test Funds"
   - Solicitar fondos de prueba (1 BTC + 10,000 USDT)
   - Los fondos se acreditan instantáneamente

#### Paso 2: Generar API Keys

1. **Ir a API Management**:
   - Clic en tu perfil → "API Management"

2. **Crear Nueva API Key**:
   - Label: `BotCopilot-Testing`
   - Permisos:
     - ✅ Enable Reading
     - ✅ Enable Spot & Margin Trading
     - ❌ Enable Withdrawals (DESACTIVAR)
   - Guardar API Key y Secret (solo se muestran una vez)

3. **Restricciones de IP** (Opcional pero recomendado):
   - Agregar tu IP actual para mayor seguridad
   - O dejar "Unrestricted" solo para testing

#### Paso 3: Configurar Bot

**Opción A: Usando .env (MÁS SEGURO - RECOMENDADO)**

1. Crear archivo `.env` en la raíz del proyecto:
```bash
cd c:\Users\javie\copilot\botcopilot-sar\descarga_datos
New-Item -ItemType File -Path .env -Force
```

2. Editar `.env` con tus API keys:
```env
# Binance Testnet API Keys
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here

# Exchange Configuration
ACTIVE_EXCHANGE=binance
SANDBOX_MODE=true
```

**Opción B: Directamente en config.yaml (MENOS SEGURO)**

Editar `config/config.yaml`:
```yaml
active_exchange: binance

exchanges:
  binance:
    api_key: 'your_testnet_api_key_here'
    api_secret: 'your_testnet_api_secret_here'
    enabled: true
    sandbox: true  # 🔥 ACTIVAR MODO SANDBOX
    timeout: 30000
```

**⚠️ CRÍTICO**: Asegurarse de que `sandbox: true` esté activado

---

### OPCIÓN 2: BYBIT TESTNET (ALTERNATIVA)

#### Paso 1: Crear Cuenta en Bybit Testnet

1. **Ir a Bybit Testnet**:
   ```
   https://testnet.bybit.com/
   ```

2. **Registrarse**:
   - Email temporal
   - Contraseña segura
   - Verificar email

3. **Obtener fondos de prueba**:
   - Fondos se acreditan automáticamente (100,000 USDT)

#### Paso 2: Generar API Keys

1. **Ir a API**:
   - Profile → API Management

2. **Crear API Key**:
   - Name: `BotCopilot-Testing`
   - Permisos:
     - ✅ Read
     - ✅ Trade
     - ❌ Withdraw
   - Guardar Key y Secret

#### Paso 3: Configurar Bot

Editar `config/config.yaml`:
```yaml
active_exchange: bybit

exchanges:
  bybit:
    api_key: 'your_bybit_testnet_api_key'
    api_secret: 'your_bybit_testnet_api_secret'
    enabled: true
    sandbox: true  # 🔥 ACTIVAR MODO SANDBOX
    timeout: 30000
```

---

## 🔐 OBTENER API KEYS DE TESTNET {#obtener-api-keys}

### BINANCE TESTNET

1. **URL**: https://testnet.binance.vision/
2. **Login** → **API Management**
3. **Create API**:
   - Label: `BotCopilot-v3`
   - Permissions:
     - ✅ Enable Reading
     - ✅ Enable Spot & Margin Trading
     - ❌ Enable Withdrawals (IMPORTANTE: DESACTIVAR)
4. **Copy API Key y Secret** (solo se muestra una vez)
5. **IP Restriction** (Opcional):
   - Agregar tu IP para seguridad adicional
   - O dejar sin restricción para testing inicial

### BYBIT TESTNET

1. **URL**: https://testnet.bybit.com/
2. **Account** → **API**
3. **Create New Key**:
   - Name: `BotCopilot-v3`
   - Permissions:
     - ✅ Contract Trade
     - ✅ Spot Trade
     - ❌ Withdraw (DESACTIVAR)
4. **Save Key and Secret**

---

## ⚙️ CONFIGURAR CONFIG.YAML {#configurar-config}

### Configuración Completa para Trading en Vivo Sandbox

Editar `descarga_datos/config/config.yaml`:

```yaml
# ========================================
# 🚀 CONFIGURACIÓN TRADING EN VIVO SANDBOX
# ========================================

active_exchange: binance  # binance o bybit

# Configuración de backtesting (usada como referencia para live)
backtesting:
  initial_capital: 500  # Capital inicial (en testnet esto es simulado)
  commission: 0.1  # Comisión por operación (0.1%)
  slippage: 0.05  # Slippage estimado (0.05%)
  timeframe: 4h  # Timeframe para análisis
  
  strategies:
    UltraDetailedHeikinAshiML: true  # ✅ Estrategia activa
  
  symbols:
    - BNB/USDT  # 🔥 Símbolo principal con 81.66% win rate

# ========================================
# 🏦 CONFIGURACIÓN DE EXCHANGES
# ========================================
exchanges:
  binance:
    api_key: ''  # Dejar vacío si usas .env (recomendado)
    api_secret: ''  # Dejar vacío si usas .env (recomendado)
    enabled: true
    sandbox: true  # 🔥 MODO SANDBOX ACTIVADO
    timeout: 30000
    testnet_url: 'https://testnet.binance.vision'  # URL del testnet
    
  bybit:
    api_key: ''  # Dejar vacío si usas .env
    api_secret: ''  # Dejar vacío si usas .env
    enabled: false  # Activar solo si usas Bybit
    sandbox: true  # 🔥 MODO SANDBOX ACTIVADO
    timeout: 30000
    testnet_url: 'https://api-testnet.bybit.com'

# ========================================
# ⚠️ GESTIÓN DE RIESGO (TRADING EN VIVO)
# ========================================
risk:
  risk_percent: 1.0  # 1% de riesgo por operación (conservador para testing)
  max_drawdown_limit: 10.0  # Stop global si drawdown > 10%
  sl_atr_multiplier: 1.5  # Stop Loss basado en ATR
  tp_atr_multiplier: 2.0  # Take Profit basado en ATR

# ========================================
# 🎯 CONFIGURACIÓN DE TRADING EN VIVO
# ========================================
live_trading:
  enabled: true
  mode: 'sandbox'  # 'sandbox' o 'live' (NUNCA cambiar a 'live' sin validación)
  
  # Parámetros de operación
  check_interval: 60  # Revisar señales cada 60 segundos
  risk_per_trade: 0.01  # 1% de capital por trade
  max_positions: 3  # Máximo 3 posiciones simultáneas
  
  # Parámetros de la estrategia (optimizados)
  strategy_params:
    ml_threshold: 0.5
    stoch_overbought: 85
    stoch_oversold: 15
    volume_ratio_min: 1.4
    kelly_fraction: 0.5
    max_concurrent_trades: 3
    max_drawdown: 0.07
    max_portfolio_heat: 0.06
  
  # Horario de operación (24/7 para crypto, pero puedes limitar)
  trading_hours:
    enabled: false  # true para habilitar restricciones horarias
    start_hour: 0
    end_hour: 24
    days: [0, 1, 2, 3, 4, 5, 6]  # Lunes (0) a Domingo (6)
  
  # Notificaciones (opcional)
  notifications:
    enabled: false  # Activar para recibir notificaciones
    email: ''
    telegram_bot_token: ''
    telegram_chat_id: ''

# ========================================
# 📊 PARÁMETROS DE ESTRATEGIA
# ========================================
strategy_params:
  UltraDetailedHeikinAshiML:
    symbol: BNB/USDT
    timeframe: 4h
    
    # ML Parameters
    ml_threshold: 0.5
    
    # Oscillators
    stoch_overbought: 85
    stoch_oversold: 15
    
    # Volume
    volume_ratio_min: 1.4
    
    # Risk Management
    kelly_fraction: 0.5
    max_concurrent_trades: 3
    max_drawdown: 0.07
    max_portfolio_heat: 0.06

# ========================================
# 📈 INDICADORES TÉCNICOS
# ========================================
indicators:
  heikin_ashi:
    enabled: true
    trend_period: 3
    size_comparison_threshold: 1.2
  
  ema:
    enabled: true
    periods: [10, 20, 200]
  
  atr:
    enabled: true
    period: 14
  
  adx:
    enabled: true
    period: 14
    threshold: 25
  
  parabolic_sar:
    enabled: true
    acceleration: 0.02
    maximum: 0.2

# ========================================
# 🗄️ ALMACENAMIENTO
# ========================================
storage:
  path: data
  sqlite_enabled: true
  csv_enabled: true
  cache_enabled: true

# ========================================
# 📝 LOGGING
# ========================================
system:
  name: Bot Trader Copilot
  version: 3.0.0
  log_level: INFO  # DEBUG para más detalles
  log_file: logs/bot_trader.log
  auto_launch_dashboard: false  # Desactivar en live para no interferir
```

---

## 🔐 CONFIGURAR .ENV (RECOMENDADO) {#configurar-env}

### Por qué usar .env:

✅ **Más seguro**: API keys no en repositorio Git  
✅ **Fácil cambio**: Cambiar entre testnet y producción fácilmente  
✅ **Best practice**: Estándar de la industria  

### Crear archivo .env

1. **Crear archivo** en `descarga_datos/.env`:

```powershell
cd c:\Users\javie\copilot\botcopilot-sar\descarga_datos
New-Item -ItemType File -Path .env -Force
```

2. **Editar .env** con tu editor favorito:

```env
# ========================================
# 🔐 BINANCE TESTNET CREDENTIALS
# ========================================
BINANCE_API_KEY=paste_your_testnet_api_key_here
BINANCE_API_SECRET=paste_your_testnet_secret_here

# ========================================
# 🔐 BYBIT TESTNET CREDENTIALS (OPCIONAL)
# ========================================
BYBIT_API_KEY=paste_your_bybit_testnet_api_key_here
BYBIT_API_SECRET=paste_your_bybit_testnet_secret_here

# ========================================
# ⚙️ CONFIGURACIÓN GENERAL
# ========================================
ACTIVE_EXCHANGE=binance
SANDBOX_MODE=true
LOG_LEVEL=INFO

# ========================================
# ⚠️ ADVERTENCIA DE SEGURIDAD
# ========================================
# NUNCA commits este archivo a Git
# NUNCA compartas estas keys públicamente
# SOLO usar en modo SANDBOX/TESTNET
# ========================================
```

3. **Agregar .env al .gitignore**:

```powershell
Add-Content -Path ..\.gitignore -Value "`n# Environment variables`n.env`n*.env"
```

---

## 🚀 EJECUTAR TRADING EN VIVO {#ejecutar-trading}

### Pre-requisitos

✅ API Keys configuradas (testnet)  
✅ `config.yaml` configurado con `sandbox: true`  
✅ `.env` creado (opcional pero recomendado)  
✅ Fondos de testnet disponibles  

### Comandos de Ejecución

```powershell
# 1. Navegar al directorio correcto
cd c:\Users\javie\copilot\botcopilot-sar\descarga_datos

# 2. Activar entorno virtual (si usas uno)
.venv\Scripts\Activate.ps1

# 3. Ejecutar trading en vivo con CCXT (SANDBOX)
python main.py --live-ccxt

# Alternativas con más verbosidad
python main.py --live-ccxt --verbose  # Más logs
python main.py --live-ccxt --debug    # Debug completo
```

### Lo que deberías ver

```
[2025-10-09 20:30:00] INFO: Iniciando BotCopilot SAR v3.0 en modo SANDBOX
[2025-10-09 20:30:01] INFO: Conectando a Binance Testnet...
[2025-10-09 20:30:02] INFO: ✅ Conectado a Binance Testnet
[2025-10-09 20:30:02] INFO: Cargando estrategia: UltraDetailedHeikinAshiML
[2025-10-09 20:30:03] INFO: ✅ Estrategia cargada: Win Rate 81.66% (backtest)
[2025-10-09 20:30:03] INFO: Capital disponible: 10000.00 USDT
[2025-10-09 20:30:04] INFO: Iniciando loop de trading...
[2025-10-09 20:30:04] INFO: Analizando BNB/USDT 4h...
[2025-10-09 20:30:05] INFO: Precio actual BNB/USDT: 580.45 USDT
[2025-10-09 20:30:06] INFO: Sin señales de trading. Esperando próxima vela...
[2025-10-09 20:31:06] INFO: Analizando BNB/USDT 4h...
...
```

---

## 📊 MONITOREAR Y VERIFICAR {#monitorear}

### 1. Verificar Logs en Tiempo Real

```powershell
# Seguir logs en vivo
Get-Content logs\bot_trader.log -Wait -Tail 50

# Buscar errores
Select-String -Path logs\bot_trader.log -Pattern "ERROR" | Select-Object -Last 10

# Buscar trades ejecutados
Select-String -Path logs\bot_trader.log -Pattern "TRADE|ORDER" | Select-Object -Last 20
```

### 2. Verificar en Exchange Testnet

**Binance Testnet**:
1. Login en https://testnet.binance.vision/
2. Ir a "Spot" → "Orders"
3. Ver órdenes abiertas y ejecutadas
4. Verificar balance

**Bybit Testnet**:
1. Login en https://testnet.bybit.com/
2. "Assets" → "Spot Account"
3. Ver órdenes y balance

### 3. Métricas Clave a Monitorear

Durante la primera hora:
- ✅ Conexión estable al exchange
- ✅ Precio actualizado cada minuto
- ✅ Sin errores de API
- ✅ Señales de trading detectadas (si las hay)

Durante las primeras 24 horas:
- ✅ Al menos 1-2 señales generadas
- ✅ Órdenes ejecutadas correctamente
- ✅ Stop Loss y Take Profit configurados
- ✅ Balance actualizado tras trades

### 4. Dashboard de Monitoreo (Opcional)

Si quieres un dashboard visual:

```powershell
# Ejecutar dashboard en paralelo (otra terminal)
python main.py --dashboard-only
```

El dashboard estará en: `http://localhost:8520`

---

## 🔧 SOLUCIÓN DE PROBLEMAS {#troubleshooting}

### Problema 1: "Exchange not connected"

**Causas**:
- API keys incorrectas
- `sandbox: false` en lugar de `true`
- Exchange testnet caído

**Solución**:
```yaml
# Verificar config.yaml
exchanges:
  binance:
    sandbox: true  # ⚠️ DEBE SER TRUE
```

```powershell
# Verificar conexión manual
python -c "import ccxt; exchange = ccxt.binance({'sandbox': True}); print(exchange.load_markets())"
```

### Problema 2: "Invalid API key"

**Causas**:
- API key de producción en lugar de testnet
- Espacios extra en API key/secret
- Permisos incorrectos

**Solución**:
1. Regenerar API keys en testnet
2. Verificar que sean de TESTNET, no producción
3. Copiar sin espacios extras
4. Activar permisos de trading

### Problema 3: "Insufficient balance"

**Causas**:
- No solicitaste fondos del faucet
- Fondos ya gastados en pruebas anteriores

**Solución**:
1. Binance Testnet: Ir a Faucet y solicitar más fondos
2. Bybit Testnet: Los fondos se recargan automáticamente

### Problema 4: "No signals generated"

**Causas**:
- Condiciones de mercado no favorables
- ML threshold muy alto
- Estrategia esperando confirmación de varios indicadores

**Solución**:
1. **Es NORMAL** - La estrategia es conservadora (81.66% win rate)
2. Esperar al menos 4-12 horas para primeras señales
3. Revisar que `ml_threshold: 0.5` (no más alto)
4. Verificar en logs: "Analyzing BNB/USDT..." significa que está funcionando

### Problema 5: "Module not found: ccxt"

**Solución**:
```powershell
pip install ccxt
pip install ccxt[async]
```

### Problema 6: "Rate limit exceeded"

**Causas**:
- Demasiadas llamadas a API

**Solución**:
```yaml
# En config.yaml, aumentar intervalo
live_trading:
  check_interval: 120  # Cambiar de 60 a 120 segundos
```

---

## 📈 PROGRESIÓN RECOMENDADA

### Fase 1: Validación Inicial (Día 1)

✅ Configurar testnet  
✅ Ejecutar bot por 1 hora  
✅ Verificar logs sin errores  
✅ Confirmar conexión estable  

### Fase 2: Primeras Operaciones (Días 2-7)

✅ Dejar bot corriendo 24/7  
✅ Esperar primeras señales de trading  
✅ Verificar ejecución de órdenes  
✅ Validar Stop Loss y Take Profit  

### Fase 3: Análisis de Resultados (Semana 2)

✅ Analizar trades ejecutados (mínimo 10)  
✅ Calcular win rate real vs backtest  
✅ Verificar drawdown máximo  
✅ Ajustar parámetros si es necesario  

### Fase 4: Validación Final (Semana 3-4)

✅ Mínimo 30 trades ejecutados  
✅ Win rate > 75% (objetivo: 81.66%)  
✅ Max Drawdown < 5%  
✅ Sistema estable sin crashes  

### ⚠️ SOLO DESPUÉS DE FASE 4 COMPLETA:
Considerar migrar a producción con capital MÍNIMO

---

## 🎯 CHECKLIST FINAL

Antes de ejecutar, verificar:

```
[ ] ✅ API Keys de TESTNET configuradas (NO producción)
[ ] ✅ sandbox: true en config.yaml
[ ] ✅ .env creado con credenciales seguras
[ ] ✅ .gitignore actualizado para excluir .env
[ ] ✅ Fondos de testnet solicitados y disponibles
[ ] ✅ Exchange testnet accesible desde navegador
[ ] ✅ Estrategia UltraDetailedHeikinAshiML activada
[ ] ✅ Símbolo BNB/USDT configurado
[ ] ✅ risk_percent: 1.0 (conservador)
[ ] ✅ max_positions: 3 (máximo)
[ ] ✅ Logs habilitados y funcionando
```

---

## 🚨 ADVERTENCIAS DE SEGURIDAD

### ⚠️ CRÍTICO

1. **NUNCA** usar API keys de producción en testing
2. **NUNCA** commitear .env a Git
3. **NUNCA** compartir API keys públicamente
4. **SIEMPRE** verificar `sandbox: true` antes de ejecutar
5. **SIEMPRE** desactivar permisos de "Withdraw" en API keys

### 🔒 Best Practices

- Usar .env para credenciales
- Regenerar API keys cada 30 días
- Monitorear logs frecuentemente
- Empezar con risk_percent bajo (1-2%)
- No ejecutar múltiples instancias simultáneamente
- Mantener backup de config.yaml

---

## 📞 SOPORTE Y RECURSOS

### Documentación Exchange Testnet

- **Binance Testnet**: https://testnet.binance.vision/
- **Binance API Docs**: https://binance-docs.github.io/apidocs/spot/en/
- **Bybit Testnet**: https://testnet.bybit.com/
- **CCXT Docs**: https://docs.ccxt.com/

### Logs Importantes

```powershell
# Ver logs completos
cat logs\bot_trader.log

# Buscar trades ejecutados
Select-String -Path logs\bot_trader.log -Pattern "ORDER_FILLED|TRADE_CLOSED"

# Verificar errores
Select-String -Path logs\bot_trader.log -Pattern "ERROR|CRITICAL"
```

---

## ✅ PRÓXIMOS PASOS

Una vez que tengas todo configurado:

1. **Ejecutar**: `python main.py --live-ccxt`
2. **Monitorear**: Ver logs en tiempo real
3. **Verificar**: Check exchange testnet tras 1 hora
4. **Esperar**: Mínimo 24-48h para primeras señales
5. **Analizar**: Revisar resultados tras 7 días

---

**🎯 OBJETIVO**: Validar que la estrategia con **81.66% win rate** en backtest funciona correctamente en entorno live simulado antes de considerar producción.

**⏱️ DURACIÓN RECOMENDADA EN TESTNET**: 2-4 semanas con mínimo 30 trades ejecutados.

---

**Fecha de creación**: 09/10/2025  
**Última actualización**: 09/10/2025  
**Versión**: 1.0  
**Estado**: ✅ COMPLETO Y LISTO PARA USAR
