"""
Gestor de configuración centralizado y optimizado.
Elimina duplicaciones de carga y validación de configuración.
"""
import yaml
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
from dataclasses import dataclass, field, asdict
from ..core.interfaces import IConfigManager

@dataclass
class ExchangeConfig:
    """Configuración de exchange"""
    name: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    sandbox: bool = False
    rate_limit: int = 1200  # requests per minute
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1

@dataclass 
class TradingPairConfig:
    """Configuración de par de trading"""
    symbol: str
    base_asset: str
    quote_asset: str
    min_notional: float = 10.0
    tick_size: float = 0.01
    step_size: float = 0.001

@dataclass
class DataConfig:
    """Configuración de datos"""
    timeframes: List[str] = field(default_factory=lambda: ['1h'])
    max_candles_per_request: int = 1000
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    update_existing: bool = False
    validate_data: bool = True

@dataclass
class IndicatorConfig:
    """Configuración de indicadores técnicos"""
    calculate_all: bool = True
    heiken_ashi: bool = True
    ema_periods: List[int] = field(default_factory=lambda: [10, 20, 50, 200])
    atr_period: int = 14
    adx_period: int = 14
    sar_af: float = 0.02
    sar_max_af: float = 0.2

@dataclass
class StorageConfig:
    """Configuración de almacenamiento"""
    sqlite_path: str = "data/data.db"
    csv_path: str = "data/csv"
    enable_sqlite: bool = True
    enable_csv: bool = True
    normalize_data: bool = True
    backup_enabled: bool = False

@dataclass
class BacktestConfig:
    """Configuración de backtesting"""
    initial_capital: float = 10000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0001   # 0.01%
    risk_free_rate: float = 0.02  # 2% annual
    max_position_size: float = 0.1  # 10% of capital
    
@dataclass
class StrategyConfig:
    """Configuración de estrategia base"""
    name: str
    enabled: bool = True
    risk_level: str = "medium"  # low, medium, high
    position_sizing: str = "fixed"  # fixed, percentage, kelly
    stop_loss_pct: float = 0.02  # 2%
    take_profit_pct: float = 0.04  # 4%

@dataclass
class UTBotPSARConfig(StrategyConfig):
    """Configuración específica para UT Bot + PSAR"""
    ut_bot_key_value: float = 1.0
    ut_bot_atr_period: int = 10
    psar_af: float = 0.02
    psar_max_af: float = 0.2
    ema_fast: int = 10
    ema_slow: int = 200
    volume_filter: bool = True
    adx_threshold: float = 25.0

@dataclass
class SystemConfig:
    """Configuración completa del sistema"""
    exchange: ExchangeConfig
    trading_pairs: List[TradingPairConfig] = field(default_factory=list)
    data: DataConfig = field(default_factory=DataConfig)
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    strategies: List[StrategyConfig] = field(default_factory=list)
    
    # Configuración del sistema
    log_level: str = "INFO"
    parallel_downloads: int = 4
    cache_enabled: bool = True
    monitoring_enabled: bool = True

