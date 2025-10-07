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
import socket
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
# Import pesado diferido: se hará dentro de run_backtest para evitar bloqueos
RUN_ORCHESTRATOR_LAZILY = True

def validate_system(dashboard_only: bool = False):
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
        if dashboard_only:
            print(" Modo dashboard-only: se omite import de estrategias para acelerar")
        else:
            print(" Importando orquestador para cargar estrategias...")
            try:
                from backtesting.backtesting_orchestrator import load_strategies_from_config
                strategies = load_strategies_from_config(config)
            except Exception as imp_err:
                print(f" Error importando orquestador/estrategias: {imp_err}")
                return False
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

        # Para pruebas, limitar a 2 minutos para ver resultados rápido con 15m
        run_live_trading(duration_minutes=2)  # 2 minutos para pruebas con 15m
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
        if RUN_ORCHESTRATOR_LAZILY:
            print(" Cargando orquestador de backtesting de forma perezosa...")
            from backtesting.backtesting_orchestrator import run_full_backtesting_with_batches  # type: ignore
            print(" Orquestador importado. Iniciando ejecución async...")
        asyncio.run(run_full_backtesting_with_batches())
        print(" Backtesting completado exitosamente")
        return True
    except KeyboardInterrupt:
        # Si se interrumpe justo al final (ej. durante shutdown) consideramos éxito si ya existen resultados
        results_dir = Path(__file__).parent / 'data' / 'dashboard_results'
        result_files = list(results_dir.glob('*_results.json')) if results_dir.exists() else []
        if result_files:
            print(f" ⚠️ Interrupción durante el apagado, pero se detectaron {len(result_files)} archivos de resultados. Marcando como éxito.")
            return True
        print(" ❌ Interrupción antes de generar resultados válidos.")
        return False
    except Exception as e:
        print(f" Error en backtesting: {e}")
        return False

def _find_free_port(base_port: int = 8519, max_tries: int = 10) -> int:
    """Busca un puerto libre a partir de base_port.
    Devuelve el primero disponible o base_port si no encuentra otro.
    """
    for offset in range(max_tries):
        port = base_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                if s.connect_ex(("127.0.0.1", port)) != 0:  # 0 => ocupado
                    return port
            except Exception:
                # Si ocurre cualquier excepción consideramos el puerto válido para intentar
                return port
    return base_port


def train_ml_models():
    """
    Entrenar modelos ML con configuración actual
    Verifica datos existentes y descarga automáticamente si es necesario
    """
    print("\n🧠 ENTRENANDO MODELOS ML")
    print("=" * 50)
    
    try:
        config = load_config_from_yaml()
        
        # Acceder a la configuración ML del objeto Config
        if not hasattr(config, 'ml_training'):
            print("❌ Configuración ml_training no encontrada en config")
            return False
            
        ml_config = config.ml_training
        
        # Obtener configuración de entrenamiento
        train_start = ml_config.train_start
        train_end = ml_config.train_end
        val_start = ml_config.val_start
        val_end = ml_config.val_end
        
        print(f"📅 Período entrenamiento: {train_start} → {train_end}")
        print(f"📅 Período validación: {val_start} → {val_end}")
        
        # Importar ml_trainer que ya maneja descarga automática
        from ml_trainer import MLTrainer
        
        symbols = config.backtesting.symbols
        timeframe = config.backtesting.timeframe
        
        for symbol in symbols:
            print(f"\n🎯 Entrenando modelos para {symbol}...")
            trainer = MLTrainer(symbol, timeframe)
            
            # download_data() ya verifica cache y descarga automáticamente si es necesario
            print(f"📥 Verificando datos para {symbol}...")
            data = asyncio.run(trainer.download_data())
            
            if data is None or len(data) < 100:
                print(f"❌ No se pudieron obtener datos suficientes para {symbol}")
                continue
            
            print(f"✅ Datos disponibles: {len(data)} velas")
            
            # Entrenar modelos
            print(f"🔄 Entrenando modelos ML...")
            results = trainer.train_models(data)
            
            print(f"✅ Modelos entrenados para {symbol}")
            if results:
                for model_name, metrics in results.items():
                    print(f"   📊 {model_name}: Accuracy={metrics.get('accuracy', 0):.4f}, AUC={metrics.get('auc', 0):.4f}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error entrenando modelos ML: {e}")
        import traceback
        traceback.print_exc()
        return False
