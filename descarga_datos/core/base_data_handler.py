"""
Base Data Handler Module
========================

Módulo base para manejo de datos con validación integrada.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Dict
from dataclasses import dataclass


@dataclass
class DataValidationResult:
    """
    Resultado de validación de datos.

    Attributes:
        is_valid (bool): True si los datos son válidos
        errors (List[str]): Lista de errores encontrados
        warnings (List[str]): Lista de advertencias
        metadata (Dict[str, Any]): Metadatos adicionales
    """
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

    def has_errors(self) -> bool:
        """Retorna True si hay errores."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Retorna True si hay advertencias."""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Agrega un error a la lista."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Agrega una advertencia a la lista."""
        self.warnings.append(warning)

    def merge(self, other: 'DataValidationResult') -> None:
        """Fusiona otro resultado de validación."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)
        self.is_valid = self.is_valid and other.is_valid


class BaseDataHandler(ABC):
    """
    Clase base abstracta para manejadores de datos.

    Proporciona la estructura básica para validación y manejo de datos
    con funcionalidades comunes como logging y configuración.
    """

    def __init__(self, config=None, logger=None):
        """
        Inicializa el manejador de datos base.

        Args:
            config: Configuración del sistema
            logger: Logger para registrar eventos
        """
        self.config = config
        if logger is not None:
            self.logger = logger
        else:
            from utils.logger import get_logger

            self.logger = get_logger(self.__class__.__name__)

    def log_info(self, message: str):
        """Registra un mensaje informativo."""
        if self.logger:
            self.logger.info(message)

    def log_error(self, message: str):
        """Registra un mensaje de error."""
        if self.logger:
            self.logger.error(message)

    def log_warning(self, message: str):
        """Registra un mensaje de advertencia."""
        if self.logger:
            self.logger.warning(message)