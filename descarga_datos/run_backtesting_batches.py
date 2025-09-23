#!/usr/bin/env python3
"""
Backtesting completo con descargas por lotes - Datos históricos completos
"""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config_from_yaml
from core.downloader import AdvancedDataDownloader
#from strategies.ut_bot_psar import UTBotPSARStrategy  # No utilizado actualmente
#from strategies.ut_bot_psar_conservative import UTBotPSARConservativeStrategy  # Eliminado módulo faltante
from strategies.ut_bot_psar import UTBotPSARStrategy
from strategies.ut_bot_psar_compensation import UTBotPSARCompensationStrategy
from strategies.solana_4h_strategy import Solana4HStrategy
from strategies.solana_4h_trailing_strategy import Solana4HTrailingStrategy
from backtesting.backtester import AdvancedBacktester
from utils.logger import setup_logging, get_logger

def load_strategies_from_config(config):
    """
    Carga dinámicamente las estrategias activas desde la configuración.
    Retorna un diccionario con las estrategias instanciadas.
    """
    strategies = {}
    strategy_config = config.backtesting.strategies

    # Mapeo de nombres de configuración a clases de estrategia
    strategy_classes = {
        'Estrategia_Basica': ('strategies.ut_bot_psar', 'UTBotPSARStrategy'),
        'Estrategia_Compensacion': ('strategies.ut_bot_psar_compensation', 'UTBotPSARCompensationStrategy'),
        'Solana4H': ('strategies.solana_4h_strategy', 'Solana4HStrategy'),
        'Solana4HTrailing': ('strategies.solana_4h_trailing_strategy', 'Solana4HTrailingStrategy'),
    }

    print(f"[DEBUG] Configuración de estrategias: {strategy_config}")

    for strategy_name, is_active in strategy_config.items():
        if is_active and strategy_name in strategy_classes:
            try:
                module_name, class_name = strategy_classes[strategy_name]
                module = __import__(module_name, fromlist=[class_name])
                strategy_class = getattr(module, class_name)
                strategies[strategy_name] = strategy_class()
                print(f"[DEBUG] ✅ {strategy_name} cargada exitosamente")
            except Exception as e:
                print(f"[DEBUG] ❌ Error cargando {strategy_name}: {e}")
                continue
        elif is_active:
            print(f"[DEBUG] ⚠️  Estrategia '{strategy_name}' configurada pero no implementada")

    print(f"[DEBUG] Estrategias activas finales: {list(strategies.keys())}")
    return strategies

