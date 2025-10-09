#!/usr/bin/env python3
"""
Script de prueba para el sistema de logging centralizado.
Este script verifica que el sistema de logging funciona correctamente.
"""
import sys
import os
import time
from pathlib import Path

# Agregar el directorio padre al path para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.logger import initialize_system_logging, get_logger
from utils.logger_metrics import log_execution_time, log_system_status, log_batch_operation

def test_basic_logging():
    """Prueba de funcionalidad básica de logging"""
    logger = get_logger('test_basic')
    
    logger.info("=== Prueba de niveles de logging ===")
    logger.debug("Este es un mensaje de nivel DEBUG")
    logger.info("Este es un mensaje de nivel INFO")
    logger.warning("Este es un mensaje de nivel WARNING")
    logger.error("Este es un mensaje de nivel ERROR")
    logger.critical("Este es un mensaje de nivel CRITICAL")
    
    assert True  # La prueba pasa si no hay excepciones

def test_exception_logging():
    """Prueba de logging de excepciones"""
    logger = get_logger('test_exception')
    
    logger.info("=== Prueba de logging de excepciones ===")
    try:
        result = 1 / 0
    except Exception as e:
        logger.error(f"Error en división: {e}", exc_info=True)
    
    assert True  # La prueba pasa si no hay excepciones

def test_unicode_handling():
    """Prueba de manejo de caracteres Unicode"""
    logger = get_logger('test_unicode')
    
    logger.info("=== Prueba de manejo de caracteres Unicode ===")
    logger.info("Mensaje con emojis: 🚀 ✅ ⚠️ ❌")
    logger.info("Mensaje con caracteres especiales: áéíóúñ")
    
    assert True  # La prueba pasa si no hay excepciones

def test_performance_metrics():
    """Prueba de métricas de rendimiento"""
    logger = get_logger('test_metrics')
    
    logger.info("=== Prueba de métricas de rendimiento ===")
    
    # Medir tiempo de ejecución
    start_time = time.time()
    time.sleep(0.5)  # Simular operación
    log_execution_time(logger, "Operación simulada", start_time)
    
    # Estado del sistema
    metrics = {
        'cpu_usage': '23%',
        'memory_usage': '156MB',
        'active_threads': 4,
        'disk_space': '1.2GB free'
    }
    log_system_status(logger, metrics)
    
    # Operación por lotes
    log_batch_operation(logger, "Procesamiento de archivos", 
                      total=100, success=95, errors=5)
    
    assert True  # La prueba pasa si no hay excepciones

def test_class_integration():
    """Prueba de integración con clases"""
    logger = get_logger('test_class')
    
    class TestClass:
        def __init__(self):
            self.logger = get_logger(__name__ + '.TestClass')
            self.logger.info("Instancia de TestClass creada")
        
        def do_something(self):
            self.logger.info("Método do_something ejecutado")
            return True
    
    logger.info("=== Prueba de integración con clases ===")
    test_instance = TestClass()
    result = test_instance.do_something()
    
    assert result  # La prueba pasa si do_something() devuelve True

def main():
    """Función principal"""
    print("Iniciando pruebas del sistema de logging centralizado")
    print("=" * 60)
    
    # Inicializar sistema de logging
    log_file = 'logs/test_logging.log'
    initialize_system_logging({
        'level': 'DEBUG',
        'file': log_file
    })
    
    logger = get_logger('test_main')
    logger.info("Prueba del sistema de logging centralizado")
    
    # Ejecutar pruebas
    tests = [
        ('Logging básico', test_basic_logging),
        ('Manejo de excepciones', test_exception_logging),
        ('Caracteres Unicode', test_unicode_handling),
        ('Métricas de rendimiento', test_performance_metrics),
        ('Integración con clases', test_class_integration)
    ]
    
    all_passed = True
    
    for name, test_func in tests:
        try:
            print(f"Ejecutando prueba: {name}...")
            result = test_func()
            if result:
                logger.info(f"✅ Prueba '{name}' EXITOSA")
                print(f"  ✅ ÉXITO")
            else:
                logger.error(f"❌ Prueba '{name}' FALLIDA")
                print(f"  ❌ FALLO")
                all_passed = False
        except Exception as e:
            logger.error(f"❌ Prueba '{name}' ERROR: {e}", exc_info=True)
            print(f"  ❌ ERROR: {e}")
            all_passed = False
    
    # Resultado final
    if all_passed:
        logger.info("✅ TODAS LAS PRUEBAS EXITOSAS")
        print("\n✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    else:
        logger.error("❌ ALGUNAS PRUEBAS FALLARON")
        print("\n❌ ALGUNAS PRUEBAS FALLARON")
    
    print(f"\nLos logs detallados están disponibles en: {log_file}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())