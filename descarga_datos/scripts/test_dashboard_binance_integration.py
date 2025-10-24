#!/usr/bin/env python3
"""
Script de prueba para verificar la integración del dashboard con datos directos de Binance.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from utils.dashboard import load_results, load_live_data_from_binance
from utils.logger import setup_logger

def test_dashboard_integration():
    """Prueba la integración del dashboard con datos de Binance."""
    logger = setup_logger(__name__)

    print("🧪 Probando integración del dashboard con datos directos de Binance...")

    try:
        # Probar carga de datos directos de Binance
        print("\n1. Probando carga directa de datos de Binance...")
        live_data = load_live_data_from_binance()

        if live_data:
            print("✅ Datos directos de Binance cargados exitosamente")
            print(f"   - Operaciones encontradas: {live_data['global_summary']['metrics']['total_trades']}")
            print(f"   - P&L Total: ${live_data['global_summary']['metrics']['total_pnl']:.2f}")
            print(f"   - Win Rate: {live_data['global_summary']['metrics']['avg_win_rate']:.1f}%")
            print(f"   - Balance Actual: ${live_data['global_summary']['metrics']['current_balance']:.2f}")
            print(f"   - Fuente de datos: {live_data.get('data_source', 'UNKNOWN')}")
        else:
            print("⚠️  No se pudieron cargar datos directos de Binance")
            print("   Esto puede deberse a:")
            print("   - No hay operaciones ejecutadas en Binance")
            print("   - Problemas de conectividad con la API")
            print("   - Configuración incorrecta de credenciales")

        # Probar función principal load_results
        print("\n2. Probando función principal load_results()...")
        results, global_summary = load_results()

        if results:
            print("✅ Función load_results() ejecutada exitosamente")

            # Verificar si hay datos de live trading
            live_keys = [k for k in results.keys() if 'LIVE' in k.upper()]
            if live_keys:
                print(f"   - Modo detectado: LIVE TRADING ({live_keys[0]})")
                print(f"   - Símbolos en resultados: {len(results)}")
                print(f"   - Resumen global disponible: {'Sí' if global_summary else 'No'}")

                if global_summary:
                    metrics = global_summary.get('metrics', {})
                    print(f"   - Total P&L: ${metrics.get('total_pnl', 0):.2f}")
                    print(f"   - Total Operaciones: {metrics.get('total_trades', 0)}")
                    print(f"   - Win Rate: {metrics.get('avg_win_rate', 0):.1f}%")
                    print(f"   - Max Drawdown: {metrics.get('max_drawdown', 0):.1f}%")
            else:
                print("   - Modo detectado: BACKTESTING")
                print(f"   - Símbolos en resultados: {len(results)}")
        else:
            print("❌ Error en load_results() - no se obtuvieron resultados")

        print("\n✅ Prueba de integración completada")

    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = test_dashboard_integration()
    sys.exit(0 if success else 1)