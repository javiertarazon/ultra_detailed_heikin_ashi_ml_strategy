#!/usr/bin/env python3
"""
Script de Ejecución para Test de Live Trading con Binance Sandbox
=================================================================

Este script ejecuta el test completo de operaciones en vivo usando el sandbox de Binance.
Verifica todas las funcionalidades del sistema de trading en tiempo real.

Requisitos previos:
1. Credenciales de Binance Testnet configuradas en variables de entorno:
   - BINANCE_TEST_API_KEY
   - BINANCE_TEST_API_SECRET

2. Instalar dependencias:
   pip install -r requirements.txt

Uso:
python run_binance_sandbox_test.py

Author: GitHub Copilot
Date: Octubre 2025
"""

import os
import sys
import time
from pathlib import Path
import argparse
import subprocess

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def check_requirements():
    """Verificar que todos los requisitos estén instalados"""
    print("🔍 Verificando requisitos del sistema...")

    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False

    # Verificar dependencias
    try:
        import ccxt
        import pandas
        import numpy
        print("✅ Dependencias principales instaladas")
    except ImportError as e:
        print(f"❌ Falta instalar dependencias: {e}")
        print("Ejecuta: pip install -r requirements.txt")
        return False

    # Verificar credenciales
    api_key = os.getenv('BINANCE_TEST_API_KEY')
    api_secret = os.getenv('BINANCE_TEST_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Credenciales de Binance Testnet no configuradas")
        print("Configura las variables de entorno:")
        print("  BINANCE_TEST_API_KEY=tu_api_key")
        print("  BINANCE_TEST_API_SECRET=tu_api_secret")
        print("\nObtén tus credenciales en: https://testnet.binance.vision/")
        return False

    print("✅ Credenciales configuradas")
    return True

def run_validation():
    """Ejecutar validación del sistema"""
    print("\n🔧 Ejecutando validación del sistema...")
    try:
        result = subprocess.run([
            sys.executable, 'validate_modular_system.py'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("✅ Sistema validado correctamente")
            return True
        else:
            print("❌ Error en validación del sistema:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error ejecutando validación: {e}")
        return False

def run_test(test_type='full'):
    """Ejecutar el test especificado"""
    print(f"\n🧪 Ejecutando test de Binance Sandbox ({test_type})...")

    test_file = 'tests/test_binance_sandbox_live.py'

    if not Path(test_file).exists():
        print(f"❌ Archivo de test no encontrado: {test_file}")
        return False

    # Configurar argumentos del test
    cmd = [sys.executable, '-m', 'unittest', test_file, '-v']

    if test_type == 'connection':
        cmd.extend(['BinanceSandboxLiveTest.test_01_connection_and_authentication'])
    elif test_type == 'data':
        cmd.extend(['BinanceSandboxLiveTest.test_02_live_data_collection'])
    elif test_type == 'orders':
        cmd.extend(['BinanceSandboxLiveTest.test_03_limit_orders_buy_sell'])
    elif test_type == 'risk':
        cmd.extend(['BinanceSandboxLiveTest.test_04_stop_loss_take_profit'])
    elif test_type == 'scenario':
        cmd.extend(['BinanceSandboxLiveTest.test_06_comprehensive_trading_scenario'])

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("✅ Test completado exitosamente")
            return True
        else:
            print("❌ Test falló")
            return False

    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        return False

def show_results():
    """Mostrar resultados del último test"""
    print("\n📊 Buscando resultados del último test...")

    results_dir = Path('tests/test_results')
    if not results_dir.exists():
        print("❌ No se encontraron resultados de test")
        return

    # Buscar el archivo más reciente
    result_files = list(results_dir.glob('binance_sandbox_test_*.json'))
    if not result_files:
        print("❌ No se encontraron archivos de resultados")
        return

    latest_file = max(result_files, key=lambda x: x.stat().st_mtime)

    try:
        import json
        with open(latest_file, 'r') as f:
            results = json.load(f)

        print(f"📈 Resultados del test: {latest_file.name}")
        print(f"   📅 Fecha: {results.get('test_timestamp', 'N/A')}")
        print(f"   📊 Trades totales: {results.get('total_trades', 0)}")
        print(f"   💰 PnL total: ${results.get('total_pnl', 0):.2f}")
        print(f"   🎯 Win rate: {results.get('win_rate', 0):.1f}%")
        print(f"   ⏱️ Duración: {results.get('test_duration_seconds', 0):.1f} segundos")

        if results.get('trades'):
            print("   📋 Últimos trades:")
            for i, trade in enumerate(results['trades'][-3:]):  # Mostrar últimos 3
                print(f"      {i+1}. {trade.get('signal', 'N/A')} {trade.get('size', 0)} @ ${trade.get('price', 0):.2f}")

    except Exception as e:
        print(f"❌ Error leyendo resultados: {e}")

def main():
    """Función principal"""
    print("🚀 Test de Live Trading con Binance Sandbox")
    print("=" * 50)

    parser = argparse.ArgumentParser(description='Test de Live Trading con Binance Sandbox')
    parser.add_argument('--test', choices=['full', 'connection', 'data', 'orders', 'risk', 'scenario'],
                       default='full', help='Tipo de test a ejecutar')
    parser.add_argument('--results', action='store_true', help='Mostrar resultados del último test')
    parser.add_argument('--skip-validation', action='store_true', help='Omitir validación del sistema')

    args = parser.parse_args()

    # Mostrar resultados si se solicita
    if args.results:
        show_results()
        return

    # Verificar requisitos
    if not check_requirements():
        sys.exit(1)

    # Ejecutar validación
    if not args.skip_validation:
        if not run_validation():
            print("❌ Validación fallida. Corrige los errores antes de continuar.")
            sys.exit(1)

    # Ejecutar test
    if run_test(args.test):
        print("\n🎉 Test completado exitosamente!")
        print("📊 Revisa los logs en '../logs/binance_sandbox_test.log'")
        print("📈 Resultados guardados en 'tests/test_results/'")
    else:
        print("\n❌ Test falló. Revisa los logs para más detalles.")
        sys.exit(1)

if __name__ == '__main__':
    main()