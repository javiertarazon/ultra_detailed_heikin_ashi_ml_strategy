"""
Módulo de almacenamiento de datos con manejo consistente de timestamps.
"""
import sqlite3
import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Union, List, Dict, Any, Optional
from pathlib import Path
from core.base_data_handler import BaseDataHandler, DataValidationResult

logger = logging.getLogger(__name__)

def _get_sqlite_type(dtype: np.dtype) -> str:
    """Maps pandas dtype to SQLite data type."""
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    # Timestamps and other objects will be stored as TEXT or INTEGER after conversion
    return "TEXT"

class DataStorage(BaseDataHandler):
    """Clase para el manejo de almacenamiento de datos."""
    
    def __init__(self, db_path: str = "data/data.db"):
        super().__init__()
        self.db_path = db_path
        self._ensure_db_path()
        # Compatibilidad: algunas llamadas antiguas referencian self.logger
        # Asignamos el logger de módulo para evitar AttributeError
        # Garantizar siempre un logger operativo (evita AttributeError en llamadas heredadas)
        try:
            if not hasattr(self, 'logger') or self.logger is None:
                self.logger = logger
        except Exception:
            # Fallback silencioso; en el peor caso se usará el logger de módulo directamente
            pass
    
    def _ensure_db_path(self):
        """Asegura que el directorio de la base de datos existe."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Directorio creado: {db_dir}")
    
    def validate_data(self, data: Any) -> DataValidationResult:
        """
        Valida los datos proporcionados.

        Args:
            data: Datos a validar (DataFrame o lista de diccionarios)

        Returns:
            DataValidationResult con el resultado de la validación
        """
        try:
            # Convertir a DataFrame si es necesario
            df = pd.DataFrame(data) if isinstance(data, list) else data

            # Usar la validación específica de timestamp
            return self.validate_timestamp_column(df)

        except Exception as e:
            return DataValidationResult(
                False,
                [f"Error en validación de datos: {str(e)}"],
                []
            )
    
    def validate_timestamp_column(self, df: pd.DataFrame) -> DataValidationResult:
        """
        Valida la columna de timestamp en el DataFrame.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            DataValidationResult con el resultado de la validación
        """
        errors = []
        warnings = []
        
        # Verificar que existe columna timestamp
        if 'timestamp' not in df.columns:
            errors.append("Columna 'timestamp' no encontrada")
            return DataValidationResult(False, errors, warnings)
        
        # Verificar que no hay valores nulos
        null_count = df['timestamp'].isnull().sum()
        if null_count > 0:
            errors.append(f"Columna 'timestamp' tiene {null_count} valores nulos")
        
        # Verificar que los valores son válidos
        try:
            ts_series = pd.to_datetime(df['timestamp'], errors='coerce')
            invalid_count = ts_series.isnull().sum()
            if invalid_count > 0:
                errors.append(f"Columna 'timestamp' tiene {invalid_count} valores inválidos")
        except Exception as e:
            errors.append(f"Error convirtiendo timestamps: {e}")
        
        # Verificar orden temporal
        if len(df) > 1:
            is_sorted = df['timestamp'].is_monotonic_increasing
            if not is_sorted:
                warnings.append("Los timestamps no están en orden ascendente")
        
        return DataValidationResult(len(errors) == 0, errors, warnings)
    
    def save_to_sqlite(self, data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                      table_name: str,
                      validate: bool = True) -> bool:
        """
        Guarda datos en SQLite con manejo consistente de timestamps.
        
        Args:
            data: DataFrame o lista de diccionarios con los datos
            table_name: Nombre de la tabla
            validate: Si se debe validar los datos antes de guardar
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        try:
            # Convertir a DataFrame si es necesario
            df = pd.DataFrame(data) if isinstance(data, list) else data.copy()
            
            # Asegurar que el índice sea parte de las columnas si es timestamp
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
            
            # Validar datos si se requiere
            if validate:
                validation_result = self.validate_timestamp_column(df)
                if not validation_result.is_valid:
                    for error in validation_result.errors:
                        logger.error(f"Error de validación: {error}")
                    return False
                
                for warning in validation_result.warnings:
                    logger.warning(warning)
            
            # Preparar tipos de datos y convertir timestamps
            # Cuando se lee desde un CSV o DataFrame, asegurarse de que los timestamps estén en el formato correcto
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Convertir a Unix timestamp en segundos
                df['timestamp'] = df['timestamp'].astype(np.int64) // 10**9
                # Validar rango temporal
                min_ts = int(pd.Timestamp('1970-01-01').timestamp())
                max_ts = int(pd.Timestamp('2050-01-01').timestamp())
                if (df['timestamp'] < min_ts).any() or (df['timestamp'] > max_ts).any():
                    raise ValueError(f"Timestamps fuera del rango válido: 1970-01-01 a 2050-01-01")
            
            # Preparar tipos de datos para SQLite
            for col in df.columns:
                # Serializar objetos complejos
                if df[col].dtype == 'object':
                    if any(isinstance(x, (dict, list)) for x in df[col].dropna()):
                        df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            
            # Guardar en SQLite
            with sqlite3.connect(self.db_path) as conn:
                # Crear tabla si no existe
                column_definitions = []
                for col in df.columns:
                    if col == 'timestamp':
                        dtype = 'INTEGER'
                    elif pd.api.types.is_float_dtype(df[col]):
                        dtype = 'REAL'
                    elif pd.api.types.is_integer_dtype(df[col]):
                        dtype = 'INTEGER'
                    else:
                        dtype = 'TEXT'
                    column_definitions.append(f"{col} {dtype}")
                
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {', '.join(column_definitions)}
                )
                """
                
                # Crear tabla
                conn.execute(create_table_sql)
                
                # Eliminar datos existentes si hay
                try:
                    delete_sql = f"DELETE FROM {table_name}"
                    conn.execute(delete_sql)
                except sqlite3.OperationalError:
                    pass  # La tabla no existe, lo cual está bien
                
                # Guardar los datos
                df.to_sql(table_name, conn, if_exists='append', index=False)
                
                return True
                
        except Exception as e:
            logger.error(f"Error guardando datos en SQLite: {e}")
            return False
    
    def save_data(self, table_name: str, data: pd.DataFrame) -> bool:
        """
        Método principal para guardar datos. Limpia la tabla si existe.
        
        Args:
            table_name: Nombre de la tabla
            data: DataFrame con los datos a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Si la tabla existe, eliminar sus datos
            if self.table_exists(table_name):
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Guardar los nuevos datos
            return self.save_to_sqlite(data, table_name)
        except Exception as e:
            logger.error(f"Error en save_data: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """
        Verifica si una tabla existe en la base de datos.
        
        Args:
            table_name: Nombre de la tabla a verificar
            
        Returns:
            bool: True si la tabla existe
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error verificando tabla: {e}")
            return False
    
    def query_data(self, table_name: str, start_ts: Optional[int] = None, end_ts: Optional[int] = None) -> pd.DataFrame:
        """
        Consulta datos de la base de datos con filtros opcionales de timestamp.
        
        Args:
            table_name: Nombre de la tabla
            start_ts: Timestamp inicial en segundos (opcional)
            end_ts: Timestamp final en segundos (opcional)
            
        Returns:
            pd.DataFrame: DataFrame con los datos consultados
        """
        try:
            # Verificar si la tabla existe
            if not self.table_exists(table_name):
                # Usar tanto self.logger (si existe) como logger de módulo para robustez
                try:
                    self.logger.error(f"La tabla {table_name} no existe")
                except Exception:
                    logger.error(f"La tabla {table_name} no existe")
                return pd.DataFrame()

            # Construir la consulta SQL
            query = f"SELECT * FROM {table_name}"
            params = []
            
            if start_ts is not None and end_ts is not None:
                query += " WHERE timestamp >= ? AND timestamp <= ?"
                params.extend([start_ts, end_ts])
            
            query += " ORDER BY timestamp"
            
            # Ejecutar la consulta
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params if params else None)
            
            if df.empty:
                try:
                    self.logger.warning(f"No se encontraron datos en la tabla {table_name}")
                except Exception:
                    logger.warning(f"No se encontraron datos en la tabla {table_name}")
                return pd.DataFrame()
            
            # Verificar que existe la columna timestamp
            if 'timestamp' not in df.columns:
                try:
                    self.logger.error(f"La columna timestamp no existe en la tabla {table_name}")
                except Exception:
                    logger.error(f"La columna timestamp no existe en la tabla {table_name}")
                return pd.DataFrame()
            
            # Convertir timestamp a datetime y establecer como índice
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.sort_values('timestamp')
                
            return df
            
        except Exception as e:
            try:
                self.logger.error(f"Error consultando datos: {e}")
            except Exception:
                logger.error(f"Error consultando datos: {e}")
            return pd.DataFrame()

    # ===================== METADATA SUPPORT =====================
    def _ensure_metadata_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS data_metadata (
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        start_ts INTEGER,
                        end_ts INTEGER,
                        records INTEGER,
                        coverage_pct REAL,
                        asset_class TEXT,
                        source_exchange TEXT,
                        last_update_ts INTEGER DEFAULT (strftime('%s','now')),
                        PRIMARY KEY(symbol,timeframe)
                    )
                    """
                )
        except Exception as e:
            try:
                self.logger.error(f"Error creando tabla metadata: {e}")
            except Exception:
                logger.error(f"Error creando tabla metadata: {e}")

    def upsert_metadata(self, row: dict):
        self._ensure_metadata_table()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO data_metadata(symbol,timeframe,start_ts,end_ts,records,coverage_pct,asset_class,source_exchange,last_update_ts)
                    VALUES(?,?,?,?,?,?,?, ?,strftime('%s','now'))
                    ON CONFLICT(symbol,timeframe) DO UPDATE SET
                        start_ts=excluded.start_ts,
                        end_ts=excluded.end_ts,
                        records=excluded.records,
                        coverage_pct=excluded.coverage_pct,
                        asset_class=excluded.asset_class,
                        source_exchange=excluded.source_exchange,
                        last_update_ts=strftime('%s','now')
                    """,
                    (
                        row.get('symbol'),
                        row.get('timeframe'),
                        row.get('start_ts'),
                        row.get('end_ts'),
                        row.get('records'),
                        row.get('coverage_pct'),
                        row.get('asset_class'),
                        row.get('source_exchange', 'unknown')
                    )
                )
        except Exception as e:
            try:
                self.logger.error(f"Error upsert metadata: {e}")
            except Exception:
                logger.error(f"Error upsert metadata: {e}")

    def get_metadata(self, symbol: str, timeframe: str) -> Optional[dict]:
        self._ensure_metadata_table()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT symbol,timeframe,start_ts,end_ts,records,coverage_pct,asset_class,source_exchange,last_update_ts FROM data_metadata WHERE symbol=? AND timeframe=?",
                    (symbol, timeframe)
                )
                row = cur.fetchone()
                if not row:
                    return None
                keys = ['symbol','timeframe','start_ts','end_ts','records','coverage_pct','asset_class','source_exchange','last_update_ts']
                return dict(zip(keys,row))
        except Exception as e:
            try:
                self.logger.error(f"Error get_metadata: {e}")
            except Exception:
                logger.error(f"Error get_metadata: {e}")
            return None

def save_to_csv(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
              filepath: str,
              storage: Optional[DataStorage] = None) -> bool:
    """
    Guarda datos en CSV con manejo consistente de timestamps.
    
    Args:
        data: DataFrame o lista de diccionarios con los datos
        filepath: Ruta del archivo CSV
        storage: Instancia opcional de DataStorage para validación
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        # Convertir a DataFrame si es necesario
        df = pd.DataFrame(data) if isinstance(data, list) else data.copy()
        
        # Validar si hay storage
        if storage:
            validation_result = storage.validate_timestamp_column(df)
            if not validation_result.is_valid:
                logger.error("Datos inválidos para guardar en CSV")
                return False
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Guardar en CSV
        df.to_csv(filepath, index=False)
        logger.info(f"Data saved to CSV: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Error guardando datos en CSV: {str(e)}")
        return False



# Additional functions for specific data types can be added here