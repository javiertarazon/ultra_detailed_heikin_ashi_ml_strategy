# 📑 ÍNDICE DE ARCHIVOS - REFERENCIA RÁPIDA v4.7

## 🎯 Archivos de Inicio Rápido

```bash
# Ejecutar bot en LIVE
python descarga_datos/main.py --live

# Ejecutar backtest
python descarga_datos/main.py --backtest-only

# Ver dashboard
python descarga_datos/tests/run_dashboard.py

# Validar cambios
python validate_protected_files.py
```

---

## 📂 ESTRUCTURA DEL PROYECTO

### 🏠 DIRECTORIO RAÍZ
```
✅ validate_protected_files.py        - Script de validación de archivos core
✅ run_bot.bat                        - Ejecutador bot (Windows)
✅ start_live_ccxt.bat               - Start live CCXT (Windows)
✅ run_bot.sh                        - Ejecutador bot (Linux/Mac)
✅ requirements.txt                  - Dependencias Python
✅ README.md                         - Documentación principal
✅ .protected_checksums.json         - Checksums de archivos protegidos
✅ .env, .env.example                - Variables de entorno
```

### 📖 DOCUMENTACIÓN (RAÍZ)
```
✅ ARCHIVOS_PROTEGIDOS.md            - Política de protección de archivos
✅ ESTRUCTURA_DEPURADA.md            - Estructura completa del proyecto
✅ GUIA_RAPIDA_v47.md                - Referencia rápida y comandos
✅ RESUMEN_DEPURACION_v47.md         - Cambios realizados en v4.7
✅ CHANGELOG_v47.md                  - Registro detallado de cambios
✅ FIX_SIGNAL2_RESOLUTION.md         - Documentación de fix Signal 2
```

---

## 🤖 NÚCLEO DEL BOT - `descarga_datos/`

### 🔒 CORE - ORQUESTACIÓN PRINCIPAL (PROTEGIDO)

**Archivo**: `main.py` 🔒
- Punto de entrada principal
- Orquesta: live, backtest, optimize
- Manejo de signals
- Logging y error handling

**Archivo**: `config/`
```
config_loader.py 🔒         - Cargador de configuración YAML
config.yaml 🔒              - Parámetros optimizados de estrategia
config_*.yaml               - Variantes y backups
```

**Directorio**: `core/` 🔒 PROTEGIDO
```
ccxt_live_trading_orchestrator.py    - Orquestación principal CCXT
ccxt_order_executor.py               - Ejecutor de órdenes (riesgo)
ccxt_live_data.py                    - Proveedor de datos tiempo real
mt5_*.py                             - Módulos MT5 (forex)
live_trading_trader.py               - Trader principal
```

---

## 📈 ESTRATEGIAS DE TRADING - `descarga_datos/strategies/` 🔒

**Archivo**: `ultra_detailed_heikin_ashi_ml_strategy.py` 🔒
- Estrategia principal ML Heikin Ashi
- Indicadores: ATR, RSI, Stochastic, CCI, EMA, SAR
- Señales de entrada/salida
- Entrenamiento ML en modelos/

**Archivo**: `base_strategy.py`
- Clase base abstracta para estrategias

**Archivo**: `machine_learning_strategy.py`
- Estrategia base con ML

---

## 📊 INDICADORES TÉCNICOS - `descarga_datos/indicators/` 🔒

**Archivo**: `technical_indicators.py` 🔒
- ATR (Average True Range)
- RSI, Stochastic, CCI
- EMA, Heikin Ashi
- SAR (Stop And Reverse)
- Señales customizadas

---

## ⚠️ GESTIÓN DE RIESGOS - `descarga_datos/risk_management/` 🔒

```
atribute_based_position_sizing.py   - Tamaño de posición
risk_metrics.py                     - Métricas de riesgo
position_validator.py               - Validación de posiciones
```

---

## 🧪 BACKTESTING - `descarga_datos/backtesting/`

```
backtesting_orchestrator.py 🔒     - Orquestador de backtest
backtester.py                       - Motor de backtesting
live_data_backtester.py            - Backtest con datos live
historical_data_loader.py          - Cargador de datos históricos
performance_analyzer.py            - Análisis de rendimiento
```

---

## 🔍 OPTIMIZACIÓN - `descarga_datos/optimizacion/`

```
strategy_optimizer.py 🔒            - Optimizador con Optuna
run_optimization_pipeline2.py       - Pipeline de optimización
neural_network_train.py             - Entrenamiento de redes
parameter_optimizer.py              - Optimización de parámetros
```

---

## 🛠️ UTILIDADES - `descarga_datos/utils/` 

### 🔒 CORE UTILS (PROTEGIDO)
```
storage.py 🔒                       - Base de datos SQLite + CSV
live_trading_tracker.py 🔒          - Tracker de métricas
talib_wrapper.py 🔒                 - Wrapper de indicadores TALIB
logger.py 🔒                        - Sistema de logging
logger_metrics.py 🔒                - Logging de métricas
```

