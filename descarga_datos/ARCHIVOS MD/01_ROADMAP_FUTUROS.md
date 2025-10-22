### 🔧 Adaptaciones Técnicas Necesarias para Futuros

#### **1. Gestión de Posiciones**
```python
# En lugar de órdenes spot simples:
# SPOT: buy(symbol, amount)
# FUTUROS: create_market_order(symbol, 'buy', amount, leverage=5)

# El sistema necesitaría:
- Calcular tamaño de contrato apropiado
- Gestionar apalancamiento dinámico
- Monitorear funding rates
- Implementar liquidación preventiva
```

#### **2. Cálculo de Riesgo**
```python
# Riesgo SPOT: amount * price
# Riesgo FUTUROS: (amount * price) / leverage + funding_costs

# Factores adicionales:
- Liquidation price monitoring
- Maintenance margin tracking
- Funding rate impact on P&L
```

#### **3. Símbolos y Datos**
```yaml
# SPOT Binance: BTC/USDT
# FUTUROS Kraken: PF_BTCUSD

# Diferencias en feeds de datos:
- Precios pueden variar ligeramente
- Volumen y liquidez diferentes
- Horarios de trading 24/7 vs limitados
```</content>
<parameter name="filePath">c:\Users\javie\copilot\botcopilot-sar\adaptaciones_futuros.md