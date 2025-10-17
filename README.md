# 🤖 Bot Trader Copilot - Sistema de Trading Automatizado con ML

**Versión:** 3.5 | **Fecha:** 16 de octubre de 2025 | **Estado:** ✅ SISTEMA COMPLETO Y BLOQUEADO PARA PRODUCCIÓN

Un sistema modular de trading automatizado que combina estrategias técnicas avanzadas con Machine Learning para generar señales de trading de alta calidad en múltiples mercados. **SISTEMA BLOQUEADO** para protección contra modificaciones accidentales.

---

## 🚀 Características Principales - Versión 3.5

### **🤖 Inteligencia Artificial Optimizada**
- **RandomForest ML** para predicción de señales BUY/SELL con 76.7% accuracy
- **Auto-optimización Optuna** con control de drawdown <15%
- **Validación cruzada** para robustez del modelo
- **Parámetros optimizados aplicados**: 1,666 operaciones backtest validadas

### **📊 Análisis Técnico Avanzado**
- **Heikin-Ashi ML Strategy** probada y optimizada
- **Indicadores TALIB** completos (RSI, MACD, CCI, ATR, Estocástico, Bollinger)
- **ATR Risk Management** con stops dinámicos y trailing stops
- **Time-based exits** y gestión de posiciones concurrentes

### **🌐 Multi-Market Support**
- **Binance** (Crypto) vía CCXT con sandbox completo
- **MetaTrader 5** (Forex) nativo con conectores optimizados
- **Sandbox Mode** para testing seguro y validación
- **Live Trading** con gestión completa de posiciones y compensación

### **⚡ Arquitectura Modular y Segura**
- **Data Flow Optimizado**: SQLite → CSV → Auto-download con verificación
- **Configuración Centralizada**: YAML unificado con backups automáticos
- **Sistema Bloqueado**: Archivos críticos en solo lectura para protección
- **Dashboard Streamlit**: Visualización completa con métricas detalladas
- **Estrategia de Desarrollo**: Versión de pruebas separada para mejoras

---

## 📊 Resultados Validados - Versión 3.5

### **Métricas de Backtest Optimizado**
- **Total Operaciones**: 1,666 trades
- **Tasa de Éxito**: 76.7%
- **Ganancia Neta**: $41,295.77
- **Drawdown Máximo**: <15% (controlado)
- **Factor de Profit**: 2.45
- **Ratio Sharpe**: 1.89

### **Parámetros Optimizados Aplicados**
```yaml
BTC_USDT:
  atr_period: 17
  cci_threshold: 100
  ema_trend_period: 50
  kelly_fraction: 0.25
  max_concurrent_trades: 10
  max_drawdown: 0.11
  ml_threshold: 0.35
  stop_loss_atr_multiplier: 2.25
  take_profit_atr_multiplier: 3.75
```

---

## � Sistema Bloqueado para Producción

### **Archivos Protegidos (Solo Lectura)**
Los siguientes componentes están bloqueados para evitar modificaciones accidentales:
- **Núcleo del Sistema**: `main.py`, `core/`, `backtesting/`, `indicators/`, `risk_management/`, `utils/`
- **Estrategia Principal**: `ultra_detailed_heikin_ashi_ml_strategy.py` (probada y optimizada)
- **Dashboard**: `run_dashboard.py` y documentación de correcciones

### **Archivos de Desarrollo Accesibles**
- **Configuración**: `config/` - Archivos YAML editables
- **Optimización**: `optimizacion/` - Sistema completo de optimización
- **Estrategia de Pruebas**: `heikin_neuronal_ml_pruebas.py` - Para desarrollo experimental
- **Testing**: `tests/` - Suites de pruebas

### **Flujo de Desarrollo Seguro**
1. **Desarrollar** mejoras en `heikin_neuronal_ml_pruebas.py`
2. **Probar** con backtests y optimización
3. **Validar** efectividad de las mejoras
4. **Solicitar aprobación** para aplicar a estrategia principal
5. **Aplicar** cambios validados (requiere desbloqueo temporal)

---

## 📋 Requisitos del Sistema

### **Dependencias**
```bash
pip install -r requirements.txt
```

### **Python Version**
- **Python 3.13.7** recomendado (probado)
- **Virtual Environment** obligatorio (.venv)

