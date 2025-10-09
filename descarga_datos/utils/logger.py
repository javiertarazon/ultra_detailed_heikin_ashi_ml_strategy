#!/usr/bin/env python3

"""
Módulo de logging centralizado para el data downloader.
Configura el logging basado en la configuración proporcionada.
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
import re
import sys
import time



def sanitize_message(message: str) -> str:
    """
    Sanitiza mensajes de logging reemplazando caracteres Unicode problemáticos
    con alternativas ASCII para compatibilidad con Windows/cp1252.
    """
    # Reemplazar emojis comunes con alternativas ASCII
    emoji_map = {
        '🔍': '[SEARCH]',
        '📋': '[CLIPBOARD]',
        '✅': '[OK]',
        '⚠️': '[WARN]',
        '❌': '[ERROR]',
        '🚀': '[START]',
        '💰': '[MONEY]',
        '📊': '[CHART]',
        '🎯': '[TARGET]',
        '⏹️': '[STOP]',
        '🔄': '[SYNC]',
        '📥': '[DOWNLOAD]',
        '📈': '[UP]',
        '📉': '[DOWN]',
        '🔢': '[NUMBERS]',
        '💡': '[IDEA]',
        '🧪': '[TEST]',
        '🛠️': '[TOOLS]',
        '📝': '[NOTE]',
        '🔧': '[CONFIG]',
        '️': '[FOLDER]',
        '📄': '[FILE]',
        '🔗': '[LINK]',
        '⚙️': '[SETTINGS]',
        '🎛️': '[CONTROL]',
        '💾': '[SAVE]'
    }

    result = message
    for emoji, replacement in emoji_map.items():
        result = result.replace(emoji, replacement)

    # Reemplazar cualquier otro carácter Unicode no ASCII
    result = re.sub(r'[^\x00-\x7F]+', '?', result)

    return result

class SafeFormatter(logging.Formatter):
    """
    Formatter personalizado que sanitiza mensajes para evitar errores Unicode en Windows.
    """

    def format(self, record):
        # Sanitizar el mensaje antes de formatear
        if isinstance(record.msg, str):
            record.msg = sanitize_message(record.msg)

        # También sanitizar args si contienen strings
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize_message(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        return super().format(record)

def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot_trader.log") -> None:
    """
    Configura el sistema de logging con parámetros simples.
    FUNCIÓN PRINCIPAL para inicializar el sistema de logging global.
    Debe ser llamada al inicio de la aplicación en main.py.

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

    # Crear formatter seguro
    formatter = SafeFormatter(
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

def setup_logger(name: str, log_level: str = "INFO", log_file: str = "logs/bot_trader.log") -> logging.Logger:
    """
    Configura un logger específico con un nombre para un componente.

    Args:
        name: Nombre del logger (normalmente el nombre del componente)
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Ruta del archivo de log

    Returns:
        Un logger configurado
    """
    # Crear directorio de logs si no existe
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configurar el nivel de logging
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Verificar si ya tiene handlers para evitar duplicados
    if not logger.handlers:
        # Crear formatter seguro
        formatter = SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Configurar handler de archivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Configurar handler de consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

def get_logger(name: str, log_level: str = "INFO", log_file: str = "logs/bot_trader.log") -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado.
    Esta función es un alias para setup_logger y debe usarse en todo el sistema.
    
    Args:
        name: Nombre del logger, usualmente __name__ del módulo.
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Ruta del archivo de log
        
    Returns:
        Instancia de Logger configurada.
    """
    return setup_logger(name, log_level, log_file)


def initialize_system_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Inicializa el sistema de logging global según la configuración proporcionada.
    Esta función debe ser llamada UNA SOLA VEZ al inicio de la aplicación.

    Args:
        config: Configuración de logging. Si es None, se usará la configuración por defecto.
               Formato esperado: {'level': 'INFO', 'file': 'logs/bot_trader.log'}
    """
    if config is None:
        config = {'level': 'INFO', 'file': 'logs/bot_trader.log'}
    
    log_level = config.get('level', 'INFO').upper()
    log_file = config.get('file', 'logs/bot_trader.log')
    
    # Verificar si el directorio de logs existe, si no, crearlo
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar el logging global
    setup_logging(log_level, log_file)
    
    # Crear un logger principal para el sistema
    logger = logging.getLogger('system')
    logger.info(f"Sistema de logging inicializado: nivel={log_level}, archivo={log_file}")
    logger.info(f"Fecha/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Sistema operativo: {sys.platform}")
    
    # Registrar el tiempo de inicio para calcular duración de ejecución
    global _start_time
    _start_time = time.time()


# Variable global para calcular duración de ejecución
_start_time = None