async def run_full_backtesting_with_batches():
    print("[BACKTEST] 🚀 BACKTESTING COMPLETO CON DESCARGAS POR LOTES")
    print("=" * 70)

    try:
        # Cargar configuración
        config = load_config_from_yaml()
        print(f"[BACKTEST] ✅ Config cargada: {config.backtesting.start_date} a {config.backtesting.end_date}")
        print(f"[BACKTEST] 📊 Timeframe: {config.backtesting.timeframe}")
        print(f"[BACKTEST] 🎯 Símbolos: {config.backtesting.symbols}")

        # Calcular estadísticas del período
        from datetime import datetime
        start = datetime.strptime(config.backtesting.start_date, "%Y-%m-%d")
        end = datetime.strptime(config.backtesting.end_date, "%Y-%m-%d")
        days = (end - start).days
        expected_velas = days * 6  # 6 velas/día en 4h

        print(f"[BACKTEST] 📅 Período: {days} días (~{expected_velas:,} velas esperadas)")

        # Configurar logging
        setup_logging(config.system.log_level, config.system.log_file)
        logger = get_logger(__name__)

        # Inicializar downloader
        downloader = AdvancedDataDownloader(config)
        success = await downloader.initialize()
        if not success:
            print("[BACKTEST] ❌ Error inicializando downloader")
            return

        print("[BACKTEST] ✅ Downloader inicializado (con soporte para lotes)")

        # Descargar datos con lotes
        active_symbols = config.backtesting.symbols
        print(f"[BACKTEST] 📦 Descargando {len(active_symbols)} símbolos usando lotes...")

        try:
            symbol_data = await downloader.download_multiple_symbols(
                active_symbols,
                timeframe=config.backtesting.timeframe,
                start_date=config.backtesting.start_date,
                end_date=config.backtesting.end_date
            )
        except asyncio.CancelledError:
            print("[BACKTEST] ❌ Descarga cancelada")
            return
        except Exception as e:
            print(f"[BACKTEST] ❌ Error descargando datos: {e}")
            return

        if not symbol_data:
            print("[BACKTEST] ❌ No se pudieron descargar datos")
            return

        downloaded_count = len([s for s in active_symbols if s in symbol_data and symbol_data[s] is not None])
        print(f"[BACKTEST] ✅ Datos descargados: {downloaded_count}/{len(active_symbols)} símbolos")

        # Mostrar estadísticas detalladas de datos
        print(f"\n[BACKTEST] 📊 ESTADÍSTICAS DE DATOS:")
        print("-" * 50)

        total_velas = 0
        for symbol in active_symbols:
            if symbol in symbol_data and symbol_data[symbol] is not None:
                df = symbol_data[symbol]
                velas = len(df)
                total_velas += velas

                # Calcular cobertura
                coverage = (velas / expected_velas) * 100 if expected_velas > 0 else 0

                # Rango de fechas
                min_date = df['timestamp'].min().strftime("%Y-%m-%d") if not df.empty else "N/A"
                max_date = df['timestamp'].max().strftime("%Y-%m-%d") if not df.empty else "N/A"

                print(f"📊 {symbol}: {velas:,} velas ({coverage:.1f}%) | {min_date} → {max_date}")

        print(f"📈 TOTAL: {total_velas:,} velas de {len(active_symbols)} símbolos")

        # Procesar datos
        print(f"\n[BACKTEST] 💾 Procesando y guardando datos...")
        processed_symbol_data = await downloader.process_and_save_data(
            symbol_data,
            config.backtesting.timeframe,
            save_csv=True
        )

        if not processed_symbol_data:
            print("[BACKTEST] ❌ Error procesando datos")
            return

        print(f"[BACKTEST] ✅ Datos procesados para {len(processed_symbol_data)} símbolos")

        # Ejecutar backtesting para cada símbolo
        backtest_results = {}
        total_trades = 0

        print(f"[DEBUG] Iniciando backtesting para {len(processed_symbol_data)} símbolos")
        print(f"[DEBUG] Símbolos a procesar: {list(processed_symbol_data.keys())}")

        for i, (symbol, df) in enumerate(processed_symbol_data.items(), 1):
            print(f"\n[BACKTEST] {i}/{len(processed_symbol_data)} 📈 PROCESANDO: {symbol}")
            print("-" * 60)

            try:
                # Crear estrategias activas según configuración usando carga dinámica
                strategies = load_strategies_from_config(config)

                if not strategies:
                    print(f"[BACKTEST] ⚠️  No hay estrategias activas para {symbol}")
                    continue

                # Ejecutar backtesting
                backtester = AdvancedBacktester(
                    initial_capital=config.backtesting.initial_capital,
                    commission=config.backtesting.commission,
                    slippage=config.backtesting.slippage
                )

                # Ejecutar cada estrategia
                symbol_results = {}
                symbol_total_trades = 0

                for strategy_name, strategy in strategies.items():
                    try:
                        result = backtester.run(strategy, df, symbol)
                        if result:
                            symbol_results[strategy_name] = result
                            trades = result.get('total_trades', 0)
                            symbol_total_trades += trades
                            pnl = result.get('total_pnl', 0)
                            win_rate = result.get('win_rate', 0) * 100

                            print(f"[BACKTEST] ✅ {strategy_name}: {trades} trades | P&L: ${pnl:.2f} | Win Rate: {win_rate:.1f}%")
                        else:
                            print(f"[BACKTEST] ❌ {strategy_name}: Sin resultados")
                    except Exception as e:
                        print(f"[BACKTEST] ❌ Error en {strategy_name}: {e}")

                if symbol_results:
                    backtest_results[symbol] = symbol_results
                    total_trades += symbol_total_trades
                    print(f"[BACKTEST] 📊 {symbol} completado: {symbol_total_trades} trades totales")
                else:
                    print(f"[BACKTEST] ❌ {symbol}: Sin resultados válidos")

            except Exception as e:
                print(f"[BACKTEST] ❌ Error general en {symbol}: {e}")

        # Resultados finales
        print(f"\n[BACKTEST] 🏆 RESULTADOS FINALES - BACKTESTING CON LOTES")
        print("=" * 80)
        print(f"[BACKTEST] 📊 Símbolos procesados: {len(backtest_results)}")
        print(f"[BACKTEST] 📊 Total operaciones: {total_trades}")
        print(f"[BACKTEST] 📊 Velas totales analizadas: {total_velas:,}")

        if backtest_results:
            print(f"\n[BACKTEST] 📈 DETALLE POR ESTRATEGIA:")
            print("-" * 80)
            print(f"{'Símbolo':<12} {'Estrategia':<20} {'Trades':<8} {'P&L':<12} {'Win Rate':<10}")
            print("-" * 80)

            for symbol, strategies in backtest_results.items():
                for strategy_name, result in strategies.items():
                    trades = result.get('total_trades', 0)
                    pnl = result.get('total_pnl', 0)
                    win_rate = result.get('win_rate', 0) * 100

                    print(f"{symbol:<12} {strategy_name:<20} {trades:<8} ${pnl:<11.2f} {win_rate:<9.1f}%")

            # Ranking final
            print(f"\n[BACKTEST] 🥇 RANKING FINAL (por P&L) - CON LOTES:")
            print("-" * 80)

            all_results = []
            for symbol, strategies in backtest_results.items():
                for strategy_name, result in strategies.items():
                    all_results.append({
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'pnl': result.get('total_pnl', 0),
                        'trades': result.get('total_trades', 0),
                        'win_rate': result.get('win_rate', 0) * 100
                    })

            # Ordenar por P&L descendente
            all_results.sort(key=lambda x: x['pnl'], reverse=True)

            for i, result in enumerate(all_results[:10], 1):  # Top 10
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}"
                print(f"{medal} {result['symbol']:<8} {result['strategy']:<20} ${result['pnl']:>10.2f} ({result['trades']} trades)")

            # Estadísticas generales
            total_pnl = sum(r['pnl'] for r in all_results)
            avg_win_rate = (sum(r['win_rate'] for r in all_results) / len(all_results)) if all_results else 0
            # Guardar resultados para dashboard
            try:
                import json
                from pathlib import Path
                # Directorio de salida para dashboard
                out_dir = Path(__file__).parent / "data" / "dashboard_results"
                # Limpiar resultados antiguos para evitar datos obsoletos
                if out_dir.exists():
                    for old in out_dir.glob("*.json"):
                        try:
                            old.unlink()
                        except Exception:
                            pass
                out_dir.mkdir(parents=True, exist_ok=True)
                # Guardar por símbolo
                for symbol, strategies in backtest_results.items():
                    # Reemplazar "/" por "_" para nombres de archivo válidos
                    safe_symbol = symbol.replace("/", "_")
                    file_path = out_dir / f"{safe_symbol}_results.json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({'symbol': symbol, 'strategies': strategies}, f, indent=2, ensure_ascii=False)
                # Resumen global
                summary = {
                    'total_symbols': len(backtest_results),
                    'period': {
                        'start_date': config.backtesting.start_date,
                        'end_date': config.backtesting.end_date,
                        'timeframe': config.backtesting.timeframe
                    },
                    'metrics': {
                        'total_pnl': total_pnl,
                        'total_trades': total_trades,
                        'avg_win_rate': avg_win_rate
                    }
                }
                with open(out_dir / 'global_summary.json', 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                print(f"[BACKTEST] ✅ Resultados guardados para dashboard en {out_dir}")
            except Exception as e:
                print(f"[BACKTEST] ❌ Error guardando resultados para dashboard: {e}")

            print(f"\n[BACKTEST] 📊 ESTADÍSTICAS GENERALES:")
            print(f"   • P&L Total: ${total_pnl:.2f}")
            print(f"   • Win Rate Promedio: {avg_win_rate:.1f}%")
            print(f"   • Velas Analizadas: {total_velas:,}")
            print(f"   • Período: {config.backtesting.start_date} a {config.backtesting.end_date}")
            print(f"   • Método: Descargas por lotes (9 lotes de ~3 meses)")

        await downloader.shutdown()
        print("[BACKTEST] ✅ Backtesting completado exitosamente con descargas por lotes")

    except Exception as e:
        print(f"[BACKTEST] ❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ejecutar backtest completo
    asyncio.run(run_full_backtesting_with_batches())
    # Lanzar dashboard con resultados generados
    try:
        import subprocess
        from pathlib import Path
        # Ruta al script dashboard.py en la carpeta descarga_datos
        dash_file = Path(__file__).parent / 'dashboard.py'
        print(f"[BACKTEST] 🚀 Lanzando dashboard: {dash_file}")

        # Lanzar streamlit en background sin esperar
        cmd = [sys.executable, '-m', 'streamlit', 'run', str(dash_file), '--server.port', '8501']
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("\n  You can now view your Streamlit app in your browser.")
        print("  Local URL: http://localhost:8501")
        print("  Network URL: http://192.168.1.156:8501")
        print(f"[BACKTEST] ✅ Dashboard iniciado con PID: {process.pid}")

        # No esperar, dejar que streamlit corra en background
        print("[BACKTEST] ✅ Sistema modular completado exitosamente")

    except Exception as e:
        print(f"[BACKTEST] ❌ No se pudo lanzar el dashboard: {e}")