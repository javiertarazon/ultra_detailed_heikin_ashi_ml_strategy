#!/usr/bin/env python3
"""
Script para ejecutar optimización de XRP/USDT
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent))

# Simular argumentos de línea de comandos
sys.argv = ['main.py', '--optimize']

# Importar y ejecutar main
from main import main

if __name__ == "__main__":
    main()