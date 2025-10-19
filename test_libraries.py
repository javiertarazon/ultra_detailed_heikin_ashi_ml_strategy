#!/usr/bin/env python3
"""
Script para verificar si las versiones arregladas de librerías funcionan con Python 3.13
"""

import sys
import subprocess

def test_import(module_name, description):
    """Prueba importar un módulo y reporta el resultado"""
    try:
        __import__(module_name)
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def test_project_imports():
    """Prueba imports específicos del proyecto que estaban fallando"""
    print("\n🏗️  Probando imports del proyecto...")

    tests = [
        ("utils.normalization", "DataNormalizer (sklearn/scipy)"),
        ("indicators.technical_indicators", "TechnicalIndicators"),
        ("strategies.heikin_neuronal_ml_pruebas", "HeikinNeuronalMLPruebas (joblib)"),
        ("core.ccxt_order_executor", "CCXT Order Executor"),
        ("core.ccxt_live_trading_orchestrator", "CCXT Live Trading Orchestrator"),
    ]

    all_passed = True
    for module, description in tests:
        try:
            __import__(module)
            print(f"✅ {description}: OK")
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
            all_passed = False

    return all_passed

def check_versions():
    """Verifica las versiones actuales de las librerías"""
    print("📦 Versiones actuales de librerías críticas:")

    libraries = {
        "scikit-learn": "sklearn",
        "scipy": "scipy",
        "joblib": "joblib",
        "aiohttp": "aiohttp",
        "ccxt": "ccxt"
    }

    for lib_name, import_name in libraries.items():
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'N/A')
            print(f"   {lib_name}: {version}")
        except Exception as e:
            print(f"   {lib_name}: ERROR - {e}")

def main():
    """Función principal"""
    print("🔧 VERIFICACIÓN DE VERSIONES DE LIBRERÍAS PYTHON 3.13")
    print("=" * 60)

    print(f"🐍 Python version: {sys.version}")
    print()

    # Verificar versiones
    check_versions()
    print()

    # Probar imports críticos
    print("📚 Probando imports críticos...")
    critical_tests = [
        ("sklearn", "scikit-learn"),
        ("scipy", "scipy"),
        ("joblib", "joblib"),
        ("aiohttp", "aiohttp"),
        ("ccxt", "ccxt"),
        ("ccxt.async_support", "ccxt async"),
    ]

    critical_ok = True
    for module, description in critical_tests:
        if not test_import(module, description):
            critical_ok = False

    print()
    project_ok = test_project_imports()

    print("\n" + "=" * 60)

    if critical_ok and project_ok:
        print("🎉 ¡ÉXITO TOTAL!")
        print("   ✅ Todas las librerías funcionan con Python 3.13")
        print("   ✅ El proyecto puede ejecutarse sin downgrade")
        print("\n🚀 Comando listo:")
        print("   python descarga_datos/main.py --live-ccxt")
        return 0
    else:
        print("❌ PROBLEMAS DETECTADOS")
        if not critical_ok:
            print("   - Librerías críticas con errores")
        if not project_ok:
            print("   - Imports del proyecto fallando")

        print("\n🔧 SOLUCIONES:")
        print("   1. Ejecutar: fix_libraries.bat (para intentar otras versiones)")
        print("   2. Si persiste: downgrade_python.bat (cambiar a Python 3.11)")
        return 1

if __name__ == "__main__":
    sys.exit(main())