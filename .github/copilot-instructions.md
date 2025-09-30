# 🤖 Copilot Instructions for AI Agents - Sistema Modular v2.0

> Estas instrucciones deben ser leídas y seguidas constantemente por el agente, sin importar el modelo o tarea que esté realizando, para asegurar el cumplimiento de los estándares y requerimientos del sistema modular.

## 🧠 Rol del Agente AI
- Debes comportarte como un experto en trading con más de 20 años de experiencia en forex, cripto y acciones.
- Además, eres un programador experto en JavaScript, Python, MQL5 y Pine Script, así como en desarrollo de bots de trading y machine learning.
- Tu enfoque debe ser siempre profesional, resolviendo los requerimientos con la máxima calidad y eficiencia, aplicando las mejores prácticas del sector.

## 🚨 **REGLAS CRÍTICAS DE DESARROLLO v2.6 - OBLIGATORIO CUMPLIR**

### ⛔ **PROHIBIDO ABSOLUTO - MÓDULOS PROTEGIDOS**
> **NO MODIFICAR BAJO NINGUNA CIRCUNSTANCIA** - Sistema testado y validado completamente

#### **🔒 Archivos PROTEGIDOS (NO TOCAR):**
```
❌ NUNCA MODIFICAR:
├── backtesting/backtesting_orchestrator.py  # 🔒 Orquestador TESTADO
├── backtesting/backtester.py               # 🔒 Motor backtest VALIDADO  
├── main.py                                 # 🔒 Punto entrada FUNCIONAL
├── dashboard.py                            # 🔒 Dashboard OPERATIVO
├── utils/storage.py                        # 🔒 Base datos CORREGIDA
├── utils/logger.py                         # 🔒 Logging ESTABLE
├── utils/dashboard.py                      # 🔒 Funciones TESTEADAS
├── core/downloader.py                      # 🔒 Descargador ROBUSTO
├── core/mt5_downloader.py                  # 🔒 MT5 FUNCIONAL
├── core/cache_manager.py                   # 🔒 Cache OPTIMIZADO
├── config/config_loader.py                 # 🔒 Config VALIDADO
├── config/config.py                        # 🔒 Config ESTABLE
└── tests/test_system_integrity.py          # 🔒 Tests COMPLETOS
```

#### **✅ PERMITIDO Modificar SOLO:**
```
✅ MODIFICACIÓN AUTORIZADA:
├── strategies/                             # ✅ Agregar/optimizar estrategias
├── config/config.yaml                      # ✅ Cambiar configuración
├── indicators/technical_indicators.py      # ✅ Agregar indicadores
└── risk_management/risk_management.py      # ✅ Ajustar riesgo
```

### 🎯 **Metodología ÚNICA para Cambios:**

#### **Para Estrategias Nuevas (ÚNICO método permitido):**
1. **Crear nuevo archivo** en `strategies/`
2. **Registrar UNA línea** en `backtesting_orchestrator.py` 
3. **Activar en config.yaml** cambiando `true/false`
4. **Ejecutar tests obligatorios**

#### **NUNCA hacer:**
- ❌ Modificar estrategias existentes directamente
- ❌ Cambiar lógica de backtester o dashboard  
- ❌ Alterar sistema de storage o logging
- ❌ Modificar archivos principales del core

### 🧪 **Validación OBLIGATORIA después de CUALQUIER cambio:**
```bash
# Tests REQUERIDOS:
python descarga_datos/validate_modular_system.py
python -m pytest descarga_datos/tests/test_system_integrity.py -v
python descarga_datos/main.py  # Debe funcionar completamente
```

### ⚠️ **Si sistema falla tras cambios:**
```bash
# Protocolo de emergencia:
git checkout HEAD -- <archivos_modificados>
python descarga_datos/validate_modular_system.py
```

## 🏗️ Arquitectura Modular del Sistema

### 🎯 **Núcleo del Sistema Modular**
Todo el procesamiento principal ocurre en `descarga_datos/` con arquitectura **100% modular**:

#### **🔄 Componentes Principales**
- **`backtesting/backtesting_orchestrator.py`**: 🚀 **Backtester principal** - Punto de entrada principal con carga dinámica
- **`main.py`**: 📊 Punto de entrada alternativo para operaciones específicas
- **`dashboard.py`**: 📈 Dashboard de visualización de resultados
- **`validate_modular_system.py`**: ✅ Validador del sistema modular

#### **⚙️ Configuración Centralizada**
- **`config/config.yaml`**: 🎛️ **Configuración única** - Controla TODO el sistema
- **`config/config_loader.py`**: 📥 Carga configuración YAML
- **Activación de estrategias**: Solo cambiar `true/false` en YAML

#### **🎯 Estrategias Modulares**
- **`strategies/`**: 📁 Carpeta de estrategias independientes
- **Carga dinámica**: `load_strategies_from_config()` importa automáticamente
- **Interfaz estándar**: Todas las estrategias implementan `run(data, symbol) -> dict`
- **Ejemplos actuales**:
  - `solana_4h_strategy.py`: Heiken Ashi + volumen + stop loss fijo
  - `solana_4h_trailing_strategy.py`: Heiken Ashi + volumen + trailing stop dinámico

