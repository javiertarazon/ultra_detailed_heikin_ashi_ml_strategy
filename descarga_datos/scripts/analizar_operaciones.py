#!/usr/bin/env python
"""Script para obtener estadísticas de operaciones en vivo desde el tracker."""

import json
import os
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, 'descarga_datos')

# Ruta del tracker
tracker_path = Path("descarga_datos/data/live_trading_results")

# Obtener el archivo más reciente
if not tracker_path.exists():
    print("❌ No se encontró la carpeta de resultados")
    sys.exit(1)

json_files = list(tracker_path.glob("*.json"))
if not json_files:
    print("❌ No hay archivos de resultados")
    sys.exit(1)

latest_file = max(json_files, key=os.path.getctime)
print(f"📊 Leyendo: {latest_file.name}")
print("=" * 80)

with open(latest_file, 'r') as f:
    data = json.load(f)

metrics = data.get("metrics", {})
trades = data.get("trades_history", [])

print(f"\n🎯 ESTADÍSTICAS DE TRADING")
print("=" * 80)
print(f"  Total de operaciones:     {metrics.get('total_trades', 0)}")
print(f"  Operaciones ganadoras:    {metrics.get('winning_trades', 0)}")
print(f"  Operaciones perdedoras:   {metrics.get('losing_trades', 0)}")
print(f"  Tasa de ganancia:         {metrics.get('win_rate', 0):.2%}")
print(f"  P&L Total:                ${metrics.get('total_pnl', 0):,.2f} USDT")
print(f"  P&L Ganancias:            ${metrics.get('total_winning_pnl', 0):,.2f} USDT")
print(f"  P&L Pérdidas:             ${metrics.get('total_losing_pnl', 0):,.2f} USDT")

print(f"\n💰 BALANCE")
print("=" * 80)
print(f"  Balance inicial:          ${metrics.get('initial_balance', 0):,.2f} USDT")
print(f"  Balance actual:           ${metrics.get('current_balance', 0):,.2f} USDT")
print(f"  Peak balance:             ${metrics.get('peak_balance', 0):,.2f} USDT")
print(f"  Retorno total:            {metrics.get('total_return_pct', 0):.2%}")

print(f"\n📈 RIESGO Y PERFORMANCE")
print("=" * 80)
print(f"  Max Drawdown:             {metrics.get('max_drawdown', 0):.2%}")
print(f"  Current Drawdown:         {metrics.get('current_drawdown', 0):.2%}")
print(f"  Profit Factor:            {metrics.get('profit_factor', 0):.2f}")
print(f"  Sharpe Ratio:             {metrics.get('sharpe_ratio', 0):.2f}")
print(f"  Calmar Ratio:             {metrics.get('calmar_ratio', 0):.2f}")

print(f"\n⏱️ TIEMPO")
print("=" * 80)
print(f"  Inicio:                   {metrics.get('start_time', 'N/A')}")
print(f"  Última actualización:     {metrics.get('last_update', 'N/A')}")
print(f"  Tiempo de ejecución:      {metrics.get('runtime_minutes', 0):.1f} minutos")

print(f"\n📋 HISTORIAL DE OPERACIONES")
print("=" * 80)

if trades:
    for i, trade in enumerate(trades[-10:], 1):  # Últimas 10 operaciones
        print(f"\n  Operación #{i}:")
        print(f"    Ticket:        {trade.get('ticket', 'N/A')}")
        print(f"    Tipo:          {trade.get('type', 'N/A').upper()}")
        print(f"    Símbolo:       {trade.get('symbol', 'N/A')}")
        print(f"    Cantidad:      {trade.get('quantity', 0):.4f}")
        print(f"    Entrada:       ${trade.get('entry_price', 0):,.2f}")
        print(f"    P&L:           ${trade.get('pnl', 0):,.2f}")
        print(f"    Estado:        {trade.get('status', 'N/A')}")
        print(f"    Trailing Stop: {trade.get('trailing_stop_pct', 0):.0%}")
else:
    print("\n  📭 Sin operaciones registradas aún")

print(f"\n{'=' * 80}\n")
