#!/usr/bin/env python3
"""
Script para verificar fechas disponibles en SQLite para SOL/USDT
"""

import sqlite3
from datetime import datetime

def check_sol_dates():
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()

    # Verificar estructura de la tabla
    cursor.execute("PRAGMA table_info(SOL_USDT_4h)")
    columns = cursor.fetchall()
    print("Columnas en SOL_USDT_4h:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    # Verificar rango de timestamps
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM SOL_USDT_4h")
    min_ts, max_ts, count = cursor.fetchone()

    print(f"\nDatos SOL_USDT_4h:")
    print(f"  Registros: {count}")
    print(f"  Timestamp mínimo: {min_ts}")
    print(f"  Timestamp máximo: {max_ts}")

    if min_ts and max_ts:
        min_date = datetime.fromtimestamp(min_ts / 1000)
        max_date = datetime.fromtimestamp(max_ts / 1000)
        print(f"  Fecha mínima: {min_date}")
        print(f"  Fecha máxima: {max_date}")

    # Verificar fechas solicitadas por el ML trainer
    train_start = "2023-01-01"
    val_end = "2024-12-31"
    print(f"\nFechas solicitadas:")
    print(f"  Train start: {train_start}")
    print(f"  Val end: {val_end}")

    conn.close()

if __name__ == "__main__":
    check_sol_dates()