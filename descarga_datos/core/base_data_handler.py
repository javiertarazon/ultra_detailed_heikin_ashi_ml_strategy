"""
Base Data Handler - Clase base simplificada para manejo de datos
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DataValidationResult:
    """Resultado de validación de datos"""
    is_valid: bool
    errors: list
    warnings: list

class BaseDataHandler:
    """Clase base simplificada para manejo de datos"""

    def __init__(self, config=None):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_data(self, data: Any) -> DataValidationResult:
        """Valida los datos de entrada"""
        return DataValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

    def process_data(self, data: Any) -> Any:
        """Procesa los datos"""
        return data
