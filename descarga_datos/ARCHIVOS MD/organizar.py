#!/usr/bin/env python3
"""
Script para organizar archivos MD en subcarpetas por categoría.
"""

import os
import shutil
from pathlib import Path

# Mapeo de patrones de nombre a categorías
CATEGORIAS = {
    "01_Configuracion": [
        "config", "setup", "environment", ".env", "kraken", "python_downgrade"
    ],
    "02_Roadmap": [
        "roadmap", "roadmap_futuros", "vision", "plan", "objetivo"
    ],
    "03_Arquitectura": [
        "arquitectura", "sistema_modular", "estructura", "modular", "completacion"
    ],
    "04_Analisis": [
        "analisis", "diagnostico", "investigacion", "profundo", "reporte", "balance_report",
        "operaciones_reales", "operaciones_live", "testnet", "system_lockdown"
    ],
    "05_Backtesting": [
        "backtest", "backtest_results", "backtesting", "optimizacion", "optimization",
        "ml_completo", "optuna", "optuna_results"
    ],
    "06_Fixes": [
        "fix", "fix_", "correcciones", "bug", "bugreport", "ajuste", "adjustment",
        "correccion", "resolucion", "solucion"
    ],
    "07_Dashboard": [
        "dashboard", "visualization", "visualizacion", "streamlit"
    ],
    "08_Live_Trading": [
        "trading_24_7", "24_7", "live_trading", "live", "operacion", "guide", "operation"
    ],
    "09_Testing": [
        "testing", "validacion", "test", "verify", "verificacion", "check", "prueba"
    ],
    "10_Documentacion": [
        "indice", "readme", "changelog", "contribu", "aclaracion", "respuesta",
        "resumen", "consolidacion", "guia", "quick", "reference"
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
    
    return "99_SIN_CLASIFICAR"

def organizar_archivos():
    """Organiza los archivos MD en subcarpetas."""
    ruta_base = Path(".")
    archivos_movidos = 0
    archivos_sin_mover = 0
    
    # Crear carpetas de categorías PRIMERO
    carpetas_creadas = []
    for categoria in CATEGORIAS.keys():
        carpeta = ruta_base / categoria
        carpeta.mkdir(exist_ok=True)
        carpetas_creadas.append(categoria)
        print(f"CARPETA: {categoria}")
    
    print(f"\n{len(carpetas_creadas)} carpetas listas\n")
    
    # Mover archivos
    for archivo in sorted(ruta_base.glob("*.md")):
        # Saltar índices maestros y archivos en carpetas
        if "INDICE_MAESTRO" in archivo.name or archivo.is_dir():
            continue
        
        categoria = clasificar_archivo(archivo.name)
        carpeta_dest = ruta_base / categoria
        destino = carpeta_dest / archivo.name
        
        try:
            if not destino.exists():
                shutil.move(str(archivo), str(destino))
                print(f"OK: {archivo.name} -> {categoria}/")
                archivos_movidos += 1
            else:
                print(f"EXISTE: {archivo.name} en {categoria}/")
                archivos_sin_mover += 1
        except Exception as e:
            print(f"ERROR: {archivo.name}: {e}")
    
    print(f"\nArchivos movidos: {archivos_movidos}")
    print(f"Archivos sin mover: {archivos_sin_mover}")
    
    # Crear archivos README en cada categoría
    print("\nCreando README en cada carpeta...")
    for categoria in CATEGORIAS.keys():
        carpeta = ruta_base / categoria
        readme = carpeta / "README.md"
        if not readme.exists():
            with open(readme, "w", encoding="utf-8") as f:
                f.write(f"# {categoria.replace('_', ' ')}\n\n")
                f.write("Archivos organizados en esta categoria:\n\n")
                
                for archivo in sorted(carpeta.glob("*.md")):
                    if archivo.name != "README.md":
                        f.write(f"- [{archivo.name}]({archivo.name})\n")
            
            print(f"OK: README.md creado en {categoria}/")

if __name__ == "__main__":
    print("Organizando archivos MD...\n")
    organizar_archivos()
    print("\nOrganizacion completada")
