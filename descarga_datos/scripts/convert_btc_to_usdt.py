#!/usr/bin/env python3
"""
Script para convertir BTC a USDT equivalente a 20,000 USDT
"""
import ccxt
import os
from dotenv import load_dotenv

def convert_btc_to_usdt(amount_usdt_equivalent):
    """Convierte BTC equivalente al monto especificado en USDT"""
    try:
        # Cargar variables de entorno desde descarga_datos/.env (igual que el sistema de trading)
        load_dotenv('descarga_datos/.env')

        # Usar las mismas variables que usa el sistema de trading
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')

        print(f"🔑 Usando API Key: {api_key[:10]}...")
        print(f"🔐 Usando API Secret: {api_secret[:10]}...")

        # Configurar exchange igual que el sistema de trading
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
        })
        exchange.set_sandbox_mode(True)

        print(f"🔄 Convirtiendo BTC equivalente a ${amount_usdt_equivalent:,.0f} USDT...")
        print("=" * 60)

        # Obtener precio actual de BTC/USDT
        ticker = exchange.fetch_ticker('BTC/USDT')
        btc_price = ticker['last']
        print(f"💰 Precio actual BTC/USDT: ${btc_price:,.2f}")

        # Calcular cantidad de BTC equivalente al monto deseado
        btc_amount = amount_usdt_equivalent / btc_price
        print(f"📊 BTC equivalente a ${amount_usdt_equivalent:,.0f} USDT: {btc_amount:.6f} BTC")

        # Verificar balance actual de BTC
        balance = exchange.fetch_balance()
        btc_balance = balance.get('BTC', {}).get('free', 0)
        print(f"💼 Balance actual BTC: {btc_balance:.8f} BTC")

        # Verificar que tenemos suficiente BTC
        if btc_balance < btc_amount:
            print(f"❌ Error: No tienes suficiente BTC. Tienes {btc_balance:.8f} BTC pero necesitas {btc_amount:.6f} BTC")
            return False

        # Crear orden de venta (market order)
        print(f"\n📈 Creando orden de venta: {btc_amount:.6f} BTC por USDT...")

        order = exchange.create_order(
            symbol='BTC/USDT',
            type='market',
            side='sell',
            amount=btc_amount
        )

        print("✅ Orden ejecutada exitosamente!")
        print(f"📋 ID de orden: {order['id']}")
        print(f"💰 Cantidad vendida: {order['amount']:.6f} BTC")
        print(f"💵 Recibido: ${order['cost']:.2f} USDT")

        # Verificar balance después de la conversión
        print("\n🔍 Verificando balance después de la conversión...")
        new_balance = exchange.fetch_balance()
        new_btc_balance = new_balance.get('BTC', {}).get('free', 0)
        new_usdt_balance = new_balance.get('USDT', {}).get('free', 0)

        print(f"📊 Balance actualizado:")
        print(f"   BTC: {new_btc_balance:.8f} BTC")
        print(f"   USDT: ${new_usdt_balance:.2f}")

        return True

    except Exception as e:
        print(f"❌ Error convirtiendo BTC a USDT: {e}")
        return False

if __name__ == "__main__":
    # Convertir BTC equivalente a 20,000 USDT
    success = convert_btc_to_usdt(20000)

    if success:
        print("\n🎉 Conversión completada exitosamente!")
        print("Ahora tienes fondos USDT disponibles para pruebas.")
    else:
        print("\n❌ La conversión falló. Revisa los errores arriba.")