#!/usr/bin/env python3
"""
Script de verificación post-downgrade de Python
Verifica que Python 3.11 esté funcionando correctamente con las dependencias del proyecto
"""

import sys
import subprocess
import importlib
import os

def check_python_version():
    """Verificar versión de Python"""
    print("🐍 Verificando versión de Python...")
    version = sys.version_info
    print(f"   Versión: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor == 11:
        print("   ✅ Python 3.11.x detectado correctamente")
        return True
    else:
        print(f"   ❌ Versión incorrecta. Esperado: 3.11.x, Actual: {version.major}.{version.minor}.{version.micro}")
        return False

def check_critical_imports():
    """Verificar imports críticos que fallaban en Python 3.13"""
    print("\n📦 Verificando imports críticos...")

    critical_modules = [
        'ccxt',
        'ccxt.async_support',
        'sklearn',
        'scipy',
        'joblib',
        'pandas',
        'numpy',
        'aiohttp'
    ]

    failed_imports = []

    for module in critical_modules:
        try:
            importlib.import_module(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module}: {e}")
            failed_imports.append(module)
        except Exception as e:
            print(f"   ⚠️  {module}: Error inesperado - {e}")

    return len(failed_imports) == 0, failed_imports

def check_project_imports():
    """Verificar imports específicos del proyecto"""
    print("\n🏗️  Verificando imports del proyecto...")

    project_modules = [
        'utils.logger',
        'config.config_loader',
        'core.ccxt_order_executor',
        'strategies.heikin_neuronal_ml_pruebas',
        'indicators.technical_indicators'
    ]

    failed_imports = []

    for module in project_modules:
        try:
            importlib.import_module(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module}: {e}")
            failed_imports.append(module)
        except Exception as e:
            print(f"   ⚠️  {module}: Error inesperado - {e}")

    return len(failed_imports) == 0, failed_imports

def check_environment():
    """Verificar entorno virtual"""
    print("\n🌍 Verificando entorno...")

    # Verificar si estamos en un venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if in_venv:
        print("   ✅ Ejecutándose en entorno virtual")
        print(f"   📁 Entorno: {sys.prefix}")
    else:
        print("   ⚠️  NO ejecutándose en entorno virtual")

    # Verificar pip
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'],
                              capture_output=True, text=True, check=True)
        print(f"   ✅ Pip: {result.stdout.strip()}")
    except Exception as e:
        print(f"   ❌ Pip no disponible: {e}")

    return in_venv

def main():
    """Función principal"""
    print("🚀 VERIFICACIÓN POST-DOWNGRADE PYTHON")
    print("=" * 50)

    all_good = True

    # Verificar Python
    python_ok = check_python_version()
    all_good &= python_ok

    # Verificar entorno
    venv_ok = check_environment()
    all_good &= venv_ok

    # Verificar imports críticos
    imports_ok, failed_critical = check_critical_imports()
    all_good &= imports_ok

    # Verificar imports del proyecto
    project_ok, failed_project = check_project_imports()
    all_good &= project_ok

    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ¡DOWNGRADE EXITOSO!")
        print("   ✅ Python 3.11.x funcionando correctamente")
        print("   ✅ Todas las dependencias críticas disponibles")
        print("   ✅ Imports del proyecto funcionando")
        print("\n🚀 Puedes proceder con:")
        print("   python descarga_datos/main.py --live-ccxt")
    else:
        print("❌ PROBLEMAS DETECTADOS:")
        if not python_ok:
            print("   - Versión de Python incorrecta")
        if not venv_ok:
            print("   - Entorno virtual no activado")
        if failed_critical:
            print(f"   - Imports críticos fallidos: {failed_critical}")
        if failed_project:
            print(f"   - Imports del proyecto fallidos: {failed_project}")

        print("\n🔧 SOLUCIONES:")
        print("   1. Asegúrate de activar el entorno virtual: .venv\\Scripts\\Activate.ps1")
        print("   2. Si faltan dependencias: pip install -r requirements.txt")
        print("   3. Si hay problemas con sklearn: pip install scikit-learn")
        print("   4. Si persisten problemas: contacta soporte")

    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())