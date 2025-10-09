#!/usr/bin/env python3
"""
Test directo de MT5 copy_rates
"""
import sys
import os
import pandas as pd
from datetime import datetime

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_mt5_direct():
    """Test directo usando MT5 copy_rates"""
    print("🧪 TEST DIRECTO MT5 copy_rates")
    print("=" * 50)

    try:
        import MetaTrader5 as mt5

        # Inicializar MT5
        if not mt5.initialize():
            print(f"❌ Error inicializando MT5: {mt5.last_error()}")
            return False

        print("✅ MT5 inicializado")

        # Probar EURUSD (forex)
        symbol = "EURUSD"
        timeframe = mt5.TIMEFRAME_H1  # 1 hora
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 5)

        print(f"🔄 Descargando {symbol} desde {start_date.date()} hasta {end_date.date()}...")

        # Obtener datos
        rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

        if rates is None:
            print(f"❌ copy_rates_range devolvió None para {symbol}")
            print(f"   Último error MT5: {mt5.last_error()}")
            mt5.shutdown()
            return False

        if len(rates) == 0:
            print(f"❌ No se encontraron datos para {symbol}")
            mt5.shutdown()
            return False

        print(f"✅ Datos obtenidos: {len(rates)} velas")

        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        print(f"   Rango temporal: {df.index[0]} → {df.index[-1]}")
        print(f"   Columnas: {list(df.columns)}")
        print(f"   Primeras filas:")
        print(df.head(3))

        # Cerrar MT5
        mt5.shutdown()
        print("✅ MT5 cerrado")

        return True

    except Exception as e:
        print(f"❌ Error en test directo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_mt5_symbol_info():
    """Test de información de símbolos"""
    print("\n🧪 TEST INFORMACIÓN DE SÍMBOLOS MT5")
    print("=" * 50)

    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            print(f"❌ Error inicializando MT5: {mt5.last_error()}")
            return False

        # Probar diferentes formatos de símbolo
        test_symbols = ["EURUSD", "EURUSD.", "BTCUSD", "TSLA.US", "TSLA_US", "AAPL.US"]

        for symbol in test_symbols:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is not None:
                print(f"✅ {symbol}: encontrado")
                print(f"   Descripción: {symbol_info.description}")
                print(f"   Dígitos: {symbol_info.digits}")
                print(f"   Punto: {symbol_info.point}")
            else:
                print(f"❌ {symbol}: no encontrado")

        mt5.shutdown()
        return True

    except Exception as e:
        print(f"❌ Error en test de símbolos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("TEST DIRECTO DE MT5")
    print("=" * 60)

    # Test de información de símbolos
    symbols_ok = test_mt5_symbol_info()

    # Test directo de descarga
    if symbols_ok:
        download_ok = test_mt5_direct()

        if download_ok:
            print("\n🎉 MT5 FUNCIONA PERFECTAMENTE")
        else:
            print("\n⚠️  Símbolos OK, pero descarga falló")
    else:
        print("\n❌ PROBLEMA CON SÍMBOLOS MT5")