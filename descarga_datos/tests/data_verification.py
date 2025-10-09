#!/usr/bin/env python3
"""
Data Verification Toolkit - Herramienta Consolidada v2.8
========================================================

Este script consolida varias herramientas de verificación de datos en una sola:
- Verificación de disponibilidad de datos para todos los símbolos
- Verificación rápida del estado de datos sin descargas
- Auditoria de datos SQLite
- Verificación de integridad de datos

Uso:
    python data_verification.py [--all] [--quick] [--sqlite] [--integrity] [--symbols SYMBOL1 SYMBOL2]

Opciones:
    --all: Ejecuta todas las verificaciones
    --quick: Ejecuta verificación rápida de datos
    --sqlite: Verifica datos en SQLite
    --integrity: Verifica integridad completa de datos
    --symbols: Especifica símbolos a verificar (separados por espacios)
"""

import os
import sys
import sqlite3
import argparse
import pandas as pd
import asyncio
from datetime import datetime
from pathlib import Path

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def get_config():
    """Obtiene la configuración del sistema"""
    try:
        from config.config_loader import load_config_from_yaml
        return load_config_from_yaml()
    except Exception as e:
        print(f"⚠️ Error cargando configuración: {e}")
        sys.exit(1)

async def verify_all_data(symbols=None):
    """Verificación completa de datos para todos los símbolos configurados"""
    print('🔍 VERIFICACIÓN DE DATOS PARA TODOS LOS SÍMBOLOS')
    print('=' * 60)

    config = get_config()
    all_symbols = config.backtesting.symbols
    
    if symbols:
        target_symbols = [s for s in all_symbols if s in symbols]
        if not target_symbols:
            print("⚠️ Ninguno de los símbolos especificados está en la configuración")
            return
    else:
        target_symbols = all_symbols

    print(f'📊 Símbolos configurados: {len(target_symbols)}')
    for i, symbol in enumerate(target_symbols, 1):
        print(f'  {i:2d}. {symbol}')

    print('\n🔄 Verificando disponibilidad de datos...\n')
    
    try:
        from main import verify_data_availability
        for symbol in target_symbols:
            print(f'▶️ Verificando {symbol}...')
            # Llamar a la función original de verify_data_availability con el símbolo específico
            await verify_data_availability([symbol], config.backtesting.timeframe)
            print('-' * 40)
    except Exception as e:
        print(f"⚠️ Error verificando datos: {e}")

