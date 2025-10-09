"""
Logger con soporte para métricas de tiempo de ejecución y statistics
"""
import logging
import time
import datetime
from typing import Optional, Dict, Any

def log_execution_time(logger: logging.Logger, operation_name: str, start_time: float) -> float:
    """
    Registra el tiempo de ejecución de una operación y lo devuelve en segundos.
    
    Args:
        logger: Logger para registrar el tiempo
        operation_name: Nombre de la operación
        start_time: Tiempo de inicio (time.time())
        
    Returns:
        Tiempo de ejecución en segundos
    """
    execution_time = time.time() - start_time
    logger.info(f"{operation_name} completado en {execution_time:.2f} segundos")
    return execution_time


def log_system_status(logger: logging.Logger, metrics: Dict[str, Any]) -> None:
    """
    Registra el estado del sistema con métricas proporcionadas.
    
    Args:
        logger: Logger para registrar el estado
        metrics: Diccionario con métricas del sistema
    """
    logger.info("Estado del sistema:")
    for key, value in metrics.items():
        logger.info(f"  - {key}: {value}")


def log_batch_operation(logger: logging.Logger, operation_name: str, 
                       total: int, success: int, errors: int) -> None:
    """
    Registra los resultados de una operación por lotes.
    
    Args:
        logger: Logger para registrar los resultados
        operation_name: Nombre de la operación
        total: Total de elementos procesados
        success: Número de éxitos
        errors: Número de errores
    """
    logger.info(f"Operación {operation_name} completada:")
    logger.info(f"  - Total procesados: {total}")
    logger.info(f"  - Éxitos: {success}")
    logger.info(f"  - Errores: {errors}")
    if total > 0:
        success_rate = (success / total) * 100
        logger.info(f"  - Tasa de éxito: {success_rate:.2f}%")