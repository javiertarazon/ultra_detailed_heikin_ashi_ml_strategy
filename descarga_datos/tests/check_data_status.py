#!/usr/bin/env python3
"""
Script rápido para verificar estado de datos sin descargar
"""
import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def check_data_status():
    """
    Verificar rápidamente el estado de datos disponibles
    """
    print("🔍 VERIFICACIÓN RÁPIDA DE DATOS")
    print("=" * 50)

    try:
        from config.config_loader import load_config_from_yaml
        config = load_config_from_yaml()

        symbols = config.backtesting.symbols
        timeframe = config.backtesting.timeframe

        print(f"📊 Verificando {len(symbols)} símbolos configurados")
        print(f"⏰ Timeframe: {timeframe}")
        print()

        # Verificar SQLite
        db_path = Path("data/data.db")
        sqlite_available = {}

        if db_path.exists():
            print("🗄️ Verificando base de datos SQLite...")
            conn = sqlite3.connect(db_path)

            for symbol in symbols:
                table_name = f"{symbol.replace('/', '_').replace('USDT', 'USDT').replace('USD', 'USD')}_{timeframe}"
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    sqlite_available[symbol] = count
                    print(f"  ✅ {symbol:<12} | SQLite: {count:>6} registros")
                except:
                    sqlite_available[symbol] = 0
                    print(f"  ❌ {symbol:<12} | SQLite: Sin datos")

            conn.close()
        else:
            print("❌ Base de datos SQLite no encontrada")
            for symbol in symbols:
                sqlite_available[symbol] = 0

        # Verificar CSV
        print("\n📄 Verificando archivos CSV...")
        csv_dir = Path("data/csv")
        csv_available = {}

        if csv_dir.exists():
            for symbol in symbols:
                csv_name = f"{symbol.replace('/', '_')}_{timeframe}.csv"
                csv_path = csv_dir / csv_name

                if csv_path.exists():
                    try:
                        df = pd.read_csv(csv_path)
                        count = len(df)
                        csv_available[symbol] = count
                        print(f"  ✅ {symbol:<12} | CSV: {count:>6} registros")
                    except:
                        csv_available[symbol] = 0
                        print(f"  ⚠️  {symbol:<12} | CSV: Error al leer")
                else:
                    csv_available[symbol] = 0
                    print(f"  ❌ {symbol:<12} | CSV: No encontrado")

        # Resumen
        print("\n📋 RESUMEN DE DATOS:")
        print("=" * 40)

        total_symbols = len(symbols)
        sqlite_ok = sum(1 for count in sqlite_available.values() if count > 0)
        csv_ok = sum(1 for count in csv_available.values() if count > 0)

        print(f"🗄️  SQLite: {sqlite_ok}/{total_symbols} símbolos con datos")
        print(f"📄 CSV:    {csv_ok}/{total_symbols} símbolos con datos")

        # Símbolos sin datos
        no_data_symbols = []
        for symbol in symbols:
            if sqlite_available.get(symbol, 0) == 0 and csv_available.get(symbol, 0) == 0:
                no_data_symbols.append(symbol)

        if no_data_symbols:
            print(f"\n⚠️  Símbolos sin datos ({len(no_data_symbols)}):")
            for symbol in no_data_symbols:
                print(f"  - {symbol}")
            print("\n💡 Ejecuta: python main.py --data-audit")
            print("   para descargar datos automáticamente")
        else:
            print("\n✅ ¡Todos los símbolos tienen datos!")
            print("💡 Puedes ejecutar backtesting selectivo:")
            print("   python selective_backtest.py --status  # Ver estado")
            print("   python selective_backtest.py          # Ejecutar backtest")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_data_status()