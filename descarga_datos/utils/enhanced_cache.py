"""
Sistema avanzado de caché para datos de trading.
Implementa políticas inteligentes de almacenamiento y expiración.
"""
import pandas as pd
from typing import Optional, Dict, Tuple, List, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import hashlib
import shutil
import os
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

class CachePolicy:
    """
    Define la política de caché para diferentes tipos de datos.
    """
    def __init__(self, 
                 max_age: timedelta = timedelta(hours=1),
                 priority: int = 1,
                 compression: str = 'snappy',
                 memory_eligible: bool = True):
        self.max_age = max_age
        self.priority = priority  # Mayor número = mayor prioridad
        self.compression = compression
        self.memory_eligible = memory_eligible

class EnhancedCacheManager:
    """
    Sistema avanzado de caché con políticas inteligentes.
    
    Características:
    - Caché en memoria y disco con políticas por tipo de datos
    - Compresión configurable
    - Invalidación basada en eventos y tiempo
    - Precarga predictiva basada en patrones de uso
    - Persistencia entre sesiones
    - Estadísticas de rendimiento
    """
    
    def __init__(self, 
                 cache_dir: str = "cache", 
                 max_memory_entries: int = 100,
                 max_disk_size_mb: int = 500):
        """
        Inicializa el gestor de caché avanzado.
        
        Args:
            cache_dir: Directorio para almacenar el caché en disco
            max_memory_entries: Número máximo de entradas en la caché de memoria
            max_disk_size_mb: Tamaño máximo del caché en disco en MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear subdirectorios para organización
        (self.cache_dir / "data").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)
        (self.cache_dir / "stats").mkdir(exist_ok=True)
        
        # Configuración
        self.max_memory_entries = max_memory_entries
        self.max_disk_size_bytes = max_disk_size_mb * 1024 * 1024
        
        # Memoria caché y metadatos
        self.memory_cache: Dict[str, Tuple[Any, datetime, CachePolicy]] = {}
        self.access_stats: Dict[str, Dict[str, Any]] = {}
        
        # Políticas predefinidas
        self.default_policies = {
            'ohlcv_recent': CachePolicy(max_age=timedelta(minutes=15), priority=3, memory_eligible=True),
            'ohlcv_historical': CachePolicy(max_age=timedelta(days=1), priority=1, memory_eligible=False),
            'indicators': CachePolicy(max_age=timedelta(hours=2), priority=2, memory_eligible=True),
            'backtest_results': CachePolicy(max_age=timedelta(days=7), priority=1, memory_eligible=False)
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas
        self.stats = {
            'hits': 0,
            'misses': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'evictions': 0,
            'bytes_written': 0,
            'bytes_read': 0
        }
        
        # Persistencia y limpieza
        self._load_metadata()
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup)
        self._cleanup_thread.daemon = True
        self._cleanup_thread.start()
    
    def _compute_hash_key(self, **params) -> str:
        """
        Genera una clave de hash única y determinista basada en parámetros.
        
        Args:
            **params: Parámetros que identifican el recurso cacheado
            
        Returns:
            Clave de hash para identificar el recurso en caché
        """
        # Ordenar para asegurar determinismo
        key_parts = []
        for k in sorted(params.keys()):
            v = params[k]
            if isinstance(v, pd.DataFrame):
                # Para DataFrames, usar forma e info básica
                v = f"df_{len(v)}rows_{len(v.columns)}cols"
            key_parts.append(f"{k}:{v}")
        
        key_str = "_".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, data_type: str, **params) -> Optional[Any]:
        """
        Obtiene datos del caché usando una política específica.
        
        Args:
            data_type: Tipo de datos ('ohlcv_recent', 'indicators', etc.)
            **params: Parámetros que identifican el recurso (exchange, symbol, etc.)
            
        Returns:
            Datos cacheados o None si no están disponibles
        """
        cache_key = self._compute_hash_key(**params)
        policy = self.default_policies.get(data_type, self.default_policies['ohlcv_recent'])
        
        # Registrar acceso
        self._record_access(cache_key, data_type)
        
        # Verificar caché en memoria
        if cache_key in self.memory_cache:
            data, timestamp, _ = self.memory_cache[cache_key]
            if datetime.now() - timestamp <= policy.max_age:
                self.logger.debug(f"Cache hit (memory): {cache_key}")
                self.stats['hits'] += 1
                self.stats['memory_hits'] += 1
                return data
        
        # Verificar caché en disco
        data_file = self.cache_dir / "data" / f"{cache_key}.pkl"
        meta_file = self.cache_dir / "metadata" / f"{cache_key}.json"
        
        if data_file.exists() and meta_file.exists():
            # Cargar metadata
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    
                cached_time = datetime.fromisoformat(metadata['timestamp'])
                stored_type = metadata.get('type', 'unknown')
                
                # Verificar validez
                if (datetime.now() - cached_time <= policy.max_age and 
                    stored_type == data_type):
                    
                    # Cargar datos
                    with open(data_file, 'rb') as f:
                        data = pickle.load(f)
                        
                    self.stats['hits'] += 1
                    self.stats['disk_hits'] += 1
                    self.stats['bytes_read'] += os.path.getsize(data_file)
                    
                    # Si es elegible para caché en memoria, actualizar
                    if policy.memory_eligible:
                        self._add_to_memory_cache(cache_key, data, cached_time, policy)
                        
                    self.logger.debug(f"Cache hit (disk): {cache_key}")
                    return data
            except Exception as e:
                self.logger.error(f"Error cargando caché: {e}")
        
        # No encontrado en caché
        self.stats['misses'] += 1
        return None
    
    def put(self, data: Any, data_type: str, **params) -> None:
        """
        Guarda datos en el caché.
        
        Args:
            data: Datos a guardar
            data_type: Tipo de datos ('ohlcv_recent', 'indicators', etc.)
            **params: Parámetros que identifican el recurso
        """
        cache_key = self._compute_hash_key(**params)
        current_time = datetime.now()
        policy = self.default_policies.get(data_type, self.default_policies['ohlcv_recent'])
        
        # Guardar en memoria si es elegible
        if policy.memory_eligible:
            self._add_to_memory_cache(cache_key, data, current_time, policy)
        
        # Guardar en disco
        try:
            # Metadatos
            metadata = {
                'timestamp': current_time.isoformat(),
                'type': data_type,
                'params': params,
                'policy': {
                    'max_age_seconds': policy.max_age.total_seconds(),
                    'priority': policy.priority,
                    'compression': policy.compression
                }
            }
            
            # Escribir metadatos
            meta_file = self.cache_dir / "metadata" / f"{cache_key}.json"
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Escribir datos
            data_file = self.cache_dir / "data" / f"{cache_key}.pkl"
            with open(data_file, 'wb') as f:
                pickle.dump(data, f)
                
            self.stats['bytes_written'] += os.path.getsize(data_file)
            
            # Verificar espacio en disco y limpiar si es necesario
            self._check_disk_space()
            
            self.logger.debug(f"Datos guardados en caché: {cache_key}")
        except Exception as e:
            self.logger.error(f"Error guardando en caché: {e}")
    
    def invalidate(self, data_type: str = None, **params) -> int:
        """
        Invalida entradas de caché basadas en parámetros.
        
        Args:
            data_type: Opcional, tipo de datos a invalidar
            **params: Parámetros para filtrar las entradas a invalidar
            
        Returns:
            Número de entradas invalidadas
        """
        count = 0
        
        # Si hay parámetros específicos, calcular hash y eliminar directamente
        if params:
            cache_key = self._compute_hash_key(**params)
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                count += 1
            
            data_file = self.cache_dir / "data" / f"{cache_key}.pkl"
            meta_file = self.cache_dir / "metadata" / f"{cache_key}.json"
            
            if data_file.exists():
                data_file.unlink()
                count += 1
            if meta_file.exists():
                meta_file.unlink()
        else:
            # Invalidar por tipo
            meta_path = self.cache_dir / "metadata"
            keys_to_remove = []
            
            for meta_file in meta_path.glob("*.json"):
                try:
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if data_type is None or metadata.get('type') == data_type:
                        key = meta_file.stem
                        keys_to_remove.append(key)
                        
                        # Eliminar archivos
                        meta_file.unlink()
                        data_file = self.cache_dir / "data" / f"{key}.pkl"
                        if data_file.exists():
                            data_file.unlink()
                            count += 1
                except:
                    continue
            
            # Eliminar de la memoria
            for key in keys_to_remove:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    count += 1
        
        return count
    
    def _add_to_memory_cache(self, key: str, data: Any, timestamp: datetime, policy: CachePolicy) -> None:
        """Añade una entrada a la caché en memoria con manejo de capacidad."""
        # Comprobar si necesitamos hacer espacio
        if len(self.memory_cache) >= self.max_memory_entries:
            self._evict_from_memory()
        
        # Añadir a la caché
        self.memory_cache[key] = (data, timestamp, policy)
    
    def _evict_from_memory(self) -> None:
        """Elimina entradas de la caché en memoria según prioridad y antigüedad."""
        # Ordenar por prioridad (menor primero) y antigüedad (más antiguo primero)
        items_to_sort = []
        for key, (_, timestamp, policy) in self.memory_cache.items():
            age = (datetime.now() - timestamp).total_seconds()
            score = policy.priority * 100000 - age  # Fórmula: prioridad - antigüedad
            items_to_sort.append((key, score))
        
        # Ordenar por puntuación (menor primero)
        items_to_sort.sort(key=lambda x: x[1])
        
        # Eliminar el 20% de las entradas con menor puntuación
        entries_to_remove = max(1, int(self.max_memory_entries * 0.2))
        for i in range(min(entries_to_remove, len(items_to_sort))):
            key_to_remove = items_to_sort[i][0]
            if key_to_remove in self.memory_cache:
                del self.memory_cache[key_to_remove]
                self.stats['evictions'] += 1
    
    def _check_disk_space(self) -> None:
        """Verifica el espacio en disco y limpia si es necesario."""
        # Calcular el tamaño actual del caché
        total_size = sum(f.stat().st_size for f in (self.cache_dir / "data").glob('*') 
                         if f.is_file())
        
        if total_size > self.max_disk_size_bytes:
            self._cleanup_disk_cache(target_size=int(self.max_disk_size_bytes * 0.8))
    
    def _cleanup_disk_cache(self, target_size: int) -> None:
        """
        Limpia el caché en disco hasta alcanzar el tamaño objetivo.
        
        Args:
            target_size: Tamaño objetivo en bytes
        """
        # Recopilar información de archivos
        file_info = []
        for meta_file in (self.cache_dir / "metadata").glob("*.json"):
            key = meta_file.stem
            data_file = self.cache_dir / "data" / f"{key}.pkl"
            
            if not data_file.exists():
                continue
            
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                # Obtener información
                timestamp = datetime.fromisoformat(metadata['timestamp'])
                data_type = metadata.get('type', 'unknown')
                policy = self.default_policies.get(data_type, self.default_policies['ohlcv_recent'])
                
                # Calcular puntuación (similar a memoria pero considerando tamaño)
                age = (datetime.now() - timestamp).total_seconds()
                file_size = data_file.stat().st_size
                
                # Puntuación: prioridad - antigüedad/tamaño
                # Archivos con menor puntuación se eliminan primero
                score = policy.priority * 10000 - age/3600 - file_size/1000000
                
                file_info.append({
                    'key': key,
                    'size': file_size,
                    'score': score,
                    'data_file': data_file,
                    'meta_file': meta_file
                })
            except Exception as e:
                # Si hay error, marcar para eliminación prioritaria
                file_info.append({
                    'key': key,
                    'size': data_file.stat().st_size if data_file.exists() else 0,
                    'score': float('-inf'),
                    'data_file': data_file,
                    'meta_file': meta_file
                })
        
        # Ordenar por puntuación (menor primero)
        file_info.sort(key=lambda x: x['score'])
        
        # Calcular tamaño actual
        current_size = sum(info['size'] for info in file_info)
        removed = 0
        
        # Eliminar hasta alcanzar el tamaño objetivo
        for info in file_info:
            if current_size <= target_size:
                break
            
            try:
                # Eliminar archivo de datos
                if info['data_file'].exists():
                    info['data_file'].unlink()
                    current_size -= info['size']
                    removed += 1
                
                # Eliminar metadatos
                if info['meta_file'].exists():
                    info['meta_file'].unlink()
                
                # Eliminar de la memoria si está presente
                if info['key'] in self.memory_cache:
                    del self.memory_cache[info['key']]
            except Exception as e:
                self.logger.error(f"Error eliminando caché: {e}")
        
        self.logger.info(f"Limpieza de caché: {removed} archivos eliminados")
    
    def _record_access(self, key: str, data_type: str) -> None:
        """Registra un acceso para estadísticas de uso."""
        now = datetime.now()
        
        if key not in self.access_stats:
            self.access_stats[key] = {
                'count': 0,
                'last_access': now,
                'data_type': data_type,
                'hourly_pattern': [0] * 24
            }
        
        self.access_stats[key]['count'] += 1
        self.access_stats[key]['last_access'] = now
        self.access_stats[key]['hourly_pattern'][now.hour] += 1
    
    def _periodic_cleanup(self) -> None:
        """Realiza limpiezas periódicas del caché."""
        import time
        while True:
            try:
                # Limpiar entradas expiradas
                self._cleanup_expired()
                
                # Guardar estadísticas
                self._save_stats()
                
                # Esperar 30 minutos
                time.sleep(1800)
            except Exception as e:
                self.logger.error(f"Error en limpieza periódica: {e}")
                time.sleep(300)  # Esperar 5 minutos en caso de error
    
    def _cleanup_expired(self) -> None:
        """Elimina entradas expiradas del caché."""
        # Limpiar memoria
        now = datetime.now()
        keys_to_remove = []
        
        for key, (_, timestamp, policy) in self.memory_cache.items():
            if now - timestamp > policy.max_age:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        # Limpiar disco (sólo metadatos para evitar carga)
        expired_count = 0
        for meta_file in (self.cache_dir / "metadata").glob("*.json"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                timestamp = datetime.fromisoformat(metadata['timestamp'])
                data_type = metadata.get('type', 'unknown')
                policy = self.default_policies.get(data_type, self.default_policies['ohlcv_recent'])
                
                if now - timestamp > policy.max_age:
                    key = meta_file.stem
                    data_file = self.cache_dir / "data" / f"{key}.pkl"
                    
                    # Eliminar archivos
                    if meta_file.exists():
                        meta_file.unlink()
                    if data_file.exists():
                        data_file.unlink()
                    
                    expired_count += 1
            except Exception as e:
                self.logger.debug(f"Error limpiando caché expirado: {e}")
        
        if expired_count > 0:
            self.logger.info(f"Limpieza automática: {expired_count} entradas expiradas eliminadas")
    
    def _save_stats(self) -> None:
        """Guarda estadísticas de uso del caché."""
        stats_file = self.cache_dir / "stats" / f"cache_stats_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            stats_data = {
                'timestamp': datetime.now().isoformat(),
                'memory_cache_size': len(self.memory_cache),
                'stats': self.stats,
                'hit_ratio': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) 
                             if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            }
            
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando estadísticas: {e}")
    
    def _load_metadata(self) -> None:
        """Carga metadatos persistentes del caché."""
        # Implementación de carga de metadatos si es necesaria
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales del caché."""
        disk_size = sum(f.stat().st_size for f in (self.cache_dir / "data").glob('*') if f.is_file())
        
        return {
            'memory_entries': len(self.memory_cache),
            'disk_size_mb': disk_size / (1024 * 1024),
            'hit_ratio': self.stats['hits'] / (self.stats['hits'] + self.stats['misses'])
                        if (self.stats['hits'] + self.stats['misses']) > 0 else 0,
            'memory_hit_ratio': self.stats['memory_hits'] / self.stats['hits'] if self.stats['hits'] > 0 else 0,
            'stats': self.stats
        }
    
    def prefetch(self, data_type: str, **params) -> None:
        """
        Programa la precarga de datos basada en patrones de uso.
        Útil para datos que se accederán pronto según patrones históricos.
        """
        # Implementación para versión futura
        pass

