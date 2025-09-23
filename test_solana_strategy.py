#!/usr/bin/env python3
"""
Script para probar la nueva estrategia Solana4H
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'descarga_datos'))

import pandas as pd
import numpy as np
from strategies.solana_4h_strategy import Solana4HStrategy

def test_solana_strategy():
    # Crear datos de prueba simulados (como cripto volátil)
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='4H')  # 4H timeframe
    prices = 100 + np.cumsum(np.random.randn(500) * 5)  # Más volátil como crypto

    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.random.uniform(0, 2, 500),
        'low': prices - np.random.uniform(0, 2, 500),
        'close': prices + np.random.randn(500) * 2,
        'volume': np.random.randint(500, 5000, 500)  # Volumen variable
    })

    # Ajustar precios para que sean realistas
    df['high'] = np.maximum(df['high'], df[['open', 'close']].max(axis=1))
    df['low'] = np.minimum(df['low'], df[['open', 'close']].min(axis=1))

    # Ejecutar estrategia
    strategy = Solana4HStrategy(
        volume_threshold=1000,
        take_profit_percent=5.0,
        stop_loss_percent=3.0
    )

    result = strategy.run(df, 'SOL/USDT')

    print("=== RESULTADOS ESTRATEGIA SOLANA 4H ===")
    print(f"Símbolo: {result['symbol']}")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Win Rate: {result['win_rate']:.1f}%")
    print(f"P&L Total: ${result['total_pnl']:.2f}")
    print(f"Max Drawdown: ${result['max_drawdown']:.2f}")
    print(f"Profit Factor: {result['profit_factor']:.2f}")

    return result

if __name__ == "__main__":
    test_solana_strategy()