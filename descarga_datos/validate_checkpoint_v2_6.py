#!/usr/bin/env python3
"""
🚨 VALIDADOR DE PUNTO DE CONTROL v2.6
Verifica que el sistema esté en el estado funcional del checkpoint
"""

import os
import sys
import json
import subprocess
import sqlite3
from pathlib import Path

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    """Mostrar header del validador"""
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("🚨 VALIDADOR DE PUNTO DE CONTROL v2.6")
    print("=" * 50)
    print("Verificando estado funcional del sistema...")
    print(f"{Colors.END}")

def check_file_exists(filepath, description):
    """Verificar que un archivo existe"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {Colors.GREEN}EXISTE{Colors.END}")
        return True
    else:
        print(f"❌ {description}: {Colors.RED}FALTANTE{Colors.END}")
        return False

def check_database_integrity():
    """Verificar integridad de la base de datos"""
    db_path = "data/data.db"
    if not os.path.exists(db_path):
        print(f"❌ Base de datos: {Colors.RED}NO EXISTE{Colors.END}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas requeridas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['historical_data', 'data_metadata']
        for table in required_tables:
            if table in tables:
                print(f"✅ Tabla {table}: {Colors.GREEN}EXISTE{Colors.END}")
            else:
                print(f"❌ Tabla {table}: {Colors.RED}FALTANTE{Colors.END}")
                conn.close()
                return False
        
        # Verificar metadata schema (9 columnas)
        cursor.execute("PRAGMA table_info(data_metadata);")
        columns = cursor.fetchall()
        if len(columns) == 9:
            print(f"✅ Schema metadata: {Colors.GREEN}9 COLUMNAS OK{Colors.END}")
        else:
            print(f"❌ Schema metadata: {Colors.RED}{len(columns)} COLUMNAS (esperadas 9){Colors.END}")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de base datos: {Colors.RED}{str(e)}{Colors.END}")
        return False

def check_config_integrity():
    """Verificar configuración"""
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        print(f"❌ Configuración: {Colors.RED}config.yaml NO EXISTE{Colors.END}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verificar símbolos
        symbols = config.get('symbols', [])
        expected_symbols = ["DOGE/USDT", "SOL/USDT", "XRP/USDT", "AVAX/USDT", "SUSHI/USDT"]
        
        if len(symbols) >= 5:
            print(f"✅ Símbolos: {Colors.GREEN}{len(symbols)} CONFIGURADOS{Colors.END}")
        else:
            print(f"⚠️ Símbolos: {Colors.YELLOW}{len(symbols)} (esperados 5+){Colors.END}")
        
        # Verificar estrategias activas
        strategies = config.get('backtesting', {}).get('strategies', {})
        active_strategies = [name for name, active in strategies.items() if active]
        
        if len(active_strategies) >= 3:
            print(f"✅ Estrategias activas: {Colors.GREEN}{len(active_strategies)}{Colors.END}")
            for strategy in active_strategies:
                print(f"   📊 {strategy}: {Colors.GREEN}ACTIVA{Colors.END}")
        else:
            print(f"⚠️ Estrategias activas: {Colors.YELLOW}{len(active_strategies)} (esperadas 3+){Colors.END}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error config: {Colors.RED}{str(e)}{Colors.END}")
        return False

def check_results_exist():
    """Verificar que existen resultados de backtesting"""
    results_dir = "data/dashboard_results"
    if not os.path.exists(results_dir):
        print(f"❌ Directorio resultados: {Colors.RED}NO EXISTE{Colors.END}")
        return False
    
    # Contar archivos JSON de resultados
    json_files = list(Path(results_dir).glob("*.json"))
    
    if len(json_files) >= 5:
        print(f"✅ Archivos resultados: {Colors.GREEN}{len(json_files)} JSON{Colors.END}")
        
        # Verificar estructura de uno de los archivos
        try:
            with open(json_files[0], 'r') as f:
                result = json.load(f)
            
            if isinstance(result, dict) and len(result) > 0:
                print(f"✅ Estructura JSON: {Colors.GREEN}VÁLIDA{Colors.END}")
                return True
            else:
                print(f"❌ Estructura JSON: {Colors.RED}INVÁLIDA{Colors.END}")
                return False
                
        except Exception as e:
            print(f"❌ Error JSON: {Colors.RED}{str(e)}{Colors.END}")
            return False
    else:
        print(f"⚠️ Archivos resultados: {Colors.YELLOW}{len(json_files)} (esperados 5+){Colors.END}")
        return False

def run_quick_tests():
    """Ejecutar tests rápidos de validación"""
    print(f"\n{Colors.BLUE}🧪 Ejecutando tests de validación...{Colors.END}")
    
    try:
        # Test de validación modular
        result = subprocess.run([
            sys.executable, "validate_modular_system.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Validación modular: {Colors.GREEN}PASÓ{Colors.END}")
        else:
            print(f"❌ Validación modular: {Colors.RED}FALLÓ{Colors.END}")
            print(f"   Error: {result.stderr}")
            return False
        
        # Test de integridad (solo verificar que pytest está disponible)
        try:
            subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                         capture_output=True, check=True)
            print(f"✅ Pytest disponible: {Colors.GREEN}OK{Colors.END}")
        except:
            print(f"⚠️ Pytest: {Colors.YELLOW}NO DISPONIBLE{Colors.END}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"❌ Tests: {Colors.RED}TIMEOUT{Colors.END}")
        return False
    except Exception as e:
        print(f"❌ Error tests: {Colors.RED}{str(e)}{Colors.END}")
        return False

def main():
    """Función principal del validador"""
    print_header()
    
    # Cambiar al directorio correcto
    if os.path.exists("descarga_datos"):
        os.chdir("descarga_datos")
        print(f"📁 Directorio: {Colors.BLUE}descarga_datos/{Colors.END}\n")
    else:
        print(f"❌ Directorio descarga_datos no encontrado")
        return False
    
    all_checks_passed = True
    
    # 1. Verificar archivos críticos
    print(f"{Colors.BOLD}1. Verificando archivos críticos:{Colors.END}")
    critical_files = [
        ("backtesting/backtesting_orchestrator.py", "Orquestador"),
        ("backtesting/backtester.py", "Motor backtest"),
        ("main.py", "Punto entrada"),
        ("dashboard.py", "Dashboard"),
        ("utils/storage.py", "Storage"),
        ("config/config.yaml", "Configuración"),
        ("tests/test_system_integrity.py", "Tests integridad")
    ]
    
    for filepath, description in critical_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # 2. Verificar base de datos
    print(f"\n{Colors.BOLD}2. Verificando base de datos:{Colors.END}")
    if not check_database_integrity():
        all_checks_passed = False
    
    # 3. Verificar configuración
    print(f"\n{Colors.BOLD}3. Verificando configuración:{Colors.END}")
    if not check_config_integrity():
        all_checks_passed = False
    
    # 4. Verificar resultados
    print(f"\n{Colors.BOLD}4. Verificando resultados:{Colors.END}")
    if not check_results_exist():
        all_checks_passed = False
    
    # 5. Ejecutar tests rápidos
    print(f"\n{Colors.BOLD}5. Tests de validación:{Colors.END}")
    if not run_quick_tests():
        all_checks_passed = False
    
    # Resultado final
    print(f"\n{Colors.BOLD}{'='*50}{Colors.END}")
    if all_checks_passed:
        print(f"🎉 {Colors.GREEN}{Colors.BOLD}SISTEMA EN ESTADO FUNCIONAL v2.6{Colors.END}")
        print(f"✅ {Colors.GREEN}Todos los checks pasaron correctamente{Colors.END}")
        print(f"🚀 {Colors.BLUE}Sistema listo para usar o desarrollar{Colors.END}")
    else:
        print(f"🚨 {Colors.RED}{Colors.BOLD}SISTEMA NO ESTÁ EN ESTADO FUNCIONAL{Colors.END}")
        print(f"❌ {Colors.RED}Algunos checks fallaron{Colors.END}")
        print(f"🔄 {Colors.YELLOW}Ejecutar: git checkout version-2.6{Colors.END}")
        
    print(f"\n📋 {Colors.BLUE}Ver detalles completos en: CHECKPOINT_v2_6_FUNCIONAL.md{Colors.END}")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)