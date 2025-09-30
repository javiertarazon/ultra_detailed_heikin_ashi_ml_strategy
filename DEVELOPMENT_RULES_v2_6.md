# 🚨 **REGLAS CRÍTICAS DE DESARROLLO v2.6** - Bot Trader Copilot

> **📋 DOCUMENTO OBLIGATORIO DE LECTURA**  
> Estas reglas deben ser seguidas estrictamente para preservar la estabilidad del sistema testado y validado.

---

## 🔒 **MÓDULOS PRINCIPALES - PROHIBIDO MODIFICAR**

### ⛔ **REGLA FUNDAMENTAL**
> **Los siguientes módulos han sido COMPLETAMENTE testados, debuggeados y validados. Cualquier modificación puede romper el sistema completo.**

### 📁 **Archivos PROTEGIDOS (NO TOCAR JAMÁS):**

```
❌ PROHIBIDO ABSOLUTO - SISTEMA TESTADO Y FUNCIONAL:

📊 BACKTESTING CORE:
├── backtesting/backtesting_orchestrator.py    # 🔒 Orquestador principal
├── backtesting/backtester.py                  # 🔒 Motor de backtesting  
└── main.py                                    # 🔒 Punto de entrada

📈 DASHBOARD Y VISUALIZACIÓN:
├── dashboard.py                               # 🔒 Dashboard Streamlit
└── utils/dashboard.py                         # 🔒 Funciones dashboard

💾 ALMACENAMIENTO Y DATOS:
├── utils/storage.py                           # 🔒 Base datos SQLite
├── core/downloader.py                         # 🔒 Descarga CCXT
├── core/mt5_downloader.py                     # 🔒 Descarga MT5
└── core/cache_manager.py                      # 🔒 Cache inteligente

⚙️ CONFIGURACIÓN Y SISTEMA:
├── config/config_loader.py                    # 🔒 Carga configuración
├── config/config.py                           # 🔒 Manejo config
├── utils/logger.py                            # 🔒 Sistema logging
└── utils/normalization.py                     # 🔒 Normalización

🧪 TESTING Y VALIDACIÓN:
└── tests/test_system_integrity.py             # 🔒 Suite testing completa
```

### 🎯 **Razones de Protección por Módulo:**

#### **🚀 backtesting_orchestrator.py**
- ✅ **Sistema de carga dinámica** funcionando perfectamente
- ✅ **Manejo de KeyboardInterrupt** implementado correctamente
- ✅ **Dashboard auto-launch** con fallback de puertos
- ❌ **Riesgo**: Romper sistema de orquestación completo

#### **📈 backtester.py** 
- ✅ **Motor de backtesting** validado con 5,465 trades
- ✅ **Métricas normalizadas** y consistentes
- ✅ **Gestión de riesgos** integrada correctamente
- ❌ **Riesgo**: Corromper cálculos financieros

#### **🌐 main.py**
- ✅ **Pipeline end-to-end** funcionando sin fricción
- ✅ **Tolerancia a interrupciones** implementada
- ✅ **Validación automática** del sistema
- ❌ **Riesgo**: Romper flujo principal del sistema

#### **💾 utils/storage.py**
- ✅ **Error SQL metadata** corregido ("9 values for 8 columns")
- ✅ **Esquema de base de datos** validado
- ✅ **Operaciones CRUD** estables
- ❌ **Riesgo**: Errores SQL críticos

#### **📊 dashboard.py**
- ✅ **Auto-launch** funcionando en puertos alternativos
- ✅ **Visualizaciones** coherentes con datos
- ✅ **Función de resumen** testeada completamente
- ❌ **Riesgo**: Pérdida de dashboard automático

---

## ✅ **MÓDULOS PERMITIDOS PARA MODIFICACIÓN**

### 🎯 **ÚNICA área segura para cambios:**

```
✅ AUTORIZADO PARA MODIFICACIÓN:

🔧 ESTRATEGIAS DE TRADING:
├── strategies/                                # ✅ Agregar nuevas estrategias
│   ├── nueva_estrategia.py                   # ✅ Crear estrategias nuevas
│   ├── optimizar_existente_v2.py            # ✅ Versiones optimizadas
│   └── parametros_ajustados.py              # ✅ Ajustar parámetros

📊 INDICADORES TÉCNICOS:
└── indicators/technical_indicators.py        # ✅ Agregar indicadores TA-Lib

⚙️ CONFIGURACIÓN:
├── config/config.yaml                        # ✅ Modificar configuración
└── risk_management/risk_management.py       # ✅ Ajustar parámetros riesgo
```

