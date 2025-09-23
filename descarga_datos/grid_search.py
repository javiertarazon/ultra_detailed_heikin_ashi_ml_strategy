#!/usr/bin/env python3
"""
Grid search para optimizar parámetros de compensación: compensation_loss_threshold, compensation_size_multiplier, compensation_tp_percent.
Ejecuta main.py para cada combinación y almacena el global_summary.json con resultados.
"""
import subprocess
import json
from pathlib import Path
import itertools
import sys

def run_combination(loss_th, size_mult, tp_percent):
    # Ejecuta main.py con variables de entorno que el script interprete para override
    env = {
        **subprocess.os.environ,
        'COMP_LOSS_TH': str(loss_th),
        'COMP_SIZE_MULT': str(size_mult),
        'COMP_TP_PCT': str(tp_percent)
    }
    subprocess.run([
        sys.executable,
        'main.py',
        '--no-dashboard'
    ], cwd=Path(__file__).parent, env=env)
    # Leer resumen global
    summary_file = Path(__file__).parent / 'data' / 'dashboard_results' / 'global_summary.json'
    if not summary_file.exists():
        return None
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    summary['params'] = {
        'loss_threshold': loss_th,
        'size_multiplier': size_mult,
        'tp_percent': tp_percent
    }
    return summary

if __name__ == '__main__':
    out = []
    # Definir rangos ajustados para mejor optimización
    loss_range = [0.1, 0.5, 1.0, 1.5, 2.0]
    size_range = [0.5, 1.0, 1.5, 2.0, 2.5]
    tp_range = [0.1, 0.25, 0.5, 1.0, 1.5]

    for loss_th, size_mult, tp_pct in itertools.product(loss_range, size_range, tp_range):
        print(f"Probando {loss_th=} {size_mult=} {tp_pct=}")
        res = run_combination(loss_th, size_mult, tp_pct)
        if res:
            out.append(res)
    # Guardar resultados de grid_search
    Path(__file__).parent.joinpath('grid_search_results.json').write_text(
        json.dumps(out, indent=2), encoding='utf-8'
    )
    print("Grid search completado. Resultados en grid_search_results.json")
    
    # Análisis de mejores resultados
    if out:
        # Ordenar por P&L total descendente
        best = max(out, key=lambda x: x.get('metrics', {}).get('total_pnl', 0))
        print(f"Mejor combinación: {best['params']}")
        print(f"P&L Total: ${best['metrics']['total_pnl']:.2f}")
        print(f"Win Rate Promedio: {best['metrics']['avg_win_rate']:.1f}%")
