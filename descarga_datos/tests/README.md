# Sistema de Tests Consolidado v2.8

Este directorio contiene herramientas de testing y verificación consolidadas para el sistema de trading.
Los tests han sido organizados y simplificados para facilitar el mantenimiento y ejecución.

## Herramientas Principales

### 1. Tests Consolidados

- **data_verification.py**: Herramientas unificadas para verificación de datos
  - Verificación rápida de estado de datos
  - Auditoría completa de datos
  - Verificación de integridad

- **sqlite_diagnostics.py**: Diagnóstico y análisis de la base de datos SQLite
  - Diagnóstico básico de tablas
  - Análisis detallado de datos
  - Verificación de integridad
  - Exportación a CSV

- **ml_training_tools.py**: Herramientas de entrenamiento ML consolidadas
  - Entrenamiento de modelos individuales
  - Entrenamiento en lote
  - Validación de modelos

### 2. Tests PyTest

- **test_quick_backtest.py**: Tests rápidos del sistema de backtesting
- **test_system_integrity.py**: Tests integrales de integridad del sistema

## Ejecutor Unificado

El archivo `run_tests.py` permite ejecutar cualquier conjunto de tests de forma centralizada.

### Uso

```bash
# Ejecutar todos los tests
python tests/run_tests.py --all

# Ejecutar solo tests rápidos
python tests/run_tests.py --quick

# Ejecutar verificación de datos
python tests/run_tests.py --data

# Ejecutar diagnóstico SQLite
python tests/run_tests.py --sqlite

# Ejecutar herramientas ML
python tests/run_tests.py --ml

# Ejecutar tests de integridad del sistema
python tests/run_tests.py --system
```

## Archivos Obsoletos

Los siguientes archivos han sido consolidados y ya no son necesarios:

- check_all_data.py → data_verification.py
- check_data_status.py → data_verification.py
- check_sqlite_data.py → data_verification.py
- check_sqlite.py → sqlite_diagnostics.py
- check_sqlite_tables.py → sqlite_diagnostics.py
- diagnose_sqlite.py → sqlite_diagnostics.py
- train_all_symbols_ml.py → ml_training_tools.py
- train_ml_individual.py → ml_training_tools.py
- train_simple.py → ml_training_tools.py

## Mantenimiento

Para añadir nuevos tests:

1. Para tests PyTest: Crear archivo con prefijo `test_` y funciones con prefijo `test_`
2. Para herramientas: Añadir función a uno de los scripts consolidados
3. Para ejecutor unificado: Actualizar `run_tests.py` si es necesario