---

## 🛠️ **METODOLOGÍA SEGURA DE DESARROLLO**

### 🎯 **Para Agregar Nueva Estrategia (ÚNICO método permitido):**

#### **Paso 1: Crear Estrategia**
```python
# 📁 strategies/mi_nueva_estrategia.py
class MiNuevaEstrategia:
    def run(self, data: pd.DataFrame, symbol: str) -> dict:
        """
        INTERFAZ OBLIGATORIA - NO CAMBIAR FIRMA
        """
        # Tu lógica aquí
        return {
            'total_trades': 100,
            'winning_trades': 65,
            'losing_trades': 35,
            'win_rate': 0.65,          # DECIMAL 0-1 OBLIGATORIO
            'total_pnl': 1500.0,
            'max_drawdown': 300.0,
            'profit_factor': 1.8,
            'symbol': symbol,
            'trades': [...],           # Lista de trades
            'equity_curve': [...]      # Curva de equity
        }
```

#### **Paso 2: Registrar en Orquestador (UNA línea ÚNICAMENTE)**
```python
# 📁 backtesting/backtesting_orchestrator.py
# BUSCAR la sección strategy_classes y AGREGAR una línea:

strategy_classes = {
    # ... estrategias existentes (NO TOCAR)
    'MiNuevaEstrategia': ('strategies.mi_nueva_estrategia', 'MiNuevaEstrategia'),  # ← AGREGAR ESTA LÍNEA
}
```

#### **Paso 3: Activar en Configuración**
```yaml
# 📁 config/config.yaml
backtesting:
  strategies:
    # ... estrategias existentes (NO TOCAR)
    MiNuevaEstrategia: true  # ← AGREGAR/CAMBIAR SOLO ESTA LÍNEA
```

### 🔧 **Para Optimizar Estrategia Existente:**

#### **✅ MÉTODO CORRECTO:**
1. **Copiar estrategia existente** con nuevo nombre
2. **Modificar parámetros** en la nueva copia
3. **Registrar como nueva estrategia** 
4. **Testear ambas versiones** side-by-side
5. **Desactivar versión anterior** si nueva es mejor

#### **❌ MÉTODO INCORRECTO (PROHIBIDO):**
1. ❌ Modificar directamente estrategia existente
2. ❌ Cambiar lógica de estrategias ya validadas  
3. ❌ Alterar interfaz `run(data, symbol) -> dict`
4. ❌ Cambiar formato de métricas retornadas

---

## 🧪 **VALIDACIÓN OBLIGATORIA POST-CAMBIOS**

### 📋 **Tests REQUERIDOS después de CUALQUIER cambio:**

```bash
# 1. Validar sistema modular
cd descarga_datos
python validate_modular_system.py

# 2. Ejecutar tests integrales (DEBEN pasar 7/7)
python -m pytest tests/test_system_integrity.py -v

# 3. Ejecutar pipeline completo
python main.py

# 4. Verificar dashboard auto-launch
# Debe abrir automáticamente en http://localhost:8519 o puerto alternativo
```

### ✅ **Criterios de Aceptación Obligatorios:**

```
🎯 TODOS estos criterios DEBEN cumplirse:

✅ Tests Integrales: 7/7 tests deben pasar
✅ Dashboard Auto-Launch: Debe abrirse automáticamente  
✅ Sin Errores SQL: Logs sin errores de metadata
✅ Win Rate Normalizado: Formato decimal (0-1) en todas las estrategias
✅ P&L Coherente: Métricas financieras consistentes
✅ Pipeline Completo: Ejecución end-to-end sin errores
✅ Logs Limpios: Sin warnings críticos en bot_trader.log
```

---

## ⚠️ **CONSECUENCIAS DE MODIFICAR MÓDULOS PROTEGIDOS**

### 💥 **Riesgos Críticos:**

