#!/usr/bin/env python3
"""
Script simple para ejecutar el dashboard de resultados
"""
import sys
import os
from pathlib import Path

# Agregar el directorio descarga_datos al path
descarga_dir = Path(__file__).parent / "descarga_datos"
sys.path.insert(0, str(descarga_dir))

try:
    # Importar streamlit
    import streamlit as st

    # Configurar la página
    st.set_page_config(
        layout="wide",
        page_title="Dashboard de Backtesting",
        page_icon="🤖"
    )

    # Importar y ejecutar el dashboard
    from utils.dashboard import main
    main()

except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Verificando estructura de directorios...")
    print(f"Directorio descarga_datos existe: {descarga_dir.exists()}")
    print(f"Archivo dashboard.py existe: {(descarga_dir / 'utils' / 'dashboard.py').exists()}")
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"Error ejecutando dashboard: {e}")
    import traceback
    traceback.print_exc()