def check_data_status(symbols=None):
    """Verificación rápida del estado de datos sin descargar"""
    print("🔍 VERIFICACIÓN RÁPIDA DE DATOS")
    print("=" * 50)

    config = get_config()
    all_symbols = config.backtesting.symbols
    
    if symbols:
        target_symbols = [s for s in all_symbols if s in symbols]
        if not target_symbols:
            print("⚠️ Ninguno de los símbolos especificados está en la configuración")
            return
    else:
        target_symbols = all_symbols

    timeframe = config.backtesting.timeframe

    print(f"📊 Verificando {len(target_symbols)} símbolos configurados")
    print(f"⏰ Timeframe: {timeframe}")
    print()

    # Verificar SQLite
    print("🗄️ Verificando base de datos SQLite...")
    db_path = os.path.join('data', 'data.db')
    
    sqlite_status = {}
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for symbol in target_symbols:
            table_name = f"{symbol.replace('/', '_')}_{timeframe}"
            
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                    min_date, max_date = cursor.fetchone()
                    min_date = datetime.fromtimestamp(min_date / 1000).strftime('%Y-%m-%d')
                    max_date = datetime.fromtimestamp(max_date / 1000).strftime('%Y-%m-%d')
                    
                    print(f"  ✅ {symbol:12} | SQLite: {count} velas ({min_date} → {max_date})")
                    sqlite_status[symbol] = True
                else:
                    print(f"  ❌ {symbol:12} | SQLite: Tabla vacía")
                    sqlite_status[symbol] = False
                    
            except sqlite3.OperationalError:
                print(f"  ❌ {symbol:12} | SQLite: Tabla no existe")
                sqlite_status[symbol] = False
                
        conn.close()
    else:
        print(f"  ❌ Base de datos SQLite no encontrada en {db_path}")
        for symbol in target_symbols:
            sqlite_status[symbol] = False
            print(f"  ❌ {symbol:12} | SQLite: Sin datos")
    
    print()
    
    # Verificar CSV
    print("📄 Verificando archivos CSV...")
    csv_dir = os.path.join('data', 'csv')
    
    csv_status = {}
    for symbol in target_symbols:
        csv_file = os.path.join(csv_dir, f"{symbol.replace('/', '_')}_{timeframe}.csv")
        
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                count = len(df)
                
                if count > 0:
                    min_date = pd.to_datetime(df.iloc[0]['timestamp'], unit='ms').strftime('%Y-%m-%d')
                    max_date = pd.to_datetime(df.iloc[-1]['timestamp'], unit='ms').strftime('%Y-%m-%d')
                    
                    print(f"  ✅ {symbol:12} | CSV: {count} velas ({min_date} → {max_date})")
                    csv_status[symbol] = True
                else:
                    print(f"  ❌ {symbol:12} | CSV: Archivo vacío")
                    csv_status[symbol] = False
                    
            except Exception as e:
                print(f"  ❌ {symbol:12} | CSV: Error leyendo archivo ({e})")
                csv_status[symbol] = False
        else:
            print(f"  ❌ {symbol:12} | CSV: No encontrado")
            csv_status[symbol] = False
    
    print()
    
    # Resumen general
    print("📋 RESUMEN DE DATOS:")
    print("=" * 40)
    
    sqlite_count = sum(1 for s in sqlite_status.values() if s)
    csv_count = sum(1 for s in csv_status.values() if s)
    
    print(f"🗄️  SQLite: {sqlite_count}/{len(target_symbols)} símbolos con datos")
    print(f"📄 CSV:    {csv_count}/{len(target_symbols)} símbolos con datos")
    print()
    
    # Símbolos sin datos
    missing_data = [s for s in target_symbols if not sqlite_status.get(s) and not csv_status.get(s)]
    if missing_data:
        print(f"⚠️  Símbolos sin datos ({len(missing_data)}):")
        for symbol in missing_data:
            print(f"  - {symbol}")
        
        print("\n💡 Ejecuta: python main.py --data-audit")
        print("   para descargar datos automáticamente")
    else:
        print("✅ Todos los símbolos tienen datos disponibles")

def audit_sqlite_data(symbols=None):
    """Audita datos en SQLite en detalle"""
    print("🔍 AUDITORÍA DE DATOS SQLITE")
    print("=" * 50)
    
    db_path = os.path.join('data', 'data.db')
    
    if not os.path.exists(db_path):
        print(f"Base de datos {db_path} no encontrada")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener lista de tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    # Filtrar tablas por símbolo si se especifican
    if symbols:
        target_tables = []
        for table in tables:
            table_name = table[0]
            for symbol in symbols:
                symbol_key = symbol.replace('/', '_')
                if symbol_key in table_name:
                    target_tables.append((table_name,))
        tables = target_tables
    
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
                first_result = cursor.fetchone()
                
                cursor.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
                last_result = cursor.fetchone()
                
                # Verificar nulos
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL")
                null_count = cursor.fetchone()[0]
                
                if first_result and last_result:
                    first_date = datetime.fromtimestamp(first_result[0] / 1000).strftime('%Y-%m-%d %H:%M')
                    last_date = datetime.fromtimestamp(last_result[0] / 1000).strftime('%Y-%m-%d %H:%M')
                    
                    print(f"\n📊 Tabla: {table_name}")
                    print(f"   Registros: {count:,}")
                    print(f"   Período:   {first_date} → {last_date}")
                    
                    if null_count > 0:
                        print(f"   ⚠️ ADVERTENCIA: {null_count} registros con valores NULL")
                    
                    # Verificar integridad de las fechas
                    timeframe_str = table_name.split('_')[-1]
                    if timeframe_str in ['1h', '4h', '1d']:
                        hours = 1 if timeframe_str == '1h' else 4 if timeframe_str == '4h' else 24
                        expected_intervals = (int(last_result[0]) - int(first_result[0])) / (3600 * 1000 * hours)
                        coverage = (count / expected_intervals) * 100
                        
                        print(f"   Cobertura: {coverage:.1f}% ({count} de {expected_intervals:.0f} velas esperadas)")
                        
                        if coverage < 95:
                            print(f"   ⚠️ ADVERTENCIA: Posibles gaps en los datos (cobertura < 95%)")
                else:
                    print(f"\n📊 Tabla: {table_name}")
                    print(f"   Registros: {count:,}")
                    print("   ⚠️ ADVERTENCIA: No se pudieron determinar fechas")
            except Exception as e:
                print(f"\n📊 Tabla: {table_name}")
                print(f"   ❌ ERROR: {e}")
    
    conn.close()

