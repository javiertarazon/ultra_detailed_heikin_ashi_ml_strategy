#!/usr/bin/env python3
"""
Script para convertir ganancias en BTC a USDT
Ganancias realizadas del bot de trading: 0.069870 BTC
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

def convertir_ganancias_a_usdt():
    """Convierte las ganancias del bot (BTC) a USDT"""
    
    print("\n" + "="*80)
    print(" 🎯 CONVERSOR DE GANANCIAS BTC → USDT")
    print("="*80)
    
    # BTC de ganancias a convertir
    btc_ganancias = 0.069870
    
    print(f"\n📊 INFORMACIÓN DE CONVERSIÓN:")
    print(f"   • BTC de ganancias a convertir: {btc_ganancias} BTC")
    print(f"   • Símbolo: BTC/USDT")
    print(f"   • Tipo: Market Sell (venta instantánea)")
    
    # Obtener balance actual
    print(f"\n💰 VERIFICANDO BALANCE ACTUAL...")
    balance = exchange.fetch_balance()
    
    btc_actual = balance.get('BTC', {}).get('free', 0)
    usdt_actual = balance.get('USDT', {}).get('free', 0)
    
    print(f"   • BTC disponible: {btc_actual}")
    print(f"   • USDT disponible: ${usdt_actual:.2f}")
    
    # Verificar que haya suficiente BTC
    if btc_actual < btc_ganancias:
        print(f"\n❌ ERROR: No hay suficiente BTC para convertir")
        print(f"   • BTC necesario: {btc_ganancias}")
        print(f"   • BTC disponible: {btc_actual}")
        return False
    
    # Confirmar operación
    print(f"\n⚠️  CONFIRMACIÓN REQUERIDA:")
    print(f"   • Se venderá: {btc_ganancias} BTC de tus ganancias")
    print(f"   • Recibirás: ~${btc_ganancias * 108054:.2f} USD (aproximado)")
    confirmacion = input("\n   ¿Deseas continuar? (s/n): ").strip().lower()
    
    if confirmacion != 's':
        print("\n❌ Operación cancelada por usuario")
        return False
    
    # Ejecutar venta
    print(f"\n🔄 EJECUTANDO VENTA...")
    try:
        order = exchange.create_market_sell_order('BTC/USDT', btc_ganancias)
        
        print(f"\n✅ ORDEN EJECUTADA EXITOSAMENTE")
        print(f"   • ID Orden: {order['id']}")
        print(f"   • Status: {order['status'].upper()}")
        print(f"   • Símbolo: {order['symbol']}")
        print(f"   • Cantidad BTC: {order['amount']}")
        print(f"   • Precio promedio: ${order['average']:.2f}")
        print(f"   • Total USDT (antes comisión): ${order['cost']:.2f}")
        
        # Esperar y verificar balance
        import time
        time.sleep(2)
        
        balance_nuevo = exchange.fetch_balance()
        btc_nuevo = balance_nuevo.get('BTC', {}).get('free', 0)
        usdt_nuevo = balance_nuevo.get('USDT', {}).get('free', 0)
        
        print(f"\n📈 BALANCE ACTUALIZADO:")
        print(f"   • BTC ANTES:  {btc_actual:.8f}")
        print(f"   • BTC AHORA:  {btc_nuevo:.8f}")
        print(f"   • Diferencia: -{btc_ganancias:.8f} ✅")
        print()
        print(f"   • USDT ANTES: ${usdt_actual:.2f}")
        print(f"   • USDT AHORA: ${usdt_nuevo:.2f}")
        print(f"   • Ganancia:   +${(usdt_nuevo - usdt_actual):.2f} ✅")
        
        # Resumen
        print(f"\n" + "="*80)
        print(f" ✅ CONVERSIÓN DE GANANCIAS COMPLETADA")
        print(f"="*80)
        print(f"\n📊 RESUMEN:")
        print(f"   • BTC convertido: {btc_ganancias}")
        print(f"   • USDT recibido: ${(usdt_nuevo - usdt_actual):.2f}")
        print(f"   • Nuevo balance BTC: {btc_nuevo:.8f}")
        print(f"   • Nuevo balance USDT: ${usdt_nuevo:.2f}")
        print(f"   • Timestamp: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR AL EJECUTAR LA VENTA:")
        print(f"   • Error: {str(e)}")
        return False

if __name__ == '__main__':
    convertir_ganancias_a_usdt()
