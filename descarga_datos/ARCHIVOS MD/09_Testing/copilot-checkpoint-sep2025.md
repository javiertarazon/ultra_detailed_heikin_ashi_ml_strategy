# 📋 INSTRUCCIONES DE COPILOT - CHECKPOINT SEP 2025

> **Nota:** Este archivo es una extensión de las instrucciones principales en `.github/copilot-instructions.md` con información actualizada sobre el estado actual del proyecto al checkpoint de septiembre 2025. GitHub Copilot debe leer ambos documentos para tener contexto completo.

## 🚀 ESTADO ACTUAL DEL PROYECTO - CHECKPOINT SEP 2025

El sistema modular Bot Trader Copilot ha alcanzado un estado estable y funcional (v2.5.1) con las siguientes características y configuraciones:

### 📊 Arquitectura y Estructura

El sistema mantiene la arquitectura modular descrita en las instrucciones principales, con las siguientes **ACTUALIZACIONES CLAVE**:

1. **Soporte Multi-Activo Completo:**
   - Acciones: TSLA.US, NVDA.US (vía MT5)
   - Forex: EURUSD, USDJPY (vía MT5)
   - Criptomonedas: SOL/USDT, ETH/USDT, BTC/USDT (vía CCXT)

2. **Orquestador Principal:**
   - `descarga_datos/run_backtesting_batches.py`: Componente principal que gestiona todo el flujo
   - **Características:** Carga dinámica de estrategias, descarga en lotes, backtesting paralelo

3. **Dashboard Actualizado:**
   - Soporte completo para equity curve y drawdown generados desde trades
   - Visualización correcta de todas las estrategias y símbolos

4. **Tests Automatizados:**
   - Validador modular: `validate_modular_system.py`
   - Smoke tests: `tests/test_quick_backtest.py`

### ⚙️ Configuración Activa

La configuración actual en `config.yaml` incluye:

```yaml
# Período de análisis
backtesting:
  timeframe: "4h"
  start_date: "2023-01-01"
  end_date: "2025-01-01"

  # Símbolos activos
  symbols:
    - "TSLA.US"
    - "NVDA.US"
    - "EURUSD"
    - "USDJPY"
    - "SOL/USDT"
    - "ETH/USDT"
    - "BTC/USDT"

  # Estrategias activas (7)
  strategies:
    Estrategia_Basica: true
    Estrategia_Compensacion: true
    Solana4H: true
    Solana4HTrailing: true
    Solana4HRiskManaged: true
    Solana4HOptimizedTrailing: true
    Solana4HEnhancedTrailingBalanced: true
```

### 🧩 Estrategias Disponibles

Las estrategias actualmente disponibles y validadas son:

1. **UTBotPSAR** (alias Estrategia_Basica): Implementada en `ut_bot_psar.py`
2. **UTBotPSARCompensation** (alias Estrategia_Compensacion): Implementada en `ut_bot_psar_compensation.py`
3. **Solana4HStrategy**: Implementada en `solana_4h_strategy.py`
4. **Solana4HTrailingStrategy**: Implementada en `solana_4h_trailing_strategy.py` 
5. **Solana4HRiskManagedStrategy**: Implementada en `solana_4h_risk_managed_strategy.py`
6. **Solana4HOptimizedTrailingStrategy**: Implementada en `solana_4h_optimized_trailing_strategy.py`
7. **Solana4HEnhancedTrailingBalancedStrategy**: Implementada en `solana_4h_enhanced_trailing_balanced_strategy.py`

### 📈 Resultados Actuales

Los resultados de backtesting ya procesados y disponibles:

- **Símbolos Completos:** TSLA.US, NVDA.US, EURUSD, USDJPY, SOL/USDT, ETH/USDT, BTC/USDT
- **Almacenamiento:** `data/dashboard_results/*.json` (un archivo por símbolo + global_summary.json)
- **Dashboard:** Accesible vía `python descarga_datos/dashboard.py` o Streamlit directamente

## 🛠️ PRÓXIMOS PASOS Y MEJORAS PENDIENTES

Estas son las áreas de enfoque para próximas iteraciones:

1. **Optimización de Rendimiento:**
   - Paralelización completa de todos los procesos de backtesting
   - Caché inteligente para reducir descargas innecesarias

2. **Mejoras de Dashboard:**
   - Comparativas cruzadas entre múltiples símbolos y estrategias
   - Exportación de informes en PDF y CSV

3. **Machine Learning:**
   - Integración de módulos de ML para predicción de tendencias
   - Optimización automatizada de parámetros

4. **Trading en Vivo:**
   - Integración con APIs de trading real
   - Sistema de monitoreo y alertas

## 📝 INSTRUCCIONES ESPECÍFICAS PARA COPILOT

Al trabajar en este proyecto después del checkpoint de septiembre 2025, ten en cuenta:

1. **Mantener Modularidad:** NUNCA modificar los componentes core (backtester, downloader) directamente. Crear módulos independientes.

2. **Formato de Estrategias:** Toda nueva estrategia debe:
   - Ubicarse en `strategies/`
   - Implementar el método `run(data, symbol) -> dict`
   - Devolver diccionario con métricas estándar, trades y curva de equity

3. **Configuración:** Siempre modificar `config.yaml` para nuevos parámetros/estrategias, nunca hardcodear.

4. **Testing:** Cada nueva funcionalidad debe incluir tests en `tests/`

5. **Real Data Only:** Usar EXCLUSIVAMENTE datos reales de CCXT y MT5. NUNCA datos sintéticos.

6. **Documentación:** Actualizar README.md y CHANGELOG.md con cada cambio significativo.

7. **Convenciones:**
   - Nombres de estrategia: PascalCase (ej. `Solana4HOptimized`)
   - Nombres de archivo: snake_case (ej. `solana_4h_optimized.py`)
   - Comentarios: Abundantes y descriptivos
   - Logging: Usar sistema central en `utils/logger.py`

## 🔍 REFERENCIAS IMPORTANTES

- [CHECKPOINT_SEP_2025.md](CHECKPOINT_SEP_2025.md) - Detalles del checkpoint actual
- [MODULAR_SYSTEM_README.md](MODULAR_SYSTEM_README.md) - Documentación del sistema modular
- `.github/copilot-instructions.md` - Instrucciones generales del proyecto

---

> Última actualización: 25 de septiembre de 2025