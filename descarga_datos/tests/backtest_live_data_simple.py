#!/usr/bin/env python3
"""
Script simplificado para ejecutar un backtest utilizando los datos recopilados en modo live.

Este script permite verificar si el sistema encuentra las mismas señales en modo backtest
que se encontrarían en modo live, utilizando los mismos datos.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import asyncio
import json
import glob
from datetime import datetime

# Añadir el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config.config_loader import load_config_from_yaml
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

def consolidate_live_data(symbol='BTC_USDT', timeframe='15m'):
    """
    Consolida los archivos CSV de datos live en un único DataFrame.
    
    Args:
        symbol (str): El símbolo para el que se recopilarán los datos
        timeframe (str): El timeframe de los datos a consolidar
    
    Returns:
        pd.DataFrame: DataFrame consolidado con todos los datos live
    """
    live_data_path = Path(current_dir).parent / "data" / "live_data"
    pattern = f"{symbol}_{timeframe}_*.csv"
    
    logger.info(f"Buscando archivos que coincidan con el patrón: {pattern}")
    files = list(live_data_path.glob(pattern))
    
    if not files:
        logger.error(f"No se encontraron archivos para {symbol} {timeframe}")
        return None
    
    logger.info(f"Se encontraron {len(files)} archivos")
    
    # Crear un DataFrame para almacenar todos los datos
    all_data = pd.DataFrame()
    
    # Procesar cada archivo
    for file in files:
        logger.info(f"Procesando archivo: {file}")
        try:
            # Leer archivo sin especificar nombres de columnas
            df = pd.read_csv(file)
            
            # Verificar que el archivo tiene las columnas esperadas
            if len(df.columns) >= 6:
                # Seleccionar solo las primeras 6 columnas
                df_processed = df.iloc[:, 0:6]
                df_processed.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                all_data = pd.concat([all_data, df_processed], ignore_index=True)
            else:
                logger.warning(f"Archivo {file} no tiene suficientes columnas, omitiendo")
        except Exception as e:
            logger.error(f"Error al procesar {file}: {e}", exc_info=True)
    
    if all_data.empty:
        logger.error("No se pudieron procesar archivos de datos")
        return None
    
    # Asegurar que timestamp sea datetime
    all_data['timestamp'] = pd.to_datetime(all_data['timestamp'])
    
    # Eliminar duplicados
    all_data = all_data.drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    # Ordenar por timestamp
    all_data = all_data.sort_values('timestamp').reset_index(drop=True)
    
    logger.info(f"Datos consolidados: {len(all_data)} registros")
    
    # Verificar que los datos sean consistentes
    start_date = all_data['timestamp'].min().strftime('%Y-%m-%d')
    end_date = all_data['timestamp'].max().strftime('%Y-%m-%d')
    logger.info(f"Rango de fechas: {start_date} a {end_date}")
    
    return all_data

async def run_backtest_with_live_data():
    """
    Ejecuta un backtest utilizando los datos recopilados en modo live.
    """
    logger.info("=" * 80)
    logger.info("INICIANDO BACKTEST CON DATOS LIVE")
    logger.info("=" * 80)
    
    config = load_config_from_yaml()
    
    # Obtener símbolos y timeframe de la configuración
    symbol = config.backtesting.symbols[0]  # Tomamos el primer símbolo configurado
    timeframe = config.backtesting.timeframe
    
    # Convertir el formato del símbolo para que coincida con los archivos de datos live
    csv_symbol = symbol.replace('/', '_')
    
    logger.info(f"Símbolo a procesar: {symbol} (formato CSV: {csv_symbol})")
    logger.info(f"Timeframe: {timeframe}")
    
    # Consolidar datos live
    logger.info("Consolidando datos live...")
    data = consolidate_live_data(csv_symbol, timeframe)
    
    if data is None or data.empty:
        logger.error("No se pudieron obtener datos live consolidados")
        return False
    
    # Cargar estrategias
    logger.info("Cargando estrategias...")
    # Importar orquestador y backtester de forma perezosa para evitar imports top-level
    try:
        from backtesting.backtesting_orchestrator import load_strategies_from_config
        from backtesting.backtester import AdvancedBacktester
        strategies = load_strategies_from_config(config)
    except Exception as e:
        logger.error(f"Error importando módulos de backtest: {e}")
        return False
    
    if not strategies:
        logger.error("No se encontraron estrategias activas en la configuración")
        return False
    
    logger.info(f"Estrategias cargadas: {list(strategies.keys())}")
    
    # Configurar backtester
    backtester = AdvancedBacktester()
    # Convertir la configuración a diccionario para la clase AdvancedBacktester
    backtest_config = {
        'initial_capital': getattr(config.backtesting, 'initial_capital', 10000.0),
        'commission': getattr(config.backtesting, 'commission', 0.0005),
        'slippage': getattr(config.backtesting, 'slippage', 0.0002)
    }
    backtester.configure(backtest_config)
    
    # Guardar resultados de backtest para cada estrategia
    results = {}
    signals = {}
    
    # Ejecutar backtest para cada estrategia
    for strategy_name, strategy in strategies.items():
        logger.info(f"Ejecutando backtest para {strategy_name}...")
        
        try:
            # Preparar datos para la estrategia (si es necesario)
            strategy_data = data.copy()
            if hasattr(strategy, 'prepare_data'):
                strategy_data = strategy.prepare_data(strategy_data)
            
            # Ejecutar backtest
            strategy_result = backtester.run(strategy, strategy_data, symbol, timeframe)
            
            if strategy_result:
                results[strategy_name] = strategy_result
                signals[strategy_name] = strategy_result.get('trades', [])
                
                logger.info(f"Resultado para {strategy_name}:")
                logger.info(f"  Señales generadas: {len(signals[strategy_name])}")
                logger.info(f"  P&L total: ${strategy_result.get('total_pnl', 0):.2f}")
                logger.info(f"  Win rate: {strategy_result.get('win_rate', 0)*100:.2f}%")
                logger.info(f"  Drawdown máximo: {strategy_result.get('max_drawdown', 0):.2f}%")
            else:
                logger.error(f"No se obtuvieron resultados para {strategy_name}")
        except Exception as e:
            logger.error(f"Error ejecutando backtest para {strategy_name}: {e}", exc_info=True)
    
    # Guardar resultados
    output_dir = Path(current_dir) / "data" / "dashboard_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"live_data_backtest_results_simple.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4, default=str)
    
    logger.info(f"Resultados guardados en {output_file}")
    
    # Si hay señales, mostrar un resumen
    for strategy_name, trades in signals.items():
        if trades:
            logger.info(f"Resumen de señales para {strategy_name}:")
            for i, trade in enumerate(trades[:5]):  # Mostrar solo las primeras 5 señales
                logger.info(f"  Señal {i+1}: {trade}")
            if len(trades) > 5:
                logger.info(f"  ... y {len(trades)-5} más")
    
    return True

if __name__ == "__main__":
    # Configurar logging
    setup_logging("DEBUG", log_file="logs/backtest_live_data_simple.log")
    
    # Ejecutar backtest
    success = asyncio.run(run_backtest_with_live_data())
    
    if success:
        logger.info("✅ BACKTEST CON DATOS LIVE COMPLETADO CON ÉXITO")
    else:
        logger.error("❌ BACKTEST CON DATOS LIVE FALLIDO")