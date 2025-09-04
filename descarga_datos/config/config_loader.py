"""
Config loader module for loading configuration from YAML files.
"""
import yaml
from typing import Dict, Any
import os
from .config import Config, StorageConfig, NormalizationConfig, IndicatorConfig, MT5Config

def load_config_from_yaml(file_path: str = None) -> Config:
    """
    Load configuration from a YAML file.
    
    Args:
        file_path (str): Path to the YAML config file. If None, uses default path.
        
    Returns:
        Config: The loaded configuration object
    """
    if file_path is None:
        # Asciende un nivel para llegar a la raíz de descarga_datos y luego entra en config
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "config", "config.yaml")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Extraer configuraciones anidadas
    storage_config_data = config_data.pop('storage', {})
    normalization_config_data = config_data.pop('normalization', {})
    indicators_config_data = config_data.pop('indicators', {})
    mt5_config_data = config_data.pop('mt5', {})
    
    # Intentar cargar configuración específica de MT5 si existe
    mt5_config_path = os.path.join(os.path.dirname(file_path), "mt5_config.yaml")
    if os.path.exists(mt5_config_path):
        with open(mt5_config_path, 'r') as f:
            mt5_extra_config = yaml.safe_load(f)
            # Solo tomamos la sección 'mt5' si existe
            if 'mt5' in mt5_extra_config:
                mt5_config_data.update(mt5_extra_config['mt5'])
            else:
                mt5_config_data.update(mt5_extra_config)
    
    # Crear instancias de las clases de configuración anidadas
    storage_config = StorageConfig(**storage_config_data)
    normalization_config = NormalizationConfig(**normalization_config_data)
    indicators_config = IndicatorConfig(**indicators_config_data)
    mt5_config = MT5Config(**mt5_config_data)
    
    # Crear la instancia de Config principal
    return Config(
        storage=storage_config,
        normalization=normalization_config,
        indicators=indicators_config,
        mt5=mt5_config,
        **config_data
    )

def save_config_to_yaml(config: Config, file_path: str = None):
    """
    Save configuration to a YAML file.
    
    Args:
        config (Config): Configuration object to save
        file_path (str): Path to save the YAML file. If None, uses default path.
    """
    if file_path is None:
        # Asciende un nivel para llegar a la raíz de descarga_datos y luego entra en config
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "config", "config.yaml")

    config_dict = {
        'active_exchange': config.active_exchange,
        'exchanges': config.exchanges,
        'default_symbols': config.default_symbols,
        'data_types': config.data_types,
        'max_retries': config.max_retries,
        'retry_delay': config.retry_delay,
        'log_level': config.log_level,
        'log_file': config.log_file,
        'timeframe': config.timeframe,
        'storage': {
            'path': config.storage.path,
            'csv': config.storage.csv,
            'sqlite': config.storage.sqlite
        },
        'normalization': {
            'enabled': config.normalization.enabled,
            'method': config.normalization.method
        },
        'indicators': {
            'volatility': config.indicators.volatility,
            'heiken_ashi': config.indicators.heiken_ashi,
            'atr': config.indicators.atr,
            'adx': config.indicators.adx,
            'ema': config.indicators.ema,
            'parabolic_sar': config.indicators.parabolic_sar,
            'normalize_output': config.indicators.normalize_output
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)