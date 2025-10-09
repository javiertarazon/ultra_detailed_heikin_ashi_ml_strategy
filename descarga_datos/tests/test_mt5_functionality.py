#!/usr/bin/env python3
"""
Test específico para MT5 - Verificar funcionamiento
"""
import sys
import os

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_mt5_basic():
    """Test básico de MT5"""
    print("🧪 TEST BÁSICO DE MT5")
    print("=" * 50)

    try:
        import MetaTrader5 as mt5
        print("✅ MetaTrader5 importado correctamente")

        # Verificar inicialización
        print("\n🔄 Intentando inicializar MT5...")
        if not mt5.initialize():
            error = mt5.last_error()
            print(f"❌ Error al inicializar MT5: {error}")
            return False

        print("✅ MT5 inicializado correctamente")

        # Verificar terminal info
        terminal = mt5.terminal_info()
        if terminal is None:
            print("❌ No se pudo obtener información del terminal")
            return False

        print(f"✅ Terminal: {terminal.name}")
        print(f"   Conectado: {terminal.connected}")
        print(f"   Comunidad: {getattr(terminal, 'community', 'N/A')}")
        print(f"   Trade permitido: {getattr(terminal, 'trade_allowed', 'N/A')}")

        # Verificar cuenta
        account = mt5.account_info()
        if account is None:
            print("❌ No se pudo obtener información de cuenta")
            return False

        print(f"✅ Cuenta: {account.login}")
        print(f"   Balance: {account.balance}")
        print(f"   Moneda: {account.currency}")

        # Verificar símbolos disponibles
        symbols = mt5.symbols_get()
        if symbols is None:
            print("❌ No se pudieron obtener símbolos")
            return False

        print(f"✅ Símbolos disponibles: {len(symbols)}")

        # Buscar símbolos específicos
        test_symbols = ["EURUSD", "TSLA.US", "BTCUSD"]
        found_symbols = []

        for symbol in symbols:
            if symbol.name in test_symbols:
                found_symbols.append(symbol.name)
                print(f"   ✅ {symbol.name}: encontrado")

        if not found_symbols:
            print("⚠️  Ninguno de los símbolos de prueba encontrados")
        else:
            print(f"✅ Símbolos de prueba encontrados: {found_symbols}")

        # Cerrar MT5
        mt5.shutdown()
        print("✅ MT5 cerrado correctamente")

        return True

    except ImportError:
        print("❌ MetaTrader5 no está instalado")
        return False
    except Exception as e:
        print(f"❌ Error en test MT5: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_mt5_download():
    """Test de descarga de datos desde MT5"""
    print("\n🧪 TEST DE DESCARGA MT5")
    print("=" * 50)

    try:
        from core.mt5_downloader import MT5Downloader
        from config.config_loader import load_config_from_yaml

        config = load_config_from_yaml()
        downloader = MT5Downloader(config)

        print("🔄 Inicializando MT5 downloader...")
        if not downloader.initialize():
            print("❌ Error al inicializar MT5 downloader")
            return False

        print("✅ MT5 downloader inicializado")

        # Intentar descargar un símbolo simple
        test_symbol = "EURUSD"
        timeframe = "1h"
        start_date = "2025-01-01"
        end_date = "2025-01-05"

        print(f"🔄 Intentando descargar {test_symbol}...")
        data = downloader.download_symbol_data(test_symbol, timeframe, start_date, end_date)

        if data is not None and not data.empty:
            print(f"✅ Descarga exitosa: {len(data)} registros")
            print(f"   Rango: {data.index[0]} → {data.index[-1]}")
            print(f"   Columnas: {list(data.columns)}")
        else:
            print("❌ Descarga falló o sin datos")
            return False

        downloader.shutdown()
        print("✅ MT5 downloader cerrado")

        return True

    except Exception as e:
        print(f"❌ Error en test de descarga: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("TEST COMPLETO DE MT5")
    print("=" * 60)

    # Test básico
    basic_ok = test_mt5_basic()

    if basic_ok:
        # Test de descarga
        download_ok = test_mt5_download()

        if download_ok:
            print("\n🎉 TODOS LOS TESTS DE MT5 PASARON")
        else:
            print("\n⚠️  MT5 básico OK, pero descarga falló")
    else:
        print("\n❌ MT5 NO FUNCIONA - Revisar instalación/conexión")