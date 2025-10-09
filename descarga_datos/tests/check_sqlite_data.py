import sqlite3
import os
from datetime import datetime

def check_sqlite_data():
    db_path = os.path.join('data', 'data.db')
    
    if not os.path.exists(db_path):
        print(f"Base de datos {db_path} no encontrada")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener lista de tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"Tablas encontradas en SQLite: {len(tables)}")
    
    for table in tables:
        table_name = table[0]
        if table_name != 'sqlite_sequence':
            try:
                # Obtener número de registros
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                # Obtener primera y última fecha
                cursor.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp ASC LIMIT 1")
                first_timestamp = cursor.fetchone()
                
                cursor.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
                last_timestamp = cursor.fetchone()
                
                # Convertir timestamps a fechas legibles
                first_date = datetime.fromtimestamp(first_timestamp[0] / 1000) if first_timestamp else None
                last_date = datetime.fromtimestamp(last_timestamp[0] / 1000) if last_timestamp else None
                
                print(f"Tabla: {table_name} | Registros: {count} | Primer fecha: {first_date} | Última fecha: {last_date}")
            except Exception as e:
                print(f"Error al procesar tabla {table_name}: {str(e)}")
    
    conn.close()

if __name__ == "__main__":
    check_sqlite_data()