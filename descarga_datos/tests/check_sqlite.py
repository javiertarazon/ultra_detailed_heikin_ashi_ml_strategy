#!/usr/bin/env python3
"""
Script para verificar datos disponibles en SQLite
"""

import sqlite3
import os

def check_sqlite_data():
    db_path = 'data/data.db'

    if not os.path.exists(db_path):
        print(f"Base de datos no encontrada: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("Tablas disponibles en SQLite:")
    for table in tables:
        table_name = table[0]
        print(f"  - {table_name}")

        # Contar registros si es una tabla de datos OHLCV
        if '_4h' in table_name or '_1h' in table_name:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"    Registros: {count}")
            except Exception as e:
                print(f"    Error al contar: {e}")

    conn.close()

if __name__ == "__main__":
    check_sqlite_data()