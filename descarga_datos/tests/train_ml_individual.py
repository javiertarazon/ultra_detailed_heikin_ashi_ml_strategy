#!/usr/bin/env python3
"""
Entrenamiento ML Individual por Símbolo
=======================================

Script simplificado para entrenar modelos ML uno por uno
para diferentes símbolos del mercado.
"""

import sys, os
import time
import asyncio
from pathlib import Path

# Añadir el directorio padre al path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from optimizacion.run_optimization_pipeline2 import OptimizationPipeline
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def train_symbol(symbol, config):
    """Entrenar modelo para un símbolo específico"""

    print(f"\n🎯 ENTRENANDO {symbol}")
    print("=" * 40)

    try:
        # Crear pipeline
        pipeline = OptimizationPipeline(
            symbols=[symbol],
            timeframe="4h",
            train_start=config['train_start'],
            train_end=config['train_end'],
            val_start=config['val_start'],
            val_end=config['val_end'],
            opt_start=config['opt_start'],
            opt_end=config['opt_end'],
            n_trials=30  # Reducido para entrenamiento más rápido
        )

        start_time = time.time()

        # Usar run_complete_pipeline (async)
        results = await pipeline.run_complete_pipeline()

        end_time = time.time()
        duration = round((end_time - start_time) / 60, 2)

        print(f"✅ {symbol} COMPLETADO en {duration} minutos")

        return {
            'status': 'SUCCESS',
            'duration': duration,
            'results': results
        }

    except Exception as e:
        print(f"❌ ERROR en {symbol}: {e}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }

async def main():
    """Entrenar todos los símbolos"""

    print("🚀 ENTRENAMIENTO ML INDIVIDUAL")
    print("=" * 50)

    # Configuración por símbolo - AJUSTADO PARA DATOS DISPONIBLES (2025) - PERÍODO EXTENDIDO
    symbols_config = {
        'SOL/USDT': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        },
        'ETH/USDT': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        },
        'TSLA/US': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        },
        'NVDA/US': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        },
        'EUR/USD': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        },
        'USD/JPY': {
            'train_start': '2025-01-01',
            'train_end': '2025-01-22',
            'val_start': '2025-01-23',
            'val_end': '2025-01-25',
            'opt_start': '2025-01-01',
            'opt_end': '2025-01-25'
        }
    }

    results = {}

    for symbol, config in symbols_config.items():
        result = await train_symbol(symbol, config)
        results[symbol] = result

        # Pequeña pausa entre entrenamientos
        await asyncio.sleep(2)

    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL")
    print("=" * 60)

    successful = 0
    failed = 0

    for symbol, result in results.items():
        if result['status'] == 'SUCCESS':
            successful += 1
            duration = result['duration']
            print(f"✅ {symbol}: {duration} min")
        else:
            failed += 1
            print(f"❌ {symbol}: ERROR")

    print(f"\n📊 TOTAL: {successful} exitosos, {failed} fallidos")

    if successful > 0:
        print("\n🎉 ¡ENTRENAMIENTO COMPLETADO!")
        print("Los modelos ML están listos para backtesting.")

if __name__ == "__main__":
    asyncio.run(main())