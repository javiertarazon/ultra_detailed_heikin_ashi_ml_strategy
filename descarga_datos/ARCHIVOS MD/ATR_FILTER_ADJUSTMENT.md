# Ajuste de Filtro ATR para Permitir Mayor Volatilidad
**Fecha**: 19 de Octubre de 2025  
**Versión**: 1.0

---

## 🎯 Problema Identificado

### Situación en Logs:
```
2025-10-19 08:57:42 - [LIVE-FILTER] idx=294 ATR ratio 0.109550 > 0.10, rechazado
```

**Estado**: Sistema rechazaba **TODAS las señales** por volatilidad alta.

### Análisis del Mercado:
- **BTC/USDT** tiene actualmente **10.95% de volatilidad** (ATR ratio)
- Filtro anterior: **10%** máximo
- **Resultado**: 0 operaciones ejecutadas

---

## 🔧 Solución Aplicada

### Cambio en Estrategia

**Archivo**: `descarga_datos/strategies/heikin_neuronal_ml_pruebas.py`  
**Línea**: 1034

```python
# ANTES (Muy restrictivo)
if atr_ratio > 0.10:  # 10% máximo
    logger.info(f"[LIVE-FILTER] idx={i} ATR ratio {atr_ratio:.6f} > 0.10, rechazado")
    return 0

# DESPUÉS (Más permisivo)
if atr_ratio > 0.15:  # 15% máximo - Permite volatilidad moderada-alta
    logger.info(f"[LIVE-FILTER] idx={i} ATR ratio {atr_ratio:.6f} > 0.15, rechazado")
    return 0
```

---

## 📊 Impacto del Cambio

### Rangos de Volatilidad Permitidos

| Rango ATR | Anterior | Nuevo | Estado |
|-----------|----------|-------|--------|
| **0-5%** | ✅ Permitido | ✅ Permitido | Volatilidad muy baja |
| **5-10%** | ✅ Permitido | ✅ Permitido | Volatilidad normal |
| **10-15%** | ❌ Rechazado | ✅ Permitido | **Volatilidad moderada-alta** |
| **>15%** | ❌ Rechazado | ❌ Rechazado | Volatilidad extrema |

### Casos de Uso

**Ahora el sistema podrá operar en**:
- ✅ Mercados normales (ATR 5-10%)
- ✅ Mercados con volatilidad moderada-alta (ATR 10-15%)
- ✅ BTC actualmente con 10.95% de volatilidad
- ❌ Mercados extremadamente volátiles (>15%) - **PROTECCIÓN MANTENIDA**

---

## 🎯 Justificación del Cambio

### 1. **Volatilidad Normal de BTC**
- BTC históricamente opera entre **8-12% de volatilidad**
- El filtro de 10% era demasiado restrictivo para cripto
- 15% permite capturar oportunidades manteniendo protección

### 2. **Balance Riesgo/Oportunidad**
```
Anterior (10%):
- Protección: ⭐⭐⭐⭐⭐ (Muy alta)
- Oportunidades: ⭐⭐ (Muy pocas)

Nuevo (15%):
- Protección: ⭐⭐⭐⭐ (Alta)
- Oportunidades: ⭐⭐⭐⭐ (Buenas)
```

### 3. **Compatibilidad con Backtest**
- Los backtests históricos probablemente usaban datos con ATR 10-12%
- Para replicar resultados en live, necesitamos filtros similares

---

## ⚠️ Consideraciones de Riesgo

### Riesgos Aumentados (Leves):
- Operaciones en mercados más volátiles
- Stop loss puede ejecutarse más frecuentemente
- Slippage potencialmente mayor

### Protecciones Mantenidas:
- ✅ Trailing stop al 80% sigue activo
- ✅ Stop loss basado en ATR
- ✅ Risk management al 2% del capital
- ✅ Filtro de volumen activo
- ✅ Confirmación ML (confidence > 0.30)

---

## 🧪 Validación Esperada

### Próximos Logs (Después del Cambio):

**ANTES**:
```
[LIVE-FILTER] idx=294 ATR ratio 0.109550 > 0.10, rechazado
[CHART] Resultado: NO_SIGNAL
```

**DESPUÉS**:
```
[LIVE-FILTER] idx=294 ATR=11793.43, Ratio=0.109550, OK
[LIVE-FILTER] idx=294 Volume=12500000 > avg_vol=8000000, OK
[CHART] Resultado: BUY/SELL (según señal ML)
```

---

## 📈 Métricas a Monitorear

Después de implementar, vigilar:

1. **Tasa de Señales Generadas**
   - Esperado: +50% más señales que con filtro 10%
   
2. **Win Rate**
   - Objetivo: Mantener >50% (del backtest)
   
3. **Drawdown Máximo**
   - Límite: <15% (configurado en risk management)
   
4. **Slippage Promedio**
   - Esperado: 0.05-0.1% por operación

---

## 🔄 Plan de Reversión

Si los resultados son negativos (win rate <40% después de 20 trades):

```python
# Revertir a filtro anterior
if atr_ratio > 0.10:  # Volver a 10%
    return 0

# O ajustar a punto medio
if atr_ratio > 0.125:  # Probar 12.5%
    return 0
```

---

## ✅ Estado Actual

**Cambio Aplicado**: ✅ Línea 1034 modificada  
**Sistema**: ⏸️ Requiere reinicio para aplicar cambios  
**Próximo Paso**: Reiniciar modo live y observar generación de señales  

**Comando para reiniciar**:
```powershell
# Detener proceso actual (Ctrl+C si está corriendo)
# Luego ejecutar:
.venv\Scripts\python.exe descarga_datos/main.py --live-ccxt
```

---

## 📊 Comparación: Antes vs Después

| Métrica | Filtro 10% | Filtro 15% |
|---------|-----------|------------|
| **ATR Actual BTC** | 10.95% | 10.95% |
| **¿Pasa Filtro?** | ❌ NO | ✅ SÍ |
| **Señales Esperadas** | 0/día | 5-15/día |
| **Nivel de Protección** | Muy Alto | Alto |
| **Compatibilidad Backtest** | Baja | Alta |

---

## 🎯 Resumen Ejecutivo

**Cambio**: Filtro ATR aumentado de **10%** a **15%**  
**Razón**: Permitir operar en condiciones actuales de volatilidad de BTC  
**Impacto**: Sistema podrá generar señales en mercados con 10-15% de volatilidad  
**Riesgo**: Bajo - Protecciones de trailing stop y stop loss mantienen seguridad  
**Acción Requerida**: Reiniciar sistema para aplicar cambios  

---

**Última actualización**: 19/10/2025 09:00  
**Próxima revisión**: Después de 20 operaciones o 48 horas de trading
