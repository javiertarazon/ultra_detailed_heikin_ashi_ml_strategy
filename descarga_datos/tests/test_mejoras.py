#!/usr/bin/env python3
"""
Script para analizar diferencias entre datos live y backtest:
1. Comparación de estructura de datos
2. Verificación de procesamiento de datos
3. Diagnóstico de problemas en generación de señales

Este script ayuda a identificar por qué no se generan señales en modo live.
"""

import sys
import os
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import glob
import json
from datetime import datetime

# Añadir el directorio raíz al path
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def analizar_estructura_csv_live():
    """Analiza la estructura de los archivos CSV en modo live."""
    live_data_path = Path(os.path.join(root_dir, "descarga_datos", "data", "live_data"))
    pattern = "BTC_USDT_15m_*.csv"
    
    logger.info(f"Analizando estructura de archivos CSV live: {pattern}")
    files = list(live_data_path.glob(pattern))
    
    if not files:
        logger.error("No se encontraron archivos CSV live")
        return
    
    logger.info(f"Encontrados {len(files)} archivos CSV live")
    
    # Tomar un archivo de ejemplo
    muestra_file = files[0]
    logger.info(f"Analizando archivo de muestra: {muestra_file}")
    
    try:
        # Leer sin procesar para ver estructura original
        df_original = pd.read_csv(muestra_file)
        logger.info(f"Estructura original del CSV:")
        logger.info(f"Columnas: {df_original.columns.tolist()}")
        logger.info(f"Tipos de datos: {df_original.dtypes.to_dict()}")
        logger.info(f"Primeras filas:\n{df_original.head(3)}")
        
        # Verificar si hay diferencias en nombres o formatos
        if 'timestamp' in df_original.columns:
            timestamp_example = df_original['timestamp'].iloc[0]
            logger.info(f"Formato de timestamp: {timestamp_example}, tipo: {type(timestamp_example)}")
            
            # Intentar convertir a datetime para ver si hay problemas
            try:
                pd.to_datetime(df_original['timestamp'])
                logger.info("Conversión de timestamp a datetime exitosa")
            except Exception as e:
                logger.error(f"Error al convertir timestamp a datetime: {e}")
        
        # Comprobar si falta alguna columna esencial
        columnas_requeridas = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df_original.columns]
        if columnas_faltantes:
            logger.warning(f"Faltan columnas requeridas: {columnas_faltantes}")
    except Exception as e:
        logger.error(f"Error al analizar estructura de CSV live: {e}")

def cargar_y_verificar_datos_backtest():
    """Carga y verifica la estructura de datos utilizada en backtest."""
    config = load_config_from_yaml()
    symbol = config.backtesting.symbols[0]  # Tomamos el primer símbolo
    csv_symbol = symbol.replace('/', '_')
    timeframe = config.backtesting.timeframe
    
    # Buscar archivos de backtest (normalmente están en descarga_datos/data/csv)
    csv_path = Path(os.path.join(root_dir, "descarga_datos", "data", "csv"))
    backtest_file = None
    
    # Buscar el archivo de backtest correspondiente
    for file in csv_path.glob(f"{csv_symbol}_{timeframe}*.csv"):
        backtest_file = file
        break
    
    if not backtest_file:
        logger.error(f"No se encontró archivo de backtest para {csv_symbol} {timeframe}")
        return
    
    logger.info(f"Analizando archivo de backtest: {backtest_file}")
    
    try:
        # Cargar datos de backtest
        df_backtest = pd.read_csv(backtest_file)
        logger.info(f"Estructura del archivo de backtest:")
        logger.info(f"Columnas: {df_backtest.columns.tolist()}")
        logger.info(f"Tipos de datos: {df_backtest.dtypes.to_dict()}")
        logger.info(f"Primeras filas:\n{df_backtest.head(3)}")
    except Exception as e:
        logger.error(f"Error al cargar datos de backtest: {e}")

