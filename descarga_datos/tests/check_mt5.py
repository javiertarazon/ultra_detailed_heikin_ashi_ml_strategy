import sys
import os
sys.path.append(os.path.dirname(__file__))

def check_mt5_status():
    """Verificar estado de MT5"""
    print("🔍 VERIFICACIÓN DE MT5")
    print("=" * 40)

    try:
        import MetaTrader5 as mt5
        print("✅ MetaTrader5 importado correctamente")

        # Intentar inicializar
        if not mt5.initialize():
            print(f"❌ Error al inicializar MT5: {mt5.last_error()}")
            return False

        print("✅ MT5 inicializado correctamente")

        # Verificar terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            print(f"❌ Error obteniendo info del terminal: {mt5.last_error()}")
            mt5.shutdown()
            return False

        print(f"✅ Terminal conectado: {terminal_info.name}")
        print(f"   Servidor: {terminal_info.server}")
        print(f"   Conectado: {terminal_info.connected}")

        # Verificar login
        account_info = mt5.account_info()
        if account_info is None:
            print(f"❌ No hay cuenta logueada: {mt5.last_error()}")
        else:
            print(f"✅ Cuenta logueada: {account_info.login} ({account_info.server})")

        # Obtener símbolos disponibles
        symbols = mt5.symbols_get()
        if symbols is None:
            print(f"❌ Error obteniendo símbolos: {mt5.last_error()}")
        else:
            print(f"✅ Símbolos disponibles: {len(symbols)}")

            # Buscar símbolos específicos
            target_symbols = ['TSLA', 'NVDA', 'AAPL', 'EURUSD', 'USDJPY', 'GBPUSD']
            found_symbols = []

            for symbol in symbols:
                if symbol.name in target_symbols:
                    found_symbols.append(symbol.name)

            print(f"   Símbolos objetivo encontrados: {found_symbols}")

        mt5.shutdown()
        return True

    except ImportError as e:
        print(f"❌ Error importando MetaTrader5: {e}")
        print("💡 Solución: pip install MetaTrader5")
        return False
    except Exception as e:
        print(f"❌ Error general con MT5: {e}")
        return False

if __name__ == "__main__":
    check_mt5_status()