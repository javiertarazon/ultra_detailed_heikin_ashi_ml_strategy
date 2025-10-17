# Test de Live Trading con Binance Sandbox

Este directorio contiene un test completo y realista para verificar todas las funcionalidades del sistema de trading en vivo usando el sandbox (testnet) de Binance.

## 🚀 Características del Test

### ✅ Funcionalidades Verificadas
- **Conexión y Autenticación**: Verifica conexión a Binance Testnet
- **Recopilación de Datos**: Obtiene datos OHLCV en tiempo real
- **Cálculo de Indicadores**: RSI, MACD, Bollinger Bands, Medias Móviles
- **Órdenes Límite**: Compra y venta con precios límite
- **Stop Loss & Take Profit**: Configuración de órdenes OCO y separadas
- **Cierre de Posiciones**: Cierre manual y automático
- **Escenario Completo**: Estrategia RSI + SMA con gestión de riesgo
- **Reportes**: Resultados detallados y métricas de rendimiento

### 🎯 Operaciones Reales en Testnet
- Todas las operaciones se ejecutan realmente en la cuenta de test
- Usa capital virtual pero órdenes reales
- Verifica latencia, ejecución y gestión de posiciones
- Resultados comparables con trading en vivo real

## 📋 Requisitos Previos

### 1. Credenciales de Binance Testnet
Obtén tus credenciales en: https://testnet.binance.vision/

```bash
# Configura variables de entorno
export BINANCE_TEST_API_KEY="tu_api_key_aqui"
export BINANCE_TEST_API_SECRET="tu_api_secret_aqui"
```

### 2. Dependencias Instaladas
```bash
pip install -r requirements.txt
```

### 3. Sistema Validado
```bash
python validate_modular_system.py
```

## 🏃‍♂️ Ejecución del Test

### Test Completo
```bash
python run_binance_sandbox_test.py
```

### Tests Específicos
```bash
# Solo verificar conexión
python run_binance_sandbox_test.py --test connection

# Solo recopilar datos
python run_binance_sandbox_test.py --test data

# Solo probar órdenes
python run_binance_sandbox_test.py --test orders

# Solo gestión de riesgo
python run_binance_sandbox_test.py --test risk

# Escenario completo
python run_binance_sandbox_test.py --test scenario
```

### Ver Resultados
```bash
# Mostrar resultados del último test
python run_binance_sandbox_test.py --results
```

## 📁 Estructura de Archivos

```
tests/
├── test_binance_sandbox_live.py      # Test principal
├── test_results/                     # Resultados de tests
│   └── binance_sandbox_test_*.json
└── README.md                         # Esta documentación

config/
└── binance_sandbox_test.yaml         # Configuración del test

run_binance_sandbox_test.py           # Script de ejecución
```

## 📊 Resultados del Test

Los resultados se guardan automáticamente en `tests/test_results/` con:
- **Métricas de Rendimiento**: Win rate, PnL total, drawdown
- **Historial de Trades**: Todos los trades ejecutados
- **Posiciones**: Estado de posiciones abiertas/cerradas
- **Órdenes**: Detalles de órdenes ejecutadas
- **Tiempos**: Latencia y duración de operaciones

### Ejemplo de Resultado
```json
{
  "test_timestamp": "2025-10-10T17:30:00",
  "total_trades": 5,
  "total_pnl": 12.45,
  "win_rate": 60.0,
  "trades": [
    {
      "symbol": "BTC/USDT",
      "signal": "BUY",
      "size": 0.001,
      "price": 45000.50,
      "timestamp": "2025-10-10T17:31:15"
    }
  ]
}
```

## 🔧 Configuración Avanzada

### Modificar Parámetros del Test
Edita `config/binance_sandbox_test.yaml`:

```yaml
trading:
  capital: 1000          # Capital de test
  max_position_size: 0.1 # 10% del capital por trade

risk_management:
  stop_loss_pct: 0.02    # 2% stop loss
  take_profit_pct: 0.04  # 4% take profit
```

### Personalizar Estrategia de Test
Modifica el método `test_06_comprehensive_trading_scenario` en `test_binance_sandbox_live.py` para usar diferentes indicadores o lógica de entrada/salida.

## ⚠️ Consideraciones de Seguridad

- **Solo Testnet**: Todas las operaciones son en entorno de prueba
- **Capital Virtual**: No se usa dinero real
- **Limpieza Automática**: El test cierra posiciones y cancela órdenes al finalizar
- **Logging Detallado**: Todos los eventos se registran para debugging

## 🐛 Troubleshooting

### Error de Conexión
```
❌ Credenciales de Binance Testnet no configuradas
```
**Solución**: Configura las variables de entorno correctamente.

### Error de Balance
```
❌ No hay balance disponible en la cuenta test
```
**Solución**: Deposita USDT de test en tu cuenta de Binance Testnet.

### Error de Órdenes
```
❌ Orden no ejecutada
```
**Solución**: Verifica que el símbolo esté disponible y los precios sean válidos.

## 📈 Próximos Pasos

Después de verificar que el test funciona correctamente:

1. **Configurar Live Trading Real**: Usa las mismas credenciales pero con `testnet: false`
2. **Implementar Estrategias Personalizadas**: Crea estrategias basadas en los indicadores verificados
3. **Configurar Monitoreo**: Activa el dashboard para seguimiento en tiempo real
4. **Backtesting vs Live**: Compara resultados entre backtest y live trading

## 🤝 Soporte

Para problemas o preguntas:
- Revisa los logs en `logs/binance_sandbox_test.log`
- Verifica la documentación en `README.md`
- Ejecuta validación: `python validate_modular_system.py`