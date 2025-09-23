#!/usr/bin/env python3
"""
Bot Trader Copilot - Orquestador de Backtesting y Dashboard
Este script orquesta la ejecución masiva de backtests y lanza el dashboard.
"""
import argparse
import asyncio
import os
import sys
import subprocess

from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger
from run_backtesting_batches import run_full_backtesting_with_batches

def main():
    parser = argparse.ArgumentParser(
        description="Orquestador: Backtesting masivo y Dashboard"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="No lanzar dashboard después del backtest"
    )
    parser.add_argument(
        "--dashboard-only", action="store_true",
        help="Solo lanzar dashboard sin backtesting"
    )
    args = parser.parse_args()

    # Cargar configuración y preparar logging
    config = load_config_from_yaml()
    setup_logging(config.system.log_level, config.system.log_file)
    logger = get_logger(__name__)

    # Si se pide solo el dashboard
    if args.dashboard_only:
        launch_dashboard(logger)
        return

    # Ejecutar backtesting masivo por lotes
    logger.info("🚀 Iniciando backtesting masivo con lotes...")
    asyncio.run(run_full_backtesting_with_batches())

    # Lanzar dashboard si no se deshabilitó
    if not args.no_dashboard and getattr(config.system, "auto_launch_dashboard", False):
        launch_dashboard(logger)

def launch_dashboard(logger):
    """Lanza el dashboard de Streamlit basado en dashboard.py"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, "dashboard.py")
    logger.info(f"📊 Lanzando dashboard: {dashboard_path}")
    # Iniciar Streamlit en segundo plano sin bloquear
    proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", dashboard_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Intentar abrir el dashboard en el navegador predeterminado
    try:
        import webbrowser
        webbrowser.open("http://localhost:8501")
    except Exception as e:
        logger.warning(f"No se pudo abrir el navegador automáticamente: {e}")

if __name__ == "__main__":
    main()