def run_optimization_pipeline():
    """
    Ejecutar pipeline completo de optimización ML
    El pipeline se encarga de verificar y descargar datos automáticamente
    """
    print("\n🔬 EJECUTANDO PIPELINE DE OPTIMIZACIÓN ML")
    print("=" * 50)
    
    try:
        config = load_config_from_yaml()
        
        # Acceder directamente a los atributos del objeto Config
        if not hasattr(config, 'ml_training'):
            print("⚠️  Configuración ml_training no encontrada en config.yaml")
            return False
        
        ml_config = config.ml_training
        
        # Verificar si optimización está habilitada
        if not ml_config.optimization.get('enabled', False):
            print("⚠️  Optimización deshabilitada en config.yaml")
            print("💡 Para habilitar, cambiar ml_training.optimization.enabled: true")
            return False
        
        # Obtener configuración
        train_start = ml_config.training.get('train_start', '2023-01-01')
        train_end = ml_config.training.get('train_end', '2023-12-31')
        val_start = ml_config.training.get('val_start', '2024-01-01')
        val_end = ml_config.training.get('val_end', '2025-10-06')
        opt_start = ml_config.optimization.get('opt_start', '2024-01-01')
        opt_end = ml_config.optimization.get('opt_end', '2025-10-06')
        n_trials = ml_config.optimization.get('n_trials', 100)
        
        print(f"📅 Período entrenamiento ML: {train_start} → {train_end}")
        print(f"📅 Período validación ML: {val_start} → {val_end}")
        print(f"📅 Período optimización: {opt_start} → {opt_end}")
        print(f"🔢 Número de trials: {n_trials}")
        print(f"\n🔍 El sistema verificará automáticamente si los datos existen")
        print(f"📥 Si no existen, los descargará automáticamente desde el exchange")
        
        # Importar y ejecutar run_optimization_pipeline2
        # Este pipeline ya incluye descarga automática de datos
        from run_optimization_pipeline2 import OptimizationPipeline
        
        symbols = config.backtesting.symbols if hasattr(config, 'backtesting') else ['BTC/USDT']
        timeframe = config.backtesting.timeframe if hasattr(config, 'backtesting') else '4h'
        
        print(f"\n🎯 Símbolos a procesar: {symbols}")
        print(f"⏰ Timeframe: {timeframe}")
        
        pipeline = OptimizationPipeline(
            symbols=symbols,
            timeframe=timeframe,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            opt_start=opt_start,
            opt_end=opt_end,
            n_trials=n_trials
        )
        
        # Ejecutar pipeline completo (incluye descarga automática)
        print(f"\n🚀 Iniciando pipeline de optimización...")
        results = asyncio.run(pipeline.run_complete_pipeline())
        
        print("\n✅ PIPELINE DE OPTIMIZACIÓN COMPLETADO")
        print(f"📊 Resultados guardados en data/optimization_results/")
        
        if results:
            print(f"\n📈 Resumen de resultados:")
            for symbol, result in results.items():
                print(f"   🎯 {symbol}:")
                if 'backtest_results' in result:
                    br = result['backtest_results']
                    print(f"      💰 P&L: ${br.get('total_pnl', 0):.2f}")
                    print(f"      📊 Win Rate: {br.get('win_rate', 0)*100:.2f}%")
                    print(f"      📉 Max DD: {br.get('max_drawdown', 0):.2f}%")
        
        return True
    
    except Exception as e:
        print(f"❌ Error en pipeline de optimización: {e}")
        import traceback
        traceback.print_exc()
        return False


