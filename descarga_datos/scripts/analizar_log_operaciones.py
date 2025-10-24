#!/usr/bin/env python
"""Script para analizar operaciones del log de trading en vivo."""

import re
from datetime import datetime
from pathlib import Path

log_file = Path("logs/bot_trader.log")

if not log_file.exists():
    print("❌ No se encontró el archivo de log")
    exit(1)

# Leer el log
with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Buscar operaciones abiertas
apertura_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*APERTURA DE OPERACI[ÓO]N: (\w+) BTC/USDT.*Precio entrada: \$([\d,.]+).*Stop Loss: \$([\d,.]+).*Take Profit: \$([\d,.]+)'
aperturas = re.findall(apertura_pattern, content)

# Buscar posiciones cerradas
cerrada_pattern = r'Posici[ó]n cerrada: (\d+) - PnL: ([-\d,.]+)'
cerradas = re.findall(cerrada_pattern, content)

# Buscar P&L activos
pnl_pattern = r'P&L: ([+-]?\$[\d,.]+) USDT.*[-+]\d\.\d+%'
pnls = re.findall(pnl_pattern, content)

# Buscar trailing stop activado
trailing_pattern = r'trailing.*stop|stop.*trailing|Trailing Stop: ([\d.]+)%'
trailing_matches = re.findall(trailing_pattern, content, re.IGNORECASE)

print("\n" + "="*80)
print("📊 ANÁLISIS DE OPERACIONES - LIVE TRADING")
print("="*80)

print(f"\n🔴 OPERACIONES ABIERTAS: {len(aperturas)}")
print("-" * 80)

buy_count = 0
sell_count = 0

for i, (tiempo, tipo, entrada, sl, tp) in enumerate(aperturas[-10:], 1):
    clean_entrada = entrada.replace(',', '')
    clean_sl = sl.replace(',', '')
    clean_tp = tp.replace(',', '')
    
    if tipo == "BUY":
        buy_count += 1
        direc = "🟢 BUY (Compra)"
    else:
        sell_count += 1
        direc = "🔴 SELL (Venta)"
    
    print(f"\n  Op #{len(aperturas) - len(aperturas) + i}: {direc}")
    print(f"    Hora:        {tiempo}")
    print(f"    Entrada:     ${float(clean_entrada):,.2f}")
    print(f"    Stop Loss:   ${float(clean_sl):,.2f}")
    print(f"    Take Profit: ${float(clean_tp):,.2f}")

print(f"\n📈 RESUMEN DE OPERACIONES ABIERTAS:")
print(f"    Total:  {len(aperturas)} operaciones")
print(f"    BUY:    {buy_count} compras")
print(f"    SELL:   {sell_count} ventas")

print(f"\n🔚 OPERACIONES CERRADAS: {len(cerradas)}")
print("-" * 80)

if cerradas:
    ganadores = 0
    perdedores = 0
    total_pnl = 0
    
    for ticket, pnl in cerradas[-10:]:
        pnl_float = float(pnl.replace(',', ''))
        total_pnl += pnl_float
        
        if pnl_float > 0:
            ganadores += 1
            estado = "✅ GANADORA"
        else:
            perdedores += 1
            estado = "❌ PERDEDORA"
        
        print(f"\n  Ticket #{ticket}: {estado}")
        print(f"    P&L: ${pnl_float:,.2f}")
    
    print(f"\n📊 RESUMEN DE OPERACIONES CERRADAS:")
    print(f"    Total cerradas:       {len(cerradas)}")
    print(f"    Ganadoras:            {ganadores}")
    print(f"    Perdedoras:           {perdedores}")
    print(f"    Total P&L:            ${total_pnl:,.2f}")
    if len(cerradas) > 0:
        print(f"    Win Rate:             {ganadores/len(cerradas):.1%}")
else:
    print("\n  📭 Sin operaciones cerradas")

print(f"\n⛔ TRAILING STOP ACTIVADO: {'Sí' if trailing_matches else 'No'}")
print("-" * 80)
if trailing_matches:
    print(f"    Trailing Stop %: {trailing_matches[0] if trailing_matches[0] else 'N/A'}")
    # Buscar menciones de cierre por trailing
    trailing_close = content.count("trailing") + content.count("Trailing")
    print(f"    Menciones: {trailing_close} veces en el log")

print("\n" + "="*80 + "\n")