class ConfigManager(IConfigManager):
    """Gestor de configuración centralizado"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path("config/config.yaml")
        self.logger = logging.getLogger(__name__)
        self._config: Optional[SystemConfig] = None
        self._config_cache: Dict[str, Any] = {}
    
    def load_config(self) -> SystemConfig:
        """Carga la configuración completa"""
        if self._config is not None:
            return self._config
        
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
                self._config = self._create_default_config()
                self.save_config(self._config)
                return self._config
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self._config = self._parse_config(config_data)
            self.logger.info(f"Configuración cargada desde: {self.config_path}")
            return self._config
            
        except Exception as e:
            self.logger.error(f"Error cargando configuración: {e}")
            self._config = self._create_default_config()
            return self._config
    
    def save_config(self, config: SystemConfig) -> bool:
        """Guarda la configuración"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = asdict(config)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            self._config = config
            self.logger.info(f"Configuración guardada en: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando configuración: {e}")
            return False
    
    def get_exchange_config(self) -> ExchangeConfig:
        """Obtiene configuración del exchange"""
        return self.load_config().exchange
    
    def get_trading_pairs(self) -> List[TradingPairConfig]:
        """Obtiene configuración de pares de trading"""
        return self.load_config().trading_pairs
    
    def get_data_config(self) -> DataConfig:
        """Obtiene configuración de datos"""
        return self.load_config().data
    
    def get_indicator_config(self) -> IndicatorConfig:
        """Obtiene configuración de indicadores"""
        return self.load_config().indicators
    
    def get_storage_config(self) -> StorageConfig:
        """Obtiene configuración de almacenamiento"""
        return self.load_config().storage
    
    def get_backtest_config(self) -> BacktestConfig:
        """Obtiene configuración de backtesting"""
        return self.load_config().backtest
    
    def get_strategy_configs(self) -> List[StrategyConfig]:
        """Obtiene configuraciones de estrategias"""
        return self.load_config().strategies
    
    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """Obtiene configuración de una estrategia específica"""
        strategies = self.get_strategy_configs()
        for strategy in strategies:
            if strategy.name == strategy_name:
                return strategy
        return None
    
    def update_config_section(self, section: str, data: Dict[str, Any]) -> bool:
        """Actualiza una sección específica de la configuración"""
        try:
            config = self.load_config()
            
            if hasattr(config, section):
                # Actualizar campos específicos
                current_section = getattr(config, section)
                if hasattr(current_section, '__dict__'):
                    for key, value in data.items():
                        if hasattr(current_section, key):
                            setattr(current_section, key, value)
                
                return self.save_config(config)
            else:
                self.logger.error(f"Sección de configuración no encontrada: {section}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error actualizando configuración: {e}")
            return False
    
    def validate_config(self) -> List[str]:
        """Valida la configuración y retorna lista de errores"""
        errors = []
        config = self.load_config()
        
        # Validar exchange
        if not config.exchange.name:
            errors.append("Nombre del exchange es requerido")
        
        # Validar pares de trading
        if not config.trading_pairs:
            errors.append("Debe configurar al menos un par de trading")
        
        for pair in config.trading_pairs:
            if not pair.symbol:
                errors.append(f"Símbolo requerido para par de trading")
            if pair.min_notional <= 0:
                errors.append(f"min_notional debe ser > 0 para {pair.symbol}")
        
        # Validar fechas
        try:
            from datetime import datetime
            start = datetime.strptime(config.data.start_date, "%Y-%m-%d")
            end = datetime.strptime(config.data.end_date, "%Y-%m-%d")
            if start >= end:
                errors.append("start_date debe ser anterior a end_date")
        except ValueError as e:
            errors.append(f"Formato de fecha inválido: {e}")
        
        # Validar timeframes
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        for tf in config.data.timeframes:
            if tf not in valid_timeframes:
                errors.append(f"Timeframe inválido: {tf}")
        
        # Validar estrategias
        for strategy in config.strategies:
            if not strategy.name:
                errors.append("Nombre de estrategia es requerido")
            if strategy.stop_loss_pct <= 0 or strategy.stop_loss_pct >= 1:
                errors.append(f"stop_loss_pct debe estar entre 0 y 1 para {strategy.name}")
        
        return errors
    
    def _create_default_config(self) -> SystemConfig:
        """Crea configuración por defecto"""
        # Exchange por defecto
        exchange = ExchangeConfig(name="bybit", sandbox=True)
        
        # Pares de trading por defecto
        default_pairs = [
            TradingPairConfig("BTC/USDT", "BTC", "USDT"),
            TradingPairConfig("ETH/USDT", "ETH", "USDT"),
            TradingPairConfig("ADA/USDT", "ADA", "USDT"),
            TradingPairConfig("SOL/USDT", "SOL", "USDT")
        ]
        
        # Estrategia UT Bot + PSAR por defecto
        strategy = UTBotPSARConfig(
            name="utbot_psar",
            risk_level="medium",
            ut_bot_key_value=1.0,
            ut_bot_atr_period=10
        )
        
        return SystemConfig(
            exchange=exchange,
            trading_pairs=default_pairs,
            strategies=[strategy]
        )
    
    def _parse_config(self, config_data: Dict[str, Any]) -> SystemConfig:
        """Parsea datos de configuración a objetos tipados"""
        # Exchange
        exchange_data = config_data.get('exchange', {})
        exchange = ExchangeConfig(**exchange_data)
        
        # Trading pairs
        pairs_data = config_data.get('trading_pairs', [])
        trading_pairs = [TradingPairConfig(**pair) for pair in pairs_data]
        
        # Secciones opcionales con valores por defecto
        data_config = DataConfig(**config_data.get('data', {}))
        indicator_config = IndicatorConfig(**config_data.get('indicators', {}))
        storage_config = StorageConfig(**config_data.get('storage', {}))
        backtest_config = BacktestConfig(**config_data.get('backtest', {}))
        
        # Estrategias
        strategies_data = config_data.get('strategies', [])
        strategies = []
        for strategy_data in strategies_data:
            strategy_type = strategy_data.get('name', '').lower()
            if 'utbot' in strategy_type or 'psar' in strategy_type:
                strategies.append(UTBotPSARConfig(**strategy_data))
            else:
                strategies.append(StrategyConfig(**strategy_data))
        
        return SystemConfig(
            exchange=exchange,
            trading_pairs=trading_pairs,
            data=data_config,
            indicators=indicator_config,
            storage=storage_config,
            backtest=backtest_config,
            strategies=strategies,
            log_level=config_data.get('log_level', 'INFO'),
            parallel_downloads=config_data.get('parallel_downloads', 4),
            cache_enabled=config_data.get('cache_enabled', True),
            monitoring_enabled=config_data.get('monitoring_enabled', True)
        )

# Instancia global del gestor de configuración
_config_manager: Optional[ConfigManager] = None

def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Obtiene instancia singleton del gestor de configuración"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager

def load_config(config_path: Optional[str] = None) -> SystemConfig:
    """Función de conveniencia para cargar configuración"""
    return get_config_manager(config_path).load_config()
