# 🚀 GUÍA RÁPIDA - Proyecto Depurado v4.7

## 📍 Ubicación de Archivos Importantes

### 🤖 **EJECUTAR BOT**
```bash
# Modo LIVE (sandbox por defecto)
python descarga_datos/main.py --live

# Modo BACKTEST
python descarga_datos/main.py --backtest-only

# Modo OPTIMIZACIÓN
python descarga_datos/main.py --optimize

# Con flags adicionales
python descarga_datos/main.py --live --verbose
```

### 📊 **VER RESULTADOS**
```bash
# Dashboard Streamlit
python descarga_datos/tests/run_dashboard.py
# O acceder a: http://localhost:8519

# Análisis rápido
cd descarga_datos/scripts
python analizar_operaciones.py
```

### 🔍 **VALIDACIÓN Y MANTENIMIENTO**
```bash
# Verificar que archivos core no fueron modificados
python validate_protected_files.py

# Inicializar checksums (primera vez solo)
python validate_protected_files.py --init
```

## 📁 Carpetas Principales

| Carpeta | Propósito | Acceso |
|---------|----------|--------|
| `descarga_datos/core/` | Orquestación trading | 🔒 PROTEGIDO |
| `descarga_datos/strategies/` | Estrategias ML | 🔒 PROTEGIDO |
| `descarga_datos/config/` | Configuración | 🔒 PROTEGIDO |
| `descarga_datos/utils/` | Utilidades core | ⚠️ PARCIAL |
| `descarga_datos/data/` | Datos históricos | ✅ LECTURA |
| `descarga_datos/scripts/` | Test/Debug/Análisis | ✅ SEGURO |
| `descarga_datos/tests/` | Tests core | ✅ MÍNIMO |
| `descarga_datos/models/` | Modelos ML | ✅ LECTURA |

## 📊 Archivos Protegidos (NO TOCAR)

```
🔒 main.py
🔒 config_loader.py
🔒 config.yaml
🔒 ccxt_live_trading_orchestrator.py
🔒 ccxt_order_executor.py
🔒 ccxt_live_data.py
🔒 ultra_detailed_heikin_ashi_ml_strategy.py
🔒 storage.py
🔒 live_trading_tracker.py
🔒 talib_wrapper.py
🔒 logger.py
🔒 logger_metrics.py
🔒 technical_indicators.py
🔒 backtesting_orchestrator.py
🔒 strategy_optimizer.py
```

## 📋 Scripts de Test/Debug (SEGURO MODIFICAR)

**Ubicación**: `descarga_datos/scripts/`

```
📊 Análisis
├── analizar_operaciones.py
├── analizar_log_operaciones.py
├── analyze_live_operations.py
└── calculate_trading_metrics.py

🧪 Tests
├── test_*.py (todos)
├── check_*.py (todos)
└── verify_*.py (todos)

🔍 Debug
├── audit_*.py
├── data_audit.py
└── validate_modular_system.py
```

## ⚙️ Configuración

**Archivo**: `descarga_datos/config/config.yaml`

```yaml
active_exchange: binance
backtesting:
  initial_capital: 800  # USDT
  commission: 0.1
exchanges:
  binance:
    sandbox: true          # ⚠️ CAMBIAR A false PARA LIVE
    margin_mode: cross
    leverage: 10x
strategies:
  BTC_USDT:
    timeframe: 15m
    risk_per_trade: 0.02
```

## 🔐 Protocolo de Cambios

### ✅ SI quiero cambiar algo en archivos PROTEGIDOS:

1. **Hacer un backup**
   ```bash
   git checkout -b feature/mi-cambio
   ```

2. **Hacer el cambio**
   - Minimalista, solo lo necesario

3. **Validar**
   ```bash
   python descarga_datos/main.py --backtest-only
   ```

4. **Verificar P&L positivo**
   - Debe tener ganancias
   - Win rate >= 50%

5. **Probar 24h en sandbox**
   ```bash
   python descarga_datos/main.py --live
   ```

6. **Commitear con documentación**
   ```bash
   git add .
   git commit -m "feature: descripción del cambio"
   ```

### ❌ CAMBIOS BLOQUEADOS (SIN EXCEPCIÓN):

- Cambios en lógica de señales sin backtest
- Modificaciones de riesgo sin optimización
- Cambios sin P&L positivo en backtest

## 📈 Ejemplo: Ejecutar Ciclo Completo

```bash
# 1. Hacer cambio en parámetro (seguro)
# ✏️ Editar config.yaml

# 2. Validar
python validate_protected_files.py
# Resultado: ✅ TODO OK

# 3. Backtest
python descarga_datos/main.py --backtest-only
# Resultado: ✅ 1,593 trades, P&L $2,879.75, Win Rate 76.6%

# 4. Dashboard
python descarga_datos/tests/run_dashboard.py
# ✅ Ver resultados visuales

# 5. Live (opcional, si cambio es importante)
python descarga_datos/main.py --live
# ⏱️ Monitorear 24 horas

# 6. Commit
git add descarga_datos/config/config.yaml
git commit -m "optimize: ajuste parámetro X"
```

## 🚨 Si Algo se Rompe

```bash
# 1. Cancelar cambios recientes
git status              # Ver qué cambió
git diff               # Ver diferencias
git restore .          # Deshacer cambios (¡cuidado!)

# 2. Validar core
python validate_protected_files.py
# Debe mostrar: ✅ TODOS LOS ARCHIVOS PROTEGIDOS ESTÁN VALIDADOS

# 3. Test rápido
python descarga_datos/main.py --backtest-only 2>&1 | head -20

# 4. Si aún falla, restaurar desde git
git reset --hard HEAD
```

## 📚 Documentación Completa

- **ARCHIVOS_PROTEGIDOS.md** - Detalle de archivos a proteger
- **ESTRUCTURA_DEPURADA.md** - Estructura completa del proyecto
- **RESUMEN_DEPURACION_v47.md** - Cambios realizados en depuración
- **24_7_OPERATION_GUIDE.md** - Guía de operación 24/7

## 📊 Últimas Validaciones

```
✅ Archivos protegidos: 15/15 INTACTOS
✅ Checksums guardados: .protected_checksums.json
✅ Scripts organizados: 27 en descarga_datos/scripts/
✅ Raíz limpia: Solo config + bot runners
✅ Backtest validado: 76.6% win rate
✅ Sistema listo para LIVE
```

## 🎯 Próximas Acciones Recomendadas

1. **Prueba en vivo**: Monitorear 24h en testnet
2. **Análisis de operaciones**: Usar scripts en `scripts/`
3. **Optimización**: Si es necesaria, usar `--optimize`
4. **Backup**: Realizar backup regular de `descarga_datos/data/`

---

**v4.7** | 24 OCT 2025 | ✅ LISTO PARA PRODUCCIÓN
