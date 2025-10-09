#!/usr/bin/env python3
"""
Entrenamiento ML Individual por Símbolo - Versión Simplificada
"""

import asyncio
import sys
import os

# Añadir el directorio padre al path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from optimizacion.run_optimization_pipeline2 import OptimizationPipeline

async def train_single_symbol(symbol):
    """Entrenar un solo símbolo"""
    print(f"\n🎯 ENTRENANDO {symbol}")
    print("=" * 50)

    try:
        pipeline = OptimizationPipeline(
            symbols=[symbol],
            timeframe="4h",
            train_start='2025-01-01',
            train_end='2025-01-22',
            val_start='2025-01-23',
            val_end='2025-01-25',
            opt_start='2025-01-01',
            opt_end='2025-01-25',
            n_trials=5  # Muy reducido para velocidad
        )

        results = await pipeline.run_complete_pipeline()
        print(f"✅ {symbol} COMPLETADO")
        return True

    except Exception as e:
        print(f"❌ ERROR en {symbol}: {e}")
        return False

async def main():
    """Entrenar todos los símbolos uno por uno"""
    symbols = ['SOL/USDT', 'ETH/USDT', 'TSLA/US', 'NVDA/US', 'EUR/USD', 'USD/JPY']

    print("🚀 ENTRENAMIENTO ML PARA TODOS LOS SÍMBOLOS")
    print("=" * 60)

    successful = 0
    total = len(symbols)

    for i, symbol in enumerate(symbols, 1):
        print(f"\n🔄 [{i}/{total}] PROCESANDO {symbol}...")

        success = await train_single_symbol(symbol)
        if success:
            successful += 1

        # Pequeña pausa
        await asyncio.sleep(2)

    print(f"\n📊 RESULTADO FINAL: {successful}/{total} símbolos entrenados exitosamente")

if __name__ == "__main__":
    asyncio.run(main())