def comparar_procesamiento_datos():
    """Compara cómo se procesan los datos en modo backtest vs modo live."""
    logger.info("=== COMPARACIÓN DE PROCESAMIENTO DE DATOS ===")
    
    # Cargar un archivo de datos live
    live_data_path = Path(os.path.join(root_dir, "descarga_datos", "data", "live_data"))
    live_files = list(live_data_path.glob("BTC_USDT_15m_*.csv"))
    
    if not live_files:
        logger.error("No se encontraron archivos de datos live")
        return
    
    # Cargar archivo de backtest
    csv_path = Path(os.path.join(root_dir, "descarga_datos", "data", "csv"))
    backtest_files = list(csv_path.glob("BTC_USDT_15m*.csv"))
    
    if not backtest_files:
        logger.error("No se encontraron archivos de backtest")
        return
    
    live_file = live_files[0]
    backtest_file = backtest_files[0]
    
    logger.info(f"Comparando: \nLIVE: {live_file} \nBACKTEST: {backtest_file}")
    
    try:
        # Cargar ambos archivos
        df_live = pd.read_csv(live_file)
        df_backtest = pd.read_csv(backtest_file)
        
        # Verificar y procesar columnas para simular el procesamiento real
        # Datos LIVE - procesamiento usando primeras 6 columnas (como en el script anterior)
        df_live_processed = df_live.iloc[:, 0:6].copy()
        if len(df_live_processed.columns) >= 6:
            df_live_processed.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Comparar columnas
        logger.info("=== COLUMNAS ANTES DE PROCESAMIENTO ===")
        logger.info(f"Live original: {df_live.columns.tolist()}")
        logger.info(f"Backtest original: {df_backtest.columns.tolist()}")
        
        logger.info("=== COLUMNAS DESPUÉS DE PROCESAMIENTO ===")
        logger.info(f"Live procesado: {df_live_processed.columns.tolist()}")
        
        # Comparar tipos de datos
        logger.info("=== TIPOS DE DATOS ===")
        logger.info(f"Live procesado:\n{df_live_processed.dtypes}")
        logger.info(f"Backtest:\n{df_backtest.dtypes}")
        
        # Verificar conversión de timestamp
        logger.info("=== CONVERSIÓN DE TIMESTAMP ===")
        try:
            df_live_processed['timestamp'] = pd.to_datetime(df_live_processed['timestamp'])
            logger.info("Conversión de timestamp live exitosa")
        except Exception as e:
            logger.error(f"Error al convertir timestamp live: {e}")
            
        try:
            df_backtest['timestamp'] = pd.to_datetime(df_backtest['timestamp'])
            logger.info("Conversión de timestamp backtest exitosa")
        except Exception as e:
            logger.error(f"Error al convertir timestamp backtest: {e}")
        
        # Verificar formato de datos
        logger.info("=== VERIFICACIÓN DE FORMATO DE DATOS ===")
        logger.info(f"Live procesado (muestra):\n{df_live_processed.head(2)}")
        logger.info(f"Backtest (muestra):\n{df_backtest.head(2)}")
        
        # Verificar rango de fechas
        logger.info("=== RANGO DE FECHAS ===")
        if 'timestamp' in df_live_processed.columns and pd.api.types.is_datetime64_any_dtype(df_live_processed['timestamp']):
            logger.info(f"Live: {df_live_processed['timestamp'].min()} a {df_live_processed['timestamp'].max()}")
        
        if 'timestamp' in df_backtest.columns and pd.api.types.is_datetime64_any_dtype(df_backtest['timestamp']):
            logger.info(f"Backtest: {df_backtest['timestamp'].min()} a {df_backtest['timestamp'].max()}")
            
    except Exception as e:
        logger.error(f"Error al comparar procesamiento de datos: {e}")

def verificar_generacion_señales():
    """Verifica cómo se generan las señales en el código actual."""
    try:
        # Ruta a los resultados del último backtest con datos live
        result_path = Path(os.path.join(root_dir, "descarga_datos", "data", "dashboard_results", "live_data_backtest_results_simple.json"))
        
        if result_path.exists():
            with open(result_path, 'r') as f:
                results = json.load(f)
                
            logger.info("=== ANÁLISIS DE SEÑALES GENERADAS ===")
            for strategy, data in results.items():
                logger.info(f"Estrategia: {strategy}")
                logger.info(f"Total trades: {data.get('total_trades', 0)}")
                logger.info(f"Trades ganadores: {data.get('winning_trades', 0)}")
                logger.info(f"Win rate: {data.get('win_rate', 0)*100:.2f}%")
                
                if 'trades' in data and len(data['trades']) > 0:
                    logger.info("=== MUESTRA DE SEÑALES ===")
                    for i, trade in enumerate(data['trades'][:3]):  # Mostrar solo 3 ejemplos
                        logger.info(f"Trade {i+1}:")
                        for key, value in trade.items():
                            logger.info(f"  {key}: {value}")
                        
                        # Verificar si hay campos clave faltantes
                        campos_clave = ['entry_time', 'entry_price', 'position_size', 'direction', 'stop_loss']
                        campos_faltantes = [campo for campo in campos_clave if campo not in trade]
                        if campos_faltantes:
                            logger.warning(f"  Campos faltantes: {campos_faltantes}")
        else:
            logger.error(f"No se encontraron resultados de backtest en {result_path}")
    except Exception as e:
        logger.error(f"Error al verificar generación de señales: {e}")

def verificar_estructura_y_proponer_soluciones():
    """
    Verifica posibles problemas de estructura y propone soluciones
    para garantizar que las señales se generen correctamente tanto
    en modo live como en backtest.
    """
    logger.info("=== VERIFICACIÓN DE ESTRUCTURA Y PROPUESTA DE SOLUCIONES ===")
    
    # 1. Verificar estructura de datos
    analizar_estructura_csv_live()
    cargar_y_verificar_datos_backtest()
    
    # 2. Comparar procesamiento de datos
    comparar_procesamiento_datos()
    
    # 3. Verificar generación de señales
    verificar_generacion_señales()
    
    logger.info("=== RECOMENDACIONES ===")
    logger.info("1. Asegurar normalización consistente de nombres de columnas entre backtest y live")
    logger.info("2. Verificar conversión de tipos de datos (especialmente timestamp)")
    logger.info("3. Comprobar que los rangos de fechas sean adecuados para la estrategia")
    logger.info("4. Validar que los parámetros de configuración sean idénticos en live y backtest")
    logger.info("5. Revisar los indicadores calculados para asegurar que sean los mismos")

if __name__ == "__main__":
    # Configurar logging
    setup_logging(log_level="DEBUG", log_file="logs/analisis_estructura_datos.log")
    
    logger.info("=" * 80)
    logger.info("INICIANDO ANÁLISIS DE ESTRUCTURA DE DATOS Y GENERACIÓN DE SEÑALES")
    logger.info("=" * 80)
    
    verificar_estructura_y_proponer_soluciones()