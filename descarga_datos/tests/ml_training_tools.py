#!/usr/bin/env python3
"""
ML Training Toolkit - Herramienta de Entrenamiento Consolidada v2.8
===================================================================

Esta herramienta unifica varios scripts de entrenamiento ML en una sola utilidad
que permite entrenar modelos individuales o en lote para diferentes símbolos.

Funcionalidades:
- Entrenamiento de modelos ML para símbolos individuales
- Entrenamiento en lote para múltiples símbolos
- Entrenamiento simplificado o avanzado
- Optimización de parámetros
- Validación de modelos entrenados

Uso:
    python ml_training_tools.py [opciones]

Opciones:
    --symbol SYMBOL      Símbolo específico a entrenar (ej: DOGE/USDT)
    --symbols S1 S2      Lista de símbolos a entrenar
    --all                Entrenar todos los símbolos configurados
    --advanced           Usar entrenamiento avanzado (ML2)
    --optimize           Ejecutar optimización de parámetros
    --validate           Validar modelos después del entrenamiento
"""

import os
import sys
import time
import asyncio
import argparse
from pathlib import Path
import json
from typing import Dict, List, Tuple

# Añadir el directorio padre al path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Importaciones del sistema
try:
    from config.config_loader import load_config_from_yaml
    from optimizacion.run_optimization_pipeline2 import OptimizationPipeline
    from optimizacion.run_optimization_pipeline3 import OptimizationPipelineAdvanced
    from optimizacion.ml_trainer import MLTrainer
    from optimizacion.ml_trainer2 import MLTrainer2
    from utils.logger import setup_logger
except ImportError as e:
    print(f"Error importando módulos necesarios: {e}")
    print("Asegúrate de ejecutar desde el directorio correcto")
    sys.exit(1)

# Configurar logger
logger = setup_logger(__name__)

# Lista predefinida de símbolos principales para referencia
DEFAULT_SYMBOLS = [
    'SOL/USDT',
    'ETH/USDT',
    'BTC/USDT',
    'DOGE/USDT',
    'XRP/USDT',
    'TSLA/US',
    'NVDA/US',
    'AAPL/US',
    'MSFT/US',
    'GOOGL/US',
    'EUR/USD',
    'GBP/USD'
]

async def train_symbol(symbol: str, config, advanced: bool = False, optimize: bool = False):
    """Entrenar modelo para un símbolo específico"""
    print(f"\n🎯 ENTRENANDO {'ML AVANZADO' if advanced else 'ML ESTÁNDAR'} PARA {symbol}")
    print("=" * 60)

    timeframe = config.backtesting.timeframe
    
    try:
        start_time = time.time()
        
        # Seleccionar versión de ML a utilizar (estándar o avanzada)
        if advanced:
            # ML2 - Versión avanzada con redes neuronales
            trainer = MLTrainer2(symbol, timeframe)
            
            # Cargar y preparar datos
            await trainer.download_data()
            data = trainer.prepare_data()
            
            if data is None or len(data) < 100:
                print(f"❌ Datos insuficientes para {symbol} (mínimo 100 velas)")
                return False
            
            # Entrenamiento de modelos
            await trainer.train_all_models()
            
            # Validación
            validation_results = await trainer.validate_models()
            
            # Mostrar resultados
            if validation_results:
                print("\n✅ Resultados de validación:")
                for model_name, metrics in validation_results.items():
                    acc = metrics.get('accuracy', 0.0)
                    print(f"  - {model_name}: {acc:.2%} precisión")
            
            # Optimización si se solicita
            if optimize:
                print("\n⚙️ Iniciando optimización de parámetros...")
                pipeline = OptimizationPipelineAdvanced(config)
                await pipeline.run_optimization_for_symbol(symbol, timeframe)
        
        else:
            # ML - Versión estándar
            trainer = MLTrainer(symbol, timeframe)
            
            # Cargar y preparar datos
            await trainer.download_data()
            data = trainer.prepare_data()
            
            if data is None or len(data) < 100:
                print(f"❌ Datos insuficientes para {symbol} (mínimo 100 velas)")
                return False
            
            # Entrenamiento de modelos
            await trainer.train_all_models()
            
            # Validación
            validation_results = await trainer.validate_models()
            
            # Mostrar resultados
            if validation_results:
                print("\n✅ Resultados de validación:")
                for model_name, metrics in validation_results.items():
                    acc = metrics.get('accuracy', 0.0)
                    print(f"  - {model_name}: {acc:.2%} precisión")
            
            # Optimización si se solicita
            if optimize:
                print("\n⚙️ Iniciando optimización de parámetros...")
                pipeline = OptimizationPipeline(config)
                await pipeline.run_optimization_for_symbol(symbol, timeframe)
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ Entrenamiento de {symbol} completado en {elapsed_time:.1f} segundos")
        return True
        
    except Exception as e:
        print(f"❌ Error entrenando {symbol}: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def train_multiple_symbols(symbols: List[str], config, advanced: bool = False, optimize: bool = False):
    """Entrenar modelos para múltiples símbolos"""
    print(f"🚀 ENTRENAMIENTO DE MODELOS {'ML AVANZADOS' if advanced else 'ML ESTÁNDAR'} EN LOTE")
    print("=" * 70)
    print(f"Símbolos a entrenar: {len(symbols)}")
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i:2d}. {symbol}")
    print()
    
    results = {}
    for symbol in symbols:
        print(f"\n📊 PROCESANDO {symbol} ({symbols.index(symbol) + 1}/{len(symbols)})")
        success = await train_symbol(symbol, config, advanced, optimize)
        results[symbol] = success
    
    # Resumen final
    print("\n📋 RESUMEN DE ENTRENAMIENTO")
    print("=" * 60)
    successful = sum(1 for s in results.values() if s)
    failed = sum(1 for s in results.values() if not s)
    
    print(f"✅ Símbolos entrenados exitosamente: {successful}/{len(symbols)}")
    print(f"❌ Símbolos con errores: {failed}/{len(symbols)}")
    
    if failed > 0:
        print("\nErrores por símbolo:")
        for symbol, success in results.items():
            if not success:
                print(f"  - {symbol}")
    
    return results

