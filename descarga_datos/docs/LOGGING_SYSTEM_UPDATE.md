# Sistema de Logging Centralizado - Actualización v2.8

## Introducción

Como parte de la mejora continua del sistema, se ha implementado un sistema de logging centralizado para estandarizar todas las operaciones de registro y trazas en el Bot Trader Copilot. Este sistema elimina las inconsistencias en el logging y proporciona una interfaz unificada y robusta.

## Características Principales

- **Centralización**: Todas las operaciones de logging se realizan a través de un sistema único.
- **Estandarización**: Formato consistente para todos los mensajes de log.
- **Métricas de rendimiento**: Funciones auxiliares para medir tiempos de ejecución.
- **Manejo de errores mejorado**: Captura y formateo adecuado de excepciones.
- **Compatibilidad Unicode**: Sanitización automática de caracteres problemáticos.

## Cómo Usar

### Importación y Obtención de Logger

```python
from utils.logger import get_logger

# Obtener un logger específico para el módulo
logger = get_logger(__name__)
```

### Inicialización del Sistema (solo en main.py)

```python
from utils.logger import initialize_system_logging

# Inicializar el sistema de logging (una sola vez al inicio)
initialize_system_logging({
    'level': 'INFO',
    'file': 'logs/bot_trader.log'
})
```

### Uso en Clases

```python
def __init__(self):
    self.logger = get_logger(__name__)
    self.logger.info("Inicialización completada")
```

### Métricas de Rendimiento

```python
import time
from utils.logger_metrics import log_execution_time

start_time = time.time()
# Operación a medir
result = process_data()
# Registrar tiempo
log_execution_time(logger, "Procesamiento", start_time)
```

## Herramientas de Conversión

Se ha creado un script para ayudar a estandarizar el logging en el código existente:

```bash
python utils/standardize_logging.py --apply
```

## Documentación

Para más detalles sobre la implementación y uso del sistema de logging centralizado, consulte la guía completa en:

- [docs/LOGGING_GUIDE.md](docs/LOGGING_GUIDE.md)

## Impacto en el Rendimiento

La implementación del sistema centralizado de logging tiene un impacto mínimo en el rendimiento, ya que:

1. Solo se carga un único módulo de logging
2. Los formateadores y handlers se configuran una sola vez
3. La sanitización de mensajes solo se aplica cuando es necesario

## Compatibilidad

El sistema es compatible con todos los componentes existentes y se ha probado en Windows, Linux y macOS.