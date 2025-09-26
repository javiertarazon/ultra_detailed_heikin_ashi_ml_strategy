#!/usr/bin/env python3
"""
Validador del Sistema Modular - Verifica la correcta integración de todos los componentes
"""
import os
import sys
import importlib
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar directorio padre al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar componentes principales del sistema
from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger

# Configurar logging
setup_logging()
logger = get_logger(__name__)

def validate_config():
    """Validar que el archivo de configuración exista y se cargue correctamente"""
    logger.info("Validando archivo de configuración...")
    try:
        from pathlib import Path
        config_path = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / 'config' / 'config.yaml'
        if config_path.exists():
            config = load_config_from_yaml(config_path)
            logger.info("✅ Configuración YAML cargada correctamente")
            return config
        else:
            logger.error(f"❌ Archivo de configuración no encontrado en {config_path}")
            return None
    except Exception as e:
        logger.error(f"❌ Error cargando configuración YAML: {e}")
        return None

def validate_core_components():
    """Validar que los componentes core del sistema se puedan importar"""
    logger.info("Validando componentes core...")
    
    components = [
        ('core.downloader', 'AdvancedDataDownloader'),
        ('core.mt5_downloader', 'MT5Downloader'),
        ('backtesting.backtester', 'AdvancedBacktester'),
        ('indicators.technical_indicators', None),
        ('utils.normalization', None),
        ('utils.storage', None),
        ('utils.logger', 'get_logger'),
    ]
    
    all_valid = True
    
    for module_name, class_name in components:
        try:
            module = importlib.import_module(module_name)
            if class_name:
                class_obj = getattr(module, class_name)
                logger.info(f"✅ Componente {module_name}.{class_name} validado")
            else:
                logger.info(f"✅ Módulo {module_name} validado")
        except Exception as e:
            logger.error(f"❌ Error validando {module_name}: {e}")
            all_valid = False
    
    return all_valid

def validate_strategies():
    """Validar que todas las estrategias se puedan importar y usar"""
    logger.info("Validando estrategias...")
    
    strategies = [
        ('strategies.ut_bot_psar', 'UTBotPSARStrategy'),
        ('strategies.ut_bot_psar_compensation', 'UTBotPSARCompensationStrategy'),
        ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
        ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
        ('strategies.solana_4h_risk_managed_strategy', 'Solana4HRiskManagedStrategy'),
        ('strategies.solana_4h_optimized_trailing_strategy', 'Solana4HOptimizedTrailingStrategy'),
        ('strategies.solana_4h_enhanced_trailing_balanced_strategy', 'Solana4HEnhancedTrailingBalancedStrategy'),
    ]
    
    all_valid = True
    
    for module_name, class_name in strategies:
        try:
            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)
            strategy = strategy_class()
            logger.info(f"✅ Estrategia {class_name} cargada correctamente")
        except Exception as e:
            logger.error(f"❌ Error validando estrategia {class_name}: {e}")
            all_valid = False
    
    return all_valid

def validate_integration():
    """Validar que todos los componentes del sistema funcionen juntos"""
    logger.info("Validando integración de componentes...")
    
    # Crear datos de prueba
    try:
        # Crear DataFrame de prueba
        logger.info("Creando datos de prueba para validación...")
        today = datetime.now()
        dates = [today - timedelta(hours=i) for i in range(100)]
        test_data = pd.DataFrame({
            'open': np.random.normal(100, 5, 100),
            'high': np.random.normal(105, 5, 100),
            'low': np.random.normal(95, 5, 100),
            'close': np.random.normal(101, 5, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        # Ordenar por fecha
        test_data = test_data.sort_index()
        
        # Asegurar que high es el máximo y low es el mínimo
        for i in range(len(test_data)):
            values = [test_data.iloc[i]['open'], test_data.iloc[i]['close']]
            test_data.iloc[i, test_data.columns.get_loc('high')] = max(values) + abs(np.random.normal(1, 0.5))
            test_data.iloc[i, test_data.columns.get_loc('low')] = min(values) - abs(np.random.normal(1, 0.5))
            
        logger.info("✅ Datos de prueba creados")
        
        # Probar estrategias con los datos
        logger.info("Probando estrategias con datos simulados...")
        
        # Lista de estrategias a probar - Solo archivos existentes
        strategies_to_test = [
            ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
            ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
            ('strategies.solana_4h_enhanced_trailing_balanced_strategy', 'Solana4HEnhancedTrailingBalancedStrategy'),
        ]
        
        for module_name, class_name in strategies_to_test:
            try:
                module = importlib.import_module(module_name)
                strategy_class = getattr(module, class_name)
                strategy = strategy_class()
                
                # Ejecutar backtest con datos de prueba
                results = strategy.run(test_data, "TEST/USDT")
                
                # Verificar resultados básicos
                if 'trades' in results and isinstance(results['trades'], list):
                    logger.info(f"✅ {class_name} ejecutada correctamente con {len(results['trades'])} trades")
                else:
                    logger.warning(f"⚠️ {class_name} no generó trades o formato incorrecto")
                    
            except Exception as e:
                logger.error(f"❌ Error probando estrategia {class_name}: {e}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en validación de integración: {e}")
        return False

def validate_modular_system():
    """Ejecutar todas las validaciones del sistema modular"""
    logger.info("=" * 50)
    logger.info("INICIO DE VALIDACIÓN DEL SISTEMA MODULAR")
    logger.info("=" * 50)
    
    # Validar configuración
    config = validate_config()
    if not config:
        return False
    
    # Validar componentes core
    core_valid = validate_core_components()
    
    # Validar estrategias
    strategies_valid = validate_strategies()
    
    # Validar integración
    integration_valid = validate_integration()
    
    # Resultado final
    all_valid = core_valid and strategies_valid and integration_valid
    
    logger.info("=" * 50)
    if all_valid:
        logger.info("✅ VALIDACIÓN COMPLETA: Sistema modular funcionando correctamente")
    else:
        logger.error("❌ VALIDACIÓN FALLIDA: Revisar errores")
    logger.info("=" * 50)
    
    return all_valid

if __name__ == "__main__":
    success = validate_modular_system()
    sys.exit(0 if success else 1)
