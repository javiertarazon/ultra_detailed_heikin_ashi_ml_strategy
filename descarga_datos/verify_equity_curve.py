#!/usr/bin/env python3
"""
Script para verificar que la equity curve se calcula correctamente
con el capital inicial correcto.
"""

import json
import sys
from pathlib import Path

def verify_equity_curve():
    # Cargar resultados
    base_path = Path(__file__).parent / "data" / "dashboard_results"
    results_file = base_path / "BTC_USDT_results.json"

    if not results_file.exists():
        print("❌ No se encontró el archivo de resultados")
        return

    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extraer datos de la estrategia
    strategy_data = data['strategies']['UltraDetailedHeikinAshiML']
    initial_capital = strategy_data['initial_capital']
    total_pnl = strategy_data['total_pnl']
    trades = strategy_data['trades']
    equity_curve = strategy_data.get('equity_curve', [])

    print("=== VERIFICACIÓN DE EQUITY CURVE ===")
    print(f"Capital inicial: ${initial_capital}")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"Capital final esperado: ${initial_capital + total_pnl:.2f}")
    print(f"Número de trades: {len(trades)}")
    print(f"Longitud equity curve: {len(equity_curve)}")

    if equity_curve:
        print(f"Primer valor equity curve: ${equity_curve[0]}")
        print(f"Último valor equity curve: ${equity_curve[-1]}")

        # Verificar consistencia
        if abs(equity_curve[0] - initial_capital) < 0.01:
            print("✅ Equity curve inicia con capital correcto")
        else:
            print(f"❌ ERROR: Equity curve inicia con ${equity_curve[0]}, debería ser ${initial_capital}")

        expected_final = initial_capital + total_pnl
        if abs(equity_curve[-1] - expected_final) < 0.01:
            print("✅ Equity curve final coincide con P&L total")
        else:
            print(f"❌ ERROR: Equity curve final es ${equity_curve[-1]}, debería ser ${expected_final}")

        # Verificar algunos puntos intermedios
        running_total = initial_capital
        for i, trade in enumerate(trades[:5]):  # Verificar primeros 5 trades
            running_total += trade['pnl']
            if i + 1 < len(equity_curve):
                if abs(equity_curve[i + 1] - running_total) > 0.01:
                    print(f"❌ ERROR en trade {i+1}: esperado ${running_total}, equity curve tiene ${equity_curve[i+1]}")
                else:
                    print(f"✅ Trade {i+1}: correcto")
    else:
        print("❌ No hay equity curve generada")

if __name__ == "__main__":
    verify_equity_curve()