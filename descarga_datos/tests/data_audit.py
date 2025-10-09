import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def audit_data_completeness():
    """Auditoría completa de datos históricos"""
    print("🔍 AUDITORÍA COMPLETA DE DATOS HISTÓRICOS")
    print("=" * 60)

    symbols = [
        'SOL/USDT', 'ETH/USDT', 'BTC/USD', 'ADA/USD', 'DOT/USD',
        'MATIC/USD', 'XRP/USD', 'LTC/USD', 'DOGE/USD',
        'TSLA/US', 'NVDA/US', 'AAPL/US', 'MSFT/US', 'GOOGL/US', 'AMZN/US',
        'EUR/USD', 'USD/JPY', 'GBP/USD'
    ]

    timeframe = '4h'
    start_date = pd.Timestamp('2023-01-01')
    end_date = pd.Timestamp('2025-10-06')

    # Calcular días esperados
    total_days = (end_date - start_date).days
    candles_per_day = 24 // 4  # 4h timeframe = 6 candles por día
    expected_candles = total_days * candles_per_day

    print(f"📅 Período esperado: {start_date.date()} → {end_date.date()}")
    print(f"🎯 Velas esperadas por símbolo: ~{expected_candles:,}")
    print()

    results = []

    for symbol in symbols:
        table_name = f"{symbol.replace('/', '_')}_{timeframe}"

        # Verificar CSV
        csv_path = f"data/csv/{table_name}.csv"
        csv_exists = os.path.exists(csv_path)
        csv_count = 0
        csv_date_range = None

        if csv_exists:
            try:
                df_csv = pd.read_csv(csv_path)
                csv_count = len(df_csv)
                if not df_csv.empty:
                    df_csv['timestamp'] = pd.to_datetime(df_csv['timestamp'])
                    csv_date_range = f"{df_csv['timestamp'].min().date()} → {df_csv['timestamp'].max().date()}"
            except Exception as e:
                csv_count = f"ERROR: {e}"

        # Verificar SQLite
        sqlite_count = 0
        sqlite_date_range = None

        try:
            conn = sqlite3.connect('data/data.db')
            cursor = conn.cursor()

            # Verificar si tabla existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = cursor.fetchone()[0]

                if sqlite_count > 0:
                    cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                    min_ts, max_ts = cursor.fetchone()
                    sqlite_date_range = f"{pd.to_datetime(min_ts).date()} → {pd.to_datetime(max_ts).date()}"
            else:
                sqlite_count = "TABLA NO EXISTE"

            conn.close()
        except Exception as e:
            sqlite_count = f"ERROR: {e}"

        # Calcular completitud
        completeness = "N/A"
        data_count = 0

        # Usar SQLite si está disponible, sino usar CSV
        if isinstance(sqlite_count, int) and sqlite_count > 0:
            data_count = sqlite_count
            completeness = f"{(sqlite_count / expected_candles * 100):.1f}%"
        elif isinstance(csv_count, int) and csv_count > 0:
            data_count = csv_count
            completeness = f"{(csv_count / expected_candles * 100):.1f}%"

        # Clasificar tipo de activo
        if symbol in ['SOL/USDT', 'ETH/USDT', 'BTC/USD', 'ADA/USD', 'DOT/USD', 'MATIC/USD', 'XRP/USD', 'LTC/USD', 'DOGE/USD']:
            asset_type = "CRYPTO"
        elif symbol in ['TSLA/US', 'NVDA/US', 'AAPL/US', 'MSFT/US', 'GOOGL/US', 'AMZN/US']:
            asset_type = "STOCKS"
        else:
            asset_type = "FOREX"

        # Determinar estado basado en datos disponibles
        if data_count >= expected_candles * 0.8:  # Al menos 80% de los datos esperados
            status = '✅ OK'
        elif data_count > 100:  # Al menos algunos datos
            status = '⚠️ PARCIAL'
        else:
            status = '❌ INSUFICIENTE'

        results.append({
            'symbol': symbol,
            'type': asset_type,
            'csv_count': csv_count,
            'sqlite_count': sqlite_count,
            'completeness': completeness,
            'date_range': sqlite_date_range or csv_date_range,
            'status': status
        })

    # Mostrar resultados
    print("📊 RESULTADOS DE AUDITORÍA:")
    print("-" * 120)
    print(f"{'Símbolo':<12} {'Tipo':<8} {'CSV':<8} {'SQLite':<10} {'Completitud':<12} {'Rango Fechas':<20} {'Estado'}")
    print("-" * 120)

    crypto_results = [r for r in results if r['type'] == 'CRYPTO']
    stocks_results = [r for r in results if r['type'] == 'STOCKS']
    forex_results = [r for r in results if r['type'] == 'FOREX']

    for category, category_results in [("🪙 CRYPTO", crypto_results), ("📈 STOCKS", stocks_results), ("💱 FOREX", forex_results)]:
        print(f"\n{category}:")
        for r in category_results:
            print(f"{r['symbol']:<12} {r['type']:<8} {str(r['csv_count']):<8} {str(r['sqlite_count']):<10} {r['completeness']:<12} {str(r['date_range'] or 'N/A'):<20} {r['status']}")

    # Resumen
    print("\n" + "=" * 60)
    print("📈 RESUMEN EJECUTIVO:")

    total_symbols = len(results)
    ok_symbols = sum(1 for r in results if r['status'] == '✅ OK')
    insufficient_symbols = total_symbols - ok_symbols

    print(f"✅ Símbolos con datos suficientes: {ok_symbols}/{total_symbols}")
    print(f"❌ Símbolos con datos insuficientes: {insufficient_symbols}/{total_symbols}")

    # Análisis por tipo
    for asset_type in ['CRYPTO', 'STOCKS', 'FOREX']:
        type_results = [r for r in results if r['type'] == asset_type]
        type_ok = sum(1 for r in type_results if r['status'] == '✅ OK')
        print(f"   {asset_type}: {type_ok}/{len(type_results)} OK")

    return results

if __name__ == "__main__":
    audit_data_completeness()