### ✅ UTILS FUNCIONALES
```
dashboard.py                        - Dashboard Streamlit
market_data_validator.py            - Validador de datos
enhanced_validator.py               - Validador mejorado
normalization.py                    - Normalización de datos
retry_manager.py                    - Gestor de reintentos
enhanced_cache.py                   - Cache mejorado
market_sessions.py                  - Sesiones de mercado
monitoring.py                       - Monitoreo
standardize_logging.py              - Logging estándar
live_trading_data_reader.py         - Lector datos live
```

---

## 📂 DATOS - `descarga_datos/data/`

```
csv/                                - Archivos CSV descargados
dashboard_results/                  - Resultados de backtesting
optimization_pipeline/              - Datos de pipeline
optimization_results/               - Resultados de optimización
*.db                                - Bases de datos SQLite
```

---

## 🤖 MODELOS ML - `descarga_datos/models/`

```
BTC_USDT_*.pkl                      - Modelos entrenados ML
README.md                           - Documentación de modelos
model_manager.py                    - Gestor de modelos
```

---

## 📋 SCRIPTS DE TEST/DEBUG - `descarga_datos/scripts/` (37 TOTAL)

### 📊 Análisis de Operaciones
```
✅ analizar_operaciones.py
✅ analizar_log_operaciones.py
✅ analizar_estadisticas_simple.py
✅ analyze_live_operations.py
✅ calculate_trading_metrics.py
```

### 🧪 Tests Diversos
```
✅ test_*.py (9 archivos)
✅ check_*.py (5 archivos)
✅ verify_*.py (3 archivos)
```

### 🔍 Auditoría y Validación
```
✅ audit_*.py (2 archivos)
✅ validate_*.py (1 archivo)
✅ data_audit.py
```

### 🛠️ Setup y Utilidades
```
✅ setup_binance_sandbox.py
✅ convert_btc_to_usdt.py
✅ download_metrics.py
✅ testnet_balance_simulator.py
```

### 📈 Backups
```
✅ dashboard.py.backup
✅ stability_monitor.py
```

---

## ✅ TESTS CORE - `descarga_datos/tests/`

```
run_dashboard.py                    - Ejecutador del dashboard
test_indicators/                    - Tests de indicadores
test_results/                       - Resultados de tests
```

---

## 📁 AUDITORÍAS - `descarga_datos/auditorias/`

```
(Archivos movidos a scripts/)
```

---

## 📋 LOGS - `descarga_datos/logs/`

```
*.log                               - Archivos de logging
```

---

## 🎯 ARCHIVOS PROTEGIDOS (NO MODIFICAR)

### Lista Completa 🔒:
```
1.  main.py
2.  config_loader.py
3.  config.yaml
4.  ccxt_live_trading_orchestrator.py
5.  ccxt_order_executor.py
6.  ccxt_live_data.py
7.  ultra_detailed_heikin_ashi_ml_strategy.py
8.  storage.py
9.  live_trading_tracker.py
10. talib_wrapper.py
11. logger.py
12. logger_metrics.py
13. technical_indicators.py
14. backtesting_orchestrator.py
15. strategy_optimizer.py
```

**Validar con**: `python validate_protected_files.py`

---

## 📊 ESTADÍSTICAS DEL PROYECTO

| Métrica | Cantidad |
|---------|----------|
| Archivos Python core | 50+ |
| Scripts test/debug | 37 |
| Archivos protegidos | 15 |
| Documentos MD | 6 |
| Líneas de código | 100,000+ |
| Bases de datos | 2+ |

---

## 🚀 OPERACIÓN DIARIA

### Inicio del Bot
```bash
cd descarga_datos
python main.py --live
```

### Verificar Resultados
```bash
python tests/run_dashboard.py
# O: http://localhost:8519
```

### Análisis Post-Operación
```bash
python scripts/analizar_operaciones.py
```

### Antes de Cambios
```bash
python validate_protected_files.py
python main.py --backtest-only
```

---

## 📞 REFERENCIAS RÁPIDAS

**Configuración**: `descarga_datos/config/config.yaml`
**Estrategia**: `descarga_datos/strategies/ultra_detailed_heikin_ashi_ml_strategy.py`
**Protección**: `ARCHIVOS_PROTEGIDOS.md`
**Guía Rápida**: `GUIA_RAPIDA_v47.md`
**Estructura**: `ESTRUCTURA_DEPURADA.md`

---

## ✨ ESTADO DEL PROYECTO

✅ **Versión**: 4.7 (24 OCT 2025)
✅ **Depuración**: COMPLETADA
✅ **Protección**: ACTIVA
✅ **Validación**: EXITOSA
✅ **Estado**: LISTO PARA LIVE

---

**Última actualización**: 24 de octubre de 2025
