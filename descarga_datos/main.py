#!/usr/bin/env python3
"""
Bot Trader Copilot - Punto de entrada principal
Orquestador central con validación automática antes de ejecutar backtest y dashboard
"""
import argparse
import asyncio
import os
import sys
import subprocess
import json
from pathlib import Path

# Importar constantes específicas de subprocess para compatibilidad
try:
    CREATE_NEW_CONSOLE = subprocess.CREATE_NEW_CONSOLE
except AttributeError:
    CREATE_NEW_CONSOLE = None  # No disponible en sistemas no-Windows

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger
from backtesting.backtesting_orchestrator import run_full_backtesting_with_batches

def validate_system():
    """
    Validación automática del sistema antes de ejecutar operaciones
    """
    print(" VALIDACIÓN AUTOMÁTICA DEL SISTEMA")
    print("=" * 50)

    try:
        # 1. Verificar configuración
        print(" Verificando configuración...")
        config = load_config_from_yaml()
        print(" Configuración cargada correctamente")

        # 2. Verificar estrategias activas
        from backtesting.backtesting_orchestrator import load_strategies_from_config
        strategies = load_strategies_from_config(config)
        if not strategies:
            print(" No hay estrategias activas configuradas")
            return False
        print(f" {len(strategies)} estrategias activas: {list(strategies.keys())}")

        # 3. Verificar entorno virtual y dependencias (importaciones seguras)
        print(" Verificando entorno Python...")
        try:
            import pandas
            import ccxt
            print(" Dependencias principales instaladas")
            # Verificar wrapper de indicadores técnicos
            try:
                from utils.talib_wrapper import talib
                print(" Wrapper de indicadores técnicos disponible")
            except ImportError:
                print("  Wrapper de indicadores no disponible - usando implementaciones básicas")
        except ImportError as e:
            print(f" Dependencia faltante: {e}")
            return False

        # 4. Verificar datos existentes
        print(" Verificando datos históricos...")
        data_dir = Path(__file__).parent / "data" / "dashboard_results"
        if not data_dir.exists():
            print("  No existe directorio de datos - se crearán en el backtest")
        else:
            result_files = list(data_dir.glob("*_results.json"))
            real_files = [f for f in result_files if 'realistic' not in f.name and f.name != 'global_summary.json']
            if real_files:
                print(f" {len(real_files)} archivos de resultados encontrados")
            else:
                print("  No hay resultados previos - se generarán nuevos")

        print(" VALIDACIÓN COMPLETADA - Sistema operativo")
        return True

    except Exception as e:
        print(f" ERROR EN VALIDACIÓN: {e}")
        return False

def run_live_mt5():
    """
    Ejecutar trading en vivo con MT5 (forex/acciones)
    """
    print("\n🔴 EJECUTANDO LIVE TRADING - MT5 (FOREX/ACCIONES)")
    print("=" * 50)

    # Verificar configuración de seguridad
    config = load_config_from_yaml()
    if config.live_trading.enabled:
        print(" ⚠️  ADVERTENCIA: Live trading está HABILITADO en configuración")
        if config.live_trading.account_type == "REAL":
            print(" 🚨 PELIGRO: Cuenta configurada como REAL - Operaciones con DINERO REAL")
            print(" Para pruebas seguras, cambiar account_type a 'DEMO' en config.yaml")
            return False
        else:
            print(" ✅ Cuenta configurada como DEMO - Modo seguro para pruebas")
    else:
        print(" ✅ Live trading DESHABILITADO - Modo seguro")

    try:
        from core.live_trading_orchestrator import run_live_trading
        print(" 🚀 Iniciando simulación de live trading MT5...")
        print(" 💡 Presione Ctrl+C para detener la simulación")

        # Para pruebas, limitar a 30 segundos en lugar de ejecución indefinida
        run_live_trading(duration_minutes=0.5)  # 30 segundos
        print(" Live trading MT5 simulado completado")
        return True
    except Exception as e:
        print(f" Error en live trading MT5: {e}")
        return False

