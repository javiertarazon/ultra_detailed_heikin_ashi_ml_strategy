#!/usr/bin/env python3
"""Verificar tablas en SQLite"""

import sqlite3
import os

db_path = 'data/data.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print('Tablas en SQLite:')
    for table in tables:
        table_name = table[0]
        print(f'  {table_name}')
        # Contar registros en cada tabla
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'    Registros: {count}')
        except Exception as e:
            print(f'    (Error al contar: {e})')
    conn.close()
else:
    print('Base de datos no encontrada')