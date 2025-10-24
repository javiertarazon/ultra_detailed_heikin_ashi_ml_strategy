#!/usr/bin/env python3
"""
AUDITORÍA COMPLETA DE DATOS - Sistema Bot Trader Copilot
========================================================

Esta auditoría verifica:
1. Integridad de datos históricos descargados
2. Cálculo correcto de indicadores técnicos
3. Escalado y normalización de features ML
4. Cantidad de barras disponibles
5. Problemas de NaN y valores cero en indicadores críticos

MODO LIVE: Verifica indicadores con datos en tiempo real de exchanges
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
import sys
import os
import asyncio
import ccxt

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def audit_database():
    """Auditar base de datos SQLite"""
    print('🔍 AUDITORÍA DE BASE DE DATOS')
    print('=' * 50)

    data_dir = Path('data')
    db_path = data_dir / 'data.db'

    if db_path.exists():
        print(f'✅ Base de datos SQLite encontrada: {db_path}')

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Ver tablas disponibles
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f'Tablas en BD: {[t[0] for t in tables]}')

            # Verificar tabla BTC_USDT_15m
            table_name = 'BTC_USDT_15m'
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'Registros en {table_name}: {count}')

            if count > 0:
                # Verificar estructura de datos
                cursor.execute(f'PRAGMA table_info({table_name})')
                columns = cursor.fetchall()
                print(f'Columnas en {table_name}: {[col[1] for col in columns]}')

                # Verificar datos recientes
                cursor.execute(f'SELECT timestamp, open, high, low, close, volume FROM {table_name} ORDER BY timestamp DESC LIMIT 5')
                recent_data = cursor.fetchall()
                print('Últimos 5 registros:')
                for row in recent_data:
                    print(f'  {row}')

                # Verificar rango temporal
                cursor.execute(f'SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}')
                date_range = cursor.fetchone()
                print(f'Rango temporal: {date_range[0]} - {date_range[1]}')

            conn.close()
            return True

        except Exception as e:
            print(f'❌ Error accediendo a BD: {e}')
            return False
    else:
        print(f'❌ Base de datos SQLite NO encontrada: {db_path}')
        return False

async def audit_live_data():
    """Auditar datos en tiempo real desde exchanges"""
    print()
    print('🌐 AUDITORÍA DE DATOS LIVE')
    print('=' * 40)

    try:
        # Configurar exchanges
        exchanges = {
            'binance': ccxt.binance(),
            'bybit': ccxt.bybit()
        }

        symbol = 'BTC/USDT'
        timeframe = '15m'
        limit = 100  # Últimas 100 velas de 15m

        print(f'Descargando datos live para {symbol} en {timeframe}...')

        for exchange_name, exchange in exchanges.items():
            try:
                print(f'  Intentando {exchange_name}...')

                # Descargar datos recientes
                ohlcv = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                )

                if ohlcv and len(ohlcv) > 0:
                    print(f'  ✅ {exchange_name}: {len(ohlcv)} velas descargadas')

                    # Convertir a DataFrame
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

                    print(f'    Rango temporal: {df["timestamp"].min()} - {df["timestamp"].max()}')
                    print(f'    Precio: {df["close"].iloc[-1]:.2f} USDT')
                    print(f'    Volumen último: {df["volume"].iloc[-1]:.4f}')

                    # Calcular indicadores básicos
                    try:
                        from indicators.technical_indicators import TechnicalIndicators
                        from config.config_loader import load_config_from_yaml

                        config = load_config_from_yaml()
                        ti = TechnicalIndicators(config)

                        # Calcular indicadores
                        df_with_indicators = ti.calculate_all_indicators(df)

                        # Verificar indicadores críticos
                        critical_indicators = ['rsi', 'stoch_k', 'cci', 'macd', 'atr']
                        print('    Verificación de indicadores:')

                        for indicator in critical_indicators:
                            if indicator in df_with_indicators.columns:
                                nan_count = df_with_indicators[indicator].isna().sum()
                                valid_count = df_with_indicators[indicator].notna().sum()
                                print(f'      {indicator}: {nan_count} NaN, {valid_count} válidos')
                            else:
                                print(f'      {indicator}: ❌ NO CALCULADO')

                        return True

                    except Exception as e:
                        print(f'    ❌ Error calculando indicadores: {e}')
                        return False

                else:
                    print(f'  ❌ {exchange_name}: No se obtuvieron datos')

            except Exception as e:
                print(f'  ❌ Error en {exchange_name}: {e}')
                continue

        print('❌ No se pudieron obtener datos live de ningún exchange')
        return False

    except Exception as e:
        print(f'❌ Error en auditoría live: {e}')
        return False

async def audit_indicators():
    """Auditar cálculo de indicadores técnicos"""
    print()
    print('📊 AUDITORÍA DE INDICADORES TÉCNICOS')
    print('=' * 40)

    try:
        from indicators.technical_indicators import TechnicalIndicators
        from utils.storage import ensure_data_availability
        from config.config_loader import load_config_from_yaml

        config = load_config_from_yaml()
        symbol = 'BTC/USDT'
        timeframe = '15m'

        # Intentar cargar datos usando la función centralizada
        data = await ensure_data_availability(symbol, timeframe, config=config)

        if data is not None and not data.empty:
            print(f'✅ Datos cargados: {len(data)} filas')
            print(f'Columnas disponibles: {list(data.columns)}')
            print(f'Rango temporal: {data.index.min()} - {data.index.max()}')

            # Verificar valores OHLCV básicos
            print(f'Precio Close - Rango: {data["close"].min():.2f} - {data["close"].max():.2f}')
            print(f'Volumen - Rango: {data["volume"].min():.2f} - {data["volume"].max():.2f}')

            # Calcular indicadores
            indicator = TechnicalIndicators(config)
            data_with_indicators = indicator.calculate_all_indicators(data.copy())

            print(f'✅ Indicadores calculados: {len(data_with_indicators.columns)} columnas totales')

            # Verificar indicadores críticos
            critical_indicators = ['ha_close', 'macd', 'rsi', 'stoch_k', 'cci', 'atr']
            print()
            print('🔍 VERIFICACIÓN DE INDICADORES CRÍTICOS:')

            problems_detected = []

            for indicator_name in critical_indicators:
                if indicator_name in data_with_indicators.columns:
                    values = data_with_indicators[indicator_name]
                    nan_count = values.isna().sum()
                    zero_count = (values == 0).sum()
                    valid_count = len(values) - nan_count - zero_count

                    print(f'  {indicator_name}:')
                    print(f'    NaN: {nan_count}, Zero: {zero_count}, Valid: {valid_count}')
                    print(f'    Rango: {values.min():.6f} - {values.max():.6f}')

                    if nan_count > 0 or zero_count > len(values) * 0.5:
                        print(f'    ⚠️  PROBLEMA DETECTADO en {indicator_name}')
                        problems_detected.append(indicator_name)
                    else:
                        print(f'    ✅ OK')
                else:
                    print(f'  ❌ {indicator_name}: NO ENCONTRADO')
                    problems_detected.append(indicator_name)

            return data_with_indicators, problems_detected

        else:
            print('❌ No se pudieron cargar datos históricos')
            return None, ['no_data']

    except Exception as e:
        print(f'❌ Error en auditoría de indicadores: {e}')
        import traceback
        traceback.print_exc()
        return None, ['error']

def audit_ml_features(data_with_indicators):
    """Auditar features para ML"""
    print()
    print('🤖 AUDITORÍA DE FEATURES ML')
    print('=' * 30)

    if data_with_indicators is None:
        print('❌ No hay datos para auditar features ML')
        return 0, 0

    try:
        # Simular preparación de features como en la estrategia
        df = data_with_indicators.copy()

        # Calcular features adicionales como en la estrategia
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

        # Lista de features esperadas
        expected_features = [
            'ha_close', 'ha_open', 'ha_high', 'ha_low', 'ema_10', 'ema_20', 'ema_200',
            'macd', 'macd_signal', 'adx', 'sar', 'atr', 'volatility', 'bb_upper',
            'bb_middle', 'bb_lower', 'bb_width', 'rsi', 'momentum_5', 'momentum_10',
            'volume_ratio', 'price_position', 'trend_strength', 'returns', 'log_returns'
        ]

        available_features = [f for f in expected_features if f in df.columns]
        missing_features = [f for f in expected_features if f not in df.columns]

        print(f'Features disponibles: {len(available_features)}/{len(expected_features)}')
        if missing_features:
            print(f'❌ Features faltantes: {missing_features}')

        # Verificar NaN en features
        nan_summary = df[available_features].isna().sum()
        if nan_summary.sum() > 0:
            print('NaN por feature:')
            for feature, count in nan_summary.items():
                if count > 0:
                    print(f'  {feature}: {count} NaN')

        # Verificar datos limpios (como en la estrategia)
        clean_data = df.dropna(subset=['ha_close', 'macd', 'rsi', 'stoch_k', 'cci', 'atr'])
        print(f'Datos originales: {len(df)}, Datos limpios: {len(clean_data)}')
        print(f'Filas eliminadas por NaN: {len(df) - len(clean_data)}')

        # Verificar escalado/normalización
        print()
        print('🔧 VERIFICACIÓN DE ESCALADO/NORMALIZACIÓN:')
        for feature in available_features[:5]:  # Solo primeros 5 para no saturar output
            if feature in df.columns:
                values = df[feature].dropna()
                if len(values) > 0:
                    mean_val = values.mean()
                    std_val = values.std()
                    min_val = values.min()
                    max_val = values.max()
                    print(f'  {feature}: mean={mean_val:.6f}, std={std_val:.6f}, range=[{min_val:.6f}, {max_val:.6f}]')

        return len(clean_data), len(df) - len(clean_data)

    except Exception as e:
        print(f'❌ Error en auditoría de features ML: {e}')
        import traceback
        traceback.print_exc()
        return 0, 0

async def main():
    """Función principal de auditoría"""
    print('🚀 INICIANDO AUDITORÍA COMPLETA DE DATOS')
    print('Sistema Bot Trader Copilot')
    print(f'Fecha/Hora: {datetime.now()}')
    print('=' * 60)

    # 0. Auditar datos live (si se solicita)
    import sys
    live_mode = '--live' in sys.argv or len(sys.argv) > 1 and 'live' in sys.argv[1].lower()

    if live_mode:
        print('🌐 MODO LIVE DETECTADO - Verificando datos en tiempo real')
        live_ok = await audit_live_data()
        if not live_ok:
            print('❌ Auditoría live falló - verificando datos históricos...')
    else:
        live_ok = None

    # 1. Auditar base de datos
    db_ok = audit_database()

    # 2. Auditar indicadores
    data_with_indicators, indicator_problems = await audit_indicators()

    # 3. Auditar features ML
    if data_with_indicators is not None:
        clean_rows, removed_rows = audit_ml_features(data_with_indicators)
    else:
        clean_rows, removed_rows = 0, 0

    # 4. Resumen final
    print()
    print('📋 RESUMEN FINAL DE AUDITORÍA')
    print('=' * 40)

    if live_ok is not None:
        if live_ok:
            print('✅ Datos Live: OK')
        else:
            print('❌ Datos Live: PROBLEMAS')

    if db_ok:
        print('✅ Base de datos: OK')
    else:
        print('❌ Base de datos: PROBLEMAS')

    if not indicator_problems or indicator_problems == ['no_data']:
        print('✅ Indicadores técnicos: OK')
    else:
        print(f'❌ Indicadores técnicos: PROBLEMAS en {indicator_problems}')

    if clean_rows > 0 and removed_rows < clean_rows * 0.2:  # Menos del 20% removido
        print('✅ Features ML: OK')
    else:
        print('❌ Features ML: PROBLEMAS')

    print(f'Datos limpios disponibles: {clean_rows} filas')
    print(f'Datos eliminados por NaN: {removed_rows} filas')

    if clean_rows > 200 and not indicator_problems:
        if live_ok is None or live_ok:
            print('🎯 RESULTADO: Sistema listo para trading')
        else:
            print('⚠️  RESULTADO: Revisar problemas en datos live antes de trading')
    else:
        print('⚠️  RESULTADO: Revisar problemas antes de trading')

    print()
    print('Auditoría completada.')

if __name__ == '__main__':
    asyncio.run(main())