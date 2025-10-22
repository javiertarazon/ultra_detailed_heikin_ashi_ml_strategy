#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para convertir BTC a USDT en Binance Testnet
Convierte la mitad del BTC disponible a USDT para capital de trading
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, 'descarga_datos')
import ccxt
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent / 'descarga_datos' / '.env'
load_dotenv(env_path)

# Credenciales testnet desde .env
api_key = os.getenv('BINANCE_API_KEY') or os.getenv('BINANCE_TEST_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET') or os.getenv('BINANCE_TEST_API_SECRET')

if not api_key or not api_secret:
    print("❌ ERROR: No se encontraron credenciales en .env")
    sys.exit(1)

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'sandbox': True,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

print("=" * 80)
print("🔄 CONVERTIDOR BTC → USDT - BINANCE TESTNET")
print("=" * 80)
print()

# ============================================================================
# PASO 1: OBTENER BALANCE ACTUAL
# ============================================================================
print("1️⃣  OBTENIENDO BALANCE ACTUAL...")
print("-" * 80)

try:
    balance = exchange.fetch_balance()
    
    btc_available = balance['BTC']['free']
    usdt_available = balance['USDT']['free']
    
    print(f"✅ Balance actual obtenido:")
    print(f"   • BTC disponible:  {btc_available:.8f}")
    print(f"   • USDT disponible: {usdt_available:.8f}")
    print()
    
except Exception as e:
    print(f"❌ Error obteniendo balance: {e}")
    sys.exit(1)

# ============================================================================
# PASO 2: CALCULAR CONVERSIÓN
# ============================================================================
print("2️⃣  CALCULANDO CONVERSIÓN...")
print("-" * 80)

btc_a_convertir = btc_available / 2

if btc_a_convertir < 0.00001:
    print(f"❌ ERROR: Cantidad de BTC demasiado pequeña para convertir")
    print(f"   BTC a convertir: {btc_a_convertir:.8f} (mínimo: 0.00001)")
    sys.exit(1)

print(f"✅ Cálculo realizado:")
print(f"   • BTC total:       {btc_available:.8f}")
print(f"   • BTC a convertir: {btc_a_convertir:.8f} (mitad)")
print(f"   • BTC restante:    {btc_available - btc_a_convertir:.8f}")
print()

# ============================================================================
# PASO 3: OBTENER PRECIO ACTUAL
# ============================================================================
print("3️⃣  OBTENIENDO PRECIO ACTUAL BTC/USDT...")
print("-" * 80)

try:
    # Obtener ticker para BTC/USDT
    ticker = exchange.fetch_ticker('BTC/USDT')
    btc_price = ticker['last']
    
    print(f"✅ Precio BTC/USDT: ${btc_price:.2f}")
    print()
    
except Exception as e:
    print(f"❌ Error obteniendo precio: {e}")
    sys.exit(1)

# ============================================================================
# PASO 4: CALCULAR USDT A RECIBIR
# ============================================================================
print("4️⃣  CALCULANDO USDT A RECIBIR...")
print("-" * 80)

usdt_a_recibir = btc_a_convertir * btc_price
# Restar comisión (0.1% en Binance)
comision = usdt_a_recibir * 0.001
usdt_neto = usdt_a_recibir - comision

print(f"✅ Cálculo de conversión:")
print(f"   • BTC a vender:    {btc_a_convertir:.8f}")
print(f"   • Precio BTC:      ${btc_price:.2f}")
print(f"   • USDT bruto:      ${usdt_a_recibir:.2f}")
print(f"   • Comisión (0.1%): ${comision:.2f}")
print(f"   • USDT neto:       ${usdt_neto:.2f}")
print()

# ============================================================================
# PASO 5: CONFIRMAR OPERACIÓN
# ============================================================================
print("5️⃣  CONFIRMACIÓN DE OPERACIÓN")
print("-" * 80)
print()
print(f"Resumen de la transacción:")
print(f"  VENDER: {btc_a_convertir:.8f} BTC @ ${btc_price:.2f}")
print(f"  RECIBIR: ${usdt_neto:.2f} USDT (después de comisión)")
print()
print(f"ANTES:")
print(f"  • BTC:  {btc_available:.8f}")
print(f"  • USDT: {usdt_available:.2f}")
print()
print(f"DESPUÉS (estimado):")
print(f"  • BTC:  {btc_available - btc_a_convertir:.8f}")
print(f"  • USDT: {usdt_available + usdt_neto:.2f}")
print()

# Pedir confirmación
confirmacion = input("¿Deseas proceder con la conversión? (s/n): ").lower().strip()

if confirmacion != 's':
    print("❌ Operación cancelada por el usuario")
    sys.exit(0)

# ============================================================================
# PASO 6: EJECUTAR ORDEN DE VENTA
# ============================================================================
print()
print("6️⃣  EJECUTANDO ORDEN DE VENTA...")
print("-" * 80)

try:
    # Crear orden de venta (SELL BTC/USDT)
    # Usaremos 'market' para ejecución inmediata al precio de mercado
    order = exchange.create_market_sell_order(
        'BTC/USDT',
        btc_a_convertir
    )
    
    print(f"✅ ORDEN EJECUTADA EXITOSAMENTE")
    print()
    print(f"Detalles de la orden:")
    print(f"  • ID Orden:        {order['id']}")
    print(f"  • Símbolo:         {order['symbol']}")
    print(f"  • Side:            {order['side'].upper()}")
    print(f"  • Cantidad:        {order['amount']:.8f}")
    print(f"  • Precio promedio: ${order.get('average', 'N/A')}")
    print(f"  • Costo:           ${order.get('cost', 'N/A')}")
    print(f"  • Status:          {order['status']}")
    print(f"  • Timestamp:       {datetime.fromtimestamp(order['timestamp']/1000)}")
    print()
    
except Exception as e:
    print(f"❌ Error ejecutando orden: {e}")
    sys.exit(1)

# ============================================================================
# PASO 7: VERIFICAR NUEVO BALANCE
# ============================================================================
print("7️⃣  VERIFICANDO NUEVO BALANCE...")
print("-" * 80)

try:
    # Esperar un momento para que se actualice el balance
    import time
    time.sleep(1)
    
    nuevo_balance = exchange.fetch_balance()
    
    btc_nuevo = nuevo_balance['BTC']['free']
    usdt_nuevo = nuevo_balance['USDT']['free']
    
    print(f"✅ BALANCE ACTUALIZADO:")
    print()
    print(f"BTC:")
    print(f"  Antes:  {btc_available:.8f}")
    print(f"  Ahora:  {btc_nuevo:.8f}")
    print(f"  Cambio: -{btc_a_convertir:.8f} ✅")
    print()
    print(f"USDT:")
    print(f"  Antes:  {usdt_available:.2f}")
    print(f"  Ahora:  {usdt_nuevo:.2f}")
    print(f"  Cambio: +{usdt_nuevo - usdt_available:.2f} ✅")
    print()
    
except Exception as e:
    print(f"⚠️  Advertencia verificando balance: {e}")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("=" * 80)
print("✅ CONVERSIÓN COMPLETADA EXITOSAMENTE")
print("=" * 80)
print()
print(f"📊 Resumen Final:")
print(f"   • BTC convertido:    {btc_a_convertir:.8f}")
print(f"   • USDT recibido:     ${usdt_neto:.2f}")
print(f"   • Precio de cierre:  ${btc_price:.2f}")
print(f"   • Comisión pagada:   ${comision:.2f}")
print()
print(f"💡 Ahora tienes capital USDT para continuar con las pruebas de trading")
print()
print("=" * 80)
