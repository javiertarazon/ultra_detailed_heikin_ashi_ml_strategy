#!/usr/bin/env python3
"""
🚀 Bot Trader Copilot - Script de Inicio Rápido
===============================================

Este script facilita la configuración inicial y ejecución del sistema.

Uso:
    python quick_start.py

Opciones:
    --setup     : Configurar el entorno por primera vez
    --test      : Ejecutar tests básicos
    --demo      : Ejecutar demo con datos de ejemplo
    --help      : Mostrar esta ayuda
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

class QuickStart:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.required_files = [
            "requirements.txt",
            "config/config.example.yaml",
            "README.md"
        ]

    def check_requirements(self):
        """Verificar que todos los archivos necesarios estén presentes"""
        print("🔍 Verificando archivos del proyecto...")

        missing_files = []
        for file in self.required_files:
            if not (self.project_root / file).exists():
                missing_files.append(file)

        if missing_files:
            print(f"❌ Archivos faltantes: {missing_files}")
            return False

        print("✅ Todos los archivos necesarios están presentes")
        return True

    def setup_environment(self):
        """Configurar el entorno virtual y dependencias"""
        print("🔧 Configurando entorno...")

        # Crear entorno virtual
        if not Path("trading_bot_env").exists():
            print("📦 Creando entorno virtual...")
            subprocess.run([sys.executable, "-m", "venv", "trading_bot_env"], check=True)

        # Activar entorno virtual
        if os.name == 'nt':  # Windows
            activate_script = self.project_root / "trading_bot_env" / "Scripts" / "activate.bat"
            python_exe = self.project_root / "trading_bot_env" / "Scripts" / "python.exe"
        else:  # Unix/Linux
            activate_script = self.project_root / "trading_bot_env" / "bin" / "activate"
            python_exe = self.project_root / "trading_bot_env" / "bin" / "python"

        # Instalar dependencias
        print("📥 Instalando dependencias...")
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(python_exe), "-m", "pip", "install", "-r", "requirements.txt"], check=True)

        print("✅ Entorno configurado exitosamente")

    def setup_config(self):
        """Configurar archivo de configuración básico"""
        print("⚙️ Configurando archivo de configuración...")

        config_dir = self.project_root / "config"
        config_dir.mkdir(exist_ok=True)

        example_config = config_dir / "config.example.yaml"
        user_config = config_dir / "config.yaml"

        if not user_config.exists():
            print("📋 Creando archivo de configuración básico...")
            # Aquí iría la lógica para crear un config básico
            print("⚠️  Recuerda configurar tus API keys en config/config.yaml")
        else:
            print("✅ Archivo de configuración ya existe")

    def run_tests(self):
        """Ejecutar tests básicos"""
        print("🧪 Ejecutando tests...")

        try:
            # Verificar imports básicos
            subprocess.run([sys.executable, "-c", "import pandas, numpy, ccxt; print('✅ Imports básicos OK')"], check=True)

            # Verificar TA-Lib
            try:
                subprocess.run([sys.executable, "-c", "import talib; print('✅ TA-Lib OK')"], check=True)
            except subprocess.CalledProcessError:
                print("⚠️  TA-Lib no disponible (opcional)")

            # Verificar MT5
            try:
                subprocess.run([sys.executable, "-c", "import MetaTrader5 as mt5; print(f'✅ MT5 v{mt5.__version__} OK')"], check=True)
            except subprocess.CalledProcessError:
                print("⚠️  MT5 no disponible (opcional para acciones)")

            print("✅ Tests básicos completados")

        except subprocess.CalledProcessError as e:
            print(f"❌ Error en tests: {e}")
            return False

        return True

    def run_demo(self):
        """Ejecutar demo con datos de ejemplo"""
        print("🎯 Ejecutando demo...")

        # Aquí iría la lógica para ejecutar una demo
        print("⚠️  Demo no implementada aún")
        print("💡 Ejecuta: python descarga_datos/main.py")

    def show_help(self):
        """Mostrar ayuda"""
        print(__doc__)

def main():
    parser = argparse.ArgumentParser(description="Bot Trader Copilot - Inicio Rápido")
    parser.add_argument("--setup", action="store_true", help="Configurar entorno")
    parser.add_argument("--test", action="store_true", help="Ejecutar tests")
    parser.add_argument("--demo", action="store_true", help="Ejecutar demo")

    args = parser.parse_args()

    quickstart = QuickStart()

    # Verificar requisitos básicos
    if not quickstart.check_requirements():
        print("❌ Requisitos no cumplidos. Verifica la instalación.")
        sys.exit(1)

    # Ejecutar acciones según argumentos
    if args.setup:
        quickstart.setup_environment()
        quickstart.setup_config()
    elif args.test:
        quickstart.run_tests()
    elif args.demo:
        quickstart.run_demo()
    else:
        quickstart.show_help()

if __name__ == "__main__":
    main()
