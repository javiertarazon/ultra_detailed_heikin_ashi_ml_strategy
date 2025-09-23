#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema modular de carga de estrategias
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config_from_yaml

def load_strategies_from_config(config):
    """
    Carga dinámicamente las estrategias activas desde la configuración.
    Retorna un diccionario con las estrategias instanciadas.
    """
    strategies = {}
    strategy_config = config.backtesting.strategies

    # Mapeo de nombres de configuración a clases de estrategia
    strategy_classes = {
        'Estrategia_Basica': ('strategies.ut_bot_psar', 'UTBotPSARStrategy'),
        'Estrategia_Compensacion': ('strategies.ut_bot_psar_compensation', 'UTBotPSARCompensationStrategy'),
        'Solana4H': ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
        'Solana4HTrailing': ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
    }

    print(f"[DEBUG] Configuración de estrategias: {strategy_config}")

    for strategy_name, is_active in strategy_config.items():
        if is_active and strategy_name in strategy_classes:
            try:
                module_name, class_name = strategy_classes[strategy_name]
                module = __import__(module_name, fromlist=[class_name])
                strategy_class = getattr(module, class_name)
                strategies[strategy_name] = strategy_class()
                print(f"[DEBUG] ✅ {strategy_name} cargada exitosamente")
            except Exception as e:
                print(f"[DEBUG] ❌ Error cargando {strategy_name}: {e}")
                continue
        elif is_active:
            print(f"[DEBUG] ⚠️  Estrategia '{strategy_name}' configurada pero no implementada")

    print(f"[DEBUG] Estrategias activas finales: {list(strategies.keys())}")
    return strategies

def test_modular_system():
    print("=== TEST DEL SISTEMA MODULAR ===")
    try:
        config = load_config_from_yaml()
        print("✅ Configuración cargada exitosamente")

        strategies = load_strategies_from_config(config)

        if 'Solana4HTrailing' in strategies:
            print("✅ Solana4HTrailing se cargó correctamente en el sistema modular")
            return True
        else:
            print("❌ Solana4HTrailing NO se cargó en el sistema modular")
            return False

    except Exception as e:
        print(f"❌ Error en el sistema modular: {e}")
        return False

if __name__ == "__main__":
    success = test_modular_system()
    if success:
        print("\n🎉 Sistema modular funcionando correctamente")
    else:
        print("\n💥 Sistema modular tiene problemas")