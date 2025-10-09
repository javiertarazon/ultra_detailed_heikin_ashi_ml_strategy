# 🤖 Copilot Instructions for AI Agents - Sistema Centralizado v2.8

## Resumen de Arquitectura Centralizada y Correcciones Críticas

Este sistema implementa una **arquitectura completamente centralizada** con **correcciones metodológicas críticas en ML** para backtesting y análisis de estrategias de trading. **CAMBIO FUNDAMENTAL**: Solo `main.py` es el punto de entrada autorizado, datos desde SQLite como prioridad #1, y eliminación completa de sesgos ML.

### 🎯 COMPONENTES CENTRALIZADOS v2.8

- **🎮 ENTRADA ÚNICA**: Solo `main.py` como punto de acceso autorizado (NO usar otros archivos directamente)
- **🗄️ SQLite-First**: Base de datos como fuente primaria, CSV solo como fallback automático
- **⚙️ Config Centralizada**: `config/config.yaml` controla absolutamente todo el sistema
- **🧠 ML Corregido**: TimeSeriesSplit elimina look-ahead bias, TechnicalIndicators centralizada
- **🔄 Async Nativo**: Funciones críticas (`run_backtest`, `run_optimization_pipeline`) convertidas a async
- **📊 Gestión Inteligente**: `ensure_data_availability()` maneja SQLite → CSV → Descarga automática
- **🎯 Estrategias**: Implementan `run(data, symbol) -> dict` usando indicadores centralizados únicamente
- **📈 Backtesting**: Orquestado por `backtesting_orchestrator.py` (PROTEGIDO - NO modificar)
- **🧠 Optimización**: Pipeline ML en `optimizacion/` con correcciones TimeSeriesSplit aplicadas
- **📊 Resultados**: JSON (`data/dashboard_results/`), dashboard automático en puerto 8520

### 🎯 FLUJOS CENTRALIZADOS OBLIGATORIOS v2.8

1. **Instalación**: 
   ```bash
   pip install -r requirements.txt
   cd descarga_datos  # ⚠️ OBLIGATORIO: Trabajar desde descarga_datos/
   ```

2. **⚠️ PUNTO DE ENTRADA ÚNICO**: 
   ```bash
   # ✅ CORRECTO: Solo usar main.py
   python main.py --backtest-only           # Backtest completo
   python main.py --optimize               # Pipeline ML completo
   python main.py --train-ml               # Solo entrenamiento
   python main.py --data-audit            # Auditoría datos
   
   # ❌ PROHIBIDO: No usar otros puntos de entrada
   python backtesting_orchestrator.py      # ❌ INCORRECTO
   python run_optimization_pipeline2.py    # ❌ INCORRECTO
   ```

3. **Configuración ÚNICA**:
   - Editar SOLAMENTE `config/config.yaml`
   - Activar/desactivar estrategias: `UltraDetailedHeikinAshiML: true/false`
   - El sistema carga automáticamente estrategias activas

4. **Agregar estrategia** (3 pasos únicos):
   ```python
   # Paso 1: Crear strategies/mi_estrategia.py
   from indicators.technical_indicators import TechnicalIndicators  # ✅ USAR CENTRALIZADA
   
   class MiEstrategia:
       def __init__(self):
           self.indicators = TechnicalIndicators()  # ✅ OBLIGATORIO
           
       def run(self, data, symbol):
           # Usar self.indicators para todos los cálculos
           rsi = self.indicators.calculate_rsi(data)  # ✅ CORRECTO
           return {...}
   
   # Paso 2: Registrar en backtesting_orchestrator.py (UNA línea)
   'MiEstrategia': ('strategies.mi_estrategia', 'MiEstrategia'),
   
   # Paso 3: Activar en config.yaml  
   strategies:
     MiEstrategia: true
   ```

5. **Validación OBLIGATORIA**:
   ```bash
   python validate_modular_system.py              # Validar sistema
   python -m pytest tests/test_system_integrity.py -v  # Tests
   ```

6. **Ejecución CENTRALIZADA**:
   ```bash
   python main.py --backtest-only  # ✅ Dashboard auto-launch puerto 8520
   ```

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

**Principio fundamental:** "Agregar estrategias = Solo 3 pasos, sin tocar backtester/main/dashboard".

### 🛡️ RESTRICCIONES CRÍTICAS Y CONVENCIONES v2.8

#### ❌ **ARCHIVOS PROTEGIDOS - NO MODIFICAR**:
```bash
# NÚCLEO PROTEGIDO (No tocar)
main.py                             # ✅ Punto de entrada único
backtesting/backtesting_orchestrator.py  # ✅ Orquestador protegido
backtesting/backtester.py           # ✅ Motor backtesting
utils/storage.py                    # ✅ StorageManager centralizado
utils/logger.py                     # ✅ Logger centralizado
core/downloader.py                  # ✅ AdvancedDataDownloader
indicators/technical_indicators.py  # ✅ TechnicalIndicators centralizada
optimizacion/ml_trainer.py          # ✅ ML con TimeSeriesSplit
```

#### ✅ **PERMITIDO MODIFICAR**:
- **Estrategias**: Crear nuevas en `strategies/` usando TechnicalIndicators centralizada
- **Configuración**: Solo `config/config.yaml` para activar/desactivar funciones
- **Risk Management**: `risk_management/risk_management.py`
- **Nuevos módulos**: Independientes que no alteren arquitectura central

