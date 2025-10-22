#!/usr/bin/env python3
"""
Script para convertir USDT a BTC manteniendo $1,000 USD de reserva para pruebas
"""

import os
from dotenv import load_dotenv
import ccxt
from datetime import datetime

# Cargar credenciales
load_dotenv(os.path.join(os.path.dirname(__file__), 'descarga_datos', '.env'))

# Configurar exchange Binance testnet
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_TEST_API_KEY'),
    'secret': os.getenv('BINANCE_TEST_API_SECRET'),
    'sandbox': True,
    'enableRateLimit': True,
})

def convertir_usdt_a_btc():
    """Convierte USDT a BTC dejando $1,000 USD de reserva"""
    
    print("\n" + "="*80)
    print(" 🎯 CONVERSOR USDT → BTC (RESERVA $1,000 USD)")
    print("="*80)
    
    # Obtener balance actual
    print(f"\n💰 VERIFICANDO BALANCE ACTUAL...")
    balance = exchange.fetch_balance()
    
    btc_actual = balance.get('BTC', {}).get('free', 0)
    usdt_actual = balance.get('USDT', {}).get('free', 0)
    
    print(f"   • BTC disponible: {btc_actual:.8f}")
    print(f"   • USDT disponible: ${usdt_actual:.2f}")
    
    # Calcular USDT a convertir (dejando $1,000 de reserva)
    usdt_reserva = 1000.00
    usdt_a_convertir = usdt_actual - usdt_reserva
    
    if usdt_a_convertir <= 0:
        print(f"\n❌ ERROR: USDT disponible (${usdt_actual:.2f}) no es suficiente")
        print(f"   • Se necesitan mínimo ${usdt_reserva:.2f}")
        return False
    
    print(f"\n📊 INFORMACIÓN DE CONVERSIÓN:")
    print(f"   • USDT total: ${usdt_actual:.2f}")
    print(f"   • USDT a convertir: ${usdt_a_convertir:.2f}")
    print(f"   • USDT de reserva: ${usdt_reserva:.2f}")
    print(f"   • Símbolo: BTC/USDT")
    print(f"   • Tipo: Market Buy (compra instantánea)")
    
    # Obtener ticker para estimar BTC
    try:
        ticker = exchange.fetch_ticker('BTC/USDT')
        precio_btc = ticker['last']
        btc_estimado = usdt_a_convertir / precio_btc
        
        print(f"\n📈 PRECIO ACTUAL:")
        print(f"   • Precio BTC/USDT: ${precio_btc:.2f}")
        print(f"   • BTC que recibirás (aprox): {btc_estimado:.8f}")
    except Exception as e:
        print(f"\n⚠️  No se pudo obtener precio: {str(e)}")
        btc_estimado = 0
    
    # Confirmar operación
    print(f"\n⚠️  CONFIRMACIÓN REQUERIDA:")
    print(f"   • Se comprarán: ~{btc_estimado:.8f} BTC")
    print(f"   • Usando: ${usdt_a_convertir:.2f} USDT")
    print(f"   • Quedarán: ${usdt_reserva:.2f} USDT para pruebas")
    print(f"   • Tu nuevo balance será:")
    print(f"     - BTC: ~{btc_actual + btc_estimado:.8f}")
    print(f"     - USDT: ${usdt_reserva:.2f}")
    
    confirmacion = input("\n   ¿Deseas continuar? (s/n): ").strip().lower()
    
    if confirmacion != 's':
        print("\n❌ Operación cancelada por usuario")
        return False
    
    # Ejecutar compra
    print(f"\n🔄 EJECUTANDO COMPRA...")
    try:
        # Calcular cantidad más precisa
        order = exchange.create_market_buy_order('BTC/USDT', usdt_a_convertir / exchange.fetch_ticker('BTC/USDT')['last'])
        
        print(f"\n✅ ORDEN EJECUTADA EXITOSAMENTE")
        print(f"   • ID Orden: {order['id']}")
        print(f"   • Status: {order['status'].upper()}")
        print(f"   • Símbolo: {order['symbol']}")
        print(f"   • Cantidad BTC: {order['amount']:.8f}")
        print(f"   • Precio promedio: ${order['average']:.2f}")
        print(f"   • Total USDT gastado: ${order['cost']:.2f}")
        
        # Esperar y verificar balance
        import time
        time.sleep(2)
        
        balance_nuevo = exchange.fetch_balance()
        btc_nuevo = balance_nuevo.get('BTC', {}).get('free', 0)
        usdt_nuevo = balance_nuevo.get('USDT', {}).get('free', 0)
        
        print(f"\n📈 BALANCE ACTUALIZADO:")
        print(f"   • BTC ANTES:  {btc_actual:.8f}")
        print(f"   • BTC AHORA:  {btc_nuevo:.8f}")
        print(f"   • Ganancia:   +{(btc_nuevo - btc_actual):.8f} ✅")
        print()
        print(f"   • USDT ANTES: ${usdt_actual:.2f}")
        print(f"   • USDT AHORA: ${usdt_nuevo:.2f}")
        print(f"   • Diferencia: -{(usdt_actual - usdt_nuevo):.2f} ✅")
        
        # Resumen
        print(f"\n" + "="*80)
        print(f" ✅ CONVERSIÓN USDT → BTC COMPLETADA")
        print(f"="*80)
        print(f"\n📊 RESUMEN FINAL:")
        print(f"   • BTC comprado: {(btc_nuevo - btc_actual):.8f}")
        print(f"   • USDT gastado: ${(usdt_actual - usdt_nuevo):.2f}")
        print(f"   • Nuevo balance BTC: {btc_nuevo:.8f}")
        print(f"   • Nuevo balance USDT: ${usdt_nuevo:.2f} (reserva para pruebas)")
        print(f"   • Timestamp: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR AL EJECUTAR LA COMPRA:")
        print(f"   • Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    convertir_usdt_a_btc()
