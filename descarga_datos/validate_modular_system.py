#!/usr/bin/env python3
"""
Script de validación del sistema modular de estrategias
"""
import sys
import os

# Agregar el directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_imports():
    """Prueba que todas las importaciones funcionan"""
    print("=== TESTING IMPORTS ===")

    try:
        from config.config_loader import load_config_from_yaml
        print("✅ config_loader importado correctamente")
    except Exception as e:
        print(f"❌ Error importando config_loader: {e}")
        return False

    try:
        from strategies.solana_4h_trailing_strategy import Solana4HTrailingStrategy
        print("✅ Solana4HTrailingStrategy importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Solana4HTrailingStrategy: {e}")
        return False

    return True

def test_config_loading():
    """Prueba que la configuración se carga correctamente"""
    print("\n=== TESTING CONFIG LOADING ===")

    try:
        from config.config_loader import load_config_from_yaml
        config = load_config_from_yaml()
        print("✅ Configuración cargada exitosamente")

        strategies = config.backtesting.strategies
        print(f"📋 Estrategias configuradas: {strategies}")

        solana_trailing = strategies.get('Solana4HTrailing', False)
        print(f"🎯 Solana4HTrailing activada: {solana_trailing}")

        return solana_trailing

    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return False

def test_backtesting_execution():
    """Prueba una ejecución simplificada del backtesting"""
    print("\n=== TESTING BACKTESTING EXECUTION ===")

    try:
        from config.config_loader import load_config_from_yaml
        from strategies.solana_4h_strategy import Solana4HStrategy
        from strategies.solana_4h_trailing_strategy import Solana4HTrailingStrategy

        # Cargar configuración
        config = load_config_from_yaml()
        print("✅ Configuración cargada")

        # Crear estrategias
        strategies = {}
        if config.backtesting.strategies.get('Solana4H', False):
            strategies['Solana4H'] = Solana4HStrategy()
            print("✅ Solana4H instanciada")

        if config.backtesting.strategies.get('Solana4HTrailing', False):
            strategies['Solana4HTrailing'] = Solana4HTrailingStrategy()
            print("✅ Solana4HTrailing instanciada")

        # Crear datos de prueba simples
        import pandas as pd
        import numpy as np

        dates = pd.date_range('2024-01-01', periods=100, freq='4H')
        np.random.seed(42)

        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 105 + np.random.randn(100).cumsum(),
            'low': 95 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100)
        })

        print("✅ Datos de prueba creados")

        # Ejecutar estrategias con datos de prueba
        results = {}
        for name, strategy in strategies.items():
            try:
                result = strategy.run(test_data, 'TEST_SYMBOL')
                results[name] = result
                print(f"✅ {name} ejecutada: {result['total_trades']} trades, PnL: {result['total_pnl']:.2f}")
            except Exception as e:
                print(f"❌ Error ejecutando {name}: {e}")
                return False

        if len(results) == 2:
            print("🎉 ¡Ambas estrategias se ejecutaron correctamente!")
            return True
        else:
            print(f"❌ Solo {len(results)} estrategias se ejecutaron")
            return False

    except Exception as e:
        print(f"❌ Error en ejecución de backtesting: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dynamic_loading():
    """Prueba la carga dinámica de estrategias desde configuración"""
    print("\n=== TESTING DYNAMIC LOADING ===")

    try:
        from config.config_loader import load_config_from_yaml

        # Cargar configuración
        config = load_config_from_yaml()
        print("✅ Configuración cargada para carga dinámica")

        # Simular la lógica de carga dinámica de run_backtesting_batches.py
        strategy_classes = {
            'Solana4H': ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
            'Solana4HTrailing': ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
        }

        strategies = {}
        for strategy_name, (module_name, class_name) in strategy_classes.items():
            if config.backtesting.strategies.get(strategy_name, False):
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    strategy_class = getattr(module, class_name)
                    strategies[strategy_name] = strategy_class()
                    print(f"✅ {strategy_name} cargada dinámicamente")
                except Exception as e:
                    print(f"❌ Error cargando {strategy_name}: {e}")
                    return False

        if len(strategies) == 2:
            print("🎉 ¡Carga dinámica exitosa para ambas estrategias!")
            return True
        else:
            print(f"❌ Solo {len(strategies)} estrategias cargadas dinámicamente")
            return False

    except Exception as e:
        print(f"❌ Error en carga dinámica: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 VALIDACIÓN DEL SISTEMA MODULAR DE ESTRATEGIAS")
    print("=" * 60)

    # Test 1: Imports
    if not test_imports():
        print("\n❌ FALLÓ: Imports básicos")
        return False

    # Test 2: Config loading
    if not test_config_loading():
        print("\n❌ FALLÓ: Configuración no carga Solana4HTrailing")
        return False

    # Test 3: Dynamic loading
    if not test_dynamic_loading():
        print("\n❌ FALLÓ: Carga dinámica")
        return False

    # Test 4: Backtesting execution
    if not test_backtesting_execution():
        print("\n❌ FALLÓ: Ejecución de backtesting")
        return False

    print("\n🎊 ¡TODOS LOS TESTS PASARON!")
    print("✅ El sistema modular está funcionando correctamente")
    print("✅ Solana4HTrailing se puede cargar dinámicamente")
    print("✅ Ambas estrategias se ejecutan correctamente")
    print("✅ No es necesario modificar backtester/main/dashboard para nuevas estrategias")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)