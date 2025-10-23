#!/usr/bin/env python3
"""
Script para verificar balance de Binance testnet
"""
import ccxt

def check_balance():
    try:
        exchange = ccxt.binance()
        exchange.set_sandbox_mode(True)

        # Verificar sin API keys primero
        print("🔍 Verificando conectividad sin API keys...")
        markets = exchange.load_markets()
        print(f"✅ Conectado - {len(markets)} mercados disponibles")

        # Ahora intentar con API keys
        print("\n🔐 Verificando con API keys actuales...")
        exchange.apiKey = 'vcZmn1Ct7HGYCnVVrZ7K3RjF4GLP1CfrGiUwqoAdMXGIkWUXofDr3LNZG899kphM'
        exchange.secret = 'PFuNU0LegDLjdc0rH7AZJcAWsaNSiEvUYo909eK7oO3SIhh9QnasGJcOv0SpGuGQ'

        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        print(f"💰 Balance actual: ${usdt_balance:.2f} USDT")

        return usdt_balance

    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    check_balance()