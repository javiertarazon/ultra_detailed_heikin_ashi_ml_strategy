#!/usr/bin/env python3
"""
Entrenamiento ML Completo para Todos los Símbolos
Entrena modelos ML para todos los símbolos configurados
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

async def train_symbol_safe(symbol, config):
    """Entrenar modelo para un símbolo específico con manejo seguro de errores"""

    print(f"\n🎯 ENTRENANDO {symbol}")
    print("=" * 50)

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
            n_trials=10  # Reducido para entrenamiento más rápido
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

    print("🚀 ENTRENAMIENTO ML COMPLETO PARA TODOS LOS SÍMBOLOS")
    print("=" * 60)

    # Configuración por símbolo - PERÍODO EXTENDIDO PARA SUFICIENTES DATOS
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
    successful = 0
    failed = 0

    for symbol, config in symbols_config.items():
        print(f"\n🔄 PROCESANDO {symbol}...")
        result = await train_symbol_safe(symbol, config)
        results[symbol] = result

        if result['status'] == 'SUCCESS':
            successful += 1
        else:
            failed += 1

        # Pausa entre entrenamientos para evitar sobrecarga
        await asyncio.sleep(5)

    # Resumen final
    print("\n" + "=" * 80)
    print("📋 RESUMEN FINAL DEL ENTRENAMIENTO ML")
    print("=" * 80)
    print(f"✅ Símbolos exitosos: {successful}")
    print(f"❌ Símbolos fallidos: {failed}")
    print(f"📊 Total procesados: {len(symbols_config)}")

    print("\n📈 DETALLE POR SÍMBOLO:")
    for symbol, result in results.items():
        status = "✅" if result['status'] == 'SUCCESS' else "❌"
        duration = f"{result.get('duration', 0):.2f}min" if result['status'] == 'SUCCESS' else "N/A"
        print(f"  {status} {symbol}: {duration}")

    if successful > 0:
        print(f"\n🎉 ENTRENAMIENTO COMPLETADO! {successful} modelos ML entrenados exitosamente.")
        print("Los modelos están guardados en la carpeta 'models/'")
    else:
        print("\n⚠️  No se pudo entrenar ningún modelo ML.")

if __name__ == "__main__":
    asyncio.run(main())