def run_live_ccxt():
    """
    Ejecutar trading en vivo con CCXT (criptomonedas)
    """
    print("\n🟡 EJECUTANDO LIVE TRADING - CCXT (CRIPTOMONEDAS)")
    print("=" * 50)

    # Verificar configuración de seguridad
    config = load_config_from_yaml()
    if config.live_trading.enabled:
        print(" ⚠️  ADVERTENCIA: Live trading está HABILITADO en configuración")
        if config.live_trading.account_type == "REAL":
            print(" 🚨 PELIGRO: Cuenta configurada como REAL - Operaciones con DINERO REAL")
            print(" Para pruebas seguras, cambiar account_type a 'DEMO' en config.yaml")
            return False
        else:
            print(" ✅ Cuenta configurada como DEMO - Modo seguro para pruebas")
    else:
        print(" ✅ Live trading DESHABILITADO - Modo seguro")

    try:
        from core.ccxt_live_trading_orchestrator import run_crypto_live_trading
        print(" 🚀 Iniciando simulación de live trading CCXT...")
        print(" 💡 Presione Ctrl+C para detener la simulación")

        # Para pruebas, ejecutar con timeout de seguridad
        import threading
        import time

        result = [None]
        exception = [None]

        def run_with_timeout():
            try:
                run_crypto_live_trading()
                result[0] = True
            except Exception as e:
                exception[0] = e
                result[0] = False

        thread = threading.Thread(target=run_with_timeout, daemon=True)
        thread.start()

        # Esperar máximo 30 segundos
        try:
            thread.join(timeout=30)
        except KeyboardInterrupt:
            print(" ⏹️  Simulación interrumpida por usuario")
            return True

        if thread.is_alive():
            print(" ⏰ Timeout de seguridad alcanzado (30s) - Deteniendo simulación")
            return True
        elif exception[0]:
            print(f" Error en simulación: {exception[0]}")
            return False
        else:
            print(" Live trading CCXT simulado completado")
            return True

    except Exception as e:
        print(f" Error en live trading CCXT: {e}")
        return False

def run_backtest():
    """
    Ejecutar backtesting completo con datos reales
    """
    print("\n🚀 EJECUTANDO BACKTESTING COMPLETO")
    print("=" * 50)

    try:
        asyncio.run(run_full_backtesting_with_batches())
        print(" Backtesting completado exitosamente")
        return True
    except Exception as e:
        print(f" Error en backtesting: {e}")
        return False

