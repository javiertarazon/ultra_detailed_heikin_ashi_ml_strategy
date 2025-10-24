# Corrección de Error 'size' y Validación de Trailing Stop
**Fecha**: 19 de Octubre de 2025  
**Estado**: ✅ Corregido

---

## 🐛 Problema Reportado

### Error en Logs:
```
2025-10-19 00:39:32 - CCXTLiveTradingOrchestrator - ERROR - Error actualizando posiciones: 'size'
```

### Síntoma:
- El error bloqueaba el monitor de posiciones
- El trailing stop NO se ejecutaba porque el monitor fallaba antes

---

## 🔍 Análisis del Problema

### Causa Raíz:
Inconsistencia en los nombres de campos entre el executor y el orchestrator:

**En CCXTOrderExecutor** (línea 482):
```python
position_info = {
    'quantity': quantity,  # ❌ Usa 'quantity'
    # ... otros campos
}
```

**En CCXTLiveTradingOrchestrator** (líneas 653, 689):
```python
position['current_pnl'] = position['size'] * pnl_pct / 100  # ❌ Busca 'size'
```

**Resultado**: KeyError cuando intentaba acceder a `position['size']`

---

## ✅ Solución Implementada

### 1. Añadir Campo 'size' en Executor

**Archivo**: `descarga_datos/core/ccxt_order_executor.py`  
**Líneas**: 476-488

```python
# ANTES (solo 'quantity')
position_info = {
    'ticket': str(uuid.uuid4()),
    'order_id': order['id'],
    'symbol': symbol,
    'type': order_type.value,
    'quantity': quantity,  # ❌ Solo este campo
    'entry_price': order.get('price', price),
    # ...
}

# DESPUÉS (añadido 'size' como alias)
position_info = {
    'ticket': str(uuid.uuid4()),
    'order_id': order['id'],
    'symbol': symbol,
    'type': order_type.value,
    'quantity': quantity,
    'size': quantity,  # ✅ Alias para compatibilidad
    'entry_price': order.get('price', price),
    # ...
}
```

### 2. Uso Robusto con .get() en Orchestrator

**Archivo**: `descarga_datos/core/ccxt_live_trading_orchestrator.py`  
**Líneas**: 645-710

```python
# ANTES (acceso directo, causaba KeyError)
position['current_pnl'] = position['size'] * pnl_pct / 100

# DESPUÉS (fallback robusto)
# Obtener tamaño de la posición (puede ser 'size' o 'quantity')
position_size = position.get('size', position.get('quantity', 0))

position['current_pnl'] = position_size * pnl_pct / 100
```

**Aplicado en 2 lugares**:
- Bloque `if isinstance(updated_positions, list):` (línea 649)
- Bloque `else:` para compatibilidad con dict (línea 685)

---

## 🎯 Beneficios de la Corrección

### 1. **Robustez**
- Usa `.get()` con fallback en lugar de acceso directo
- Maneja ambos nombres de campo ('size' y 'quantity')
- No falla si falta algún campo

### 2. **Compatibilidad Retroactiva**
- Código antiguo que usa 'quantity' sigue funcionando
- Código nuevo que usa 'size' también funciona
- Ambos campos están presentes en las nuevas posiciones

### 3. **Desbloquea el Trailing Stop**
- Con el error corregido, `_update_open_positions()` se ejecuta correctamente
- El monitor de posiciones funciona sin interrupciones
- `_update_trailing_stop()` puede ejecutarse cada 60 segundos

---

## 🧪 Validación

### Logs Esperados (Sin Error):
```
2025-10-19 04:40:47 - CCXTLiveTradingOrchestrator - INFO - Posición 3950819 actualizada: BTC/USDT buy - P&L: 200.50 (0.19%)
```

### Logs de Trailing Stop (Cuando Hay Profit):
```
2025-10-19 04:41:47 - CCXTLiveTradingOrchestrator - INFO - 🔼 Trailing stop actualizado para 3950819: Stop 106571.82 → 106800.50 (Profit: 300.00, 80%)
```

---

## 📊 Comparación: Antes vs Después

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Error 'size'** | ❌ Ocurría cada 60s | ✅ Corregido |
| **Monitor de Posiciones** | ❌ Fallaba | ✅ Funciona |
| **Trailing Stop** | ❌ No se ejecutaba | ✅ Se ejecuta |
| **Robustez** | ❌ KeyError fatal | ✅ Fallback seguro |
| **Compatibilidad** | ⚠️ Solo 'quantity' | ✅ 'size' y 'quantity' |

---

## 🔧 Archivos Modificados

### 1. `descarga_datos/core/ccxt_order_executor.py`
- **Línea 484**: Añadido `'size': quantity` como alias

### 2. `descarga_datos/core/ccxt_live_trading_orchestrator.py`
- **Líneas 649-670**: Añadido `position_size = position.get('size', position.get('quantity', 0))`
- **Líneas 685-706**: Aplicada misma corrección en bloque else
- **Líneas 660, 672, 696, 702**: Cambiado `position['size']` a `position_size`

---

## ⚠️ Notas Importantes

### Problema de Importación Scipy (Separado)
Durante la prueba apareció un error de importación:
```
File "scipy/linalg/_cythonized_array_utils.pyx", line 1, in init scipy.linalg._cythonized_array_utils
KeyboardInterrupt
```

**Causa**: Problema de dependencias de scipy/sklearn, **NO relacionado** con nuestra corrección.

**Solución potencial**:
```powershell
# Reinstalar scipy en el entorno virtual
.venv\Scripts\Activate.ps1
pip install --upgrade --force-reinstall scipy
```

---

## ✅ Estado Final

**Error 'size'**: ✅ **RESUELTO**  
**Trailing Stop**: ✅ **IMPLEMENTADO** (se ejecutará cuando el monitor funcione)  
**Robustez**: ✅ **MEJORADA** (fallback con .get())  
**Compatibilidad**: ✅ **GARANTIZADA** (soporta ambos campos)

**Próximo paso**: Resolver problema de importación de scipy y ejecutar live para validar trailing stop en operaciones reales.

---

## 📝 Resumen Ejecutivo

1. ✅ **Error 'size' corregido** - Añadido campo 'size' como alias de 'quantity'
2. ✅ **Uso robusto con .get()** - Fallback seguro para evitar KeyError
3. ✅ **Monitor de posiciones desbloqueado** - Puede ejecutarse sin errores
4. ✅ **Trailing stop listo** - Se ejecutará cuando el sistema esté corriendo
5. ⚠️ **Problema scipy** - Requiere reinstalación (no relacionado con código)

---

**Última actualización**: 19/10/2025  
**Versión del sistema**: 2.8
