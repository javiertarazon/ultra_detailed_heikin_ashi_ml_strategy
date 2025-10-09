import sqlite3
import pandas as pd
from datetime import datetime

def audit_sqlite_data():
    """Auditar datos históricos en SQLite para verificar integridad"""
    print('📊 AUDITORÍA DE DATOS HISTÓRICOS EN SQLITE')
    print('=' * 60)

    try:
        conn = sqlite3.connect('data/data.db')
        cursor = conn.cursor()

        # Obtener todas las tablas con timeframe 4h
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_4h';")
        tables = cursor.fetchall()

        for table in sorted([t[0] for t in tables]):
            try:
                # Consultar el rango de fechas
                query = f"SELECT MIN(timestamp), MAX(timestamp) FROM {table};"
                cursor.execute(query)
                min_date, max_date = cursor.fetchone()
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                
                # Convertir fechas
                min_date = pd.to_datetime(min_date).strftime('%Y-%m-%d')
                max_date = pd.to_datetime(max_date).strftime('%Y-%m-%d')
                
                # Verificar si los datos cubren el período mínimo requerido
                start_req = '2025-01-01'
                end_req = '2025-10-06'
                
                if min_date <= start_req and max_date >= end_req:
                    status = '✅'
                else:
                    status = '⚠️'
                
                print(f'{status} {table}: {count:,} registros ({min_date} → {max_date})')
                
            except Exception as e:
                print(f'❌ Error consultando {table}: {e}')

        # Verificar estructura de tablas (ejemplo con una tabla)
        if tables:
            table_name = tables[0][0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print(f"\n📋 Estructura de tabla ejemplo ({table_name}):")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

if __name__ == "__main__":
    audit_sqlite_data()