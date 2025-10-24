#!/usr/bin/env python3
"""
Script de validación para prevenir cambios en archivos protegidos.
Ejecutar antes de commits importantes.

Uso: python validate_protected_files.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Lista de archivos protegidos - NO DEBEN SER MODIFICADOS
PROTECTED_FILES = [
    "descarga_datos/main.py",
    "descarga_datos/config/config_loader.py",
    "descarga_datos/config/config.yaml",
    "descarga_datos/core/ccxt_live_trading_orchestrator.py",
    "descarga_datos/core/ccxt_order_executor.py",
    "descarga_datos/core/ccxt_live_data.py",
    "descarga_datos/strategies/ultra_detailed_heikin_ashi_ml_strategy.py",
    "descarga_datos/utils/storage.py",
    "descarga_datos/utils/live_trading_tracker.py",
    "descarga_datos/utils/talib_wrapper.py",
    "descarga_datos/utils/logger.py",
    "descarga_datos/utils/logger_metrics.py",
    "descarga_datos/indicators/technical_indicators.py",
    "descarga_datos/backtesting/backtesting_orchestrator.py",
    "descarga_datos/optimizacion/strategy_optimizer.py",
]

# Archivo de checksums
CHECKSUMS_FILE = ".protected_checksums.json"


def get_file_hash(filepath):
    """Calcula hash SHA256 de un archivo."""
    import hashlib
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"❌ Error al leer {filepath}: {e}")
        return None


def load_checksums():
    """Carga checksums previos."""
    if os.path.exists(CHECKSUMS_FILE):
        try:
            with open(CHECKSUMS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_checksums(checksums):
    """Guarda checksums actuales."""
    try:
        with open(CHECKSUMS_FILE, "w") as f:
            json.dump(checksums, f, indent=2)
        print(f"✅ Checksums guardados en {CHECKSUMS_FILE}")
    except Exception as e:
        print(f"❌ Error al guardar checksums: {e}")


def validate_protected_files():
    """Valida que archivos protegidos no hayan sido modificados sin validación."""
    print("\n" + "="*80)
    print("🔒 VALIDACIÓN DE ARCHIVOS PROTEGIDOS")
    print("="*80 + "\n")
    
    old_checksums = load_checksums()
    new_checksums = {}
    
    modified_files = []
    missing_files = []
    all_ok = True
    
    for filepath in PROTECTED_FILES:
        full_path = Path(filepath)
        
        if not full_path.exists():
            missing_files.append(filepath)
            print(f"⚠️  FALTANTE: {filepath}")
            all_ok = False
            continue
        
        new_hash = get_file_hash(filepath)
        old_hash = old_checksums.get(filepath)
        
        new_checksums[filepath] = new_hash
        
        if old_hash and old_hash != new_hash:
            modified_files.append(filepath)
            print(f"🔴 MODIFICADO: {filepath}")
            all_ok = False
        else:
            print(f"✅ OK: {filepath}")
    
    print("\n" + "="*80)
    
    if all_ok and not missing_files:
        print("✅ TODOS LOS ARCHIVOS PROTEGIDOS ESTÁN VALIDADOS")
        print("="*80 + "\n")
        
        # Guardar checksums para próxima validación
        save_checksums(new_checksums)
        return True
    else:
        print("❌ VALIDACIÓN FALLIDA\n")
        
        if modified_files:
            print(f"\n🔴 {len(modified_files)} archivos modificados:")
            for f in modified_files:
                print(f"   - {f}")
        
        if missing_files:
            print(f"\n⚠️  {len(missing_files)} archivos faltantes:")
            for f in missing_files:
                print(f"   - {f}")
        
        print("\n" + "="*80)
        print("⚠️  IMPORTANTE: Los archivos protegidos fueron modificados.")
        print("⚠️  Debe ejecutar backtesting y validar antes de hacer commit:")
        print("   python descarga_datos/main.py --backtest-only")
        print("="*80 + "\n")
        
        return False


def init_checksums():
    """Inicializa checksums de los archivos protegidos."""
    print("\n" + "="*80)
    print("🔓 INICIALIZANDO CHECKSUMS DE ARCHIVOS PROTEGIDOS")
    print("="*80 + "\n")
    
    checksums = {}
    for filepath in PROTECTED_FILES:
        full_path = Path(filepath)
        if full_path.exists():
            hash_val = get_file_hash(filepath)
            checksums[filepath] = hash_val
            print(f"✅ {filepath}")
        else:
            print(f"⚠️  FALTANTE: {filepath}")
    
    save_checksums(checksums)
    print("\n" + "="*80)
    print("✅ Checksums inicializados correctamente")
    print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        init_checksums()
    else:
        success = validate_protected_files()
        sys.exit(0 if success else 1)
