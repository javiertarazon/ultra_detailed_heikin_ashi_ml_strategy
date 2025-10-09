import sqlite3
import os

db_path = 'data/data.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tablas en SQLite:')
    for table in tables:
        table_name = table[0]
        if '4h' in table_name:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'  {table_name}: {count} registros')
    conn.close()
else:
    print('Base de datos no encontrada')