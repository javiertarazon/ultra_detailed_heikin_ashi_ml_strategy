#!/usr/bin/env python3
"""
Script para lanzar el dashboard de manera robusta
"""
import subprocess
import sys
import os
import time

def launch_dashboard():
    """Lanza el dashboard y lo mantiene corriendo"""
    try:
        # Cambiar al directorio raíz del proyecto
        project_root = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_root)

        print("🚀 Iniciando Dashboard de Backtesting Avanzado...")
        print("📊 Sistema Modular - Análisis Comparativo de Estrategias")
        print("=" * 60)

        # Comando para ejecutar streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", "descarga_datos/dashboard.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ]

        print(f"📋 Ejecutando: {' '.join(cmd)}")
        print("🌐 Dashboard disponible en: http://localhost:8501")
        print("⏹️  Presiona Ctrl+C para detener el dashboard")
        print("=" * 60)

        # Ejecutar streamlit
        process = subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar dashboard: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Dashboard detenido por el usuario")
        return True
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = launch_dashboard()
    sys.exit(0 if success else 1)