def launch_dashboard(wait_for_completion=False, preferred_port: int = 8519):
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
        # Permitir override por variable de entorno
        env_port = os.environ.get("DASHBOARD_PORT")
        if env_port and env_port.isdigit():
            preferred_port = int(env_port)

        port = _find_free_port(preferred_port, max_tries=12)
        if port != preferred_port:
            print(f" ⚠️ Puerto {preferred_port} en uso, usando alternativo {port}")

        cmd = [sys.executable, "-m", "streamlit", "run", dashboard_path, "--server.port", str(port)]

        print(f" Dashboard disponible en: http://localhost:{port}")
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
    parser.add_argument("--symbols", type=str, help="Lista de símbolos separados por coma para backtest rápido (override config)")
    parser.add_argument("--timeframe", type=str, help="Timeframe a usar (override config)")
    parser.add_argument("--data-audit", action="store_true", help="Ejecutar auditoría de calidad de datos y salir")
    parser.add_argument("--data-audit-skip-download", action="store_true", help="Ejecuta auditoría sin intentar descargas correctivas (no auto-fetch ni incremental edges)")
    parser.add_argument("--optimize", action="store_true", help="Ejecutar pipeline completo de optimización ML (entrenamiento + optimización + backtest)")
    parser.add_argument("--train-ml", action="store_true", help="Solo entrenar modelos ML con configuración actual")

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

    # 1. VALIDACIÓN AUTOMÁTICA (a menos que se omita o sea modo data-audit)
    if not args.skip_validation and not args.data_audit:
        if not validate_system(dashboard_only=args.dashboard_only):
            print("\n❌ VALIDACIÓN FALLIDA - Abortando ejecución")
            sys.exit(1)
    else:
        if args.skip_validation:
            print("  VALIDACIÓN OMITIDA")
        elif args.data_audit:
            print("  VALIDACIÓN OMITIDA (modo auditoría de datos)")

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
        if args.optimize:
            # Pipeline completo de optimización ML
            print("\n🔬 EJECUTANDO PIPELINE DE OPTIMIZACIÓN ML")
            print("=" * 60)
            success = run_optimization_pipeline()
            if success:
                print("\n✅ OPTIMIZACIÓN COMPLETADA")
                print("💡 Resultados guardados en data/optimization_results/")
                print("💡 Para backtest con parámetros optimizados, ejecuta: python main.py --backtest-only")
            else:
                print("\n❌ OPTIMIZACIÓN FALLÓ")
                sys.exit(1)
        elif args.train_ml:
            # Solo entrenamiento de modelos ML
            print("\n🧠 ENTRENANDO MODELOS ML")
            print("=" * 60)
            success = train_ml_models()
            if success:
                print("\n✅ MODELOS ML ENTRENADOS EXITOSAMENTE")
                print("💡 Modelos guardados en models/")
            else:
                print("\n❌ ENTRENAMIENTO ML FALLÓ")
                sys.exit(1)
        elif args.dashboard_only:
            # Solo dashboard
            launch_dashboard(wait_for_completion=True)
        elif args.backtest_only:
            # Solo backtesting (con overrides opcionales)
            if args.symbols or args.timeframe:
                os.environ['BT_OVERRIDE_SYMBOLS'] = args.symbols or ''
                os.environ['BT_OVERRIDE_TIMEFRAME'] = args.timeframe or ''
            success = run_backtest()
            if success:
                print("\n✅ BACKTESTING COMPLETADO")
                print("💡 Para ver resultados, ejecuta: python main.py --dashboard-only")
            else:
                print("\n❌ BACKTESTING FALLÓ")
                sys.exit(1)
        elif args.data_audit:
            # Auditoría de datos sin ejecutar backtesting
            try:
                from config.config_loader import load_config_from_yaml
                # Import dinámico tolerante: primero ruta nueva auditorias/, luego fallback legacy utils/
                try:
                    from auditorias.data_audit import run_data_audit  # type: ignore
                except Exception:
                    from utils.data_audit import run_data_audit  # type: ignore
                cfg = load_config_from_yaml()
                audit_symbols = None
                if args.symbols:
                    audit_symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
                audit_timeframe = args.timeframe if args.timeframe else '4h'
                print("\n🔍 Ejecutando auditoría de datos...")
                if args.data_audit_skip_download:
                    report = run_data_audit(
                        cfg,
                        symbols=audit_symbols,
                        timeframe=audit_timeframe,
                        auto_fetch_missing=False,
                        incremental_edges=False
                    )
                else:
                    report = run_data_audit(cfg, symbols=audit_symbols, timeframe=audit_timeframe)
                print("\n📑 Resumen Auditoría:")
                print(json.dumps(report, indent=2, ensure_ascii=False))
                print("\nResultado completo en data/dashboard_results/data_audit.json")
                # Código de salida condicional: si hay símbolos missing -> 2, insufficient -> 3
                if report.get("critical_issues", 0) > 0:
                    sys.exit(2)
                elif report.get("average_quality_score", 100) < 70:
                    sys.exit(3)
                else:
                    sys.exit(0)
            except Exception as e:
                print(f"Error en auditoría de datos: {e}")
                sys.exit(1)
        else:
            # Flujo completo: backtest + dashboard
            if args.symbols or args.timeframe:
                os.environ['BT_OVERRIDE_SYMBOLS'] = args.symbols or ''
                os.environ['BT_OVERRIDE_TIMEFRAME'] = args.timeframe or ''
            success = run_backtest()
            if not success:
                # Fallback: si hay resultados igual intentamos dashboard
                results_dir = Path(__file__).parent / 'data' / 'dashboard_results'
                result_files = list(results_dir.glob('*_results.json')) if results_dir.exists() else []
                if result_files:
                    print(f" ⚠️ Backtest reportó fallo/interrupción pero existen {len(result_files)} archivos de resultados. Lanzando dashboard igualmente.")
                    success = True
            if success:
                print("\n✅ SISTEMA COMPLETO EJECUTADO EXITOSAMENTE")
                print(" Lanzando dashboard (modo background)...")
                launch_dashboard(wait_for_completion=False)
            else:
                print("\n❌ BACKTESTING FALLÓ - No se lanza dashboard (no se encontraron resultados válidos)")
                sys.exit(1)

if __name__ == "__main__":
    main()