#### 🎯 **REGLAS METODOLÓGICAS CRÍTICAS**:
- **Datos Reales**: Solo datos reales normalizados. Prohibido sintéticos o simulaciones
- **Backtesting Fiel**: Métricas exactas sin alteraciones. No favorecer estrategias artificialmente  
- **Dashboard Exacto**: Reflejar métricas del backtest sin modificaciones adicionales
- **ML Sin Sesgos**: Solo TimeSeriesSplit, prohibida validación con train_test_split estático
- **Indicadores Únicos**: Solo usar `self.indicators = TechnicalIndicators()` - prohibida duplicación
- **SQLite-First**: Siempre verificar SQLite primero, CSV como fallback automático
- **Async Obligatorio**: Funciones críticas deben ser async para centralización
- **Testing Real**: No crear archivos test temporales, solucionar problemas directamente
- **Logging Centralizado**: Solo `utils/logger.py` y `logs/bot_trader.log`
- **Validación Obligatoria**: `validate_modular_system.py` tras cada cambio relevante

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

### 🚨 ERRORES CRÍTICOS Y FALLAS COMUNES - LECCIONES APRENDIDAS

Esta sección documenta todos los errores críticos encontrados y corregidos durante el desarrollo. **LEER OBLIGATORIAMENTE** antes de cualquier modificación para evitar repetir fallas.

#### ❌ **ERROR 1: Features Mismatch en ML Prediction (CRÍTICO)**
**Problema**: `ValueError: X has 23 features, but RandomForestClassifier is expecting 21 features`
- **Causa**: `expected_features` hardcoded como 21 en lugar de dinámico
- **Archivo**: `strategies/ultra_detailed_heikin_ashi_ml_strategy.py`
- **Línea**: `expected_features = 21` (hardcoded)
- **Solución**: Cambiar a `expected_features = len(features.columns)`
- **Impacto**: Impide predicciones ML durante backtest y optimización
- **Prevención**: Nunca hardcodear número de features, siempre usar `len(features.columns)`

#### ❌ **ERROR 2: Scaler Not Fitted (CRÍTICO)**
**Problema**: `NotFittedError: This StandardScaler instance is not fitted yet`
- **Causa**: Scaler guardado sin fitting o mismatch entre training y prediction
- **Archivo**: `strategies/ultra_detailed_heikin_ashi_ml_strategy.py`
- **Método**: `predict_signal()`
- **Solución**: Validar scaler.is_fitted_ antes de usar, re-fit si necesario
- **Impacto**: Falla completa de predicciones ML
- **Prevención**: Siempre validar `scaler.is_fitted_` antes de `transform()`

#### ❌ **ERROR 3: ML Re-training con Labels Continuos (CRÍTICO)**
**Problema**: `ValueError: Unknown label type: continuous. Maybe you are trying to fit a classifier, which expects discrete classes on a regression target with continuous values.`
- **Causa**: Intentar re-entrenar modelo con `pd.Series([0.5])` (continuo) en clasificador
- **Archivo**: `strategies/ultra_detailed_heikin_ashi_ml_strategy.py`
- **Código problemático**: `model.fit(features_scaled, pd.Series([0.5] * len(features_scaled)))`
- **Solución**: ELIMINAR código de re-entrenamiento, usar confianza neutral (0.5) como fallback
- **Impacto**: Crash completo durante optimización Optuna
- **Prevención**: Nunca intentar re-entrenar modelos en producción, solo fallback a valores neutrales

#### ❌ **ERROR 4: Optimización con Trials Incompletos**
**Problema**: Configurado 150 trials pero solo ejecuta 100
- **Causa**: Interrupciones durante optimización o límites de tiempo
- **Archivo**: `config/config.yaml`
- **Config**: `optimization.n_trials: 150`
- **Resultado**: Optimización incompleta, parámetros subóptimos
- **Prevención**: Monitorear progreso de optimización, verificar trials completados vs configurados

#### ❌ **ERROR 5: Resultados de Optimización Inválidos**
**Problema**: Valores imposibles (Win Rate: 334.69%, Max Drawdown: -87.80%)
- **Causa**: Errores durante trials de optimización generan resultados corruptos
- **Archivo**: `data/optimization_results/*/optimization_report.md`
- **Impacto**: Parámetros optimizados inválidos, backtest con parámetros erróneos
- **Prevención**: Validar resultados de optimización antes de usar, verificar rangos lógicos

#### ❌ **ERROR 6: Labels NaN en ML Training**
**Problema**: Labels contienen NaN causando "continuous labels" en clasificadores
- **Causa**: `create_labels()` genera NaN cuando `future_returns` está entre -0.005 y 0.005
- **Archivo**: `optimizacion/ml_trainer.py`
- **Método**: `create_labels()`
- **Solución**: `labels.dropna()` después de crear labels
- **Impacto**: Modelos ML entrenados con datos incompletos
- **Prevención**: Siempre filtrar NaN de labels antes del entrenamiento

#### ❌ **ERROR 7: Mismatch entre Training y Prediction Features**
**Problema**: Features diferentes entre entrenamiento y predicción
- **Causa**: `prepare_features()` no idéntico en training vs prediction
- **Archivos**: `optimizacion/ml_trainer.py` vs `strategies/ultra_detailed_heikin_ashi_ml_strategy.py`
- **Solución**: Usar EXACTAMENTE el mismo código de features en ambos lugares
- **Impacto**: Modelos inutilizables en producción
- **Prevención**: Copiar literalmente código de features del trainer a la estrategia

#### ⚠️ **REGLAS DE ORO PARA EVITAR ERRORES ML**
1. **Nunca hardcodear números de features** - usar `len(features.columns)`
2. **Validar scaler antes de usar** - `hasattr(scaler, 'mean_')` o `scaler.is_fitted_`
3. **No re-entrenar modelos en producción** - solo fallbacks seguros
4. **Filtrar NaN de labels** - `labels.dropna()` obligatorio
5. **Features idénticos** - mismo código en training y prediction
6. **Validar resultados** - rangos lógicos antes de usar parámetros
7. **Monitorear trials** - verificar completitud de optimización

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
