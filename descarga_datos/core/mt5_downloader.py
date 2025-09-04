"""
Módulo para descarga de datos desde MetaTrader 5
Permite descargar datos de múltiples instrumentos y timeframes
"""
import os
import pandas as pd
import numpy as np
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pytz

# Importación condicionada para manejar casos donde MT5 no está instalado
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from ..config.config import Config
from ..utils.logger import get_logger
from ..utils.retry_manager import with_retry, RetryManager
from ..utils.monitoring import PerformanceMonitor
from ..utils.storage import save_to_csv, DataStorage

# Mapeo de timeframes de formato string a constantes de MT5
TIMEFRAME_MAP = {
    '1m': mt5.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
    '2m': mt5.TIMEFRAME_M2 if MT5_AVAILABLE else 2,
    '3m': mt5.TIMEFRAME_M3 if MT5_AVAILABLE else 3,
    '4m': mt5.TIMEFRAME_M4 if MT5_AVAILABLE else 4,
    '5m': mt5.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
    '6m': mt5.TIMEFRAME_M6 if MT5_AVAILABLE else 6,
    '10m': mt5.TIMEFRAME_M10 if MT5_AVAILABLE else 10,
    '12m': mt5.TIMEFRAME_M12 if MT5_AVAILABLE else 12,
    '15m': mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
    '20m': mt5.TIMEFRAME_M20 if MT5_AVAILABLE else 20,
    '30m': mt5.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
    '1h': mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
    '2h': mt5.TIMEFRAME_H2 if MT5_AVAILABLE else 120,
    '3h': mt5.TIMEFRAME_H3 if MT5_AVAILABLE else 180,
    '4h': mt5.TIMEFRAME_H4 if MT5_AVAILABLE else 240,
    '6h': mt5.TIMEFRAME_H6 if MT5_AVAILABLE else 360,
    '8h': mt5.TIMEFRAME_H8 if MT5_AVAILABLE else 480,
    '12h': mt5.TIMEFRAME_H12 if MT5_AVAILABLE else 720,
    '1d': mt5.TIMEFRAME_D1 if MT5_AVAILABLE else 1440,
    '1w': mt5.TIMEFRAME_W1 if MT5_AVAILABLE else 10080,
    '1M': mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else 43200,
}

