#!/usr/bin/env python3
"""
Script simple para probar generación de señales DOGE/USDT
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config_from_yaml
import asyncio
from utils.storage import ensure_data_availability
from strategies.ultra_detailed_heikin_ashi_ml_strategy import MLModelManager

async def test_signals():
    print("🧪 PRUEBA SIMPLE DE SEÑALES DOGE/USDT")
    print("=" * 50)

    # Cargar configuración
    config = load_config_from_yaml()

    # Cargar datos usando la función centralizada
    data = await ensure_data_availability('DOGE/USDT', '4h', '2022-01-01', '2025-10-06', config)
    print(f"✅ Datos cargados: {len(data)} filas")

    if len(data) == 0:
        print("❌ No hay datos")
        return

    # Verificar modelos ML
    ml_manager = MLModelManager(config=config)
    model, scaler = ml_manager.load_model('DOGE/USDT', 'random_forest')
    print(f"✅ Modelo ML: {'Cargado' if model else 'NO ENCONTRADO'}")

    if not model:
        print("❌ No hay modelo ML entrenado")
        return

    # Simular prepare_features del MLModelManager
    config = load_config_from_yaml()
    df = data.copy()

    # Calcular indicadores básicos
    from indicators.technical_indicators import TechnicalIndicators
    indicator = TechnicalIndicators(config.__dict__ if hasattr(config, '__dict__') else config)
    df = indicator.calculate_all_indicators(df)

    # Features básicas
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    df['volatility'] = df['returns'].rolling(window=20).std()
    df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df['ha_open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)
    df['momentum_5'] = df['close'] - df['close'].shift(5)
    df['momentum_10'] = df['close'] - df['close'].shift(10)
    df['price_position'] = (df['close'] - df['close'].rolling(50).min()) / (df['close'].rolling(50).max() - df['close'].rolling(50).min())
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    df['trend_strength'] = abs(df['ema_10'] - df['ema_20']) / df['atr']

    # Seleccionar features
    feature_cols = ['ha_close', 'ha_open', 'ha_high', 'ha_low', 'ema_10', 'ema_20', 'ema_200',
                   'returns', 'log_returns', 'volatility', 'momentum_5', 'momentum_10',
                   'price_position', 'volume_ratio', 'trend_strength']

    # Preparar features para predicción
    features_df = df[feature_cols].dropna()
    print(f"✅ Features preparados: {len(features_df)} filas")

    if len(features_df) == 0:
        print("❌ No hay features válidos")
        return

    # Hacer predicciones
    try:
        predictions = ml_manager.predict_signal(features_df, 'DOGE/USDT', 'random_forest')
        print(f"✅ Predicciones ML: {len(predictions)} valores")
        print(f"   Rango: {predictions.min():.3f} - {predictions.max():.3f}")
        print(f"   > 0.5: {(predictions > 0.5).sum()}")
        print(f"   > 0.3: {(predictions > 0.3).sum()}")
    except Exception as e:
        print(f"❌ Error en predicciones: {e}")
        return

    # Verificar indicadores para señales
    recent_data = df.tail(100)  # Últimas 100 velas
    ha_changes = recent_data['ha_color_change'].value_counts()
    print(f"✅ Cambios HA recientes: {dict(ha_changes)}")

    rsi_stats = recent_data['rsi'].describe()
    print(f"✅ RSI stats: mean={rsi_stats['mean']:.1f}, min={rsi_stats['min']:.1f}, max={rsi_stats['max']:.1f}")

    stoch_stats = recent_data['stoch_k'].describe()
    print(f"✅ Stochastic stats: mean={stoch_stats['mean']:.1f}, min={stoch_stats['min']:.1f}, max={stoch_stats['max']:.1f}")

    volume_stats = recent_data['volume_ratio'].describe()
    print(f"✅ Volume ratio stats: mean={volume_stats['mean']:.2f}, min={volume_stats['min']:.2f}, max={volume_stats['max']:.2f}")

    print("\n🎯 ANÁLISIS:")
    print(f"- Predicciones ML altas (>0.5): {(predictions > 0.5).sum()}/{len(predictions)}")
    print(f"- Cambios HA LONG: {ha_changes.get(1, 0)}")
    print(f"- Cambios HA SHORT: {ha_changes.get(-1, 0)}")
    print(f"- RSI en rango 20-80: {((recent_data['rsi'] >= 20) & (recent_data['rsi'] <= 80)).sum()}/{len(recent_data)}")
    print(f"- Stochastic en rango 10-90: {((recent_data['stoch_k'] >= 10) & (recent_data['stoch_k'] <= 90)).sum()}/{len(recent_data)}")
    print(f"- Volume ratio > 0.8: {(recent_data['volume_ratio'] > 0.8).sum()}/{len(recent_data)}")

if __name__ == "__main__":
    import numpy as np
    asyncio.run(test_signals())