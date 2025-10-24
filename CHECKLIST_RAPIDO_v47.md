# ⚡ CHECKLIST RÁPIDO v4.7 - PRÓXIMA SESIÓN

**Imprime esto o guarda en favoritos**

---

## 📋 AL INICIAR PRÓXIMA SESIÓN

### Paso 1: Validación (1 minuto)
```powershell
python validate_protected_files.py
# Resultado esperado: ✅ TODOS LOS 15 ARCHIVOS VALIDADOS
```

### Paso 2: Leer Documentación (5 minutos)
1. **PRIMERO**: `GUIA_DE_HANDOFF_v47.md` (contiene contexto completo)
2. **LUEGO**: `GUIA_RAPIDA_v47.md` (para comandos rápidos)
3. **REFERENCIA**: `INDICE_MAESTRO_v47.md` (para encontrar MD)

### Paso 3: Validar Funcionalidad (2 minutos)
```powershell
python descarga_datos/main.py --backtest
# Resultado esperado: ~1,600 trades completados
```

---

## 📁 UBICACIONES CLAVE

| Qué necesito | Dónde está |
|--------------|-----------|
| **Scripts de test/análisis** | `descarga_datos/scripts/` |
| **Documentación clasificada** | `descarga_datos/ARCHIVOS MD/` (12 carpetas) |
| **Estrategia principal** | `descarga_datos/main.py` (🔒 PROTEGIDA) |
| **Configuración** | `descarga_datos/config/config.yaml` (🔒 PROTEGIDA) |
| **Guías de referencia** | Raíz del proyecto (6 nuevos archivos) |
| **Índice de todo** | `INDICE_MAESTRO_v47.md` |

---

## ⚡ COMANDOS MÁS USADOS

```powershell
# Validar integridad de archivos core
python validate_protected_files.py

# Ejecutar bot en LIVE
python descarga_datos/main.py --live

# Ejecutar BACKTEST
python descarga_datos/main.py --backtest

# Hacer OPTIMIZACIÓN
python descarga_datos/main.py --optimize

# Ver estadísticas de operaciones
python descarga_datos/scripts/analizar_operaciones.py

# Ejecutar tests rápidos
python -m pytest descarga_datos/tests/test_quick_backtest.py -q
```

---

## 🔒 ARCHIVOS PROTEGIDOS (No modificar sin protocolo)

```
15 ARCHIVOS PROTEGIDOS CON CHECKSUMS:
  🔒 descarga_datos/main.py
  🔒 descarga_datos/config/config.yaml
  🔒 descarga_datos/strategies/ultra_detailed_heikin_ashi_ml_strategy.py
  🔒 descarga_datos/core/ccxt_live_trading_orchestrator.py
  🔒 descarga_datos/core/ccxt_order_executor.py
  🔒 descarga_datos/core/ccxt_live_data.py
  🔒 descarga_datos/utils/storage.py
  🔒 descarga_datos/utils/live_trading_tracker.py
  🔒 descarga_datos/utils/talib_wrapper.py
  🔒 descarga_datos/utils/logger.py
  🔒 descarga_datos/utils/logger_metrics.py
  🔒 descarga_datos/indicators/technical_indicators.py
  🔒 descarga_datos/backtesting/backtesting_orchestrator.py
  🔒 descarga_datos/optimizacion/strategy_optimizer.py
  🔒 descarga_datos/config/config_loader.py

Si necesitas modificar alguno: Leer ARCHIVOS_PROTEGIDOS.md
Después: Ejecutar python validate_protected_files.py --init
```

---

## 📊 ESTADÍSTICAS ACTUALES

| Métrica | Valor |
|---------|-------|
| Scripts organizados | 27 |
| Documentos organizados | 92 |
| Categorías de documentación | 12 |
| Archivos protegidos | 15 |
| Validación checksums | ✅ OK |
| Backtest validado | 1,593 trades, 76.6% win rate ✅ |
| Funcionalidad bot | 100% compatible ✅ |

---

## ❓ ¿QUÉ CAMBIÓ EN v4.7?

✅ **CAMBIÓ**:
- Ubicación de scripts de test/debug (ahora en `descarga_datos/scripts/`)
- Ubicación de documentación MD (ahora en `descarga_datos/ARCHIVOS MD/`)
- Documentación de raíz (ahora con 6 nuevos archivos de referencia)

❌ **NO CAMBIÓ**:
- Estrategia de trading (100% preservada)
- Configuración core (intacta)
- Funcionalidad del bot (100% compatible)
- Datos (sin cambios)

---

## 🚨 SI ALGO FALLA

### Si validate_protected_files.py muestra ❌
```powershell
# Problema: Un archivo protegido fue modificado
# Solución: Ver ARCHIVOS_PROTEGIDOS.md para protocolo
# O: Restaurar desde git si fue cambio no intencional
```

### Si backtest no funciona
```powershell
# Problema: Posible corrupción de datos o config
# Solución: Ejecutar python validate_protected_files.py primero
# Luego: python descarga_datos/main.py --backtest --verbose
```

### Si no encuentro un archivo
```powershell
# Solución: Ver INDICE_MAESTRO_v47.md
# O: Leer GUIA_DE_HANDOFF_v47.md
# O: Buscar en descarga_datos/ARCHIVOS MD/ (92 archivos organizados)
```

---

## ✅ RESUMEN

```
v4.7 = Proyecto más limpio, organizado, protegido
  ✅ 27 scripts consolidados
  ✅ 92 MD organizados en 12 categorías
  ✅ 15 archivos core protegidos
  ✅ Sistema de validación automática
  ✅ Bot 100% funcional
  ✅ Listo para trading live
```

---

**Próxima sesión**: Lee `GUIA_DE_HANDOFF_v47.md` al iniciar  
**Dudas**: Consulta `GUIA_RAPIDA_v47.md` para referencias rápidas  
**Contexto completo**: `PROYECTO_COMPLETADO_v47.md`

🚀 **¡Proyecto v4.7 listo para continuar!** 🚀
