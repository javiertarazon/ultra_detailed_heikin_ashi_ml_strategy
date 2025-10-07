# 🤖 Copilot Instructions for AI Agents - Sistema Modular v2.7

## Resumen de Arquitectura y Flujos

Este sistema implementa una arquitectura modular para backtesting y análisis de estrategias de trading en cripto, forex y acciones. El núcleo está en `descarga_datos/` y todo el flujo es controlado por configuración YAML y carga dinámica de módulos.

- **Estrategias**: Cada estrategia es un archivo independiente en `strategies/` y debe implementar `run(data, symbol) -> dict`.
- **Backtesting**: Orquestado por `backtesting/backtesting_orchestrator.py` (NO modificar), que carga estrategias activas desde `config/config.yaml`.
- **Optimización**: Sistema de optimización ML y parámetros en `optimizacion/` (gestionado desde `main.py`), incluye entrenamiento de modelos y optimización con Optuna.
- **Optimización v2**: Sistema avanzado para estrategias ML2 en `optimizacion/run_optimization_pipeline3.py` con `strategy_optimizer2.py`.
- **Indicadores**: Centralizados en `indicators/technical_indicators.py` (TA-Lib, etc.).
- **Gestión de riesgo**: Ajustable en `risk_management/risk_management.py`.
- **Datos**: Descarga automática desde CCXT (cripto) y MT5 (acciones) vía `core/downloader.py` y `core/mt5_downloader.py`.
- **Resultados**: Salida en JSON (`data/dashboard_results/`), CSV (`data/csv/`), y dashboard interactivo (`dashboard.py`).

### Flujos de Trabajo Esenciales
1. **Instalación**: `pip install -r requirements.txt` (usar entorno virtual recomendado).
2. **Configuración**: Editar solo `config/config.yaml` para activar/desactivar estrategias (`true/false`).
3. **Agregar estrategia**:
   - Crear archivo en `strategies/`.
   - Registrar UNA línea en `backtesting/backtesting_orchestrator.py` (ejemplo: `'MiEstrategia': ('strategies.mi_estrategia', 'MiEstrategia')`).
   - Activar en `config.yaml`.
4. **Validar**: Ejecutar `python descarga_datos/validate_modular_system.py` y `python -m pytest descarga_datos/tests/test_system_integrity.py -v` tras cualquier cambio.
5. **Ejecución**: `python backtesting/backtesting_orchestrator.py` (lanzará dashboard automáticamente).
6. **Optimización**: Ejecutar `python optimizacion/run_optimization_pipeline2.py` desde `descarga_datos/` para optimizar estrategias con ML y Optuna.

### Convenciones y Restricciones
- **NO modificar**: backtester, dashboard, storage, logger, ni archivos core protegidos (ver lista en este archivo). Los módulos principales ya están en funcionamiento y no deben alterarse.
- **Solo modificar**: estrategias (modificar existentes o crear nuevas), indicadores, gestión de riesgo, configuración YAML, o crear nuevos módulos independientes.
- **Datos**: Siempre reales, normalizados por `utils/normalization.py`. Prohibido usar datos sintéticos, simulaciones o cualquier alteración que modifique datos o métricas reales.
- **Backtesting**: Debe ser super realista y fiel a los resultados que generan las estrategias con datos reales. No alterar métricas ni resultados para favorecer estrategias.
- **Dashboard**: Debe reflejar exclusivamente las métricas del backtest sin modificaciones, alteraciones o cálculos adicionales. Mantener formatos correctos y cálculos exactos.
- **Testing**: No crear continuamente archivos test, simples o quick como solución temporal para errores en módulos principales. Solucionar problemas directamente en el código hasta que funcione correctamente.
- **Logging**: Centralizado en `utils/logger.py` y `logs/bot_trader.log`.
- **Validación**: Obligatoria tras cada cambio relevante.

### Ejemplo de Estrategia
```python
# descarga_datos/strategies/mi_estrategia.py
class MiEstrategia:
    def run(self, data, symbol):
        return {
            'total_trades': 100,
            'win_rate': 0.65,
            'total_pnl': 1500.0,
            'max_drawdown': 300.0,
            'profit_factor': 1.8,
            'symbol': symbol,
            'trades': [...],
        }
```

### Referencias Rápidas
- **Documentación**: `README.md`, `MODULAR_SYSTEM_README.md`, `CONTRIBUTING.md`.
- **Validación**: `validate_modular_system.py`, `tests/test_system_integrity.py`.
- **Optimización**: `optimizacion/run_optimization_pipeline2.py` (gestionado desde `main.py`).
- **Optimización v2**: `optimizacion/run_optimization_pipeline3.py` (para estrategias ML2 con NN).
- **ML Trainer**: `optimizacion/ml_trainer.py` (para estrategias ML tradicionales).
- **ML Trainer v2**: `optimizacion/ml_trainer2.py` (para estrategias ML2 con redes neuronales).
- **Ejemplo de estrategia**: `strategies/ultra_detailed_heikin_ashi_ml_strategy.py`.
- **Ejemplo de estrategia ML2**: `strategies/ultra_detailed_heikin_ashi_ml2_strategy.py`.

---

**Principio fundamental:** “Agregar estrategias = Solo 3 pasos, sin tocar backtester/main/dashboard”.
