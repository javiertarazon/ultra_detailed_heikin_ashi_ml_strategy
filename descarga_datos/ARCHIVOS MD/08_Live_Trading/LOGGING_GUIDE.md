# Guía de Implementación del Sistema de Logging Centralizado

## Objetivo

Este documento describe la implementación del sistema de logging centralizado para el Bot Trader Copilot. El sistema ha sido diseñado para estandarizar todas las operaciones de logging en la aplicación, eliminar inconsistencias y proporcionar una interfaz unificada para todas las partes del sistema.

## Estructura del Sistema de Logging

### Archivos Principales

1. **utils/logger.py**: Contiene la configuración centralizada y funciones principales de logging.
2. **utils/logger_metrics.py**: Contiene funciones auxiliares para métricas y tiempos de ejecución.

### Funciones Principales

- **initialize_system_logging()**: Inicializa el sistema de logging global. Debe ser llamada una sola vez al inicio de la aplicación.
- **setup_logging()**: Configura el sistema de logging con parámetros simples. (Uso interno)
- **setup_logger()**: Configura un logger específico para un componente.
- **get_logger()**: Obtiene un logger con el nombre especificado. Esta es la función principal que debe usarse en todos los módulos.

## Integración en Módulos Existentes

Para integrar el sistema de logging centralizado en los módulos existentes, siga estos pasos:

### 1. Importar el módulo y obtener un logger

```python
from utils.logger import get_logger

# Obtener un logger específico para el módulo
logger = get_logger(__name__)
```

### 2. Reemplazar los loggers existentes

Reemplazar:
```python
import logging
logger = logging.getLogger(__name__)
```

Por:
```python
from utils.logger import get_logger
logger = get_logger(__name__)
```

### 3. Para clases, inicializar el logger en el constructor

```python
def __init__(self, ...):
    self.logger = get_logger(__name__)
```

### 4. Uso de funcionalidades de métricas

```python
from utils.logger_metrics import log_execution_time

start_time = time.time()
# Operación a medir
result = do_something()
# Registrar tiempo de ejecución
execution_time = log_execution_time(logger, "Operación", start_time)
```

## Niveles de Logging

- **DEBUG**: Información detallada para diagnóstico.
- **INFO**: Información general sobre el flujo del programa.
- **WARNING**: Advertencias que no afectan la ejecución normal.
- **ERROR**: Errores que no detienen el programa pero afectan a una funcionalidad.
- **CRITICAL**: Errores críticos que pueden detener el programa.

## Estandarización de Mensajes de Log

Para mantener la consistencia, siga estas recomendaciones:

1. Use oraciones completas con puntuación.
2. Para operaciones importantes, use prefijos como [START], [END], [ERROR], etc.
3. Para tiempos de ejecución, use el formato "X completado en Y segundos"
4. Para errores, incluya siempre el tipo de excepción y detalles.

## Ejemplos de Uso

### Logging básico

```python
from utils.logger import get_logger
logger = get_logger(__name__)

# Diferentes niveles de log
logger.debug("Información detallada para diagnóstico")
logger.info("Iniciando proceso...")
logger.warning("Advertencia: datos incompletos")
logger.error("Error al procesar archivo")
logger.critical("Error crítico: base de datos no disponible")
```

### Métricas de ejecución

```python
import time
from utils.logger import get_logger
from utils.logger_metrics import log_execution_time

logger = get_logger(__name__)

start_time = time.time()
# Operación
result = process_data()
# Log del tiempo de ejecución
log_execution_time(logger, "Procesamiento de datos", start_time)
```

### Logging de operaciones por lotes

```python
from utils.logger import get_logger
from utils.logger_metrics import log_batch_operation

logger = get_logger(__name__)

# Después de procesar un lote
log_batch_operation(logger, "Importación de datos", 
                   total=100, success=95, errors=5)
```

## Recomendaciones

1. Evite crear loggers manualmente. Use siempre get_logger().
2. No modifique los handlers de logging directamente.
3. En modo producción, mantenga el nivel de logging en INFO.
4. Para desarrollo y depuración, use DEBUG.

## Ruta del Archivo de Log

Por defecto, los logs se guardan en: `logs/bot_trader.log`