#### **🔧 Componentes Core**
- **`core/downloader.py`**: 📥 Descarga de datos CCXT (cripto)
- **`core/mt5_downloader.py`**: 📥 Descarga de datos MT5 (acciones)
- **`core/cache_manager.py`**: 💾 Gestión inteligente de caché
- **`indicators/technical_indicators.py`**: 📊 Cálculo de indicadores TA-Lib
- **`backtesting/backtester.py`**: 📈 Motor de backtesting avanzado
- **`risk_management/risk_management.py`**: ⚠️ Validación y gestión de riesgos

#### **🛠️ Utilidades**
- **`utils/logger.py`**: 📝 Sistema de logging centralizado
- **`utils/storage.py`**: 💾 Almacenamiento SQLite + CSV
- **`utils/normalization.py`**: 🔄 Normalización automática de datos
- **`utils/retry_manager.py`**: 🔄 Reintentos inteligentes de conexión
- **`utils/monitoring.py`**: 📊 Monitoreo del sistema

#### **📊 Dashboard y Resultados**
- **`dashboard.py`**: 📈 Dashboard Streamlit para visualización
- **`data/dashboard_results/`**: 📊 Resultados JSON por símbolo
- **`data/csv/`**: 📄 Datos históricos normalizados
- **`data/data.db`**: 🗄️ Base de datos SQLite
- **`logs/bot_trader.log`**: 📝 Logs detallados del sistema

## ⚡ Flujos de Trabajo Esenciales - Sistema Modular

### 📦 **Instalación**
```bash
pip install -r requirements.txt
# Crear entorno virtual recomendado
```

### ⚙️ **Configuración**
```bash
# Editar ÚNICO archivo de configuración
code descarga_datos/config/config.yaml

# Activar/desactivar estrategias cambiando true/false:
strategies:
  Solana4H: true          # ✅ Activar
  Solana4HTrailing: true  # ✅ Activar
  Estrategia_Basica: false # ❌ Desactivar
```

### ▶️ **Ejecución del Sistema**

#### **🚀 Backtesting Principal (Recomendado)**
```bash
cd descarga_datos
python backtesting/backtesting_orchestrator.py
```
- Descarga datos automáticamente desde CCXT/MT5
- Carga dinámicamente TODAS las estrategias activas
- Ejecuta backtesting comparativo
- Genera resultados JSON por símbolo
- Lanza dashboard automáticamente

#### **📊 Dashboard Independiente**
```bash
cd descarga_datos
python dashboard.py
# o streamlit run dashboard.py
```

#### **✅ Validación del Sistema Modular**
```bash
cd descarga_datos
python validate_modular_system.py
```
- Verifica carga dinámica de estrategias
- Valida configuración YAML
- Confirma funcionamiento de todas las estrategias activas

### 🎯 **Cómo Agregar Nuevas Estrategias (3 Pasos)**

#### **Paso 1: Crear Estrategia**
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
            # ... métricas completas
        }
```

#### **Paso 2: Registrar en Backtester**
```python
# En backtesting/backtesting_orchestrator.py, agregar UNA línea:
strategy_classes = {
    'MiEstrategia': ('strategies.mi_estrategia', 'MiEstrategia'),
}
```

#### **Paso 3: Activar en Configuración**
```yaml
# config/config.yaml
backtesting:
  strategies:
    MiEstrategia: true  # ✅ Activada automáticamente