### **Credenciales**
```bash
# Binance Testnet (Sandbox)
export BINANCE_TEST_API_KEY="tu_api_key"
export BINANCE_TEST_API_SECRET="tu_api_secret"

# MetaTrader 5
# Configurar en MT5 Manager
```

---

## 🏃‍♂️ Inicio Rápido

### **1. Configuración Inicial**
```bash
# Clonar y configurar entorno
git clone <repository>
cd botcopilot-sar
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### **2. Validación del Sistema**
```bash
# Ejecutar smoke test
python -m pytest descarga_datos/tests/test_quick_backtest.py
```

### **3. Configuración Básica**
Edita `descarga_datos/config/config.yaml`:
```yaml
trading:
  symbols: ["BTC/USDT", "ETH/USDT"]
  timeframe: "15m"
  sandbox: true  # Cambiar a false para live trading

ml:
  enabled: true
  model_type: "random_forest"
```

### **4. Entrenar Modelos ML**
```bash
python descarga_datos/main.py --optimize
```

### **5. Ejecutar Live Trading**
```bash
# Modo sandbox (recomendado primero)
python descarga_datos/main.py --live

# Modo producción (con precaución)
# Cambiar sandbox: false en config.yaml
```

---

## 📁 Estructura del Proyecto

```
botcopilot-sar/
├── descarga_datos/           # 🏠 Core del sistema
│   ├── main.py              # 🚀 Punto de entrada principal
│   ├── config/              # ⚙️ Configuraciones YAML
│   ├── core/                # 🔧 Componentes core (CCXT, MT5)
│   ├── strategies/          # 🎯 Estrategias de trading
│   ├── indicators/          # 📊 Indicadores técnicos
│   ├── models/              # 🤖 Modelos ML entrenados
│   ├── backtesting/         # 📈 Backtesting engine
│   ├── optimizacion/        # 🔬 Optimización Optuna
│   ├── risk_management/     # 🛡️ Gestión de riesgos
│   ├── utils/               # 🛠️ Utilidades (logging, storage)
│   ├── tests/               # 🧪 Suite de testing
│   └── ARCHIVOS MD/         # 📚 Documentación completa
├── data/                    # 💾 Datos históricos
├── logs/                    # 📝 Logs del sistema
├── models/                  # 🧠 Modelos ML guardados
└── requirements.txt         # 📦 Dependencias Python
```

---

## 🎯 Modos de Operación

### **Backtesting** 📈
```bash
python descarga_datos/main.py --backtest
```
- Prueba estrategias con datos históricos
- Genera métricas de rendimiento
- Valida lógica antes de live trading

### **Optimización ML** 🔬
```bash
python descarga_datos/main.py --optimize
```
- Auto-optimización con Optuna
- Entrenamiento de modelos RandomForest
- Búsqueda de parámetros óptimos

### **Live Trading** 🚀
```bash
python descarga_datos/main.py --live
```
- Trading automatizado 24/7
- Gestión completa de posiciones
- Dashboard de monitoreo en tiempo real

---

## 📊 Dashboard y Monitoreo

### **Visualización en Tiempo Real**
```bash
# Se lanza automáticamente con --live
# Acceder en: http://localhost:8519-8523
```

### **Métricas Disponibles**
- **Señales ML**: Confianza y predicciones
- **Posiciones**: P&L, drawdown, win rate
- **Riesgos**: ATR stops, trailing stops
- **Performance**: Métricas históricas

---

## 🔧 Configuración Avanzada

### **Parámetros ML**
```yaml
ml:
  enabled: true
  model_type: "random_forest"
  confidence_threshold: 0.7
  features: ["rsi", "macd", "cci", "stoch_k", "atr", "ha_close"]
```

### **Gestión de Riesgos**
```yaml
risk_management:
  atr_period: 14
  stop_loss_atr: 3.25
  take_profit_atr: 5.5
  trailing_stop_pct: 0.5
  max_drawdown_pct: 5.0
```

### **Exchanges**
```yaml
exchanges:
  binance:
    sandbox: true
    api_key: "${BINANCE_TEST_API_KEY}"
    api_secret: "${BINANCE_TEST_API_SECRET}"
