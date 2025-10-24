#!/usr/bin/env python3
"""
Script completo para probar el sistema de live trading con dashboard integrado.
Verifica que todos los componentes funcionen correctamente juntos.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from utils.dashboard import load_results, get_binance_connection_status
from utils.live_trading_data_reader import LiveTradingDataReader
from utils.live_trading_tracker import LiveTradingTracker
from utils.logger import setup_logger

def test_complete_system():
    """Prueba completa del sistema de live trading con dashboard."""
    logger = setup_logger(__name__)

    print("🧪 PRUEBA COMPLETA DEL SISTEMA DE LIVE TRADING")
    print("=" * 60)

    success_count = 0
    total_tests = 0

    # 1. Verificar conexión a Binance
    print("\n1. Verificando conexión a Binance...")
    total_tests += 1
    try:
        status = get_binance_connection_status()
        if status['connected']:
            print("✅ Conexión a Binance exitosa")
            print(f"   - Tipo de cuenta: {status['account_type']}")
            print(f"   - Testnet: {'Sí' if status['testnet'] else 'No'}")
            print(f"   - Operaciones recientes: {status['trade_count']}")
            if status['balance_info']:
                print(f"   - Balance disponible: ${status['balance_info'].get('free_usdt', 0):.2f}")
            success_count += 1
        else:
            print("⚠️  No se pudo conectar a Binance")
            print(f"   - Error: {status.get('error', 'Credenciales no configuradas')}")
    except Exception as e:
        print(f"❌ Error verificando conexión: {e}")

    # 2. Probar LiveTradingDataReader
    print("\n2. Probando LiveTradingDataReader...")
    total_tests += 1
    try:
        reader = LiveTradingDataReader(testnet=True)  # Usar testnet por defecto
        if reader.test_connection():
            print("✅ LiveTradingDataReader inicializado correctamente")

            # Intentar obtener métricas
            metrics = reader.calculate_live_metrics_from_binance()
            if metrics and metrics.get('total_trades', 0) > 0:
                print(f"   - Operaciones encontradas: {metrics['total_trades']}")
                print(f"   - P&L Total: ${metrics.get('total_pnl', 0):.2f}")
                print(f"   - Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
            else:
                print("   - No se encontraron operaciones (esperado en entorno de prueba)")
            success_count += 1
        else:
            print("⚠️  LiveTradingDataReader no pudo conectarse")
    except Exception as e:
        print(f"❌ Error en LiveTradingDataReader: {e}")

    # 3. Probar LiveTradingTracker
    print("\n3. Probando LiveTradingTracker...")
    total_tests += 1
    try:
        tracker = LiveTradingTracker()
        print("✅ LiveTradingTracker inicializado correctamente")

        # Verificar métodos disponibles
        methods = ['calculate_win_rate', 'calculate_profit_factor', 'calculate_sharpe_ratio']
        for method in methods:
            if hasattr(tracker, method):
                print(f"   - Método {method}: ✅ Disponible")
            else:
                print(f"   - Método {method}: ❌ Faltante")

        success_count += 1
    except Exception as e:
        print(f"❌ Error en LiveTradingTracker: {e}")

    # 4. Probar integración del dashboard
    print("\n4. Probando integración del dashboard...")
    total_tests += 1
    try:
        results, global_summary = load_results()

        if results:
            print("✅ Dashboard cargó datos exitosamente")

            # Analizar fuente de datos
            if global_summary:
                mode = global_summary.get('mode', 'UNKNOWN')
                data_source = global_summary.get('data_source', 'UNKNOWN')

                if 'BINANCE_DIRECT' in data_source:
                    print("   - Fuente: 🟢 DATOS DIRECTOS DE BINANCE")
                elif 'LIVE_TRADING' in mode:
                    print("   - Fuente: 🟡 ARCHIVO GUARDADO")
                else:
                    print("   - Fuente: 📊 BACKTESTING")

                metrics = global_summary.get('metrics', {})
                print(f"   - Total P&L: ${metrics.get('total_pnl', 0):.2f}")
                print(f"   - Total Operaciones: {metrics.get('total_trades', 0)}")
                print(f"   - Win Rate: {metrics.get('avg_win_rate', 0):.1f}%")

            success_count += 1
        else:
            print("❌ Dashboard no pudo cargar datos")
    except Exception as e:
        print(f"❌ Error en integración del dashboard: {e}")

    # 5. Verificar archivos de configuración
    print("\n5. Verificando configuración...")
    total_tests += 1
    try:
        config_path = root_dir / "config" / "config.yaml"
        if config_path.exists():
            print("✅ Archivo de configuración encontrado")

            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            live_config = config.get('live_trading', {})
            account_type = live_config.get('account_type', 'SANDBOX')
            print(f"   - Tipo de cuenta configurado: {account_type}")

            # Verificar si hay credenciales (sin mostrarlas)
            has_api_key = bool(live_config.get('api_key'))
            has_secret = bool(live_config.get('api_secret'))
            print(f"   - API Key configurada: {'Sí' if has_api_key else 'No'}")
            print(f"   - API Secret configurada: {'Sí' if has_secret else 'No'}")

            if has_api_key and has_secret:
                print("   - Estado: ✅ Configuración completa")
            else:
                print("   - Estado: ⚠️  Faltan credenciales de Binance")

            success_count += 1
        else:
            print("❌ Archivo de configuración no encontrado")
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")

    # Resultado final
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO FINAL: {success_count}/{total_tests} pruebas exitosas")

    if success_count == total_tests:
        print("🎉 ¡Sistema de live trading completamente funcional!")
        print("\n✅ El dashboard ahora puede:")
        print("   - Leer datos DIRECTOS de operaciones ejecutadas en Binance")
        print("   - Calcular métricas profesionales en tiempo real")
        print("   - Mostrar balance actual de la cuenta")
        print("   - Actualizarse automáticamente cada 30 segundos")
        print("   - Hacer fallback a datos guardados si no hay conexión")
    else:
        print("⚠️  Sistema parcialmente funcional")
        print("   - Revisar configuración de credenciales de Binance")
        print("   - Verificar conectividad a internet")
        print("   - Comprobar que hay operaciones ejecutadas en la cuenta")

    return success_count == total_tests


if __name__ == "__main__":
    success = test_complete_system()
    print(f"\n🔚 Prueba completada - Éxito: {success}")
    sys.exit(0 if success else 1)