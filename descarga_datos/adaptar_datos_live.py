#!/usr/bin/env python3
"""
Script para adaptar los datos live al formato esperado por la estrategia en backtest.

Este script procesa los archivos CSV de datos live para:
1. Consolidar todos los datos en un único DataFrame
2. Calcular todos los indicadores técnicos necesarios
3. Guardar los datos procesados en un formato compatible con backtest
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import talib

# Añadir el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from utils.logger import setup_logging, get_logger
from indicators.technical_indicators import calculate_all_indicators
from config.config_loader import load_config_from_yaml

logger = get_logger(__name__)

def consolidar_datos_live(symbol='BTC_USDT', timeframe='15m'):
    """
    Consolidar los datos live en un único DataFrame.
    
    Args:
        symbol: Símbolo a procesar
        timeframe: Timeframe a procesar
        
    Returns:
        DataFrame consolidado con los datos live
    """
    live_data_path = Path(os.path.join(current_dir, "data", "live_data"))
    pattern = f"{symbol}_{timeframe}_*.csv"
    
    logger.info(f"Buscando archivos que coincidan con: {pattern}")
    files = list(live_data_path.glob(pattern))
    
    if not files:
        logger.error(f"No se encontraron archivos para {symbol} {timeframe}")
        return None
    
    logger.info(f"Se encontraron {len(files)} archivos")
    
    # DataFrame consolidado
    all_data = pd.DataFrame()
    
    # Procesar cada archivo
    for file in files:
        try:
            # Leer CSV sin especificar nombres de columnas
            df = pd.read_csv(file)
            
            if len(df.columns) >= 6:
                # Seleccionar las primeras 6 columnas y nombrarlas correctamente
                df_processed = df.iloc[:, 0:6]
                df_processed.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                all_data = pd.concat([all_data, df_processed], ignore_index=True)
            else:
                logger.warning(f"Archivo {file} no tiene suficientes columnas")
        except Exception as e:
            logger.error(f"Error al procesar {file}: {e}", exc_info=True)
    
    if all_data.empty:
        logger.error("No se pudieron procesar archivos de datos")
        return None
    
    # Convertir timestamp a datetime
    all_data['timestamp'] = pd.to_datetime(all_data['timestamp'])
    
    # Eliminar duplicados
    all_data = all_data.drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    # Ordenar por timestamp
    all_data = all_data.sort_values('timestamp').reset_index(drop=True)
    
    logger.info(f"Datos consolidados: {len(all_data)} registros")
    logger.info(f"Rango de fechas: {all_data['timestamp'].min()} a {all_data['timestamp'].max()}")
    
    return all_data

def calcular_indicadores_tecnicos(df):
    """
    Calcular todos los indicadores técnicos necesarios para la estrategia.
    
    Args:
        df: DataFrame con los datos básicos (OHLCV)
        
    Returns:
        DataFrame con todos los indicadores calculados
    """
    logger.info("Calculando indicadores técnicos...")
    
    # Utilizar la función de cálculo de indicadores del sistema
    try:
        df_with_indicators = calculate_all_indicators(df)
        
        # Verificar que los indicadores críticos fueron calculados
        indicadores_criticos = ['ha_close', 'ha_open', 'ha_high', 'ha_low', 'atr', 'rsi', 'macd']
        faltantes = [ind for ind in indicadores_criticos if ind not in df_with_indicators.columns]
        
        if faltantes:
            logger.warning(f"Faltan indicadores críticos: {faltantes}")
            # Calcular indicadores faltantes de forma manual si es necesario
            
        logger.info(f"Indicadores calculados. Columnas finales: {df_with_indicators.columns.tolist()}")
        return df_with_indicators
    except Exception as e:
        logger.error(f"Error al calcular indicadores: {e}", exc_info=True)
        # Intento de cálculo manual de indicadores críticos
        try:
            # Calculamos indicadores Heikin Ashi
            df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
            df['ha_open'] = df['open'].copy()
            for i in range(1, len(df)):
                df.loc[df.index[i], 'ha_open'] = (df.loc[df.index[i-1], 'ha_open'] + df.loc[df.index[i-1], 'ha_close']) / 2
            df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
            df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)
            
            # Calculamos indicadores básicos
            df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
            df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
            df['ema_10'] = talib.EMA(df['close'].values, timeperiod=10)
            df['ema_20'] = talib.EMA(df['close'].values, timeperiod=20)
            df['ema_50'] = talib.EMA(df['close'].values, timeperiod=50)
            df['ema_200'] = talib.EMA(df['close'].values, timeperiod=200)
            
            macd, macdsignal, macdhist = talib.MACD(df['close'].values)
            df['macd'] = macd
            df['macd_signal'] = macdsignal
            df['macd_hist'] = macdhist
            
            stoch_k, stoch_d = talib.STOCH(df['high'].values, df['low'].values, df['close'].values)
            df['stoch_k'] = stoch_k
            df['stoch_d'] = stoch_d
            
            df['cci'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
            df['sar'] = talib.SAR(df['high'].values, df['low'].values)
            
            # Calcular color change para Heikin Ashi
            df['ha_color_change'] = 0.0
            for i in range(1, len(df)):
                if (df.loc[df.index[i-1], 'ha_close'] <= df.loc[df.index[i-1], 'ha_open'] and 
                    df.loc[df.index[i], 'ha_close'] > df.loc[df.index[i], 'ha_open']):
                    df.loc[df.index[i], 'ha_color_change'] = 1.0  # cambio a verde/alcista
                elif (df.loc[df.index[i-1], 'ha_close'] >= df.loc[df.index[i-1], 'ha_open'] and 
                      df.loc[df.index[i], 'ha_close'] < df.loc[df.index[i], 'ha_open']):
                    df.loc[df.index[i], 'ha_color_change'] = -1.0  # cambio a rojo/bajista
            
            # Volumen
            df['volume_sma'] = talib.SMA(df['volume'].values, timeperiod=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            logger.info("Indicadores calculados manualmente")
            return df
            
        except Exception as e2:
            logger.error(f"Error en cálculo manual de indicadores: {e2}", exc_info=True)
            return None

def guardar_datos_procesados(df, symbol='BTC_USDT', timeframe='15m'):
    """
    Guardar los datos procesados en un formato compatible con backtest.
    
    Args:
        df: DataFrame con todos los indicadores calculados
        symbol: Símbolo procesado
        timeframe: Timeframe procesado
    """
    # Crear directorio si no existe
    output_dir = Path(os.path.join(current_dir, "data", "live_data_with_indicators"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{symbol}_{timeframe}_processed_{timestamp}.csv"
    
    # Guardar a CSV
    df.to_csv(output_file, index=False)
    logger.info(f"Datos procesados guardados en: {output_file}")
    
    return output_file

def adaptar_datos_live_para_backtest():
    """
    Flujo principal para adaptar los datos live al formato de backtest.
    """
    logger.info("=" * 80)
    logger.info("ADAPTANDO DATOS LIVE PARA FORMATO BACKTEST")
    logger.info("=" * 80)
    
    # Cargar configuración
    config = load_config_from_yaml()
    symbol = config.backtesting.symbols[0].replace('/', '_')  # Primer símbolo configurado
    timeframe = config.backtesting.timeframe
    
    logger.info(f"Procesando símbolo: {symbol}, timeframe: {timeframe}")
    
    # Paso 1: Consolidar datos live
    data = consolidar_datos_live(symbol, timeframe)
    if data is None or data.empty:
        logger.error("No se pudieron consolidar los datos live")
        return False
    
    # Paso 2: Calcular indicadores técnicos
    data_with_indicators = calcular_indicadores_tecnicos(data)
    if data_with_indicators is None or data_with_indicators.empty:
        logger.error("No se pudieron calcular los indicadores técnicos")
        return False
    
    # Paso 3: Guardar datos procesados
    output_file = guardar_datos_procesados(data_with_indicators, symbol, timeframe)
    
    logger.info(f"Procesamiento completo. Datos adaptados guardados en: {output_file}")
    return True

if __name__ == "__main__":
    # Configurar logging
    setup_logging(log_level="DEBUG", log_file="logs/adaptar_datos_live.log")
    
    success = adaptar_datos_live_para_backtest()
    
    if success:
        logger.info("✅ ADAPTACIÓN DE DATOS COMPLETADA CON ÉXITO")
    else:
        logger.error("❌ ADAPTACIÓN DE DATOS FALLIDA")