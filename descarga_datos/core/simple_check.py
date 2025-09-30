#!/usr/bin/env python3
"""
Verificación básica de módulos core
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

def check_module(module_name):
    """Verifica si un módulo se puede importar"""
    try:
        __import__(f"core.{module_name}")
        print(f"[OK] {module_name}: Import successful")
        return True
    except Exception as e:
        print(f"[ERROR] {module_name}: Import failed - {e}")
        return False

def main():
    print("Core Modules Verification")
    print("=" * 30)

    modules = [
        "base_data_handler",
        "downloader",
        "mt5_downloader",
        "live_trading_orchestrator",
        "mt5_live_data",
        "mt5_order_executor",
        "ccxt_live_data",
        "ccxt_live_trading_orchestrator",
        "ccxt_order_executor"
    ]

    success_count = 0
    for module in modules:
        if check_module(module):
            success_count += 1

    print(f"\nResults: {success_count}/{len(modules)} modules OK")

    # Check if cache_manager file exists
    cache_file = Path(__file__).parent / "cache_manager.py"
    if cache_file.exists():
        print("[OK] cache_manager: File exists")
        success_count += 1
    else:
        print("[ERROR] cache_manager: File not found")

    print(f"\nFinal: {success_count}/{len(modules) + 1} components OK")

if __name__ == "__main__":
    main()