"""
Módulo core con componentes optimizados del sistema de trading.
"""

# Importar las interfaces principales
from .interfaces import (
    IStrategy,
    IIndicatorCalculator, 
    IDataStorage,
    IBacktester,
    IDataValidator,
    IOHLCVData,
    IDataDownloader,
    IDataAdapter,
    ICacheManager,
    IConfigManager,
    TradingSignal,
    TradeResult
)

__all__ = [
    'IStrategy',
    'IIndicatorCalculator',
    'IDataStorage', 
    'IBacktester',
    'IDataValidator',
    'IOHLCVData',
    'IDataDownloader',
    'IDataAdapter',
    'ICacheManager',
    'IConfigManager',
    'TradingSignal',
    'TradeResult'
]
