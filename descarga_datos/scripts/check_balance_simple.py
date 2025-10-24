#!/usr/bin/env python3
"""
Script simplificado para verificar balance de Binance testnet
"""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    print("❌ CCXT no está disponible")
    sys.exit(1)

def check_binance_balance():
    """Verifica balance de Binance testnet"""

    # Verificar credenciales
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Credenciales no encontradas")
        return

    try:
        # Conectar a testnet
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': True,
            'enableRateLimit': True
        })

        # Obtener balance
        balance = exchange.fetch_balance()

        print("🏦 BALANCE BINANCE TESTNET")
        print("=" * 40)

        total_usdt = 0
        assets = []

        for currency, data in balance.items():
            if currency in ['info', 'timestamp', 'datetime']:
                continue

            if isinstance(data, dict):
                free = float(data.get('free', 0))
                total = float(data.get('total', 0))

                if total > 0.0001:  # Solo saldos significativos
                    assets.append((currency, free, total))

                    if currency == 'USDT':
                        total_usdt += total
                    elif currency == 'BTC' and total > 0:
                        try:
                            ticker = exchange.fetch_ticker('BTC/USDT')
                            total_usdt += total * ticker['last']
                        except:
                            pass

        # Mostrar activos
        for currency, free, total in assets:
            print("<10")

        print("-" * 40)
        print(f"💰 TOTAL ESTIMADO: ${total_usdt:.2f} USDT")
        # Evaluación
        if total_usdt >= 100:
            print("✅ SALDO SUFICIENTE para trading")
        else:
            print("⚠️ SALDO INSUFICIENTE - mínimo 100 USDT recomendado")

        return total_usdt

    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    balance = check_binance_balance()
    if balance > 0:
        print(f"📊 Balance verificado: ${balance:.2f} USDT")
    else:
        print("\nPara configurar credenciales:")
        print("1. Ve a https://testnet.binance.vision/")
        print("2. Crea API Key")
        print("3. Actualiza el archivo .env con las credenciales")