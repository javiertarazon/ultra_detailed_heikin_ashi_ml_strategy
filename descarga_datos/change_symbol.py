#!/usr/bin/env python3
"""
SCRIPT DE EJEMPLO: Cómo cambiar entre símbolos sin modificar la estrategia
============================================================================

Este script demuestra cómo cambiar fácilmente entre diferentes símbolos
modificando solo la configuración centralizada, sin tocar la estrategia.
"""

import yaml
import os
from pathlib import Path

def change_symbol(new_symbol):
    """
    Cambia el símbolo activo en la configuración centralizada.

    Args:
        new_symbol: Nuevo símbolo (ej: 'XRP/USDT', 'DOGE/USDT')
    """
    config_path = Path('config/config.yaml')

    # Leer configuración actual
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Cambiar símbolo en la lista de símbolos activos
    config['backtesting']['symbols'] = [new_symbol]

    # Cambiar study_name para que sea específico del símbolo
    symbol_clean = new_symbol.replace('/', '_').replace('.', '_').lower()
    config['backtesting']['optimization']['study_name'] = f'{symbol_clean}_ml_optimization'

    # Cambiar comentario del exchange si es necesario
    if 'SOL' in new_symbol:
        config['active_exchange'] = 'bybit  # 🔥 Bybit para mejor conectividad con SOL/USDT'
    elif 'XRP' in new_symbol:
        config['active_exchange'] = 'bybit  # 🔥 Bybit para mejor conectividad con XRP/USDT'
    elif 'DOGE' in new_symbol:
        config['active_exchange'] = 'binance  # 🔥 Binance para mejor conectividad con DOGE/USDT'

    # Guardar configuración actualizada
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"✅ Símbolo cambiado a {new_symbol}")
    print(f"📝 Study name: {config['backtesting']['optimization']['study_name']}")
    print(f"🔄 Exchange: {config['active_exchange']}")
    print()
    print("🚀 PRÓXIMOS PASOS:")
    print("1. python main.py --train-ml      # Entrenar modelos ML")
    print("2. python main.py --optimize     # Optimizar parámetros")
    print("3. python main.py --backtest-only # Ejecutar backtest")
    print("4. python main.py --dashboard-only # Ver resultados")

if __name__ == "__main__":
    print("🔄 CAMBIO DE SÍMBOLO - EJEMPLOS:")
    print("=================================")
    print()
    print("Símbolos disponibles:")
    print("- SOL/USDT  (actual)")
    print("- XRP/USDT")
    print("- DOGE/USDT")
    print()

    # Ejemplo: cambiar a XRP/USDT
    new_symbol = input("Ingrese el nuevo símbolo (ej: XRP/USDT): ").strip()
    if new_symbol:
        change_symbol(new_symbol)
    else:
        print("❌ No se especificó símbolo")