```
🚨 MODIFICAR MÓDULOS PRINCIPALES CAUSARÁ:

💔 FALLAS DEL SISTEMA:
├── Dashboard no se lanza automáticamente
├── Errores SQL de metadata ("9 values for 8 columns")  
├── KeyboardInterrupt rompe pipeline
├── Pérdida de fidelidad en métricas
├── Tests integrity fallan completamente
└── Sistema completamente NO FUNCIONAL

🔄 PROBLEMAS DE DATOS:
├── Inconsistencias en normalización
├── Métricas win_rate corruptas
├── P&L calculations erróneos
└── Base de datos corrompida

⏰ TIEMPO DE RECUPERACIÓN:
├── Horas de debugging requeridas
├── Re-testing completo del sistema
├── Posible pérdida de funcionalidad
└── Reversión compleja de cambios
```

### 🚨 **Protocolo de Emergencia:**

```bash
# Si modificaste módulos protegidos por error:

# 1. REVERTIR INMEDIATAMENTE
git status  # Ver archivos modificados
git checkout HEAD -- <archivo_modificado>

# 2. VERIFICAR FUNCIONAMIENTO
python descarga_datos/validate_modular_system.py

# 3. SI HAY PROBLEMAS, restaurar desde commit funcional
git log --oneline | head -10
git checkout <commit_id_funcional>

# 4. EJECUTAR VALIDACIÓN COMPLETA
python descarga_datos/main.py
```

---

## 📊 **EJEMPLOS DE DESARROLLO CORRECTO**

### ✅ **Caso 1: Nueva Estrategia RSI**

```python
# ✅ CORRECTO: strategies/rsi_strategy.py
class RSIStrategy:
    def run(self, data, symbol):
        # Lógica RSI aquí
        return {
            'total_trades': 150,
            'win_rate': 0.62,  # ✅ Formato decimal
            'total_pnl': 2500.0,
            'symbol': symbol,
            # ... resto métricas estándar
        }

# ✅ CORRECTO: Una línea en backtesting_orchestrator.py
'RSIStrategy': ('strategies.rsi_strategy', 'RSIStrategy'),

# ✅ CORRECTO: config.yaml
RSIStrategy: true
```

### ✅ **Caso 2: Optimizar Estrategia Existente**

```python
# ✅ CORRECTO: Crear nueva versión
# strategies/solana_4h_optimized_v2.py (nuevo archivo)
class Solana4HOptimizedV2:
    def run(self, data, symbol):
        # Parámetros optimizados
        # MISMA interfaz, MEJORES parámetros
        return {...}

# config.yaml
Solana4H: false           # ✅ Desactivar original  
Solana4HOptimizedV2: true # ✅ Activar optimizada
```

### ❌ **Casos INCORRECTOS (PROHIBIDOS):**

```python
# ❌ INCORRECTO: Modificar directamente existente
# strategies/solana_4h_strategy.py (MODIFICAR archivo existente)
# ¡PROHIBIDO!

# ❌ INCORRECTO: Cambiar interfaz
def run(self, data, symbol, new_parameter):  # ¡NO!
    
# ❌ INCORRECTO: Cambiar formato métricas  
return {
    'win_rate': 62  # ❌ Debe ser 0.62 (decimal)
}

# ❌ INCORRECTO: Modificar backtester
# backtesting/backtester.py
# ¡PROHIBIDO COMPLETAMENTE!
```

---

## 🎯 **RESUMEN EJECUTIVO**

### 🔒 **Regla de Oro:**
> **"Solo estrategias y configuración. Nunca tocar el core system."**

### ✅ **Desarrollo Permitido:**
1. **Crear nuevas estrategias** en `strategies/`
2. **Optimizar parámetros** creando versiones nuevas
3. **Modificar configuración** en `config.yaml`
4. **Agregar indicadores** en `technical_indicators.py`

### ❌ **Desarrollo PROHIBIDO:**
1. **Modificar backtester, dashboard, o main.py**
2. **Cambiar sistema de storage o logging**
3. **Alterar orquestador o tests**
4. **Modificar interfaz de estrategias**

### 🧪 **Validación SIEMPRE:**
```bash
python validate_modular_system.py && 
python -m pytest tests/test_system_integrity.py -v &&
python main.py
```

---

**📅 Fecha de Documento**: 30 de Septiembre de 2025  
**👨‍💻 Sistema**: Bot Trader Copilot v2.6  
**🎯 Estado**: SISTEMA COMPLETAMENTE TESTADO Y VALIDADO  
**⚠️ Cumplimiento**: OBLIGATORIO para todos los desarrolladores