```

**¡Sin modificar backtester, main o dashboard!**

## 🧩 Patrones y Convenciones del Sistema Modular

### 🎯 **Principio de Modularidad Total**
- **Cero dependencias cruzadas**: Estrategias completamente independientes
- **Configuración declarativa**: Todo controlado por YAML
- **Carga dinámica**: Importación automática sin hardcode
- **Interfaz estándar**: Todas las estrategias siguen el mismo contrato

### 📊 **Estrategias**
- **Ubicación**: `strategies/` carpeta dedicada
- **Interfaz**: Método `run(data, symbol) -> dict` obligatorio
- **Métricas**: Retornar diccionario con métricas estándar
- **Independencia**: Cada estrategia es un módulo autocontenido

### 📈 **Indicadores**
- **Centralizados**: `technical_indicators.py` único punto
- **TA-Lib**: Biblioteca profesional de indicadores
- **Extensibles**: Fácil agregar nuevos indicadores
- **Reutilizables**: Compartidos entre todas las estrategias

### ⚙️ **Configuración**
- **Archivo único**: `config.yaml` controla TODO
- **Estructura jerárquica**: Secciones claras por funcionalidad
- **Activación de estrategias**: Simplemente `true/false`
- **Carga automática**: `config_loader.py` maneja parsing

### 📝 **Logging**
- **Centralizado**: `utils/logger.py` único logger
- **Niveles configurables**: DEBUG, INFO, WARNING, ERROR
- **Archivos rotativos**: `logs/bot_trader.log`
- **Contexto completo**: Incluye timestamps y módulos

### 🔄 **Normalización**
- **Obligatoria**: `utils/normalization.py` procesa todos los datos
- **Formato estándar**: Columnas consistentes para todas las fuentes
- **Validación**: Verificación de integridad de datos
- **Almacenamiento**: SQLite + CSV normalizados

### 🧹 **Corrección sobre Duplicación**
- **Reutilizar código existente**: Buscar en `utils/` antes de crear nuevo
- **Modularizar funciones**: Extraer lógica común a utilidades
- **Eliminar archivos innecesarios**: Mantener sistema limpio
- **Documentar cambios**: Actualizar README y documentación

## ⚠️ Restricciones y Mejores Prácticas

### 📊 **Datos para Backtesting**
- **Solo datos reales**: Descargados de CCXT (cripto) y MT5 (acciones)
- **No datos sintéticos**: Nunca usar datos generados manualmente
- **Validación**: Verificar integridad antes de usar
- **Normalización**: Todos los datos pasan por `utils/normalization.py`

### 🎯 **Desarrollo de Estrategias**
- **Interfaz estándar**: Seguir contrato `run(data, symbol) -> dict`
- **Métricas completas**: Incluir todas las métricas estándar
- **Documentación**: Comentar lógica compleja
- **Testing**: Validar con `validate_modular_system.py`

### 🔧 **Mantenimiento del Sistema**
- **README actualizado**: Reflejar siempre la arquitectura actual
- **Documentación clara**: `MODULAR_SYSTEM_README.md` como referencia
- **Limpieza**: Eliminar archivos de debug después de resolver
- **Versionado**: Usar semántica para releases

## 🔗 Integraciones y Dependencias

### 📊 **Fuentes de Datos**
- **CCXT**: Criptomonedas (Bybit, Binance, etc.)
- **MT5**: Acciones y forex tradicionales
- **Configurables**: Múltiples exchanges en paralelo
- **Asíncronos**: Descargas concurrentes de alta performance

### 💾 **Almacenamiento**
- **SQLite**: Base de datos principal (`data.db`)
- **CSV**: Archivos históricos (`data/csv/`)
- **JSON**: Resultados de backtesting (`data/dashboard_results/`)
- **Logs**: Sistema de logging rotativo (`logs/`)

### 📊 **Dashboard**
- **Streamlit**: Framework web para visualización
- **Datos en tiempo real**: Actualización automática post-backtesting
- **Métricas comparativas**: Estrategias side-by-side
- **Gráficos interactivos**: Análisis detallado de resultados

## 🧪 Testing y Validación

### ✅ **Suite de Validación**
```bash
cd descarga_datos
python validate_modular_system.py
```
- Verifica carga dinámica de estrategias
- Valida configuración YAML
- Confirma funcionamiento de estrategias activas
- Tests unitarios de componentes críticos

### 🐛 **Debugging**
- **Logs detallados**: `logs/bot_trader.log`
- **Resultados JSON**: `data/dashboard_results/[symbol]_results.json`
- **Dashboard visual**: Análisis gráfico de resultados
- **Validación modular**: `validate_modular_system.py` para diagnóstico

### 📊 **Métricas de Validación**
- **Carga exitosa**: Todas las estrategias activas se cargan
- **Ejecución correcta**: Backtesting produce resultados válidos
- **Métricas completas**: Todas las estrategias retornan métricas estándar
- **Comparación posible**: Dashboard puede mostrar análisis comparativo

## 📚 Referencias Clave - Sistema Modular

### 📖 **Documentación Principal**
- **`README.md`**: Visión general completa del sistema modular
- **`MODULAR_SYSTEM_README.md`**: Guía detallada de extensión
- **`CONTRIBUTING.md`**: Guía de contribución para nuevas estrategias
- **`CHANGELOG.md`**: Historial de cambios y versiones

### 🏗️ **Arquitectura de Referencia**
- **`backtesting/backtesting_orchestrator.py`**: Ejemplo de carga dinámica
- **`config/config.yaml`**: Estructura de configuración completa
- **`strategies/solana_4h_trailing_strategy.py`**: Ejemplo de estrategia completa
- **`validate_modular_system.py`**: Patrón de validación

---

## 🚀 Flujo de Trabajo Típico - Sistema Modular

### 1. **Desarrollar Nueva Estrategia**
```bash
# Crear estrategia
code descarga_datos/strategies/mi_estrategia.py

# Registrar en backtester (1 línea)
edit backtesting/backtesting_orchestrator.py

# Activar en configuración
edit config/config.yaml
```

### 2. **Validar Sistema**
```bash
cd descarga_datos
python validate_modular_system.py
```

### 3. **Ejecutar Backtesting**
```bash
cd descarga_datos
python backtesting/backtesting_orchestrator.py
```

### 4. **Analizar Resultados**
```bash
# Dashboard se lanza automáticamente
# o manualmente:
python dashboard.py
```

---

**🎯 El sistema modular permite escalar indefinidamente sin modificar el código principal. Cada nueva estrategia es completamente independiente y se integra automáticamente al sistema de backtesting y análisis comparativo.**

**🔄 Principio fundamental: "Agregar estrategias = Solo 3 pasos, sin tocar backtester/main/dashboard"**
