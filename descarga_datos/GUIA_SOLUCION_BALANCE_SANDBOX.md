# Guía para solucionar el error "Account has insufficient balance for requested action"

## Problema detectado
El sistema está generando correctamente las señales de trading pero no puede ejecutar operaciones debido a un saldo insuficiente en la cuenta de sandbox de Binance.

## Solución paso a paso

### 1. Verificar y configurar API Keys de Binance Testnet

1. Visita el sitio oficial de Binance Testnet: [https://testnet.binance.vision/](https://testnet.binance.vision/)
2. Inicia sesión o crea una nueva cuenta de testnet
3. Genera nuevas API Keys (si no tienes o las existentes no funcionan)
4. Asegúrate de que las API Keys tengan permisos de trading habilitados

### 2. Configurar variables de entorno

Edita el archivo `.env` en la carpeta `c:\Users\javie\copilot\botcopilot-sar\descarga_datos\` y actualiza estos valores:

```
BINANCE_TEST_API_KEY=tu_api_key_de_binance_testnet
BINANCE_TEST_API_SECRET=tu_api_secret_de_binance_testnet
```

Reemplaza los valores con tus credenciales reales de Binance Testnet.

### 3. Solicitar fondos de prueba

1. En la plataforma web de Binance Testnet, busca la opción "Get Test Funds" o "Fund Account"
2. Solicita fondos de prueba en USDT (al menos 1000 USDT)
3. También es recomendable solicitar otros activos como BTC y ETH

### 4. Verificar balance

Ejecuta el siguiente comando para verificar que tienes suficiente saldo:
```
python setup_binance_sandbox.py
```

### 5. Ejecutar trading en vivo

Una vez que tengas suficiente saldo, ejecuta:
```
python descarga_datos/main.py --live-ccxt
```

## Notas importantes

- Los fondos en Binance Testnet son virtuales, no representan valor real
- Las cuentas de testnet suelen resetearse periódicamente
- Si sigues teniendo problemas, verifica los logs en `logs/binance_sandbox_test.log`
- Asegúrate de que sandbox: true esté configurado en los archivos de configuración