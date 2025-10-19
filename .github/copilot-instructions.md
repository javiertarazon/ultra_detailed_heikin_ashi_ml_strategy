# AI Agent Instructions for Bot Trader Copilot

## Architecture Overview
This is a modular trading system with centralized entry via `descarga_datos/main.py`. Key components:
- **Core**: Data providers (CCXT for crypto, MT5 for forex), order executors, live trading orchestrators
- **Strategies**: ML-enhanced strategies like `UltraDetailedHeikinAshiML` using trained models from `models/`
- **Backtesting**: Parallel optimization with Optuna, results in `data/dashboard_results/`
- **Data Flow**: SQLite primary → CSV fallback → auto-download via `utils/storage.py`
- **Config**: Centralized in `descarga_datos/config/config.yaml` (YAML format)

## Critical Workflows
- **Backtest**: `python descarga_datos/main.py --backtest` (uses config.yaml symbols/timeframes)
- **Optimize**: `python descarga_datos/main.py --optimize` (Optuna trials, saves to models/)
- **Live Trading**: `python descarga_datos/main.py --live` (sandbox mode by default in config)
- **Tests**: `python -m pytest descarga_datos/tests/test_quick_backtest.py` (smoke test)
- **Data Download**: Handled automatically by `ensure_data_availability()` in backtests

## Project Conventions
- **Sandbox First**: Always enable `sandbox: true` in exchange configs for testing
- **ML Models**: Train via optimization, load from `models/` using `ModelManager`
- **Indicators**: Use TALIB via `utils/talib_wrapper.py`, fallback to pandas implementations
- **Risk Management**: ATR-based stops, max drawdown limits from config
- **Logging**: Structured via `utils/logger.py`, metrics in `utils/logger_metrics.py`
- **Dependencies**: Install from root `requirements.txt`, uses virtual env `.venv/`

## Integration Points
- **Exchanges**: CCXT for crypto (Binance/Bybit), MT5 for forex
- **Data Sources**: Yahoo Finance fallback, auto-download for missing data
- **External APIs**: Streamlit dashboard, Plotly for visualization
- **Cross-Component**: Strategies call indicators, risk management applies to all trades

## Examples
- Add new strategy: Extend `strategies/base_strategy.py`, register in config.yaml `strategies:` section
- Modify indicators: Update `indicators/technical_indicators.py`, ensure TALIB compatibility
- Change config: Edit `config/config.yaml`, reload via `config_loader.py`

## AI Response Guidelines
- **Language**: All responses must be in Spanish.
- **Code Modifications**: The strategy (`strategies/ultra_detailed_heikin_ashi_ml_strategy.py`) and main modules (`descarga_datos/main.py`, core modules) are blocked from structural modifications. Only parameter improvements are allowed that enhance functionality and profitability without altering the core structure.

## Data Management Rules
- **Centralized Configuration**: All configuration is centralized in `descarga_datos/config/config.yaml`. Use this for all parameters.
- **Data Verification Flow**: When executing any main function requiring historical data (backtest, optimization, data download, data audit, model training), first verify if data exists in the SQLite database. If present, use those data. If not, proceed to download with corresponding modules, process, verify, calculate necessary indicators, and execute the corresponding main function.
- **Data Priority**: SQLite primary → CSV fallback → auto-download. Never skip verification steps.

## Error Prevention Rules
- **Avoid SQL Metadata Errors**: Ensure correct column count in INSERT statements (e.g., 9 values for 9 columns in data_metadata). Reference `utils/storage.py` fixes.
- **Handle KeyboardInterrupt Gracefully**: Implement try/except/finally blocks for shutdown, always launch dashboard if results exist.
- **Normalize Metrics Consistently**: Win rate must be decimal (0-1), not percentage. Validate in tests.
- **Dashboard Port Fallback**: Check port availability (8519-8523) and use fallback if occupied.
- **Async Shutdown Handling**: Manage `asyncio.CancelledError` and close connections properly.
- **Avoid Synthetic Data**: Never use or generate synthetic data; all operations must use real downloaded or live data.

## Critical Error Prevention - v4.0 Lessons Learned

