# Solución para el error "Saldo insuficiente" en Trading Live con Binance Testnet

## Problema detectado

El sistema está generando señales de trading (SELL) correctamente cuando la confianza ML alcanza valores de aproximadamente 0.5, pero al intentar ejecutar las órdenes en Binance Testnet, se produce el siguiente error:

```
Error abriendo posición: binance Account has insufficient balance for requested action.
```

Este error ocurre porque:
1. El cálculo del tamaño de la posición está requiriendo más fondos de los disponibles en la cuenta de Binance Testnet
2. No se está verificando si hay saldo suficiente antes de intentar crear la orden
3. Los valores de riesgo configurados pueden ser demasiado altos para los fondos disponibles

## Solución

Hemos preparado varios scripts para solucionar este problema:

### 1. Verificar saldo y recargarlo si es necesario

```bash
python descarga_datos/check_binance_balance.py
```

Este script:
- Muestra los saldos disponibles en tu cuenta de Binance Testnet
- Proporciona instrucciones para recargar fondos si son insuficientes
- Permite crear una pequeña orden de prueba para verificar la conectividad

### 2. Ajustar el tamaño de posición en la configuración

```bash
python descarga_datos/adjust_position_size.py
```

Este script:
- Muestra los saldos disponibles en tu cuenta
- Modifica automáticamente los parámetros `risk_per_trade` y `max_position_size_pct` en `config.yaml` para usar valores más conservadores
- Reduce los parámetros de riesgo para adaptarse al saldo disponible

### 3. Modificar el cálculo de tamaño de posición (solución avanzada)

```bash
python descarga_datos/fix_insufficient_balance.py
```

Este script:
- Crea una copia de seguridad del archivo `ccxt_order_executor.py`
- Modifica el cálculo de riesgo para usar valores más conservadores
- Añade verificación de saldo antes de crear órdenes
- Implementa un ajuste automático de la cantidad para adaptarse al saldo disponible

## Instrucciones paso a paso

1. **Verifica el saldo disponible**:
   ```bash
   python descarga_datos/check_binance_balance.py
   ```
   Si no hay suficiente saldo, sigue las instrucciones para recargar fondos en Binance Testnet.

2. **Ajusta la configuración de riesgo**:
   ```bash
   python descarga_datos/adjust_position_size.py
   ```
   Esto modificará los parámetros en `config.yaml` para usar valores más seguros.

3. **Si los pasos anteriores no funcionan**, modifica el ejecutor de órdenes:
   ```bash
   python descarga_datos/fix_insufficient_balance.py
   ```
   Este es un cambio más profundo que modifica el código del ejecutor.

4. **Inicia el trading en vivo nuevamente**:
   ```bash
   python descarga_datos/main.py --live-ccxt
   ```

## Notas adicionales

- Las cuentas de Binance Testnet tienen límites de fondos y es necesario recargarlas periódicamente
- Si necesitas restaurar la configuración original después de usar `fix_insufficient_balance.py`, puedes usar:
  ```bash
  python -c "import shutil; shutil.copy('descarga_datos/core/ccxt_order_executor.py.bak', 'descarga_datos/core/ccxt_order_executor.py')"
  ```

- Si modificas directamente `config.yaml`, estos son los valores recomendados:
  ```yaml
  risk_management:
    risk_per_trade: 0.002  # Usar solo 0.2% del capital por operación
    max_position_size_pct: 0.01  # Máximo 1% del capital por posición
  ```

## Verificación de éxito

Cuando el problema esté solucionado:
1. El sistema generará señales cuando la confianza ML alcance ~0.5
2. Las órdenes se ejecutarán correctamente sin errores de saldo insuficiente
3. Verás mensajes confirmando la apertura de posiciones en los logs