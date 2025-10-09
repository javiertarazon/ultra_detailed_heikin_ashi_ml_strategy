#!/usr/bin/env python3
"""
Test Runner Unificado - v2.8
============================

Script centralizado para ejecutar diferentes conjuntos de tests del sistema.
Permite ejecutar pruebas PyTest, verificación de datos, diagnóstico de SQLite,
y entrenamiento de modelos ML desde un único punto de entrada.

Uso:
    python run_tests.py [opciones]

Opciones:
    --all: Ejecutar todos los tests disponibles
    --quick: Ejecutar solo tests rápidos (humo)
    --system: Ejecutar tests de integridad del sistema
    --data: Ejecutar verificación de datos
    --sqlite: Ejecutar diagnóstico de SQLite
    --ml: Ejecutar herramientas de entrenamiento ML
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
import asyncio

# Directorio base - asegurar que estamos en la ruta correcta
BASE_DIR = Path(__file__).resolve().parent.parent  # descarga_datos/
sys.path.insert(0, str(BASE_DIR))  # Añadir descarga_datos al path
sys.path.insert(0, str(BASE_DIR.parent))  # Añadir botcopilot-sar al path

def run_pytest(test_file=None):
    """Ejecutar tests PyTest"""
    print("\n🧪 EJECUTANDO TESTS PYTEST")
    print("=" * 50)
    
    cmd = [sys.executable, "-m", "pytest", "-v"]
    if test_file:
        cmd.append(test_file)
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Tests PyTest completados correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Algunos tests PyTest fallaron")
        return False
    except FileNotFoundError:
        print("❌ Error al ejecutar Python. Verifica la instalación")
        return False

def run_data_verification(quick=False):
    """Ejecutar verificación de datos"""
    print("\n🔍 EJECUTANDO VERIFICACIÓN DE DATOS")
    print("=" * 50)
    
    script = BASE_DIR / "tests" / "data_verification.py"
    
    if not script.exists():
        print(f"❌ Script {script} no encontrado")
        return False
    
    cmd = [sys.executable, str(script)]
    if quick:
        cmd.append("--quick")
    else:
        cmd.append("--all")
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Verificación de datos completada")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error en la verificación de datos")
        return False

def run_sqlite_diagnostics(basic=True):
    """Ejecutar diagnóstico de SQLite"""
    print("\n🗄️ EJECUTANDO DIAGNÓSTICO SQLITE")
    print("=" * 50)
    
    script = BASE_DIR / "tests" / "sqlite_diagnostics.py"
    
    if not script.exists():
        print(f"❌ Script {script} no encontrado")
        return False
    
    cmd = [sys.executable, str(script)]
    if basic:
        cmd.append("--basic")
    else:
        cmd.extend(["--basic", "--integrity"])
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Diagnóstico SQLite completado")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error en el diagnóstico SQLite")
        return False

async def run_ml_tools(validate_only=True):
    """Ejecutar herramientas ML"""
    print("\n🧠 EJECUTANDO HERRAMIENTAS ML")
    print("=" * 50)
    
    script = BASE_DIR / "tests" / "ml_training_tools.py"
    
    if not script.exists():
        print(f"❌ Script {script} no encontrado")
        return False
    
    cmd = [sys.executable, str(script), "--all"]
    if validate_only:
        cmd.append("--validate")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print("✅ Herramientas ML completadas correctamente")
            return True
        else:
            print(f"❌ Error en las herramientas ML: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando herramientas ML: {e}")
        return False

def run_system_validation():
    """Ejecutar validación del sistema"""
    print("\n🛡️ EJECUTANDO VALIDACIÓN DEL SISTEMA")
    print("=" * 50)
    
    try:
        # Buscar el script de validación en diferentes ubicaciones
        validate_script = BASE_DIR / "utils" / "validate_modular_system.py"
        if not validate_script.exists():
            # Probar en la raíz del proyecto
            validate_script = BASE_DIR.parent / "validate_modular_system.py"
            if not validate_script.exists():
                print(f"❌ Script de validación no encontrado")
                return False
        
        print(f"✅ Script de validación encontrado en {validate_script}")
        # Ejecutar como script en lugar de importar
        cmd = [sys.executable, str(validate_script)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Sistema validado correctamente")
            return True
        else:
            print(f"❌ La validación del sistema falló: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la validación del sistema: {e}")
        return False

async def run_quick_tests():
    """Ejecutar solo tests rápidos"""
    print("\n🚀 EJECUTANDO TESTS RÁPIDOS")
    print("=" * 60)
    
    results = []
    
    # Validación del sistema
    system_ok = run_system_validation()
    results.append(("Validación del sistema", system_ok))
    
    # Tests PyTest rápidos
    test_path = BASE_DIR / "tests" / "test_quick_backtest.py"
    if not test_path.exists():
        print(f"⚠️ Archivo {test_path} no encontrado. Ejecutando todos los tests PyTest disponibles.")
        pytest_ok = run_pytest()
    else:
        pytest_ok = run_pytest(str(test_path))
    results.append(("PyTest rápidos", pytest_ok))
    
    # Verificación básica de datos
    data_ok = run_data_verification(quick=True)
    results.append(("Verificación de datos", data_ok))
    
    # Diagnóstico básico SQLite
    sqlite_ok = run_sqlite_diagnostics(basic=True)
    results.append(("Diagnóstico SQLite", sqlite_ok))
    
    # Mostrar resumen
    print("\n📋 RESUMEN DE TESTS RÁPIDOS")
    print("=" * 30)
    
    all_ok = True
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} - {name}")
        all_ok = all_ok and ok
    
    return all_ok

async def run_all_tests():
    """Ejecutar todos los tests disponibles"""
    print("\n🔬 EJECUTANDO TODOS LOS TESTS")
    print("=" * 60)
    
    results = []
    
    # Validación del sistema
    system_ok = run_system_validation()
    results.append(("Validación del sistema", system_ok))
    
    # Tests PyTest completos
    pytest_ok = run_pytest()
    results.append(("Tests PyTest", pytest_ok))
    
    # Verificación completa de datos
    data_ok = run_data_verification(quick=False)
    results.append(("Verificación de datos", data_ok))
    
    # Diagnóstico completo SQLite
    sqlite_ok = run_sqlite_diagnostics(basic=False)
    results.append(("Diagnóstico SQLite", sqlite_ok))
    
    # Herramientas ML (solo validación)
    ml_ok = await run_ml_tools(validate_only=True)
    results.append(("Validación ML", ml_ok))
    
    # Mostrar resumen
    print("\n📋 RESUMEN DE TODOS LOS TESTS")
    print("=" * 30)
    
    all_ok = True
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} - {name}")
        all_ok = all_ok and ok
    
    if all_ok:
        print("\n✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
    else:
        print("\n⚠️ ALGUNOS TESTS FALLARON - Revisa los detalles")
    
    return all_ok

async def main():
    parser = argparse.ArgumentParser(description="Test Runner Unificado para el sistema de trading")
    parser.add_argument("--all", action="store_true", help="Ejecutar todos los tests")
    parser.add_argument("--quick", action="store_true", help="Ejecutar solo tests rápidos")
    parser.add_argument("--system", action="store_true", help="Ejecutar tests de integridad del sistema")
    parser.add_argument("--data", action="store_true", help="Ejecutar verificación de datos")
    parser.add_argument("--sqlite", action="store_true", help="Ejecutar diagnóstico de SQLite")
    parser.add_argument("--ml", action="store_true", help="Ejecutar herramientas de entrenamiento ML")
    
    args = parser.parse_args()
    
    # Si no se especifica ninguna opción, mostrar ayuda
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    start_time = time.time()
    
    # Ejecutar tests solicitados
    if args.all:
        success = await run_all_tests()
    elif args.quick:
        success = await run_quick_tests()
    else:
        results = []
        
        if args.system:
            system_ok = run_system_validation()
            results.append(("Validación del sistema", system_ok))
            
            pytest_ok = run_pytest("tests/test_system_integrity.py")
            results.append(("Tests de integridad", pytest_ok))
        
        if args.data:
            data_ok = run_data_verification(quick=False)
            results.append(("Verificación de datos", data_ok))
        
        if args.sqlite:
            sqlite_ok = run_sqlite_diagnostics(basic=False)
            results.append(("Diagnóstico SQLite", sqlite_ok))
        
        if args.ml:
            ml_ok = await run_ml_tools(validate_only=True)
            results.append(("Herramientas ML", ml_ok))
        
        # Mostrar resumen
        if results:
            print("\n📋 RESUMEN DE TESTS")
            print("=" * 30)
            
            all_ok = True
            for name, ok in results:
                status = "✅ PASS" if ok else "❌ FAIL"
                print(f"{status} - {name}")
                all_ok = all_ok and ok
            
            success = all_ok
        else:
            success = True
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️ Tiempo total: {elapsed_time:.2f} segundos")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))