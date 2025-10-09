#!/usr/bin/env python3
"""
Script para Entrenamiento ML Completo - UltraDetailedHeikinAshiML
=================================================================

Entrena modelos ML para múltiples símbolos y ejecuta optimización completa:
- SOL/USDT (ya entrenado)
- ETH/USDT (ya entrenado)
- TSLA/US (nuevo - acción)
- NVDA/US (nuevo - acción)
- EUR/USD (nuevo - forex)
- USD/JPY (nuevo - forex)

Proceso:
1. Entrenamiento de modelos ML para cada símbolo
2. Optimización de parámetros con Optuna
3. Backtesting final con mejores parámetros
"""

import sys, os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple

# Añadir el directorio padre al path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from config.config_loader import load_config_from_yaml
from optimizacion.run_optimization_pipeline2 import OptimizationPipeline
from utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Entrenar modelos ML para todos los símbolos"""

    print("🚀 INICIANDO ENTRENAMIENTO ML COMPLETO")
    print("=" * 50)

    # Configuración de símbolos a entrenar
    symbols_to_train = [
        'SOL/USDT',   # Ya entrenado - referencia
        'ETH/USDT',   # Ya entrenado - referencia
        'TSLA/US',    # Nuevo - acción Tesla
        'NVDA/US',    # Nuevo - acción Nvidia
        'EUR/USD',    # Nuevo - forex Euro/Dólar
        'USD/JPY'     # Nuevo - forex Dólar/Yen
    ]

    # Configuración temporal adaptada para diferentes mercados
    market_configs = {
        # Criptomonedas (datos más recientes disponibles)
        'SOL/USDT': {
            'train_start': '2023-01-01',
            'train_end': '2024-06-30',
            'val_start': '2024-07-01',
            'val_end': '2024-12-31',
            'opt_start': '2023-01-01',
            'opt_end': '2024-12-31'
        },
        'ETH/USDT': {
            'train_start': '2023-01-01',
            'train_end': '2024-06-30',
            'val_start': '2024-07-01',
            'val_end': '2024-12-31',
            'opt_start': '2023-01-01',
            'opt_end': '2024-12-31'
        },
        # Acciones (datos históricos más largos disponibles)
        'TSLA/US': {
            'train_start': '2022-01-01',
            'train_end': '2023-12-31',
            'val_start': '2024-01-01',
            'val_end': '2024-06-30',
            'opt_start': '2022-01-01',
            'opt_end': '2024-06-30'
        },
        'NVDA/US': {
            'train_start': '2022-01-01',
            'train_end': '2023-12-31',
            'val_start': '2024-01-01',
            'val_end': '2024-06-30',
            'opt_start': '2022-01-01',
            'opt_end': '2024-06-30'
        },
        # Forex (datos históricos muy largos disponibles)
        'EUR/USD': {
            'train_start': '2020-01-01',
            'train_end': '2023-12-31',
            'val_start': '2024-01-01',
            'val_end': '2024-06-30',
            'opt_start': '2020-01-01',
            'opt_end': '2024-06-30'
        },
        'USD/JPY': {
            'train_start': '2020-01-01',
            'train_end': '2023-12-31',
            'val_start': '2024-01-01',
            'val_end': '2024-06-30',
            'opt_start': '2020-01-01',
            'opt_end': '2024-06-30'
        }
    }

    results_summary = {}

    for symbol in symbols_to_train:
        print(f"\n🎯 ENTRENANDO MODELO PARA {symbol}")
        print("-" * 40)

        try:
            # Obtener configuración específica del mercado
            config = market_configs[symbol]

            # Crear pipeline de optimización
            pipeline = OptimizationPipeline(
                symbols=[symbol],
                timeframe="4h",
                train_start=config['train_start'],
                train_end=config['train_end'],
                val_start=config['val_start'],
                val_end=config['val_end'],
                opt_start=config['opt_start'],
                opt_end=config['opt_end'],
                n_trials=50  # Número de trials de optimización
            )

            # Ejecutar pipeline completo
            print(f"📊 Ejecutando pipeline completo para {symbol}...")
            start_time = time.time()

            results = pipeline.run()

            end_time = time.time()
            duration = end_time - start_time

            # Guardar resultados
            results_summary[symbol] = {
                'status': 'SUCCESS',
                'duration_minutes': round(duration / 60, 2),
                'results': results,
                'config': config
            }

            print(f"✅ {symbol} completado en {duration:.1f} segundos")

        except Exception as e:
            print(f"❌ Error entrenando {symbol}: {e}")
            results_summary[symbol] = {
                'status': 'ERROR',
                'error': str(e),
                'config': market_configs[symbol]
            }

    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL DEL ENTRENAMIENTO ML")
    print("=" * 60)

    successful = 0
    failed = 0

    for symbol, result in results_summary.items():
        status = result['status']
        if status == 'SUCCESS':
            successful += 1
            duration = result['duration_minutes']
            print(f"✅ {symbol}: ENTRENADO ({duration} min)")
        else:
            failed += 1
            print(f"❌ {symbol}: ERROR - {result.get('error', 'Unknown')}")

    print(f"\n📊 TOTAL: {successful} exitosos, {failed} fallidos")

    # Guardar resumen completo
    summary_file = "data/training_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, default=str)

    print(f"💾 Resumen guardado en: {summary_file}")

    if successful > 0:
        print("\n🎉 ENTRENAMIENTO COMPLETADO!")
        print("Los modelos ML están listos para usar en backtesting y trading.")
    else:
        print("\n⚠️  No se pudo entrenar ningún modelo. Revisar logs para más detalles.")

if __name__ == "__main__":
    main()