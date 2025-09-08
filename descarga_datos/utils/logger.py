#!/usr/bin/env python3
"""
Módulo de logging centralizado para el data downloader.
Configura el logging basado en la configuración proporcionada.
"""
import logging
import os
from typing import Optional

def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot_trader.log") -> None:
    """
    Configura el sistema de logging con parámetros simples.

    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Ruta del archivo de log
    """
    # Crear directorio de logs si no existe
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configurar el nivel de logging
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configurar el logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Limpiar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Crear formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler para archivo si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger configurado con el nombre especificado.

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)    # Configurar el nuevo logger
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reducir el nivel de logging para librerías externas si es necesario
    logging.getLogger('ccxt').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado.
    
    Args:
        name: Nombre del logger, usualmente __name__ del módulo.
        
    Returns:
        Instancia de Logger configurada.
    """
    return logging.getLogger(name)

def close_logging() -> None:
    """
    Cierra todos los handlers de logging para liberar archivos.
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)