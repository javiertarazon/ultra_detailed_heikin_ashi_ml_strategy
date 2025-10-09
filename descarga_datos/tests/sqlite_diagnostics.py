#!/usr/bin/env python3
"""
SQLite Diagnostics Toolkit - Herramienta Consolidada v2.8
=========================================================

Este script consolida varias herramientas de diagnóstico de SQLite en una sola:
- Diagnóstico básico de tablas y datos
- Análisis detallado de tablas
- Verificación de integridad de datos
- Análisis de gaps y problemas comunes
- Exportación a CSV para respaldo

Uso:
    python sqlite_diagnostics.py [--basic] [--detailed] [--integrity] [--export] [--table TABLE_NAME]

Opciones:
    --basic: Ejecuta diagnóstico básico de tablas
    --detailed: Ejecuta análisis detallado de datos
    --integrity: Verifica integridad de datos
    --export: Exporta datos a CSV
    --table: Nombre específico de tabla a analizar
"""

import os
import sys
import sqlite3
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Constantes
DB_PATH = os.path.join(parent_dir, 'data', 'data.db')
CSV_DIR = os.path.join(parent_dir, 'data', 'csv')

def get_db_connection():
    """Obtiene conexión a la base de datos SQLite"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def basic_diagnosis():
    """Diagnóstico básico de tablas SQLite"""
    print("🔍 DIAGNÓSTICO BÁSICO DE SQLITE")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ No se encontraron tablas en la base de datos")
        conn.close()
        return
    
    print(f"📊 Tablas disponibles en SQLite: {len(tables)}")
    
    for i, table in enumerate(tables, 1):
        table_name = table[0]
        
        if table_name == 'sqlite_sequence':
            continue
        
        print(f"\n{i:2d}. {table_name}")
        
        # Contar registros
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Obtener fechas min/max si es una tabla OHLCV
                if any(suffix in table_name for suffix in ['_1h', '_4h', '_1d']):
                    cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                    min_ts, max_ts = cursor.fetchone()
                    
                    min_date = datetime.fromtimestamp(min_ts / 1000).strftime('%Y-%m-%d %H:%M')
                    max_date = datetime.fromtimestamp(max_ts / 1000).strftime('%Y-%m-%d %H:%M')
                    
                    print(f"    Registros: {count:,}")
                    print(f"    Período: {min_date} → {max_date}")
                else:
                    print(f"    Registros: {count:,}")
            else:
                print("    ❌ Tabla vacía (0 registros)")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Estadísticas generales
    print("\n📊 ESTADÍSTICAS GENERALES")
    print("=" * 30)
    
    try:
        # Contar tablas por tipo
        ohlcv_tables = [t[0] for t in tables if any(suffix in t[0] for suffix in ['_1h', '_4h', '_1d'])]
        other_tables = [t[0] for t in tables if t[0] != 'sqlite_sequence' and t[0] not in ohlcv_tables]
        
        print(f"Tablas OHLCV:     {len(ohlcv_tables)}")
        print(f"Otras tablas:     {len(other_tables)}")
        print(f"Total tablas:     {len(tables)}")
        
        # Verificar tamaño de la base de datos
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024)  # MB
        print(f"Tamaño de BD:     {db_size:.2f} MB")
        
    except Exception as e:
        print(f"❌ Error calculando estadísticas: {e}")
    
    conn.close()

def detailed_diagnosis(table_name=None):
    """Análisis detallado de datos SQLite"""
    print("🔬 ANÁLISIS DETALLADO DE DATOS SQLITE")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener lista de tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    all_tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
    
    if not all_tables:
        print("❌ No se encontraron tablas en la base de datos")
        conn.close()
        return
    
    # Filtrar por tabla específica si se proporciona
    if table_name:
        if table_name not in all_tables:
            print(f"❌ Tabla '{table_name}' no encontrada en la base de datos")
            conn.close()
            return
        tables = [table_name]
    else:
        # Usar solo tablas OHLCV
        tables = [t for t in all_tables if any(suffix in t for suffix in ['_1h', '_4h', '_1d'])]
    
    for table in tables:
        print(f"\n📊 ANÁLISIS DE TABLA: {table}")
        print("-" * 40)
        
        try:
            # Estructura de la tabla
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print("Estructura:")
            for col in columns:
                col_id, name, type_name, not_null, default_val, pk = col
                print(f"  - {name} ({type_name}){' [PK]' if pk else ''}{' [NOT NULL]' if not_null else ''}")
            
            # Estadísticas básicas
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("\n❌ Tabla vacía (0 registros)")
                continue
                
            print(f"\nRegistros totales: {count:,}")
            
            # Análisis de timestamps para tablas OHLCV
            if any(col[1] == 'timestamp' for col in columns):
                cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
                min_ts, max_ts = cursor.fetchone()
                
                min_date = datetime.fromtimestamp(min_ts / 1000)
                max_date = datetime.fromtimestamp(max_ts / 1000)
                
                duration = max_date - min_date
                
                print(f"Período: {min_date.strftime('%Y-%m-%d %H:%M')} → {max_date.strftime('%Y-%m-%d %H:%M')}")
                print(f"Duración: {duration.days} días")
                
                # Análisis de gaps
                if '_1h' in table:
                    expected_interval = 3600 * 1000  # 1 hora en ms
                    label = "1 hora"
                elif '_4h' in table:
                    expected_interval = 4 * 3600 * 1000  # 4 horas en ms
                    label = "4 horas"
                elif '_1d' in table:
                    expected_interval = 24 * 3600 * 1000  # 1 día en ms
                    label = "1 día"
                else:
                    expected_interval = None
                
                if expected_interval:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM (
                            SELECT timestamp, LEAD(timestamp) OVER (ORDER BY timestamp) next_ts
                            FROM {table}
                            WHERE next_ts IS NOT NULL
                        ) WHERE next_ts - timestamp > {expected_interval * 1.5}
                    """)
                    gaps = cursor.fetchone()[0]
                    
                    expected_candles = duration.total_seconds() / (expected_interval / 1000)
                    coverage = min(100, (count / expected_candles) * 100)
                    
                    print(f"Intervalo esperado: {label}")
                    print(f"Velas esperadas: ~{int(expected_candles):,}")
                    print(f"Cobertura de datos: {coverage:.1f}%")
                    
                    if gaps > 0:
                        print(f"⚠️ Gaps detectados: {gaps}")
                        
                        # Mostrar los gaps más significativos
                        cursor.execute(f"""
                            SELECT timestamp, next_ts, (next_ts - timestamp) / {expected_interval} as gap_size
                            FROM (
                                SELECT timestamp, LEAD(timestamp) OVER (ORDER BY timestamp) next_ts
                                FROM {table}
                            ) 
                            WHERE next_ts - timestamp > {expected_interval * 1.5}
                            ORDER BY gap_size DESC
                            LIMIT 5
                        """)
                        
                        major_gaps = cursor.fetchall()
                        
                        if major_gaps:
                            print("\nGaps principales:")
                            for ts, next_ts, gap_size in major_gaps:
                                gap_start = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
                                gap_end = datetime.fromtimestamp(next_ts / 1000).strftime('%Y-%m-%d %H:%M')
                                print(f"  - {gap_start} → {gap_end} ({int(gap_size)} velas faltantes)")
                
                # Análisis de valores NULL
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL")
                nulls = cursor.fetchone()[0]
                
                if nulls > 0:
                    print(f"⚠️ Valores NULL encontrados: {nulls}")
                
                # Análisis de valores atípicos (extremos)
                cursor.execute(f"""
                    SELECT 
                        MIN(open), MAX(open),
                        MIN(high), MAX(high),
                        MIN(low), MAX(low),
                        MIN(close), MAX(close),
                        MIN(volume), MAX(volume)
                    FROM {table}
                """)
                
                min_o, max_o, min_h, max_h, min_l, max_l, min_c, max_c, min_v, max_v = cursor.fetchone()
                
                print("\nRangos de valores:")
                print(f"  Open:   {min_o:.6g} → {max_o:.6g}")
                print(f"  High:   {min_h:.6g} → {max_h:.6g}")
                print(f"  Low:    {min_l:.6g} → {max_l:.6g}")
                print(f"  Close:  {min_c:.6g} → {max_c:.6g}")
                print(f"  Volume: {min_v:.6g} → {max_v:.6g}")
                
        except Exception as e:
            print(f"❌ Error analizando tabla {table}: {e}")
    
    conn.close()

