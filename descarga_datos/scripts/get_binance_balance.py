#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Obtener balance e historial de operaciones de Binance testnet"""

import sys
import os
from pathlib import Path
sys.path.insert(0, 'descarga_datos')
import ccxt
import json
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

print("=" * 70)
print("BALANCE ACTUAL - BINANCE TESTNET")
print("=" * 70)

try:
    balance = exchange.fetch_balance()
    
    # Mostrar monedas con saldo
    balances_with_funds = []
    for currency in balance:
        if currency not in ['free', 'used', 'total']:
            free = balance[currency]['free']
            used = balance[currency]['used']
            total = free + used
            if total > 0:
                balances_with_funds.append({
                    'currency': currency,
                    'free': free,
                    'used': used,
                    'total': total
                })
    
    for b in balances_with_funds:
        print(f"\n{b['currency']}:")
        print(f"  Disponible:   {b['free']:.8f}")
        print(f"  Utilizado:    {b['used']:.8f}")
        print(f"  Total:        {b['total']:.8f}")
    
    if not balances_with_funds:
        print("\n(Sin fondos detectados)")
    
except Exception as e:
    print(f"Error obteniendo balance: {e}")

print("\n" + "=" * 70)
print("ÓRDENES ABIERTAS")
print("=" * 70)

try:
    open_orders = exchange.fetch_open_orders('BTC/USDT')
    print(f"\nTotal órdenes abiertas en BTC/USDT: {len(open_orders)}")
    
    if open_orders:
        for i, order in enumerate(open_orders, 1):
            print(f"\n{i}. Orden {order['id']}")
            print(f"   Side: {order['side'].upper()}")
            print(f"   Cantidad: {order['amount']}")
            print(f"   Precio: {order['price']}")
            print(f"   Estado: {order['status']}")
            print(f"   Timestamp: {datetime.fromtimestamp(order['timestamp']/1000)}")
    else:
        print("\n(Sin órdenes abiertas)")
        
except Exception as e:
    print(f"Error obteniendo órdenes: {e}")

print("\n" + "=" * 70)
print("TRADES CERRADOS RECIENTES - BTC/USDT")
print("=" * 70)

try:
    # Obtener últimos trades
    trades = exchange.fetch_my_trades('BTC/USDT', limit=20)
    print(f"\nÚltimos {len(trades)} trades (últimos 20):")
    
    if trades:
        total_pnl = 0
        for i, trade in enumerate(trades[-10:], 1):  # Mostrar últimos 10
            timestamp = datetime.fromtimestamp(trade['timestamp']/1000)
            side = "BUY" if trade['side'] == 'buy' else "SELL"
            amount = trade['amount']
            price = trade['price']
            cost = trade['cost']
            fee = trade['fee']['cost'] if trade['fee'] else 0
            
            print(f"\n{i}. {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Side: {side}")
            print(f"   Amount: {amount:.8f} BTC @ ${price:.2f}")
            print(f"   Costo: ${cost:.2f}")
            print(f"   Fee: ${fee:.2f}")
            
    else:
        print("\n(Sin trades registrados)")
        
except Exception as e:
    print(f"Error obteniendo trades: {e}")

print("\n" + "=" * 70)
print("POSICIONES ACTIVAS SEGÚN LOG")
print("=" * 70)

# Leer log local
try:
    with open('../logs/bot_trader.log', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar operaciones cerradas
    closed_count = content.count('Posición cerrada:')
    open_count = content.count('Posición abierta con risk management')
    
    print(f"\nOperaciones CERRADAS: {closed_count}")
    
    # Extraer ejemplos de cierres
    import re
    pnl_matches = re.findall(r'Posición cerrada:[^-]*- PnL: ([-\d.]+)', content)
    
    if pnl_matches:
        total_pnl = sum(float(p) for p in pnl_matches)
        winners = sum(1 for p in pnl_matches if float(p) > 0)
        losers = len(pnl_matches) - winners
        win_rate = (winners / len(pnl_matches) * 100) if pnl_matches else 0
        
        print(f"  Total: {len(pnl_matches)} operaciones cerradas")
        print(f"  Ganadoras: {winners}")
        print(f"  Perdedoras: {losers}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  P&L Total (realizado): {total_pnl:.8f} BTC ≈ ${total_pnl * 108400:.2f} USD")
        
        print("\n  Cierres registrados (últimos 10):")
        tickets_and_pnls = re.findall(r'Posición cerrada: ([a-f0-9\-]+)[^-]*- PnL: ([-\d.]+)', content)
        for ticket, pnl in tickets_and_pnls[-10:]:
            pnl_f = float(pnl)
            status = "✓ GANA" if pnl_f > 0 else "✗ PIERDE"
            print(f"    {status} - Ticket: {ticket[:8]}... | PnL: {pnl_f:.6f} BTC | ${pnl_f * 108400:.2f}")
    
    print(f"\nOperaciones ABIERTAS (en log): {open_count}")
    
except Exception as e:
    print(f"Error leyendo log: {e}")

print("\n" + "=" * 70)
