#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Análisis detallado de balance y operaciones - Binance Testnet"""

import sys
import os
from pathlib import Path
sys.path.insert(0, 'descarga_datos')
import ccxt
import re
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent / 'descarga_datos' / '.env'
load_dotenv(env_path)

api_key = os.getenv('BINANCE_API_KEY') or os.getenv('BINANCE_TEST_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET') or os.getenv('BINANCE_TEST_API_SECRET')

print("\n" + "=" * 80)
print("📊 ANÁLISIS COMPLETO - BALANCE Y OPERACIONES BINANCE TESTNET")
print("=" * 80)

# ============================================================================
# SECCIÓN 1: BALANCE ACTUAL
# ============================================================================
print("\n1️⃣  BALANCE ACTUAL DE LA CUENTA")
print("-" * 80)

try:
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'sandbox': True,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    balance = exchange.fetch_balance()
    
    # Extraer monedas con saldo
    balances_with_funds = []
    for currency in balance:
        if currency not in ['free', 'used', 'total']:
            try:
                free = float(balance[currency]['free'])
                used = float(balance[currency]['used'])
                total = free + used
                if total > 0:
                    balances_with_funds.append({
                        'currency': currency,
                        'free': free,
                        'used': used,
                        'total': total
                    })
            except:
                pass
    
    if balances_with_funds:
        for b in sorted(balances_with_funds, key=lambda x: x['total'], reverse=True):
            print(f"\n  💰 {b['currency']}")
            print(f"     Disponible: {b['free']:.8f}")
            print(f"     En uso:     {b['used']:.8f}")
            print(f"     Total:      {b['total']:.8f}")
    else:
        print("  (Sin fondos disponibles)")
        
except Exception as e:
    print(f"  ❌ Error obteniendo balance: {e}")

# ============================================================================
# SECCIÓN 2: ÓRDENES ABIERTAS
# ============================================================================
print("\n\n2️⃣  ÓRDENES ABIERTAS EN EL EXCHANGE")
print("-" * 80)

try:
    open_orders = exchange.fetch_open_orders('BTC/USDT')
    print(f"  Total órdenes abiertas: {len(open_orders)}")
    
    if open_orders:
        for i, order in enumerate(open_orders, 1):
            timestamp = datetime.fromtimestamp(order['timestamp']/1000)
            print(f"\n  {i}. Orden {order['id']}")
            print(f"     Side:   {order['side'].upper()}")
            print(f"     Qty:    {order['amount']}")
            print(f"     Precio: ${order['price']:.2f}")
            print(f"     Estado: {order['status']}")
            print(f"     Fecha:  {timestamp}")
    else:
        print("  (Sin órdenes abiertas)")
        
except Exception as e:
    print(f"  ❌ Error obteniendo órdenes: {e}")

# ============================================================================
# SECCIÓN 3: TRADES RECIENTES DEL EXCHANGE
# ============================================================================
print("\n\n3️⃣  TRADES RECIENTES (ÚLTIMOS 20)")
print("-" * 80)

try:
    trades = exchange.fetch_my_trades('BTC/USDT', limit=20)
    print(f"  Total trades recuperados: {len(trades)}")
    
    if trades:
        print("\n  Últimos 10 trades:")
        for i, trade in enumerate(trades[-10:], 1):
            timestamp = datetime.fromtimestamp(trade['timestamp']/1000)
            side = "BUY " if trade['side'] == 'buy' else "SELL"
            
            print(f"\n  {i}. {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {side}")
            print(f"     Cantidad: {trade['amount']:.8f} BTC @ ${trade['price']:.2f}")
            print(f"     Costo:    ${trade['cost']:.2f}")
            if trade['fee']:
                print(f"     Fee:      ${trade['fee'].get('cost', 0):.2f}")
    else:
        print("  (Sin trades registrados)")
        
except Exception as e:
    print(f"  ❌ Error obteniendo trades: {e}")

# ============================================================================
# SECCIÓN 4: ANÁLISIS DEL LOG - OPERACIONES CERRADAS
# ============================================================================
print("\n\n4️⃣  OPERACIONES EJECUTADAS (DESDE LOG)")
print("-" * 80)

