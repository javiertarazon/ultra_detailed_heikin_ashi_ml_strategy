#!/usr/bin/env python3
"""Diagnostic script for SQLite data"""

import sqlite3
import pandas as pd
from datetime import datetime

def diagnose_sqlite_data():
    db_path = 'data/data.db'
    conn = sqlite3.connect(db_path)

    # Verificar tablas
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    symbols_to_check = ['SOL/USDT', 'ETH/USDT', 'TSLA/US', 'NVDA/US', 'EUR/USD', 'USD/JPY']

    for symbol in symbols_to_check:
        table_name = f"{symbol.replace('/', '_').replace('.', '_')}_4h"
        print(f"\n🔍 Diagnóstico para {symbol} (tabla: {table_name})")
        print("-" * 50)

        try:
            # Contar total de registros
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]
            print(f"Total registros: {total_count}")

            if total_count > 0:
                # Ver rango de fechas
                cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                min_ts, max_ts = cursor.fetchone()
                min_date = datetime.fromtimestamp(min_ts)
                max_date = datetime.fromtimestamp(max_ts)
                print(f"Rango fechas: {min_date} → {max_date}")

                # Verificar período requerido
                train_start = pd.Timestamp('2023-01-01')
                val_end = pd.Timestamp('2024-06-30')
                print(f"Período requerido: {train_start} → {val_end}")

                # Contar registros en período requerido
                train_start_ts = int(train_start.timestamp())
                val_end_ts = int(val_end.timestamp())
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE timestamp >= ? AND timestamp <= ?",
                             (train_start_ts, val_end_ts))
                period_count = cursor.fetchone()[0]
                print(f"Registros en período requerido: {period_count}")

                # Mostrar algunas filas de ejemplo
                cursor.execute(f"SELECT timestamp, open, high, low, close, volume FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print("Ejemplo de datos:")
                for row in rows:
                    ts = datetime.fromtimestamp(row[0])
                    print(f"  {ts}: O={row[1]:.4f} H={row[2]:.4f} L={row[3]:.4f} C={row[4]:.4f} V={row[5]}")

        except Exception as e:
            print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    diagnose_sqlite_data()