def integrity_check(table_name=None):
    """Verificación de integridad de datos SQLite"""
    print("🛡️ VERIFICACIÓN DE INTEGRIDAD DE DATOS SQLITE")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Ejecutando PRAGMA integrity_check...")
    cursor.execute("PRAGMA integrity_check")
    integrity_result = cursor.fetchall()
    
    if len(integrity_result) == 1 and integrity_result[0][0] == 'ok':
        print("✅ Integridad básica de la base de datos: OK")
    else:
        print("❌ Problemas de integridad encontrados:")
        for issue in integrity_result:
            print(f"  - {issue[0]}")
    
    print("\nEjecutando PRAGMA foreign_key_check...")
    cursor.execute("PRAGMA foreign_key_check")
    fk_result = cursor.fetchall()
    
    if not fk_result:
        print("✅ Verificación de claves foráneas: OK")
    else:
        print("❌ Problemas de claves foráneas encontrados:")
        for issue in fk_result:
            print(f"  - {issue}")
    
    # Verificación de tablas específicas
    if table_name:
        tables = [table_name]
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
    
    # Verificar tablas OHLCV
    ohlcv_tables = [t for t in tables if any(suffix in t for suffix in ['_1h', '_4h', '_1d'])]
    
    if ohlcv_tables:
        print("\nVerificando coherencia de datos OHLCV...")
        
        for table in ohlcv_tables:
            print(f"\n📊 Tabla: {table}")
            
            try:
                # Verificar relaciones entre OHLC (high >= open, high >= close, low <= open, low <= close)
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE high < open OR high < close OR low > open OR low > close
                """)
                invalid_ohlc = cursor.fetchone()[0]
                
                if invalid_ohlc > 0:
                    print(f"❌ Datos OHLC inválidos encontrados: {invalid_ohlc} registros")
                    
                    # Mostrar ejemplos
                    cursor.execute(f"""
                        SELECT timestamp, open, high, low, close
                        FROM {table}
                        WHERE high < open OR high < close OR low > open OR low > close
                        LIMIT 3
                    """)
                    examples = cursor.fetchall()
                    
                    print("  Ejemplos:")
                    for ts, o, h, l, c in examples:
                        date_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
                        print(f"  - {date_str}: OHLC({o}, {h}, {l}, {c})")
                else:
                    print("✅ Relaciones OHLC: Válidas")
                
                # Verificar valores negativos en volumen
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE volume < 0")
                neg_volume = cursor.fetchone()[0]
                
                if neg_volume > 0:
                    print(f"❌ Volúmenes negativos encontrados: {neg_volume} registros")
                else:
                    print("✅ Volúmenes: No negativos")
                
                # Verificar timestamps duplicados
                cursor.execute(f"""
                    SELECT timestamp, COUNT(*)
                    FROM {table}
                    GROUP BY timestamp
                    HAVING COUNT(*) > 1
                """)
                duplicates = cursor.fetchall()
                
                if duplicates:
                    print(f"❌ Timestamps duplicados: {len(duplicates)}")
                    
                    # Mostrar ejemplos
                    print("  Ejemplos:")
                    for ts, count in duplicates[:3]:
                        date_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
                        print(f"  - {date_str}: {count} ocurrencias")
                else:
                    print("✅ Timestamps: Sin duplicados")
                
                # Verificar ordenamiento de timestamps
                cursor.execute(f"""
                    SELECT COUNT(*) FROM (
                        SELECT timestamp, LAG(timestamp) OVER (ORDER BY rowid) prev_ts
                        FROM {table}
                        WHERE prev_ts IS NOT NULL
                    ) WHERE timestamp <= prev_ts
                """)
                disorder = cursor.fetchone()[0]
                
                if disorder > 0:
                    print(f"❌ Timestamps desordenados: {disorder} instancias")
                else:
                    print("✅ Orden de timestamps: Correcto")
                
            except Exception as e:
                print(f"❌ Error verificando tabla {table}: {e}")
    
    conn.close()

def export_to_csv(table_name=None):
    """Exporta datos de SQLite a CSV"""
    print("📤 EXPORTACIÓN DE DATOS SQLITE A CSV")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener tablas a exportar
    if table_name:
        # Verificar que la tabla existe
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"❌ La tabla '{table_name}' no existe en la base de datos")
            conn.close()
            return
        tables = [table_name]
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
        
        # Filtrar solo tablas OHLCV para evitar exportar todo
        tables = [t for t in tables if any(suffix in t for suffix in ['_1h', '_4h', '_1d'])]
    
    # Crear directorio si no existe
    os.makedirs(CSV_DIR, exist_ok=True)
    
    for table in tables:
        export_path = os.path.join(CSV_DIR, f"{table}.csv")
        
        print(f"Exportando {table} → {export_path}")
        
        try:
            # Leer datos
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"  ⚠️ La tabla {table} está vacía, no se exporta")
                continue
            
            # Obtener nombres de columnas
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Crear DataFrame y guardar a CSV
            df = pd.DataFrame(rows, columns=columns)
            df.to_csv(export_path, index=False)
            
            print(f"  ✅ {len(df):,} registros exportados")
            
        except Exception as e:
            print(f"  ❌ Error exportando tabla {table}: {e}")
    
    conn.close()
    print(f"\n✅ Exportación completada en {CSV_DIR}")

def main():
    parser = argparse.ArgumentParser(description="Herramientas de diagnóstico SQLite")
    parser.add_argument("--basic", action="store_true", help="Ejecutar diagnóstico básico")
    parser.add_argument("--detailed", action="store_true", help="Ejecutar análisis detallado")
    parser.add_argument("--integrity", action="store_true", help="Verificar integridad de datos")
    parser.add_argument("--export", action="store_true", help="Exportar datos a CSV")
    parser.add_argument("--table", help="Nombre específico de tabla a analizar")
    
    args = parser.parse_args()
    
    # Si no se especifica ninguna opción, mostrar diagnóstico básico
    if not (args.basic or args.detailed or args.integrity or args.export):
        basic_diagnosis()
        return
    
    if args.basic:
        basic_diagnosis()
        print("\n" + "=" * 60 + "\n")
    
    if args.detailed:
        detailed_diagnosis(args.table)
        print("\n" + "=" * 60 + "\n")
    
    if args.integrity:
        integrity_check(args.table)
        print("\n" + "=" * 60 + "\n")
    
    if args.export:
        export_to_csv(args.table)

if __name__ == "__main__":
    main()