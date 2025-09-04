"""
Clase base para el manejo de datos en el sistema.
Proporciona una interfaz común y validación consistente.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class DataValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]

class BaseDataHandler:
    """Clase base para el manejo de datos en el sistema."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @staticmethod
    def validate_timestamp_column(df: pd.DataFrame) -> DataValidationResult:
        """Valida la columna timestamp del DataFrame."""
        errors = []
        warnings = []
        stats = {}
        
        # Verificar que existe la columna timestamp
        if 'timestamp' not in df.columns:
            errors.append("No se encontró la columna 'timestamp'")
            return DataValidationResult(False, errors, warnings, stats)
        
        # Convertir a timestamp si es necesario
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            try:
                if pd.api.types.is_integer_dtype(df['timestamp']):
                    # Determinar la unidad basada en la magnitud del timestamp
                    max_ts = df['timestamp'].max()
                    if max_ts > 1e18:  # Probablemente nanosegundos
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
                    elif max_ts > 1e15:  # Probablemente microsegundos
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='us')
                    elif max_ts > 1e12:  # Probablemente milisegundos
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    else:  # Probablemente segundos
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    # Intentar parsear como datetime
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
            except Exception as e:
                errors.append(f"Error al convertir timestamps: {str(e)}")
                return DataValidationResult(False, errors, warnings, stats)
        
        # Validar rango de timestamps
        min_valid_date = pd.Timestamp('1970-01-01')
        max_valid_date = pd.Timestamp('2050-01-01')
        
        invalid_dates = df[
            (df['timestamp'] < min_valid_date) | 
            (df['timestamp'] > max_valid_date)
        ]
        
        if not invalid_dates.empty:
            errors.append(
                f"Se encontraron {len(invalid_dates)} timestamps fuera del rango válido "
                f"({min_valid_date} a {max_valid_date})"
            )
            return DataValidationResult(False, errors, warnings, stats)
        
        # Verificar orden y continuidad
        if not df['timestamp'].is_monotonic_increasing:
            warnings.append("Los timestamps no están en orden ascendente")
        
        # Calcular estadísticas
        stats['timestamp_range'] = {
            'start': df['timestamp'].min(),
            'end': df['timestamp'].max(),
            'duration': df['timestamp'].max() - df['timestamp'].min()
        }
        
        return DataValidationResult(True, errors, warnings, stats)
    
    @staticmethod
    def standardize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
        """Estandariza los timestamps en el DataFrame."""
        if 'timestamp' not in df.columns:
            raise ValueError("No se encontró la columna 'timestamp'")
        
        # Si ya es datetime, no hacer nada
        if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            return df
        
        # Si es entero, asumir milisegundos
        if pd.api.types.is_integer_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        
        # Intentar parsear como datetime
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            raise ValueError(f"No se pudo convertir la columna timestamp: {str(e)}")
    
    @staticmethod
    def timestamps_to_ms(df: pd.DataFrame) -> pd.DataFrame:
        """Convierte los timestamps a milisegundos desde epoch."""
        if 'timestamp' not in df.columns:
            raise ValueError("No se encontró la columna 'timestamp'")
        
        # Si ya es entero, verificar que esté en milisegundos
        if pd.api.types.is_integer_dtype(df['timestamp']):
            # Si parece estar en segundos, convertir a milisegundos
            if (df['timestamp'] < 1000000000000).any():
                df['timestamp'] = df['timestamp'] * 1000
            return df
        
        # Convertir a milisegundos
        if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = df['timestamp'].astype('int64') // 10**6
            return df
        
        # Intentar convertir a datetime primero
        df = BaseDataHandler.standardize_timestamps(df)
        return BaseDataHandler.timestamps_to_ms(df)
