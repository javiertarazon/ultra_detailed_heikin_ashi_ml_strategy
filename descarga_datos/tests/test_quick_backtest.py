import os
import sys
import json
from pathlib import Path

# Asegurar imports relativos funcionen
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validate_modular_system import validate_modular_system


def test_modular_system_validation():
    assert validate_modular_system() is True


def test_dashboard_results_exist_after_run(monkeypatch):
    """
    Test de humo: si existen resultados en data/dashboard_results, el formato es válido.
    No ejecuta el backtest completo para mantenerlo rápido.
    """
    base = Path(__file__).resolve().parent.parent / 'data' / 'dashboard_results'
    assert base.exists(), "No existe el directorio de resultados del dashboard"

    # Debe existir al menos el resumen global
    summary = base / 'global_summary.json'
    assert summary.exists(), "Falta global_summary.json"

    with open(summary, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert 'period' in data and 'metrics' in data

    # Validar al menos un archivo de símbolo
    symbol_files = list(base.glob('*_results.json'))
    symbol_files = [p for p in symbol_files if p.name != 'global_summary.json']
    assert symbol_files, "No hay archivos de resultados por símbolo"

    with open(symbol_files[0], 'r', encoding='utf-8') as f:
        d = json.load(f)
        assert 'strategies' in d and isinstance(d['strategies'], dict)
