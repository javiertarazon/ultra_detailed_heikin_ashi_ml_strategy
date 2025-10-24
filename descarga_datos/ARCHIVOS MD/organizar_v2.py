#!/usr/bin/env python3
"""
Script mejorado para organizar archivos MD en subcarpetas por categoría.
Más seguro y robusto.
"""

import os
import shutil
from pathlib import Path
import sys

# Mapeo de patrones de nombre a categorías
CATEGORIAS = {
    "01_Configuracion": [
        "config", "setup", "environment", ".env", "kraken", "python_downgrade"
    ],
    "02_Roadmap": [
        "roadmap", "roadmap_futuros", "vision", "plan", "objetivo"
    ],
    "03_Arquitectura": [
        "arquitectura", "sistema_modular", "estructura", "modular", "completacion", "diagram"
    ],
    "04_Analisis": [
        "analisis", "diagnostico", "investigacion", "profundo", "reporte", "balance_report",
        "operaciones_reales", "operaciones_live", "testnet", "system_lockdown", "pnl", "tabla",
        "calculo", "metricas", "summary", "resumen"
    ],
    "05_Backtesting": [
        "backtest", "backtest_results", "backtesting", "optimizacion", "optimization",
        "ml_completo", "optuna", "optuna_results"
    ],
    "06_Fixes": [
        "fix", "fix_", "correcciones", "bug", "bugreport", "ajuste", "adjustment",
        "correccion", "resolucion", "solucion", "cleanup", "error", "trailing"
    ],
    "07_Dashboard": [
        "dashboard", "visualization", "visualizacion", "streamlit"
    ],
    "08_Live_Trading": [
        "trading_24_7", "24_7", "live_trading", "live", "operacion", "guide", "operation",
        "trading", "logging", "migration"
    ],
    "09_Testing": [
        "testing", "validacion", "test", "verify", "verificacion", "check", "prueba", "training", "checkpoint"
    ],
    "10_Documentacion": [
        "indice", "readme", "changelog", "contribu", "aclaracion", "respuesta",
        "resumen", "consolidacion", "guia", "quick", "reference", "instrucciones", "license", "protected"
    ],
    "11_Protected": [
        "archivos_protegidos", "protected"
    ],
    "12_Historial": [
        "changelog", "historial", "version", "consolidation", "logs", "checkpoint"
    ]
}

def clasificar_archivo(nombre):
    """Clasifica un archivo según su nombre."""
    nombre_lower = nombre.lower()
    
    for categoria, patrones in CATEGORIAS.items():
        for patron in patrones:
            if patron.lower() in nombre_lower:
                return categoria
    
    return None  # Retorna None si no encuentra categoría

def organizar_archivos():
    """Organiza los archivos MD en subcarpetas."""
    ruta_base = Path(".")
    
    # Paso 1: Crear todas las carpetas primero
    print("Creando carpetas...")
    for categoria in CATEGORIAS.keys():
        carpeta = ruta_base / categoria
        carpeta.mkdir(exist_ok=True)
    
    # Paso 2: Mover archivos
    print("\nMoviendo archivos...")
    archivos_movidos = 0
    archivos_sin_clasificar = []
    
    for archivo in sorted(ruta_base.glob("*.md")):
        # Saltar índices maestros
        if "INDICE_MAESTRO" in archivo.name or archivo.name == "README.md":
            print(f"SALTAR: {archivo.name}")
            continue
        
        categoria = clasificar_archivo(archivo.name)
        
        if categoria:
            carpeta_dest = ruta_base / categoria
            destino = carpeta_dest / archivo.name
            
            if not destino.exists():
                shutil.move(str(archivo), str(destino))
                print(f"OK: {archivo.name} -> {categoria}/")
                archivos_movidos += 1
            else:
                print(f"EXISTE: {archivo.name} en {categoria}/")
        else:
            archivos_sin_clasificar.append(archivo.name)
            print(f"SIN CLASIFICAR: {archivo.name}")
    
    print(f"\nArchivos movidos: {archivos_movidos}")
    if archivos_sin_clasificar:
        print(f"Archivos sin clasificar ({len(archivos_sin_clasificar)}):")
        for archivo in archivos_sin_clasificar:
            print(f"  - {archivo}")
    
    # Paso 3: Crear README en cada carpeta
    print("\nCreando README en cada carpeta...")
    for categoria in CATEGORIAS.keys():
        carpeta = ruta_base / categoria
        readme = carpeta / "README.md"
        
        archivos_en_carpeta = sorted([f.name for f in carpeta.glob("*.md") if f.name != "README.md"])
        
        if archivos_en_carpeta:
            contenido = f"# {categoria.replace('_', ' ')}\n\n"
            contenido += "Archivos en esta categoria:\n\n"
            for archivo in archivos_en_carpeta:
                contenido += f"- [{archivo}]({archivo})\n"
            
            with open(readme, "w", encoding="utf-8") as f:
                f.write(contenido)
            
            print(f"OK: {categoria}/ ({len(archivos_en_carpeta)} archivos)")

if __name__ == "__main__":
    organizar_archivos()
    print("\nOrganizacion completada")
