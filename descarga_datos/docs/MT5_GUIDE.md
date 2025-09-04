# Guía para Descarga de Datos con MetaTrader 5

Esta guía explica cómo configurar y utilizar la integración de MetaTrader 5 para la descarga de datos en el sistema de backtesting.

## Requisitos Previos

1. **Instalación de MetaTrader 5**:
   - Descarga e instala el terminal [MetaTrader 5](https://www.metatrader5.com/es/download) desde el sitio oficial.
   - Ejecuta el terminal al menos una vez y configura una cuenta (demo o real).

2. **Instalación del paquete Python**:
   ```bash
   pip install MetaTrader5>=5.0.45 pytz
   ```

3. **Verificar la instalación**:
   ```bash
   python test_mt5_installation.py
   ```
   Este script verificará si MetaTrader 5 está instalado y funcionando correctamente.

## Configuración

### 1. Configuración básica

En el archivo `config.yaml`, establece `use_mt5` en `true`:

```yaml
# Configuración del Data Downloader
active_exchange: "bybit"  # Esto se puede mantener para otras funcionalidades
use_mt5: true  # Activa la descarga desde MT5
```

### 2. Configuración avanzada

Puedes personalizar la configuración de MT5 en el archivo `mt5_config.yaml`:

```yaml
# Configuración específica para MetaTrader 5
mt5:
  enabled: true
  # Parámetros de conexión
  terminal_path: ""  # Ruta al terminal (opcional)
  server: ""  # Nombre del servidor (opcional)
  login: 0  # ID de login (0 para modo invitado)
  password: ""  # Contraseña (vacío para modo invitado)
  timeout: 60000  # Timeout en milisegundos
  
  # Símbolos a descargar
  default_symbol_list:
    - "EURUSD"
    - "USDJPY"
    - "GBPUSD"
    - "BTCUSD"
  
  # Timeframes disponibles
  default_timeframe: "1h"
  timeframes:
    - "15m"
    - "1h"
    - "4h"
    - "1d"
```

## Uso

### 1. Prueba de descarga independiente

Para probar la descarga de datos sin ejecutar todo el sistema:

```bash
python test_mt5_download.py --symbols EURUSD GBPUSD --timeframes 1h 4h --days 30
```

Parámetros:
- `--symbols`: Lista de símbolos a descargar
- `--timeframes`: Lista de timeframes a descargar
- `--days`: Número de días hacia atrás (por defecto: 30)
- `--output-dir`: Directorio de salida (opcional)

### 2. Uso integrado en el sistema

Ejecuta el sistema normalmente con la configuración actualizada:

```bash
python -m descarga_datos.main
```

El sistema automáticamente utilizará MetaTrader 5 como fuente de datos si `use_mt5` está configurado como `true`.

## Notas Importantes

1. **Símbolos**: Los nombres de los símbolos en MT5 pueden diferir de los utilizados en exchanges como Binance. Por ejemplo, "BTC/USDT" en Binance sería "BTCUSDT" en MT5.

2. **Terminal activo**: El terminal de MetaTrader 5 debe estar instalado, pero no necesariamente en ejecución, ya que la API puede conectarse directamente.

3. **Limitaciones de datos**: MT5 puede tener limitaciones en la cantidad de datos históricos disponibles según el broker.

4. **Performance**: La descarga de datos desde MT5 puede ser más rápida que desde exchanges públicos, ya que no tiene limitaciones de API rate.

5. **Modo invitado**: Si no proporciona credenciales de login, el sistema utilizará el "modo invitado" que permite acceso a datos pero no a trading en vivo.

## Resolución de problemas

1. **Error "MetaTrader 5 no está instalado"**:
   - Verifica que MetaTrader 5 esté instalado correctamente.
   - Reinstala el paquete Python: `pip install --force-reinstall MetaTrader5>=5.0.45`

2. **Error "No se pudo inicializar MT5"**:
   - Asegúrate de que el terminal de MetaTrader 5 esté instalado correctamente.
   - Verifica que el usuario actual tenga permisos para acceder a los archivos de MT5.

3. **No se encuentran símbolos**:
   - Verifica que los símbolos estén disponibles en tu broker de MT5.
   - Algunos brokers tienen diferentes nomenclaturas (ej. EURUSD.m, EUR/USD).

4. **Errores de timeout**:
   - Aumenta el valor de timeout en la configuración.
   - Verifica la conexión a Internet.

## Formato de datos

Los datos descargados desde MT5 tienen la siguiente estructura:

- **timestamp**: Marca de tiempo UNIX en segundos
- **open**: Precio de apertura
- **high**: Precio máximo
- **low**: Precio mínimo
- **close**: Precio de cierre
- **volume**: Volumen (tick_volume en MT5)

Los datos se guardan en el formato estándar del sistema para mantener la compatibilidad con las estrategias existentes.

---

Para más información y asistencia, consulta la [documentación oficial de MT5 para Python](https://www.mql5.com/en/docs/python_metatrader5).
