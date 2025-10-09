#!/usr/bin/env python3
"""
Módulo para auditar la autenticidad de los datos de trading.
Proporciona funciones para validar datos y detectar manipulaciones.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from utils.logger import get_logger

logger = get_logger(__name__)

def validate_data_authenticity(data: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Valida la autenticidad de los datos de trading verificando patrones anómalos.
    
    Args:
        data: DataFrame con datos de trading (OHLCV)
        
    Returns:
        Tupla (bool, List[str]): El primer elemento es True si los datos parecen auténticos,
        False en caso contrario. El segundo elemento es una lista de mensajes de error/advertencia.
    """
    if data is None or len(data) == 0:
        return False, ["No hay datos para validar"]
    
    issues = []
    
    # Verificar columnas requeridas
    required_columns = ['open', 'high', 'low', 'close']
    for col in required_columns:
        if col not in data.columns:
            issues.append(f"Falta la columna requerida: {col}")
    
    if issues:
        return False, issues
    
    # Verificar NaNs
    for col in data.columns:
        if data[col].isna().any():
            issues.append(f"La columna {col} contiene valores NaN")
    
    # Verificar valores negativos en precios y volumen
    for col in required_columns:
        if (data[col] < 0).any():
            issues.append(f"La columna {col} contiene valores negativos")
    
    if 'volume' in data.columns and (data['volume'] < 0).any():
        issues.append("La columna volume contiene valores negativos")
    
    # Verificar inconsistencias en OHLC
    if (data['low'] > data['high']).any():
        issues.append("Hay registros donde el precio low es mayor que el high")
    
    if (data['open'] > data['high']).any():
        issues.append("Hay registros donde el precio open es mayor que el high")
    
    if (data['open'] < data['low']).any():
        issues.append("Hay registros donde el precio open es menor que el low")
    
    if (data['close'] > data['high']).any():
        issues.append("Hay registros donde el precio close es mayor que el high")
    
    if (data['close'] < data['low']).any():
        issues.append("Hay registros donde el precio close es menor que el low")
    
    # Verificar repeticiones exactas (posible manipulación)
    for col in required_columns:
        consecutive_equals = (data[col].shift() == data[col]).sum()
        if consecutive_equals > len(data) * 0.1:  # Más del 10% son iguales consecutivos
            issues.append(f"La columna {col} tiene muchos valores consecutivos idénticos ({consecutive_equals})")
    
    # Verificar orden temporal
    if 'timestamp' in data.columns and not data['timestamp'].is_monotonic_increasing:
        issues.append("Los timestamps no están en orden cronológico")
    
    return len(issues) == 0, issues

def validate_dataset_authenticity(data: pd.DataFrame, symbol: str) -> Dict[str, Union[bool, List[str], Dict]]:
    """
    Valida y genera un informe detallado sobre la autenticidad del dataset.
    
    Args:
        data: DataFrame con datos de trading
        symbol: Símbolo del instrumento analizado
        
    Returns:
        Diccionario con resultados de la validación:
        {
            'is_authentic': bool,
            'issues': List[str],
            'metrics': Dict con métricas estadísticas
        }
    """
    is_authentic, issues = validate_data_authenticity(data)
    
    # Calcular métricas adicionales para evaluación
    metrics = {}
    if not data.empty:
        # Calcular volatilidad
        if 'close' in data.columns:
            returns = data['close'].pct_change().dropna()
            metrics['volatility'] = returns.std()
            metrics['max_daily_change'] = returns.abs().max()
        
        # Otras métricas de integridad
        metrics['timeframe_gaps'] = 0
        if 'timestamp' in data.columns:
            # Convertir a datetime si es necesario
            if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                try:
                    timestamps = pd.to_datetime(data['timestamp'])
                    # Calcular diferencias entre timestamps consecutivos
                    diffs = timestamps.diff().dropna()
                    # Encontrar la diferencia más común (el timeframe esperado)
                    expected_diff = diffs.mode().iloc[0]
                    # Contar gaps mayores al timeframe esperado
                    metrics['timeframe_gaps'] = (diffs > expected_diff * 1.5).sum()
                except:
                    logger.warning(f"No se pudo analizar los timestamps para {symbol}")
    
    logger.info(f"Validación de autenticidad para {symbol}: {'PASÓ' if is_authentic else 'FALLÓ'}")
    if issues:
        for issue in issues:
            logger.warning(f"Problema en datos de {symbol}: {issue}")
    
    return {
        'is_authentic': is_authentic,
        'issues': issues,
        'metrics': metrics,
        'symbol': symbol
    }