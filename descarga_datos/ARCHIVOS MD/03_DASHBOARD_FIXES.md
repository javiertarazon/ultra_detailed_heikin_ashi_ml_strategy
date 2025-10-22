# Guía de Correcciones y Bloqueos - Dashboard Trading Bot

## Fecha de Creación
16 de octubre de 2025

## Resumen Ejecutivo
Este documento registra todas las correcciones realizadas en el sistema de dashboard del bot de trading para evitar errores recurrentes. El dashboard está funcionando correctamente con Streamlit y debe mantenerse bloqueado para evitar modificaciones accidentales.

## Correcciones Realizadas

### 1. Problemas de Ejecución de Streamlit
**Problema**: El dashboard no se ejecutaba correctamente, mostrando warnings sobre "missing ScriptRunContext" y ejecutándose en "bare mode".

**Solución Implementada**:
- Usar `python -m streamlit run run_dashboard.py` en lugar de ejecutar el script Python directamente
- Agregar parámetros `--server.port 8519 --server.headless true` para ejecución en background
- Crear script personalizado `run_dashboard.py` que importa y ejecuta el dashboard correctamente

**Código Correcto**:
```bash
python -m streamlit run run_dashboard.py --server.port 8519 --server.headless true
```

### 2. Problemas de Carga de Datos
**Problema**: Errores en la carga de resultados JSON desde `data/dashboard_results/`.

**Solución Implementada**:
- Verificar existencia de archivos antes de cargar
- Implementar manejo de errores robusto en `load_results()`
- Usar rutas absolutas para acceso a archivos

### 3. Configuración de Puerto
**Problema**: Conflictos de puerto al ejecutar múltiples instancias.

**Solución Implementada**:
- Puerto fijo 8519 para dashboard
- Verificación de disponibilidad de puerto antes de iniciar
- Fallback automático a puertos alternativos (8520-8523)

## Lo Que NO Se Debe Modificar

### ❌ Estructura del Dashboard
- NO modificar `descarga_datos/utils/dashboard.py` sin aprobación
- NO cambiar la función `load_results()` que carga datos JSON
- NO alterar las rutas de archivos en `data/dashboard_results/`

### ❌ Comando de Ejecución
- NO ejecutar `python run_dashboard.py` directamente
- SIEMPRE usar `python -m streamlit run run_dashboard.py`
- NO cambiar los parámetros `--server.port 8519 --server.headless true`

### ❌ Archivos de Resultados
- NO modificar archivos JSON en `data/dashboard_results/`
- NO alterar la estructura de datos de backtest
- NO cambiar nombres de archivos de resultados

### ❌ Dependencias
- NO actualizar Streamlit sin testing exhaustivo
- NO cambiar versiones de Plotly o Pandas
- Mantener requirements.txt intacto

## Script Bloqueado: run_dashboard.py

Este archivo está bloqueado para modificaciones. Contiene:

```python
import streamlit as st
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descarga_datos.utils.dashboard import main

if __name__ == "__main__":
    main()
```

**Razones del bloqueo**:
- Evita ejecución incorrecta que cause warnings
- Mantiene consistencia en la carga del dashboard
- Previene modificaciones accidentales que rompan la funcionalidad

## Protocolo de Modificaciones Futuras

### Para modificar el dashboard:
1. Crear rama separada en Git
2. Documentar cambios propuestos
3. Probar exhaustivamente en entorno local
4. Obtener aprobación antes de merge

### Para ejecutar el dashboard:
1. Usar comando: `python -m streamlit run run_dashboard.py --server.port 8519 --server.headless true`
2. Verificar que no hay procesos Streamlit corriendo en el puerto 8519
3. Abrir navegador en http://localhost:8519

## Métricas de Éxito Actuales

El dashboard muestra correctamente:
- ✅ 1,666 operaciones backtest
- ✅ Ganancia neta: $41,295.77
- ✅ Tasa de éxito: 76.7%
- ✅ Drawdown máximo < 15%
- ✅ Gráficos de rendimiento funcionales

## Contacto para Modificaciones
Para cualquier modificación al dashboard o corrección de errores, contactar al desarrollador principal con evidencia de testing completo.

---

**Estado**: ✅ Dashboard funcionando correctamente - BLOQUEADO PARA MODIFICACIONES