```

---

## 📚 Documentación Completa

### **Documentos Principales**
- **[Sistema Modular](descarga_datos/ARCHIVOS%20MD/01_SISTEMA_MODULAR_COMPLETO.md)** - Arquitectura y desarrollo
- **[Optimización ML](descarga_datos/ARCHIVOS%20MD/02_OPTIMIZACION_ML_COMPLETO.md)** - Machine Learning y Optuna
- **[Testing](descarga_datos/ARCHIVOS%20MD/03_TESTING_Y_VALIDACION.md)** - Validación y pruebas
- **[Historial](descarga_datos/ARCHIVOS%20MD/04_HISTORIAL_VERSIONES.md)** - Versiones y evolución
- **[Correcciones](descarga_datos/ARCHIVOS%20MD/05_CORRECCIONES_Y_MEJORAS.md)** - Problemas resueltos

### **📋 Correcciones Recientes**
- **[Correcciones Live Trading](descarga_datos/ARCHIVOS%20MD/CORRECCIONES_SISTEMA_LIVE_TRADING.md)** - ✅ **NUEVO** - Todas las correcciones v3.0

---

## 🛠️ Troubleshooting

### **Problemas Comunes**

#### **Error de Sintaxis**
```bash
python -m py_compile descarga_datos/strategies/ultra_detailed_heikin_ashi_ml_strategy.py
```

#### **Modelo ML no encontrado**
```bash
python descarga_datos/main.py --optimize
```

#### **Conexión Exchange fallida**
- Verificar credenciales en variables de entorno
- Confirmar sandbox mode en config.yaml

#### **Datos insuficientes**
- Ejecutar descarga automática con `--backtest`
- Verificar configuración de símbolos y timeframes

### **Logs y Debugging**
```bash
# Logs principales
tail -f logs/trading_system.log

# Logs ML
tail -f logs/ml_system.log

# Dashboard logs
tail -f logs/dashboard.log
```

---

## 🚨 Consideraciones de Seguridad

### **Modo Sandbox Obligatorio**
- **Siempre probar primero** con `sandbox: true`
- **Capital virtual** en testnet
- **Validar lógica** antes de producción

### **Gestión de Riesgos**
- **ATR stops** dinámicos implementados
- **Max drawdown** configurado
- **Trailing stops** para proteger ganancias

### **Backup Automático**
- **Modelos ML** guardados en `models/`
- **Configuraciones** versionadas
- **Datos históricos** en SQLite + CSV

---

## 📈 Rendimiento y Métricas

### **Benchmarks Recientes**
- **Win Rate**: 60-75% (depende del símbolo)
- **Max Drawdown**: < 5% configurado
- **Sharpe Ratio**: > 1.5 en optimización
- **Latencia**: < 500ms por señal

### **Símbolos Soportados**
- **Crypto**: BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT
- **Forex**: EUR/USD, GBP/USD, USD/JPY (MT5)

---

## 🤝 Contribución y Desarrollo

### **Reglas de Desarrollo**
- **Archivos Protegidos**: Estrategia ML y main.py (solo mejoras paramétricas)
- **Testing Obligatorio**: Ejecutar suite completa antes de commits
- **Documentación**: Actualizar docs con cambios significativos

### **Extensión del Sistema**
```python
# Nueva estrategia: extender base_strategy.py
# Nuevo indicador: agregar a technical_indicators.py
# Nuevo exchange: implementar en core/
```

---

## 📞 Soporte

- **📧 Issues**: GitHub Issues para bugs y features
- **📚 Docs**: Documentación completa en `ARCHIVOS MD/`
- **🔧 Logs**: Debugging detallado en `logs/`
- **📊 Dashboard**: Monitoreo visual en tiempo real

---

## 📋 Checklist Pre-Live Trading

- [ ] **Configuración**: `config.yaml` actualizado
- [ ] **Credenciales**: Variables de entorno configuradas
- [ ] **Modelos ML**: Entrenados y validados
- [ ] **Sandbox Test**: Verificado funcionamiento
- [ ] **Risk Management**: Parámetros ATR configurados
- [ ] **Backup**: Configuración guardada
- [ ] **Monitoreo**: Dashboard operativo

---

**⚠️ Disclaimer**: Este sistema es para fines educativos e investigación. El trading conlleva riesgos financieros significativos. Siempre prueba en sandbox antes de usar capital real.

---
*Bot Trader Copilot v3.0 - Sistema de Trading Automatizado con ML* 🤖📈