### **🚨 JSON Serialization Errors - PREVENIR SIEMPRE**
**Problema v3.5**: Objetos `datetime` no serializables causaban errores recurrentes al guardar historial de posiciones.
**Lección**: NUNCA guardar objetos datetime directamente en estructuras que serán serializadas a JSON.
**Regla de Oro**:
```
✅ SIEMPRE usar convert_to_json_serializable() antes de json.dump()
✅ Convertir datetime.now() a datetime.now().isoformat() inmediatamente
✅ Validar tipos antes de serialización
✅ Implementar try/catch en todas las operaciones de guardado
```

**Código Problemático (NUNCA REPETIR)**:
```python
# ❌ MAL - Causó errores cada 5 minutos
position['open_time'] = datetime.now()  # Objeto datetime
json.dump(position_history, file)       # ERROR: not JSON serializable

# ✅ BIEN - Implementado en v4.0
position['open_time'] = datetime.now().isoformat()  # String
serializable_data = [convert_to_json_serializable(pos) for pos in position_history]
json.dump(serializable_data, file)
```

### **🚨 Missing Method Errors - IMPLEMENTAR INTERFACES COMPLETAS**
**Problema v3.5**: Método `calculate_position_risk` faltante causaba errores cada 60 segundos.
**Lección**: NUNCA dejar métodos abstractos o interfaces sin implementar.
**Regla de Oro**:
```
✅ Verificar TODOS los métodos requeridos antes de commits
✅ Implementar interfaces 100% completas
✅ Usar @abstractmethod para forzar implementación
✅ Validar llamadas existentes antes de cambios
```

**Prevención**:
```python
# ✅ REQUERIDO - Verificación antes de commits
def validate_implementation(self):
    required_methods = ['calculate_position_risk', 'validate_position', 'update_stops']
    for method in required_methods:
        if not hasattr(self, method):
            raise NotImplementedError(f"Método requerido faltante: {method}")
```

### **🚨 Resource Leak Errors - SHUTDOWN GRACEFUL OBLIGATORIO**
**Problema v3.5**: Conexiones no cerradas causaban memory leaks y warnings.
**Lección**: NUNCA omitir manejo de recursos en shutdown.
**Regla de Oro**:
```
✅ try/except/finally en TODOS los shutdown
✅ await close() en conexiones async
✅ Manejar asyncio.CancelledError explícitamente
✅ Liberar recursos en finally block
```

**Patrón Correcto**:
```python
async def shutdown(self):
    try:
        # Operaciones de cierre
        await self.connection.close()
    except asyncio.CancelledError:
        pass  # Graceful cancellation
    except Exception as e:
        self.logger.error(f"Shutdown error: {e}")
    finally:
        # ✅ SIEMPRE ejecutar - liberación de recursos
        self.resources = None
        self.logger.info("Shutdown completo")
```

### **🚨 Data Type Errors - VALIDACIÓN ESTRICTA**
**Problema v3.5**: Tipos inconsistentes causaban operaciones erróneas.
**Lección**: NUNCA asumir tipos de datos sin validación.
**Regla de Oro**:
```
✅ Validar tipos antes de operaciones numéricas
✅ Normalizar None a valores por defecto
✅ Usar type hints estrictos
✅ Implementar validación de entrada en métodos públicos
```

**Validación Requerida**:
```python
def validate_numeric_input(self, value: Any, default: float = 0.0) -> float:
    """Valida entrada numérica, retorna default si inválido."""
    try:
        result = float(value) if value is not None else default
        return result if not (math.isnan(result) or math.isinf(result)) else default
    except (TypeError, ValueError):
        return default
```

### **🚨 Live Trading Stability - VALIDACIÓN OBLIGATORIA**
**Problema v3.5**: Sistema funcional pero con errores recurrentes.
**Lección**: NUNCA desplegar sin validación completa de estabilidad.
**Regla de Oro**:
```
✅ 24h testing mínimo antes de producción
✅ Validar sin errores JSON en logs
✅ Verificar shutdown graceful
✅ Confirmar integridad de datos
✅ Monitoreo de recursos sin leaks
```

## Data Integrity Rules
- **Real Data Only**: All metrics, results, and strategy executions must derive from real downloaded or live data. No artificial alterations, improvements, or synthetic enhancements.
- **Result Authenticity**: Metrics and results must be the direct outcome of strategy execution on real data, without manipulation or optimization beyond parameter tuning.

Reference: `descarga_datos/ARCHIVOS MD/README.md` for sandbox testing details.