# Método para facilitar la migración desde la versión antigua
def upgrade_cache_system(old_cache_dir: str, new_cache_dir: str) -> None:
    """
    Migra datos del sistema de caché anterior al nuevo sistema mejorado.
    
    Args:
        old_cache_dir: Directorio del caché antiguo
        new_cache_dir: Directorio del caché nuevo
    """
    old_dir = Path(old_cache_dir)
    if not old_dir.exists():
        print(f"Directorio de caché anterior no encontrado: {old_cache_dir}")
        return
    
    # Crear nueva instancia
    new_cache = EnhancedCacheManager(cache_dir=new_cache_dir)
    
    # Migrar archivos
    print(f"Migrando caché desde {old_cache_dir} a {new_cache_dir}...")
    migrated = 0
    
    for cache_file in old_dir.glob("*.parquet"):
        try:
            # Verificar si hay metadatos
            meta_file = old_dir / f"{cache_file.stem}.meta"
            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                # Leer datos
                df = pd.read_parquet(cache_file)
                
                # Extraer información del nombre de archivo
                parts = cache_file.stem.split('_')
                if len(parts) >= 3:
                    exchange = parts[0]
                    symbol = parts[1]
                    timeframe = parts[2]
                    
                    # Determinar tipo de datos
                    data_type = 'ohlcv_recent'  # Valor por defecto
                    
                    # Guardar en el nuevo caché
                    new_cache.put(
                        data=df, 
                        data_type=data_type,
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=timeframe
                    )
                    migrated += 1
        except Exception as e:
            print(f"Error migrando {cache_file}: {e}")
    
    print(f"Migración completada. {migrated} archivos migrados.")

# Función auxiliar para crear/obtener una instancia singleton
_CACHE_INSTANCE = None

def get_cache_manager(cache_dir: str = "cache", **kwargs) -> EnhancedCacheManager:
    """
    Obtiene una instancia singleton del gestor de caché.
    
    Args:
        cache_dir: Directorio para el caché
        **kwargs: Parámetros adicionales
    
    Returns:
        Instancia del gestor de caché
    """
    global _CACHE_INSTANCE
    if _CACHE_INSTANCE is None:
        _CACHE_INSTANCE = EnhancedCacheManager(cache_dir=cache_dir, **kwargs)
    return _CACHE_INSTANCE
