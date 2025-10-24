# Guía de Operación 24/7 - Sistema de Trading en Vivo

## Estado del Sistema
✅ **COMPLETADO**: Sistema 24/7 con auto-restart, recuperación automática y límites de memoria
✅ **COMPLETADO**: Monitoreo de conectividad de red y reconexión automática
✅ **COMPLETADO**: Límites de cache (50 entradas) para prevenir memory leaks

## Inicio del Sistema 24/7

### Comando Principal
```bash
python descarga_datos/main.py --live
```

### Modo Sandbox (Recomendado para pruebas)
El sistema inicia automáticamente en modo sandbox según configuración en `config/config.yaml`:
```yaml
exchanges:
  bybit:
    sandbox: true  # Siempre true para pruebas
```

## Parada Manual del Sistema

### Método 1: Interrupción por Teclado (Ctrl+C)
- **Presione Ctrl+C** en la terminal donde se ejecuta el bot
- El sistema detectará la señal SIGINT y realizará shutdown graceful
- Se guardarán todas las posiciones abiertas y métricas
- Se cerrarán todas las conexiones de red
- Se detendrán todos los hilos de manera ordenada

### Método 2: Comando de Parada por Chat
Envíe el siguiente comando al sistema:
```
STOP_TRADING
```
- El sistema verificará este comando en cada ciclo de health check
- Realizará shutdown graceful igual que Ctrl+C

### Método 3: Apagado de Emergencia (Kill Signal)
Si el sistema no responde a Ctrl+C:
```bash
# En Windows PowerShell
Get-Process python | Where-Object {$_.MainWindowTitle -like "*main.py*"} | Stop-Process -Force

# O usando taskkill
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*"
```

## Monitoreo del Sistema

### Logs en Tiempo Real
```bash
# Ver logs del sistema
Get-Content "logs/bot_trader.log" -Wait -Tail 20
```

### Verificación de Salud
El sistema ejecuta health checks cada 30 segundos que verifican:
- ✅ Conectividad de red y reconexión automática
- ✅ Uso de memoria (< 85%)
- ✅ Tamaño del cache (< 50 entradas)
- ✅ Funcionamiento del logger
- ✅ Estado de hilos de trading

### Dashboard de Resultados
Los resultados se guardan automáticamente en:
```
descarga_datos/data/dashboard_results/
```

## Recuperación Automática

### Tipos de Fallos Manejados
1. **Desconexiones de Red**: Reconexión automática cada 30 segundos
2. **Memory Leaks**: Límites de cache + limpieza automática
3. **Errores de Exchange**: Reintentos con backoff exponencial
4. **Hilos Congelados**: Timeouts de 24 horas + reinicio automático
5. **Errores de Serialización**: Validación de tipos antes de guardar

### Auto-Restart
- Máximo 5 reinicios automáticos por hora
- Espera de 30 segundos entre reinicios
- Logging detallado de cada reinicio

## Configuración de Seguridad

### Sandbox Mode
```yaml
# config/config.yaml
exchanges:
  bybit:
    sandbox: true  # NUNCA cambiar a false en producción real
```

### Límites de Riesgo
```yaml
risk_management:
  max_drawdown: 0.05  # 5% máximo drawdown
  max_positions: 3     # Máximo 3 posiciones abiertas
  atr_multiplier: 2.0  # Stop loss basado en ATR
```

## Troubleshooting

### Sistema No Inicia
```bash
# Verificar dependencias
python -c "import ccxt, pandas, numpy; print('Dependencias OK')"

# Verificar configuración
python -c "from config.config_loader import load_config; print('Config OK')"
```

### Problemas de Conectividad
```bash
# Probar conexión manual
python -c "import ccxt; exchange = ccxt.bybit(); print(exchange.fetch_time())"
```

### Memory Issues
- El sistema limpia cache automáticamente
- Reinicio automático si memoria > 85%
- Logs detallados en `logs/bot_trader.log`

### Apagado Forzado
Si el sistema no responde:
1. Intentar Ctrl+C primero
2. Si no funciona, usar taskkill como arriba
3. Verificar que no queden procesos huérfanos

## Próximos Pasos
- [ ] Testing extendido (24h+)
- [ ] Monitoreo de estabilidad en producción
- [ ] Optimización de rendimiento
- [ ] Alertas por email/SMS para fallos críticos</content>
<parameter name="filePath">c:\Users\javie\copilot\botcopilot-sar\descarga_datos\24_7_OPERATION_GUIDE.md