class MT5Downloader:
    """
    Clase para descarga de datos desde MetaTrader 5
    """
    
    def __init__(self, config: Config):
        """
        Inicializa el downloader de MT5
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.initialized = False
        
        # Inicializar sistemas de soporte
        self.retry_manager = RetryManager(
            max_retries=config.max_retries,
            base_delay=config.retry_delay,
            max_delay=60.0
        )
        
        # Crear directorio para almacenar datos
        self.data_dir = os.path.join(config.storage.path, "mt5")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Inicializar MT5
        self._initialize_mt5()
    
    def _initialize_mt5(self) -> bool:
        """
        Inicializa la conexión con MetaTrader 5
        
        Returns:
            bool: True si se inicializó correctamente, False en caso contrario
        """
        if not MT5_AVAILABLE:
            self.logger.error("MetaTrader5 no está instalado. Instale con: pip install MetaTrader5>=5.0.45")
            return False
        
        # Verificar si ya está inicializado
        if self.initialized:
            return True
        
        try:
            # Inicializar conexión con MT5
            if not mt5.initialize():
                self.logger.error(f"Error inicializando MT5: {mt5.last_error()}")
                return False
            
            # Verificar conexión
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                self.logger.error("No se pudo obtener información del terminal MT5")
                return False
            
            # Mostrar información de conexión
            version_info = mt5.version()
            self.logger.info(f"MT5 inicializado correctamente - Versión: {version_info}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error en la inicialización de MT5: {e}")
            return False
    
    def shutdown(self):
        """Cierra la conexión con MT5"""
        if MT5_AVAILABLE and self.initialized:
            mt5.shutdown()
            self.initialized = False
            self.logger.info("Conexión MT5 cerrada")
            
    async def initialize_async(self):
        """Inicializa MT5 de manera asíncrona para uso con async/await"""
        return self._initialize_mt5()
        
    def get_available_symbols(self):
        """
        Obtiene la lista de símbolos disponibles en MT5
        
        Returns:
            list: Lista con los nombres de los símbolos disponibles
        """
        if not MT5_AVAILABLE or not self.initialized:
            self.logger.warning("MT5 no está inicializado para obtener símbolos")
            return []
            
        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                self.logger.error("No se pudieron obtener símbolos de MT5")
                return []
                
            # Extraer solo los nombres
            symbol_names = [symbol.name for symbol in symbols]
            return symbol_names
            
        except Exception as e:
            self.logger.error(f"Error al obtener símbolos de MT5: {e}")
            return []
    
    # Versión directa sin el decorador para evitar problemas
    async def download_data(self, symbol: str, timeframe: str, 
                     start_date: datetime, end_date: datetime = None) -> pd.DataFrame:
        """
        Descarga datos OHLCV desde MT5
        
        Args:
            symbol: Símbolo a descargar (en formato MT5, ej: "EURUSD")
            timeframe: Timeframe en formato string ("1m", "5m", "1h", etc)
            start_date: Fecha de inicio
            end_date: Fecha de fin (por defecto: ahora)
            
        Returns:
            DataFrame con datos OHLCV o None si hay error
        """
        if not self._initialize_mt5():
            return None
        
        try:
            # Preparar parámetros
            if end_date is None:
                end_date = datetime.now()
            
            # Convertir timeframe a formato MT5
            if timeframe not in TIMEFRAME_MAP:
                self.logger.error(f"Timeframe no soportado: {timeframe}")
                return None
            
            mt5_timeframe = TIMEFRAME_MAP[timeframe]
            
            # Asegurar que las fechas estén en formato UTC
            start_date_utc = start_date.replace(tzinfo=pytz.UTC)
            end_date_utc = end_date.replace(tzinfo=pytz.UTC)
            
            # Descargar datos desde MT5
            self.logger.info(f"Descargando datos de {symbol} ({timeframe}) desde {start_date.date()} hasta {end_date.date()}")
            
            # Obtener rates (datos OHLCV)
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date_utc, end_date_utc)
            
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No se encontraron datos para {symbol} en el periodo especificado")
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(rates)
            
            # Procesar datos
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Renombrar columnas para consistencia con el formato del sistema
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
                'spread': 'spread',
                'real_volume': 'real_volume'
            }, inplace=True)
            
            # Seleccionar solo las columnas OHLCV para consistencia con otras fuentes
            columns = ['open', 'high', 'low', 'close', 'volume']
            if all(col in df.columns for col in columns):
                df = df[columns]
            
            # Agregar timestamp para compatibilidad con el resto del sistema
            df['timestamp'] = df.index.astype(int) // 10**9  # Convertir a segundos
            
            self.logger.info(f"Datos descargados: {len(df)} barras")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error descargando datos de MT5 para {symbol}: {e}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """
        Obtiene la lista de símbolos disponibles en MT5
        
        Returns:
            Lista de símbolos disponibles
        """
        if not self._initialize_mt5():
            return []
        
        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                self.logger.error("No se pudieron obtener los símbolos disponibles")
                return []
            
            return [s.name for s in symbols]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo símbolos disponibles: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Obtiene información detallada de un símbolo
        
        Args:
            symbol: Nombre del símbolo
            
        Returns:
            Diccionario con información del símbolo
        """
        if not self._initialize_mt5():
            return {}
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                self.logger.warning(f"No se encontró información para el símbolo: {symbol}")
                return {}
            
            # Convertir a diccionario
            return info._asdict()
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información del símbolo {symbol}: {e}")
            return {}
    
    def save_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """
        Guarda los datos descargados en formato CSV
        
        Args:
            df: DataFrame con datos OHLCV
            symbol: Símbolo
            timeframe: Timeframe
            
        Returns:
            Ruta al archivo guardado
        """
        if df is None or df.empty:
            return ""
        
        try:
            # Preparar path
            symbol_safe = symbol.replace('/', '_').replace('\\', '_')
            filename = f"MT5_{symbol_safe}_{timeframe}_ohlcv.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            # Guardar a CSV
            df.to_csv(filepath)
            self.logger.info(f"Datos guardados en: {filepath}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error guardando datos: {e}")
            return ""

# Ejemplo de uso
if __name__ == "__main__":
    from ..config.config_loader import load_config_from_yaml
    
    # Cargar configuración
    config = load_config_from_yaml()
    
    # Crear downloader
    mt5_downloader = MT5Downloader(config)
    
    # Obtener símbolos disponibles
    symbols = mt5_downloader.get_available_symbols()
    print(f"Símbolos disponibles: {len(symbols)}")
    
    # Descargar datos de ejemplo
    if symbols:
        symbol = symbols[0]  # Usar el primer símbolo disponible
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        df = mt5_downloader.download_data(symbol, "1h", start_date, end_date)
        
        if df is not None:
            print(f"Datos descargados: {len(df)} barras")
            print(df.head())
            
            # Guardar datos
            mt5_downloader.save_data(df, symbol, "1h")
    
    # Cerrar conexión
    mt5_downloader.shutdown()