async def validate_models(symbols: List[str], config, advanced: bool = False):
    """Validar modelos entrenados para los símbolos especificados"""
    print(f"🔍 VALIDACIÓN DE MODELOS {'ML AVANZADOS' if advanced else 'ML ESTÁNDAR'}")
    print("=" * 60)
    
    timeframe = config.backtesting.timeframe
    results = {}
    
    for symbol in symbols:
        print(f"\n📊 VALIDANDO MODELOS PARA {symbol}")
        try:
            if advanced:
                trainer = MLTrainer2(symbol, timeframe)
            else:
                trainer = MLTrainer(symbol, timeframe)
                
            # Cargar datos
            await trainer.download_data()
            data = trainer.prepare_data()
            
            if data is None or len(data) < 100:
                print(f"❌ Datos insuficientes para {symbol}")
                results[symbol] = {'status': 'error', 'message': 'Datos insuficientes'}
                continue
            
            # Validar modelos existentes
            validation_results = await trainer.validate_models()
            
            if validation_results:
                print("✅ Resultados de validación:")
                
                max_acc = 0.0
                best_model = None
                
                for model_name, metrics in validation_results.items():
                    acc = metrics.get('accuracy', 0.0)
                    print(f"  - {model_name}: {acc:.2%} precisión")
                    
                    if acc > max_acc:
                        max_acc = acc
                        best_model = model_name
                
                results[symbol] = {
                    'status': 'ok',
                    'best_model': best_model,
                    'best_accuracy': max_acc,
                    'all_results': validation_results
                }
            else:
                print("⚠️ No se encontraron modelos para validar")
                results[symbol] = {'status': 'warning', 'message': 'No hay modelos'}
                
        except Exception as e:
            print(f"❌ Error validando {symbol}: {e}")
            results[symbol] = {'status': 'error', 'message': str(e)}
    
    # Resumen de validación
    print("\n📋 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    ok_count = sum(1 for r in results.values() if r.get('status') == 'ok')
    warning_count = sum(1 for r in results.values() if r.get('status') == 'warning')
    error_count = sum(1 for r in results.values() if r.get('status') == 'error')
    
    print(f"✅ Símbolos validados correctamente: {ok_count}/{len(symbols)}")
    print(f"⚠️ Símbolos sin modelos: {warning_count}/{len(symbols)}")
    print(f"❌ Símbolos con errores: {error_count}/{len(symbols)}")
    
    if ok_count > 0:
        print("\nMejores modelos por símbolo:")
        for symbol, data in results.items():
            if data.get('status') == 'ok':
                print(f"  - {symbol}: {data['best_model']} ({data['best_accuracy']:.2%})")
    
    return results

async def main():
    parser = argparse.ArgumentParser(description="Herramienta de entrenamiento ML unificada")
    parser.add_argument("--symbol", help="Símbolo específico a entrenar (ej: DOGE/USDT)")
    parser.add_argument("--symbols", nargs="+", help="Lista de símbolos a entrenar")
    parser.add_argument("--all", action="store_true", help="Entrenar todos los símbolos configurados")
    parser.add_argument("--advanced", action="store_true", help="Usar entrenamiento avanzado (ML2)")
    parser.add_argument("--optimize", action="store_true", help="Ejecutar optimización de parámetros")
    parser.add_argument("--validate", action="store_true", help="Solo validar modelos existentes")
    
    args = parser.parse_args()
    
    # Cargar configuración
    try:
        config = load_config_from_yaml()
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        sys.exit(1)
    
    # Determinar símbolos a procesar
    if args.all:
        symbols = config.backtesting.symbols
    elif args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    else:
        print("⚠️ Debe especificar un símbolo (--symbol), varios símbolos (--symbols) o todos (--all)")
        parser.print_help()
        sys.exit(1)
    
    # Ejecutar acción correspondiente
    if args.validate:
        # Solo validar modelos existentes
        await validate_models(symbols, config, args.advanced)
    else:
        # Entrenar modelos
        if len(symbols) == 1:
            await train_symbol(symbols[0], config, args.advanced, args.optimize)
        else:
            await train_multiple_symbols(symbols, config, args.advanced, args.optimize)

if __name__ == "__main__":
    asyncio.run(main())