def verify_data_integrity(symbols=None):
    """Verificación completa de integridad de datos"""
    print("🔍 VERIFICACIÓN DE INTEGRIDAD DE DATOS")
    print("=" * 60)
    
    config = get_config()
    all_symbols = config.backtesting.symbols
    timeframe = config.backtesting.timeframe
    
    if symbols:
        target_symbols = [s for s in all_symbols if s in symbols]
        if not target_symbols:
            print("⚠️ Ninguno de los símbolos especificados está en la configuración")
            return
    else:
        target_symbols = all_symbols
    
    # Calcular fechas esperadas según configuración
    start_date = pd.Timestamp(config.backtesting.start_date)
    end_date = pd.Timestamp(config.backtesting.end_date)
    
    # Calcular días esperados
    total_days = (end_date - start_date).days
    hours_in_tf = int(timeframe[:-1]) if 'h' in timeframe else 24
    candles_per_day = 24 // hours_in_tf
    expected_candles = total_days * candles_per_day
    
    print(f"📅 Período esperado: {start_date.date()} → {end_date.date()}")
    print(f"⏰ Timeframe: {timeframe}")
    print(f"🎯 Velas esperadas por símbolo: ~{expected_candles:,}")
    print()
    
    # Verificar integridad en SQLite y CSV
    db_path = os.path.join('data', 'data.db')
    csv_dir = os.path.join('data', 'csv')
    
    results = []
    
    for symbol in target_symbols:
        print(f"\n🔍 Verificando {symbol}...")
        symbol_key = symbol.replace('/', '_')
        table_name = f"{symbol_key}_{timeframe}"
        csv_path = os.path.join(csv_dir, f"{table_name}.csv")
        
        sqlite_count = 0
        sqlite_start = None
        sqlite_end = None
        sqlite_gaps = 0
        
        # Verificar SQLite
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = cursor.fetchone()[0]
                
                if sqlite_count > 0:
                    # Obtener fechas
                    cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                    min_ts, max_ts = cursor.fetchone()
                    sqlite_start = datetime.fromtimestamp(min_ts / 1000)
                    sqlite_end = datetime.fromtimestamp(max_ts / 1000)
                    
                    # Verificar gaps
                    if 'h' in timeframe:
                        hours = int(timeframe[:-1])
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM (
                                SELECT timestamp, LEAD(timestamp) OVER (ORDER BY timestamp) next_ts
                                FROM {table_name}
                            ) WHERE next_ts - timestamp > {hours*3600*1000+100}
                        """)
                        sqlite_gaps = cursor.fetchone()[0]
                
                conn.close()
            except Exception as e:
                print(f"  ❌ Error en SQLite: {e}")
        
        # Verificar CSV
        csv_count = 0
        csv_start = None
        csv_end = None
        csv_gaps = 0
        
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                csv_count = len(df)
                
                if csv_count > 0:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    csv_start = df['timestamp'].min()
                    csv_end = df['timestamp'].max()
                    
                    # Verificar gaps
                    if 'h' in timeframe:
                        hours = int(timeframe[:-1])
                        expected_diff = pd.Timedelta(hours=hours)
                        df = df.sort_values('timestamp')
                        time_diffs = df['timestamp'].diff()
                        gaps = (time_diffs > expected_diff * 1.1).sum()
                        csv_gaps = int(gaps)
            except Exception as e:
                print(f"  ❌ Error en CSV: {e}")
        
        # Mostrar resultados
        print(f"  📊 SQLite: {sqlite_count:,} velas")
        if sqlite_start and sqlite_end:
            print(f"     Período: {sqlite_start.strftime('%Y-%m-%d')} → {sqlite_end.strftime('%Y-%m-%d')}")
            coverage = min(100, (sqlite_count / expected_candles) * 100)
            print(f"     Cobertura estimada: {coverage:.1f}%")
            if sqlite_gaps > 0:
                print(f"     ⚠️ {sqlite_gaps} gaps detectados")
        
        print(f"  📄 CSV: {csv_count:,} velas")
        if csv_start and csv_end:
            print(f"     Período: {csv_start.strftime('%Y-%m-%d')} → {csv_end.strftime('%Y-%m-%d')}")
            coverage = min(100, (csv_count / expected_candles) * 100)
            print(f"     Cobertura estimada: {coverage:.1f}%")
            if csv_gaps > 0:
                print(f"     ⚠️ {csv_gaps} gaps detectados")
        
        # Determinar mejor fuente
        best_source = None
        if sqlite_count > csv_count:
            best_source = "SQLite"
        elif csv_count > sqlite_count:
            best_source = "CSV"
        elif sqlite_count > 0:
            best_source = "Ambos iguales"
        
        if best_source:
            print(f"  🔍 Mejor fuente: {best_source}")
        
        # Guardar resultado para resumen
        results.append({
            'symbol': symbol,
            'sqlite_count': sqlite_count,
            'csv_count': csv_count,
            'sqlite_coverage': (sqlite_count / expected_candles) * 100 if sqlite_count > 0 else 0,
            'csv_coverage': (csv_count / expected_candles) * 100 if csv_count > 0 else 0,
            'best_source': best_source,
            'sqlite_gaps': sqlite_gaps,
            'csv_gaps': csv_gaps
        })
    
    # Mostrar resumen final
    print("\n📋 RESUMEN DE INTEGRIDAD DE DATOS")
    print("=" * 60)
    
    good_data = [r for r in results if max(r['sqlite_coverage'], r['csv_coverage']) >= 95]
    ok_data = [r for r in results if 80 <= max(r['sqlite_coverage'], r['csv_coverage']) < 95]
    poor_data = [r for r in results if max(r['sqlite_coverage'], r['csv_coverage']) < 80]
    
    print(f"✅ Datos completos (>95%): {len(good_data)}/{len(results)}")
    print(f"⚠️ Datos parciales (80-95%): {len(ok_data)}/{len(results)}")
    print(f"❌ Datos insuficientes (<80%): {len(poor_data)}/{len(results)}")
    
    if poor_data:
        print("\nSímbolos con datos insuficientes:")
        for r in poor_data:
            print(f"  - {r['symbol']} (mejor cobertura: {max(r['sqlite_coverage'], r['csv_coverage']):.1f}%)")
        
        print("\n💡 Ejecuta: python main.py --data-audit")
        print("   para descargar datos automáticamente")

async def main():
    parser = argparse.ArgumentParser(description="Herramienta consolidada de verificación de datos")
    parser.add_argument("--all", action="store_true", help="Ejecutar todas las verificaciones")
    parser.add_argument("--quick", action="store_true", help="Ejecutar verificación rápida")
    parser.add_argument("--sqlite", action="store_true", help="Verificar datos en SQLite")
    parser.add_argument("--integrity", action="store_true", help="Verificar integridad de datos")
    parser.add_argument("--symbols", nargs="+", help="Símbolos específicos a verificar")
    
    args = parser.parse_args()
    
    # Si no se especifica ninguna opción, mostrar la ayuda
    if not (args.all or args.quick or args.sqlite or args.integrity):
        parser.print_help()
        return
    
    if args.all or args.quick:
        check_data_status(args.symbols)
        print("\n" + "=" * 60 + "\n")
    
    if args.all or args.sqlite:
        audit_sqlite_data(args.symbols)
        print("\n" + "=" * 60 + "\n")
    
    if args.all or args.integrity:
        verify_data_integrity(args.symbols)
        print("\n" + "=" * 60 + "\n")
        
    if args.all:
        await verify_all_data(args.symbols)

if __name__ == "__main__":
    asyncio.run(main())