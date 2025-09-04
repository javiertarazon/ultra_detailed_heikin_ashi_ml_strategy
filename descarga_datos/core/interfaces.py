"""
Interfaces base para el sistema de trading.
Define contratos claros entre módulos y elimina duplicaciones.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TradingSignal:
    """Señal de trading estandarizada"""
    timestamp: datetime
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 - 1.0
    price: float
    metadata: Dict[str, Any] = None

@dataclass
class TradeResult:
    """Resultado de un trade estandarizado"""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    pnl: Optional[float]
    position_type: str  # 'long', 'short'
    exit_reason: Optional[str]
    metadata: Dict[str, Any] = None

class IStrategy(ABC):
    """Interface para estrategias de trading"""
    
    @abstractmethod
    def calculate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula señales de trading basadas en los datos"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, capital: float, entry_price: float, stop_loss: float) -> float:
        """Calcula el tamaño de la posición"""
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, data: pd.DataFrame, direction: int) -> pd.Series:
        """Calcula niveles de stop loss"""
        pass
    
    @abstractmethod
    def calculate_take_profit(self, data: pd.DataFrame, direction: int) -> pd.Series:
        """Calcula niveles de take profit"""
        pass

class IIndicatorCalculator(ABC):
    """Interface para calculadores de indicadores técnicos"""
    
    @abstractmethod
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores técnicos"""
        pass

class IDataStorage(ABC):
    """Interface para almacenamiento de datos"""
    
    @abstractmethod
    def save_data(self, table_name: str, data: pd.DataFrame) -> bool:
        """Guarda datos en el almacenamiento"""
        pass
    
    @abstractmethod
    def query_data(self, table_name: str, start_ts: Optional[int] = None, 
                   end_ts: Optional[int] = None) -> pd.DataFrame:
        """Consulta datos del almacenamiento"""
        pass
    
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe"""
        pass

class IBacktester(ABC):
    """Interface para backtesting"""
    
    @abstractmethod
    def run(self, strategy: IStrategy, data: pd.DataFrame) -> Dict[str, Any]:
        """Ejecuta el backtesting de una estrategia"""
        pass

class IDataValidator(ABC):
    """Interface para validación de datos"""
    
    @abstractmethod
    def validate_ohlcv_data(self, data: pd.DataFrame) -> bool:
        """Valida datos OHLCV"""
        pass
    
    @abstractmethod
    def validate_trading_data(self, data: pd.DataFrame) -> bool:
        """Valida datos para trading"""
        pass

class IOHLCVData(ABC):
    """Interface para datos OHLCV"""
    
    @abstractmethod
    def get_dataframe(self) -> pd.DataFrame:
        """Obtiene el DataFrame con datos OHLCV"""
        pass
    
    @abstractmethod
    def get_timeframe(self) -> str:
        """Obtiene el timeframe de los datos"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Valida los datos OHLCV"""
        pass

class IDataDownloader(ABC):
    """Interface para descarga de datos"""
    
    @abstractmethod
    async def setup_exchange(self) -> bool:
        """Configura la conexión al exchange"""
        pass
    
    @abstractmethod
    async def download_symbol_data(self, symbol: str, timeframe: str, 
                                 start_date: str, end_date: str) -> IOHLCVData:
        """Descarga datos de un símbolo específico"""
        pass
    
    @abstractmethod
    async def download_multiple_symbols(self, symbols: List[str], timeframe: str,
                                      start_date: str, end_date: str) -> Dict[str, IOHLCVData]:
        """Descarga datos para múltiples símbolos"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Limpia recursos del downloader"""
        pass

class IDataAdapter(ABC):
    """Interface para adaptadores de datos"""
    
    @abstractmethod
    def adapt_ohlcv(self, raw_data: Any, symbol: str, timeframe: str) -> IOHLCVData:
        """Adapta datos raw a formato OHLCV estandarizado"""
        pass

class ICacheManager(ABC):
    """Interface para gestión de caché"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_minutes: Optional[int] = None) -> bool:
        """Almacena un valor en el caché"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Elimina una entrada del caché"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Limpia todo el caché"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        pass

class IConfigManager(ABC):
    """Interface para gestión de configuración"""
    
    @abstractmethod
    def load_config(self) -> Any:
        """Carga la configuración completa"""
        pass
    
    @abstractmethod
    def save_config(self, config: Any) -> bool:
        """Guarda la configuración"""
        pass
    
    @abstractmethod
    def validate_config(self) -> List[str]:
        """Valida la configuración y retorna lista de errores"""
        pass
