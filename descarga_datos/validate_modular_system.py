#!/usr/bin/env python3#!/usr/bin/env python3

""""""

Validador del Sistema Modular - v2.8Validador del Sistema             base_dir / "backtesting",

=================================            base_dir / "config", 

"""            base_dir / "core",

            base_dir / "data",

def validate_modular_system():            base_dir / "indicators", 

    """Valida la estructura y componentes del sistema modular."""            base_dir / "strategies",

    print("✅ Sistema validado correctamente")            base_dir / "utils"

    return True        ]

        

if __name__ == "__main__":        for directory in required_dirs:

    validate_modular_system()            if not directory.exists():
                print(f"❌ Directorio requerido no encontrado: {directory}")
                return False
        
        print("✅ Estructura de directorios verificada")
        
        # Verificar archivos críticos
        critical_files = [
            base_dir / 'main.py',
            base_dir / 'config' / 'config.yaml',
            base_dir / 'backtesting' / 'backtesting_orchestrator.py',
            base_dir / 'core' / 'downloader.py',
            base_dir / 'indicators' / 'technical_indicators.py',
            base_dir / 'utils' / 'storage.py',
            base_dir / 'utils' / 'logger.py'
        ]==============================

Este módulo verifica que el sistema modular esté correctamente configurado
y que todos los componentes necesarios estén disponibles.
"""
import os
import sys
import importlib
from pathlib import Path

def validate_modular_system():
    """Valida la estructura y componentes del sistema modular.
    
    Returns:
        bool: True si el sistema está correctamente configurado
    """
    try:
        print("\n🔍 VALIDACIÓN DEL SISTEMA MODULAR DE TRADING v2.8")
        print("=" * 60)
        
        # Verificar estructura de directorios
        base_dir = Path(__file__).resolve().parent
        
        required_dirs = [
            base_dir / "backtesting",

            base_dir / "config",         'backtesting', 'config', 'core', 'data', 'indicators',

            base_dir / "core",        'models', 'optimizacion', 'risk_management', 'strategies',

            base_dir / "data",        'tests', 'utils'

            base_dir / "indicators",     ]

            base_dir / "strategies",    

            base_dir / "utils"    for dir_name in required_dirs:

        ]        if not os.path.isdir(dir_name):

                    print(f"❌ Directorio requerido no encontrado: {dir_name}")

        for directory in required_dirs:            return False

            if not directory.exists():    

                print(f"❌ Directorio requerido no encontrado: {directory}")    print("✅ Estructura de directorios verificada")

                return False    

            # Verificar archivos críticos

        # Verificar archivos clave    critical_files = [

        required_files = [        'main.py',

            base_dir / "main.py",        'config/config.yaml',

            base_dir / "config" / "config.yaml",        'backtesting/backtesting_orchestrator.py',

            base_dir / "backtesting" / "backtesting_orchestrator.py",        'core/downloader.py',

            base_dir / "indicators" / "technical_indicators.py"        'indicators/technical_indicators.py',

        ]
    
        for file_path in critical_files:
            if not file_path.is_file():
                print(f"❌ Archivo crítico no encontrado: {file_path}")
                return False
    
        print("✅ Archivos críticos verificados")
            
        # Verificar importaciones básicas
        modules_to_check = [
            ('config.config_loader', 'load_config_from_yaml'),
            ('backtesting.backtesting_orchestrator', 'load_strategies_from_config'),
            ('core.downloader', 'AdvancedDataDownloader'),
            ('indicators.technical_indicators', 'TechnicalIndicators'),
            ('utils.storage', 'DataStorage'),
            ('utils.logger', 'setup_logging')
        ]
        
        sys.path.insert(0, str(base_dir))
        
        for module_path, expected_attribute in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                if not hasattr(module, expected_attribute):
                    print(f"❌ Módulo {module_path} no tiene el atributo esperado: {expected_attribute}")
                    return False
            except ImportError as e:
                print(f"❌ Error importando {module_path}: {e}")
                return False
        
        print("✅ Módulos principales importados correctamente")
        
        print("\n✅ VALIDACIÓN DEL SISTEMA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        
        return True
            
    except Exception as e:
        print(f"❌ Error validando sistema modular: {e}")
        return False

if __name__ == "__main__":
    result = validate_modular_system()
    sys.exit(0 if result else 1)