try:
    with open('logs/bot_trader.log', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraer P&L finales
    pnl_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*P&L Final: ([\d.-]+)\s+BTC\s+\(\$([0-9.,\-]+)\)'
    matches = re.findall(pnl_pattern, content)
    
    print(f"\n  Total operaciones cerradas: {len(matches)}")
    
    if matches:
        # Calcular estadísticas
        pnl_btcs = [float(m[1]) for m in matches]
        winners = sum(1 for p in pnl_btcs if p > 0)
        losers = len(pnl_btcs) - winners
        win_rate = (winners / len(pnl_btcs) * 100) if pnl_btcs else 0
        total_pnl_btc = sum(pnl_btcs)
        total_pnl_usd = sum(float(m[2].replace(',', '').replace('.', '').replace('$', '')) / 100 if '-' not in m[2] else -float(m[2].replace(',', '').replace('$', '').replace('-', '')) / 100 for m in matches)
        
        print(f"\n  📈 ESTADÍSTICAS:")
        print(f"     Ganadoras:  {winners}")
        print(f"     Perdedoras: {losers}")
        print(f"     Win Rate:   {win_rate:.1f}%")
        print(f"     P&L Total:  {total_pnl_btc:.6f} BTC")
        
        # Extraer en USD correctamente del regex
        try:
            pnl_usds = [float(re.search(r'\$([0-9,.-]+)', m[2]).group(1).replace(',', '')) for m in matches]
            total_usd = sum(pnl_usds)
            print(f"     P&L Total:  ${total_usd:,.2f} USD")
        except:
            print(f"     P&L Total:  (no pudo parsearse en USD)")
        
        print(f"\n  📋 OPERACIONES (últimas 10):")
        for i, (timestamp, pnl_btc, pnl_str) in enumerate(matches[-10:], 1):
            pnl_f = float(pnl_btc)
            status = "✅" if pnl_f > 0 else "❌"
            print(f"     {i}. {timestamp} {status} PnL: {pnl_btc:>8} BTC | {pnl_str}")
    
except Exception as e:
    print(f"  ❌ Error analizando log: {e}")

# ============================================================================
# SECCIÓN 5: OPERACIONES ABIERTAS EN LOG
# ============================================================================
print("\n\n5️⃣  POSICIONES ABIERTAS SEGÚN LOG")
print("-" * 80)

try:
    with open('logs/bot_trader.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Buscar apertura y cierre de operaciones
    open_pattern = r"'ticket':\s*'([a-f0-9\-]+)'.*'entry_price':\s*([\d.]+)"
    close_pattern = r"Posición\s+(\w+):\s+([a-f0-9\-]+)\s+-\s+PnL:\s+([\d.\-]+)"
    
    # Contar operaciones aún abiertas
    opened = re.findall(open_pattern, content)
    closed_tickets = re.findall(r"'ticket':\s*'([a-f0-9\-]+)'", ' '.join([l for l in lines if 'P&L Final' in l]))
    
    open_tickets = set([t for t, _ in opened]) - set(closed_tickets)
    
    print(f"  Posiciones abiertas actualmente: {len(open_tickets)}")
    
    # Buscar última posición abierta con P&L en tiempo real
    position_pnl = re.findall(r"POSICIÓN ACTIVA\s+([a-f0-9\-]+).*\n.*\[DOWN\]\s+P&L:\s+([\d.\-]+)\s+BTC\s+\(\$([0-9.,\-]+)\)", content)
    
    if position_pnl:
        ticket, pnl_btc, pnl_usd = position_pnl[-1]
        print(f"\n  Última posición abierta con P&L:")
        print(f"     Ticket: {ticket[:8]}...")
        print(f"     P&L:    {pnl_btc} BTC ({pnl_usd})")
    
except Exception as e:
    print(f"  ❌ Error analizando posiciones: {e}")

print("\n" + "=" * 80)
print("✅ Análisis completado")
print("=" * 80 + "\n")
