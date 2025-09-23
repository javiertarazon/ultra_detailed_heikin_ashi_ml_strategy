#!/usr/bin/env python3
"""
Script para generar informe de métricas de backtesting a partir de los JSONs en data/dashboard_results
"""
import json
from pathlib import Path
import yaml

def load_results(results_dir: Path):
    # Cargar lista de símbolos desde config.yaml
    cfg_path = Path(__file__).parent / 'config' / 'config.yaml'
    try:
        with open(cfg_path, 'r', encoding='utf-8') as cf:
            cfg = yaml.safe_load(cf)
        symbols_cfg = cfg.get('backtesting', {}).get('symbols', [])
    except Exception:
        symbols_cfg = []
    # Cargar resultados filtrando solo los símbolos de config
    # data: symbol -> {strategy_name: metrics}
    data = {}
    for f in results_dir.glob("*_results.json"):
        # Evitar archivos simplificados
        if f.name.endswith("_simplified_results.json"): continue
        js = json.loads(f.read_text(encoding='utf-8'))
        symbol = js.get('symbol')
        if symbol not in symbols_cfg:
            continue
        strategies = js.get('strategies', {})
        if not strategies:
            continue
        data[symbol] = strategies  # keep dict of strategy_name -> metrics
    # Cargar resumen global
    global_summary = {}
    summary_file = results_dir / 'global_summary.json'
    if summary_file.exists():
        global_summary = json.loads(summary_file.read_text(encoding='utf-8'))
    return data, global_summary


def print_report(data: dict, summary: dict):
    print("\nINFORME DE BACKTESTING - 5 SÍMBOLOS")
    print("=" * 50)
    print(f"Total símbolos: {summary.get('total_symbols', len(data))}")
    metrics = summary.get('metrics', {})
    print(f"P&L Global Total: ${metrics.get('total_pnl', 0):.2f}")
    print(f"Total trades global: {metrics.get('total_trades', 0)}")
    print(f"Win rate promedio: {metrics.get('avg_win_rate', 0):.2f}%")
    print(f"Balance final estimado: ${10000 + metrics.get('total_pnl', 0):.2f}")

    print("\nDetalle por símbolo:")
    print(f"{'Símbolo':<10} {'Estrategia':<15} {'PnL':>10} {'Trades':>8} {'Win%':>6} {'Rentable':>9} {'MaxDD':>8} {'CompT':>6} {'CompP':>8} {'Balance':>10}")
    print('-' * 70)
    for sym, strategies in data.items():
        for strat_name, m in strategies.items():
            pnl = m.get('total_pnl', 0)
            trades = m.get('total_trades', 0)
            win = m.get('win_rate', 0)
            profitable = 'Sí' if pnl > 0 else 'No'
            maxdd = m.get('max_drawdown', 0)
            comp_tr = m.get('compensation_trades', 0)
            comp_p = m.get('total_compensation_pnl', 0)
            balance = 10000 + pnl
            print(f"{sym:<10} {strat_name:<15} {pnl:10.2f} {trades:8d} {win:6.2f}% {profitable:>9} {maxdd:8.2f} {comp_tr:6d} {comp_p:8.2f} {balance:10.2f}")

if __name__ == '__main__':
    results_dir = Path(__file__).parent / 'data' / 'dashboard_results'
    data, summary = load_results(results_dir)
    if not data:
        print("No se encontraron resultados en", results_dir)
    else:
        print_report(data, summary)
