#!/bin/bash
# Script para ejecutar Bot Trader Copilot en Linux/Mac
# Asegura que se use el entorno virtual correcto

echo "========================================"
echo "Bot Trader Copilot - Launcher Linux/Mac"
echo "========================================"
echo

# Verificar si el entorno virtual existe
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ ERROR: No se encuentra el entorno virtual .venv"
    echo "   Ejecuta primero: python3 -m venv .venv"
    echo "   Luego instala dependencias: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Activar entorno virtual
echo "✅ Activando entorno virtual..."
source .venv/bin/activate

# Verificar versión de Python
python3 -c "import sys; v=sys.version_info; print(f'Versión Python: {v.major}.{v.minor}.{v.micro}'); sys.exit(0 if v.major==3 and v.minor==11 else 1)"
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Se requiere Python 3.11.x"
    echo "   Versión actual:"
    python3 -c "import sys; print(sys.version)"
    exit 1
fi

echo "✅ Entorno verificado correctamente"
echo

# Ejecutar main.py con todos los argumentos pasados
echo "Ejecutando: python main.py $@"
python main.py "$@"

# Verificar si hubo error
if [ $? -ne 0 ]; then
    echo
    echo "❌ Se produjo un error durante la ejecución"
    exit 1
fi