def launch_dashboard(wait_for_completion=False):
    """
    Lanzar dashboard de visualización
    Args:
        wait_for_completion: Si True, espera a que el dashboard termine (modo --dashboard-only)
                           Si False, lanza en background y continúa (modo automático)
    """
    print("\n📊 LANZANDO DASHBOARD")
    print("=" * 30)

    try:
        dashboard_path = os.path.join(current_dir, "utils", "dashboard.py")
        cmd = [sys.executable, "-m", "streamlit", "run", dashboard_path, "--server.port", "8519"]

        print(" Dashboard disponible en: http://localhost:8519")
        print(" Presiona Ctrl+C para detener el dashboard")

        if wait_for_completion:
            # Modo dashboard-only: esperar a que termine
            subprocess.run(cmd, cwd=current_dir)
        else:
            # Modo automático: lanzar en background independiente
            if os.name == 'nt' and CREATE_NEW_CONSOLE is not None:  # Windows
                # En Windows, usar CREATE_NEW_CONSOLE para que sobreviva al proceso padre
                process = subprocess.Popen(
                    cmd,
                    cwd=current_dir,
                    creationflags=CREATE_NEW_CONSOLE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # En Unix/Linux/Mac, usar nohup o similar
                process = subprocess.Popen(
                    cmd,
                    cwd=current_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )

            print(" Dashboard ejecutándose en background...")
            print(" El programa principal ha terminado. El dashboard permanece activo.")

    except KeyboardInterrupt:
        print("\n⏹️  Dashboard detenido por usuario")
    except Exception as e:
        print(f" Error lanzando dashboard: {e}")

def main():
    """
    Punto de entrada principal del sistema
    """
    print(" BOT TRADER COPILOT - Sistema Modular de Trading")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Sistema de Backtesting y Live Trading")
    parser.add_argument("--mode", choices=["backtest", "live_mt5", "live_ccxt"],
                       default="backtest", help="Modo de ejecución")
    parser.add_argument("--backtest-only", action="store_true", help="Solo ejecutar backtesting")
    parser.add_argument("--dashboard-only", action="store_true", help="Solo lanzar dashboard")
    parser.add_argument("--live-mt5", action="store_true", help="Ejecutar live trading con MT5")
    parser.add_argument("--live-ccxt", action="store_true", help="Ejecutar live trading con CCXT")
    parser.add_argument("--test-live-mt5", action="store_true", help="Probar live trading MT5 (modo seguro, 30s)")
    parser.add_argument("--test-live-ccxt", action="store_true", help="Probar live trading CCXT (modo seguro, 30s)")
    parser.add_argument("--skip-validation", action="store_true", help="Omitir validación automática")

    args = parser.parse_args()

    # Determinar modo basado en argumentos
    if args.test_live_mt5:
        mode = "test_live_mt5"
    elif args.test_live_ccxt:
        mode = "test_live_ccxt"
    elif args.live_mt5 or args.mode == "live_mt5":
        mode = "live_mt5"
    elif args.live_ccxt or args.mode == "live_ccxt":
        mode = "live_ccxt"
    else:
        mode = "backtest"

    print(f" MODO SELECCIONADO: {mode.upper()}")

    # 1. VALIDACIÓN AUTOMÁTICA (a menos que se omita)
    if not args.skip_validation:
        if not validate_system():
            print("\n❌ VALIDACIÓN FALLIDA - Abortando ejecución")
            sys.exit(1)
    else:
        print("  VALIDACIÓN OMITIDA")

    # 2. EJECUTAR OPERACIONES SEGÚN MODO
    if mode == "test_live_mt5":
        # Prueba segura de live trading MT5
        print("\n🧪 MODO DE PRUEBA: Simulación segura de live trading MT5")
        success = run_live_mt5()
        if success:
            print("\n✅ PRUEBA MT5 COMPLETADA EXITOSAMENTE")
        else:
            print("\n❌ PRUEBA MT5 FALLÓ")
            sys.exit(1)

    elif mode == "test_live_ccxt":
        # Prueba segura de live trading CCXT
        print("\n🧪 MODO DE PRUEBA: Simulación segura de live trading CCXT")
        success = run_live_ccxt()
        if success:
            print("\n✅ PRUEBA CCXT COMPLETADA EXITOSAMENTE")
        else:
            print("\n❌ PRUEBA CCXT FALLÓ")
            sys.exit(1)

    elif mode == "live_mt5":
        # Live trading con MT5
        success = run_live_mt5()
        if not success:
            print("\n❌ LIVE TRADING MT5 FALLÓ")
            sys.exit(1)

    elif mode == "live_ccxt":
        # Live trading con CCXT
        success = run_live_ccxt()
        if not success:
            print("\n❌ LIVE TRADING CCXT FALLÓ")
            sys.exit(1)

    else:  # backtest
        if args.dashboard_only:
            # Solo dashboard
            launch_dashboard(wait_for_completion=True)
        elif args.backtest_only:
            # Solo backtesting
            success = run_backtest()
            if success:
                print("\n✅ BACKTESTING COMPLETADO")
                print("💡 Para ver resultados, ejecuta: python main.py --dashboard-only")
            else:
                print("\n❌ BACKTESTING FALLÓ")
                sys.exit(1)
        else:
            # Flujo completo: backtest + dashboard
            success = run_backtest()
            if success:
                print("\n✅ SISTEMA COMPLETO EJECUTADO EXITOSAMENTE")
                launch_dashboard(wait_for_completion=False)
            else:
                print("\n❌ BACKTESTING FALLÓ - No se lanza dashboard")
                sys.exit(1)

if __name__ == "__main__":
    main()
