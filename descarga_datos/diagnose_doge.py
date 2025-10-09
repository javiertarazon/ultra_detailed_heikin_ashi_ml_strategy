#!/usr/bin/env python3
"""
Script de diagnóstico para DOGE/USDT
Verifica por qué no se generan señales de trading
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config_from_yaml
from core.downloader import AdvancedDataDownloader
from strategies.ultra_detailed_heikin_ashi_ml_strategy import UltraDetailedHeikinAshiMLStrategy
from utils.storage import StorageManager

def diagnose_doge_signals():
    """Diagnosticar por qué DOGE/USDT no genera señales"""

    print("🔍 DIAGNÓSTICO DOGE/USDT - ¿Por qué no hay señales?")
    print("=" * 60)

    # 1. Cargar configuración
    config = load_config_from_yaml()
    print(f"✅ Configuración cargada: exchange={config.active_exchange}")

    # 2. Verificar datos
    storage = StorageManager()
    data = storage.load_data('DOGE/USDT', '4h', '2022-01-01', '2025-10-06')
    print(f"✅ Datos cargados: {len(data)} filas")

    if len(data) == 0:
        print("❌ ERROR: No hay datos para DOGE/USDT")
        return

    # 3. Verificar estrategia
    strategy = UltraDetailedHeikinAshiMLStrategy(config)
    print(f"✅ Estrategia inicializada para DOGE/USDT")

    # 4. Verificar modelos ML
    from models.model_manager import ModelManager
    mm = ModelManager()
    model, scaler = mm.load_model('DOGE/USDT', 'random_forest')
    print(f"✅ Modelo ML cargado: {model is not None}")

    if model is None:
        print("❌ ERROR: No hay modelo ML entrenado para DOGE/USDT")
        return

    # 5. Preparar datos con indicadores
    try:
        data_processed = strategy._prepare_data(data.copy())
        print(f"✅ Datos procesados con indicadores: {len(data_processed)} filas")
        print(f"   Columnas disponibles: {len(data_processed.columns)}")
        print(f"   Primeras columnas: {list(data_processed.columns[:10])}")
    except Exception as e:
        print(f"❌ ERROR procesando datos: {e}")
        return

    # 6. Verificar indicadores clave
    required_indicators = ['ha_color_change', 'rsi', 'stoch_k', 'volume_ratio', 'atr']
    missing_indicators = [ind for ind in required_indicators if ind not in data_processed.columns]
    if missing_indicators:
        print(f"❌ Indicadores faltantes: {missing_indicators}")
        return
    else:
        print("✅ Todos los indicadores requeridos presentes")

    # 7. Verificar valores de indicadores
    print("\n📊 MUESTRA DE INDICADORES (últimas 5 filas):")
    sample_cols = ['close', 'ha_color_change', 'rsi', 'stoch_k', 'volume_ratio', 'atr']
    print(data_processed[sample_cols].tail())

    # 8. Generar predicciones ML
    try:
        ml_confidence = strategy.ml_manager.predict_signal(data_processed, 'DOGE/USDT', 'random_forest')
        print(f"✅ Predicciones ML generadas: {len(ml_confidence)} valores")
        print(f"   Rango de confianza: {ml_confidence.min():.3f} - {ml_confidence.max():.3f}")
        print(f"   Valores > 0.5: {(ml_confidence > 0.5).sum()}")
    except Exception as e:
        print(f"❌ ERROR en predicciones ML: {e}")
        return

    # 9. Generar señales
    try:
        signals = strategy._generate_signals(data_processed, 'DOGE/USDT', ml_confidence)
        print(f"✅ Señales generadas: {len(signals)} valores")
        print(f"   Señales LONG: {(signals == 1).sum()}")
        print(f"   Señales SHORT: {(signals == -1).sum()}")
        print(f"   Sin señal: {(signals == 0).sum()}")
    except Exception as e:
        print(f"❌ ERROR generando señales: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n🎯 DIAGNÓSTICO COMPLETADO")

if __name__ == "__main__":
    diagnose_doge_signals()