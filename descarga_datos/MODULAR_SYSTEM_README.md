# Sistema Modular de Estrategias - Guía de Extensión

## 🎯 Objetivo

El sistema ha sido diseñado para ser **completamente modular**. Esto significa que puedes agregar nuevas estrategias simplemente:

1. **Creando el archivo de estrategia** en la carpeta `strategies/`
2. **Configurándola** en `config/config.yaml`
3. **Sin modificar** el código de `backtester`, `main` o `dashboard`

## 🏗️ Arquitectura Modular

### Componentes Principales

```
descarga_datos/
├── strategies/           # 📁 Carpeta de estrategias
│   ├── solana_4h_strategy.py
│   ├── solana_4h_trailing_strategy.py
│   └── [nuevas estrategias aquí]
├── config/
│   └── config.yaml       # ⚙️ Configuración centralizada
└── run_backtesting_batches.py  # 🔄 Backtester modular
```

### Sistema de Carga Dinámica

El backtester utiliza `load_strategies_from_config()` que:

1. **Lee la configuración** desde `config.yaml`
2. **Importa dinámicamente** las estrategias activas
3. **Instancia las clases** automáticamente
4. **Maneja errores** gracefully

## 🚀 Cómo Agregar una Nueva Estrategia

### Paso 1: Crear la Estrategia

Crea un archivo en `strategies/` con este formato:

```python
# strategies/mi_nueva_estrategia.py
import numpy as np
import pandas as pd
import talib

class MiNuevaEstrategia:
    def __init__(self, parametro1=valor_default, parametro2=valor_default):
        self.parametro1 = parametro1
        self.parametro2 = parametro2

    def calculate_signals(self, df):
        # Lógica de señales
        # Retorna DataFrame con señales
        pass

    def run(self, data, symbol):
        # Lógica principal de backtesting
        # Debe retornar dict con métricas estándar
        return {
            'total_trades': int,
            'winning_trades': int,
            'losing_trades': int,
            'win_rate': float,
            'total_pnl': float,
            'max_drawdown': float,
            'sharpe_ratio': float,
            'profit_factor': float,
            'symbol': str,
            'trades': list,
            # ... otras métricas
        }
```

### Paso 2: Configurar en YAML

Agrega la estrategia en `config/config.yaml`:

```yaml
backtesting:
  strategies:
    MiNuevaEstrategia: true  # o false para desactivar
```

### Paso 3: Registrar en el Sistema

Edita `run_backtesting_batches.py` y agrega al diccionario `strategy_classes`:

```python
strategy_classes = {
    'Estrategia_Basica': ('strategies.ut_bot_psar', 'UTBotPSARStrategy'),
    'Estrategia_Compensacion': ('strategies.ut_bot_psar_compensation', 'UTBotPSARCompensationStrategy'),
    'Solana4H': ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
    'Solana4HTrailing': ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
    'MiNuevaEstrategia': ('strategies.mi_nueva_estrategia', 'MiNuevaEstrategia'),  # ← Agregar aquí
}
```

## ✅ Ventajas del Sistema Modular

- **🔧 Mantenibilidad**: Cambios localizados
- **🚀 Escalabilidad**: Fácil agregar nuevas estrategias
- **🛡️ Robustez**: Errores en una estrategia no afectan otras
- **📊 Flexibilidad**: Activación/desactivación por configuración
- **🔍 Debugging**: Logging detallado de carga de estrategias

## 🧪 Validación

Ejecuta `validate_modular_system.py` para verificar que todo funciona:

```bash
cd descarga_datos
python validate_modular_system.py
```

## 📋 Estrategias Implementadas

| Estrategia | Archivo | Estado | Descripción |
|------------|---------|--------|-------------|
| Solana4H | `solana_4h_strategy.py` | ✅ Activa | Heiken Ashi + Volumen |
| Solana4HTrailing | `solana_4h_trailing_strategy.py` | ✅ Activa | Heiken Ashi + Trailing Stop |
| UT Bot PSAR | `ut_bot_psar.py` | 🔧 Configurable | Estrategia base |
| Compensación | `ut_bot_psar_compensation.py` | 🔧 Configurable | Con sistema de compensación |

## 🎯 Próximos Pasos

1. **Agregar más estrategias** siguiendo el patrón modular
2. **Crear métricas específicas** por tipo de estrategia
3. **Implementar optimización automática** de parámetros
4. **Desarrollar sistema de comparación** visual entre estrategias

---

**Nota**: Este sistema garantiza que el código principal (`backtester`, `main`, `dashboard`) nunca necesite modificaciones para agregar nuevas estrategias, manteniendo la estabilidad y modularidad del sistema.</content>
<parameter name="filePath">c:\Users\javie\copilot\botcopilot-sar\descarga_datos\MODULAR_SYSTEM_README.md