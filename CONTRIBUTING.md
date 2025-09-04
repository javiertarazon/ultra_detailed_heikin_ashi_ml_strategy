# 🤝 Guía de Contribución - Bot Trader Copilot

¡Gracias por tu interés en contribuir al **Bot Trader Copilot**! Este documento describe cómo puedes ayudar a mejorar el proyecto.

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Configuración del Entorno de Desarrollo](#configuración-del-entorno-de-desarrollo)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Estándares de Código](#estándares-de-código)
- [Proceso de Pull Request](#proceso-de-pull-request)
- [Reportar Issues](#reportar-issues)
- [Tipos de Contribuciones](#tipos-de-contribuciones)

## 🤝 Código de Conducta

Este proyecto sigue un código de conducta para asegurar un entorno colaborativo y respetuoso. Al participar, aceptas:

- **Respeto**: Trata a todos los colaboradores con respeto
- **Inclusividad**: Contribuciones de cualquier persona son bienvenidas
- **Calidad**: Mantén altos estándares de calidad en el código
- **Comunicación**: Sé claro y constructivo en tus comunicaciones

## 🚀 Cómo Contribuir

### 1. **Fork y Clone**
```bash
# Fork el repositorio en GitHub
# Luego clona tu fork
git clone https://github.com/TU_USUARIO/bot-trader-copilot.git
cd bot-trader-copilot
```

### 2. **Crear una Branch**
```bash
# Crea una branch descriptiva
git checkout -b feature/nueva-funcionalidad
# o
git checkout -b fix/error-en-modulo
# o
git checkout -b docs/mejora-documentacion
```

### 3. **Desarrollar**
```bash
# Configura el entorno
python scripts/quick_start.py --setup

# Ejecuta tests antes de cambiar código
python -m pytest tests/

# Desarrolla tu feature/fix
# ...
```

### 4. **Commit y Push**
```bash
# Agrega cambios
git add .

# Commit con mensaje descriptivo
git commit -m "feat: agregar nueva estrategia de trading XYZ

- Implementa lógica de entrada/salida
- Agrega validaciones de riesgo
- Incluye tests unitarios
- Actualiza documentación"

# Push a tu fork
git push origin feature/nueva-funcionalidad
```

### 5. **Pull Request**
- Crea un PR desde tu fork hacia el repositorio principal
- Describe claramente los cambios realizados
- Referencia issues relacionados
- Espera revisión del equipo

## 🔧 Configuración del Entorno de Desarrollo

### **Requisitos Previos**
- Python 3.8+
- Git
- (Opcional) MetaTrader 5 para desarrollo con acciones

### **Configuración Rápida**
```bash
# Clona el repositorio
git clone <repository-url>
cd bot-trader-copilot

# Configuración automática
python scripts/quick_start.py --setup

# Verificar instalación
python scripts/quick_start.py --test
```

### **Configuración Manual**
```bash
# Crear entorno virtual
python -m venv trading_bot_env
source trading_bot_env/bin/activate  # Linux/Mac
# trading_bot_env\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Configurar pre-commit hooks
pre-commit install
```

## 🏗️ Estructura del Proyecto

```
bot-trader-copilot/
├── descarga_datos/          # 🧠 Núcleo del sistema
│   ├── main.py             # 🚀 Punto de entrada
│   ├── core/               # 🔧 Componentes core
│   ├── indicators/         # 📊 Indicadores técnicos
│   ├── strategies/         # 🎯 Estrategias
│   ├── backtesting/        # 📈 Backtesting
│   ├── risk_management/    # 🛡️ Gestión de riesgos
│   ├── utils/              # 🛠️ Utilidades
│   ├── config/             # ⚙️ Configuración
│   └── tests/              # 🧪 Tests
├── scripts/                # 📜 Scripts de utilidad
├── docs/                   # 📚 Documentación
├── data/                   # 💾 Datos (gitignored)
├── logs/                   # 📝 Logs (gitignored)
├── metrics/                # 📊 Métricas (gitignored)
├── requirements.txt        # 📦 Dependencias
├── requirements-dev.txt    # 🔧 Dev dependencies
├── pyproject.toml          # ⚙️ Configuración Python
├── .pre-commit-config.yaml # 🔧 Pre-commit hooks
├── .gitignore             # 🚫 Archivos ignorados
└── README.md              # 📖 Documentación principal
```

## 📏 Estándares de Código

### **Python Style Guide**
- Seguimos **PEP 8** con algunas modificaciones
- Usamos **Black** para formateo automático
- **Flake8** para linting
- **MyPy** para type hints

### **Convenciones de Nombres**
```python
# Clases: PascalCase
class TradingStrategy:
    pass

# Funciones/Métodos: snake_case
def calculate_profit_loss(self):
    pass

# Variables: snake_case
total_profit = 0.0

# Constantes: UPPER_CASE
MAX_DRAWDOWN = 0.50
```

### **Type Hints**
```python
from typing import Optional, List, Dict, Any
import pandas as pd

def process_data(df: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Procesa datos de trading con configuración específica.

    Args:
        df: DataFrame con datos OHLCV
        config: Diccionario de configuración

    Returns:
        DataFrame procesado o None si hay error
    """
    pass
```

### **Documentación**
```python
def complex_function(param1: int, param2: str) -> bool:
    """
    Descripción clara de lo que hace la función.

    Args:
        param1: Descripción del primer parámetro
        param2: Descripción del segundo parámetro

    Returns:
        Descripción del valor de retorno

    Raises:
        ValueError: Cuando los parámetros son inválidos
        ConnectionError: Cuando falla la conexión

    Example:
        >>> result = complex_function(42, "test")
        >>> print(result)
        True
    """
    pass
```

## 🔄 Proceso de Pull Request

### **Plantilla de PR**
```
## Título: [TYPE] Breve descripción

## Descripción
Explicación detallada de los cambios realizados.

## Tipo de Cambio
- [ ] 🐛 Bug fix
- [ ] ✨ Nueva funcionalidad
- [ ] 💥 Breaking change
- [ ] 📚 Documentación
- [ ] 🎨 Estilo/código
- [ ] ✅ Tests
- [ ] 🔧 Configuración

## Checklist
- [ ] Tests pasan localmente
- [ ] Documentación actualizada
- [ ] Código sigue estándares
- [ ] Commits siguen convención
- [ ] No hay conflictos de merge

## Issues Relacionados
Closes #123
Relacionado con #456

## Testing
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Backtesting verificado
- [ ] Performance test
```

### **Convención de Commits**
```
feat: nueva funcionalidad
fix: corrección de bug
docs: cambios en documentación
style: cambios de estilo (formateo, etc.)
refactor: refactorización de código
test: agregar o modificar tests
chore: cambios de mantenimiento
```

### **Etiquetas de PR**
- `bug` - Corrección de errores
- `enhancement` - Mejora de funcionalidad existente
- `feature` - Nueva funcionalidad
- `documentation` - Cambios en documentación
- `breaking-change` - Cambios que rompen compatibilidad
- `work-in-progress` - Trabajo en progreso

## 🐛 Reportar Issues

### **Plantilla de Bug Report**
```markdown
## Descripción del Bug
Breve descripción del problema.

## Pasos para Reproducir
1. Ir a '...'
2. Ejecutar '....'
3. Ver error

## Comportamiento Esperado
Qué debería suceder.

## Comportamiento Actual
Qué sucede en realidad.

## Contexto Adicional
- Versión del sistema: v1.0.0
- Python version: 3.9
- OS: Windows 10
- Configuración específica
- Logs relevantes
```

### **Plantilla de Feature Request**
```markdown
## Resumen
Breve descripción de la funcionalidad solicitada.

## Motivación
Por qué esta funcionalidad sería útil.

## Solución Propuesta
Descripción de la implementación sugerida.

## Alternativas Consideradas
Otras soluciones que se consideraron.

## Contexto Adicional
Cualquier información adicional relevante.
```

## 🎯 Tipos de Contribuciones

### **💻 Desarrollo**
- Implementar nuevas estrategias de trading
- Mejorar algoritmos existentes
- Optimizar performance
- Agregar nuevos indicadores técnicos
- Desarrollar nuevas funcionalidades del core

### **🧪 Testing**
- Escribir tests unitarios
- Crear tests de integración
- Desarrollar tests de performance
- Testing de estrategias de trading

### **📚 Documentación**
- Mejorar README y documentación
- Crear guías de usuario
- Documentar APIs
- Traducir documentación

### **🎨 UI/UX**
- Desarrollar dashboard web
- Crear interfaces de usuario
- Mejorar experiencia de usuario
- Diseñar visualizaciones de datos

### **🔧 DevOps**
- Configurar CI/CD
- Optimizar deployment
- Mejorar infraestructura
- Automatizar procesos

### **📊 Análisis**
- Analizar performance de estrategias
- Optimizar algoritmos
- Mejorar métricas de backtesting
- Research de nuevas estrategias

## 🙏 Reconocimientos

¡Gracias a todos los contribuidores que hacen posible este proyecto!

### **Contribuidores Destacados**
- [Lista de contribuidores principales]

### **Cómo Ser Reconocido**
- Todos los contribuidores aparecen en el CHANGELOG
- Contribuciones significativas se reconocen especialmente
- Menciones en releases y comunicaciones del proyecto

---

## 📞 Contacto

¿Preguntas sobre contribución?
- 📧 Email: contribuciones@bottradercopilot.com
- 💬 Discord: [Enlace al servidor]
- 📋 Issues: [GitHub Issues]

¡Esperamos tus contribuciones! 🚀
