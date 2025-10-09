"""
Caché optimizado para mejorar rendimiento y reducir llamadas redundantes.
Implementa múltiples estrategias de caché según el tipo de datos.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, Tuple
import hashlib
import pickle
import json
from utils.logger import get_logger

logger = get_logger("__name__)
    
    def get_dataframe(self, key: str") -> Optional[pd.DataFrame]:
        """Obtiene un DataFrame con caché inteligente"""
        # Intentar memoria primero
        result = self.memory_cache.get(key)
        if result is not None:
            return result
        
        # Intentar disco
        result = self.file_cache.get(key)
        if result is not None:
            # Almacenar en memoria para acceso rápido
            self.memory_cache.set(key, result, ttl_minutes=10)
            return result
        
        return None
    
    def set_dataframe(self, key: str, df: pd.DataFrame, persist: bool = True) -> bool:
        """Almacena un DataFrame con estrategia inteligente"""
        # Siempre en memoria para acceso rápido
        memory_success = self.memory_cache.set(key, df, ttl_minutes=15)
        
        # En disco solo si se solicita persistencia
        disk_success = True
        if persist and len(df) > 100:  # Solo DataFrames grandes
            disk_success = self.file_cache.set(key, df, ttl_minutes=60)
        
        return memory_success or disk_success
    
    def get_cache_key(self, symbol: str, timeframe: str, start_date: str, end_date: str, 
                     indicators: bool = False) -> str:
        """Genera una clave de caché única"""
        key_parts = [symbol, timeframe, start_date, end_date]
        if indicators:
            key_parts.append("indicators")
        
        key_string = "_".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas combinadas"""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.file_cache.get_stats()
        
        return {
            'memory_cache': memory_stats,
            'disk_cache': disk_stats,
            'total_entries': memory_stats['total_entries'] + disk_stats['total_entries']
        }
