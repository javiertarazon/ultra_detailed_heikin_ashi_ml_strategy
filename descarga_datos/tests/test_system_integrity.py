"""Test integral del sistema modular de backtesting.

Objetivos del usuario:
- Verificar que solo se usen datos históricos reales (no sintéticos).
- Validar normalización de métricas clave (win_rate en decimal 0-1, drawdown como % ya calculado, etc.).
- Confirmar consistencia de datos en base de datos (tabla principal y metadata coherente si existe).
- Asegurar que el dashboard refleja fielmente las métricas del backtest (comparando JSON vs resumen generado).
- Control centralizado por config.yaml (estrategias activas presentes y cargables).

Este test NO ejecuta un backtest completo (costoso); asume que `python main.py --mode backtest --backtest-only` se ejecutó previamente.
Si se requiere ejecución on-demand, se puede extender con un flag de entorno.
"""
from pathlib import Path
import json
import os
import sqlite3
import sys
import pytest
import importlib

# Paths base
BASE_DIR = Path(__file__).resolve().parent.parent
# Asegurar que la carpeta raíz (descarga_datos) esté en sys.path para imports tipo 'config', 'utils'
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
DATA_DIR = BASE_DIR / 'data' / 'dashboard_results'
CONFIG_DIR = BASE_DIR / 'config'
CONFIG_FILE = CONFIG_DIR / 'config.yaml'
DB_FILE = BASE_DIR / 'data' / 'data.db'

def test_config_and_strategies_active():
    """Verifica que la config exista y que las estrategias activas son importables."""
    assert CONFIG_FILE.exists(), "config.yaml no encontrado"
    from config.config_loader import load_config_from_yaml
    cfg = load_config_from_yaml()
    active = [k for k,v in cfg.backtesting.strategies.items() if v]
    assert active, "No hay estrategias activas en la configuración"
    # Intentar importar clases declaradas en orquestador dinámico
    from backtesting.backtesting_orchestrator import load_strategies_from_config
    loaded = load_strategies_from_config(cfg)
    assert set(active).issubset(set(loaded.keys())), "Algunas estrategias activas no se pudieron cargar"

def test_results_json_files_exist_and_structure():
    """Valida que existen archivos de resultados y estructura esperada."""
    assert DATA_DIR.exists(), "Directorio de resultados no existe (ejecuta backtest antes)."
    result_files = list(DATA_DIR.glob('*_results.json'))
    assert result_files, "No hay archivos *_results.json"
    for f in result_files:
        if f.name == 'global_summary.json' or 'realistic' in f.name:
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        # Validar formato flexible pero consistente
        assert isinstance(data, dict), f"Archivo {f.name} no contiene un dict"
        assert 'strategies' in data or 'symbol' in data or any('total_trades' in v for v in data.values() if isinstance(v, dict)), f"Formato inesperado en {f.name}"

def test_metrics_normalization_and_consistency():
    """Comprueba normalización de win_rate y coherencia trades = wins + losses."""
    from utils.dashboard import load_results, summarize_results_structured
    results, global_summary = load_results()  # type: ignore
    assert results, "Resultados vacíos"
    df = summarize_results_structured(results)
    assert not df.empty, "Resumen vacío"
    for sym, data in results.items():
        strategies = data.get('strategies', {}) if isinstance(data, dict) else {}
        for sname, sdata in strategies.items():
            if not isinstance(sdata, dict):
                continue
            total_trades = sdata.get('total_trades', 0) or 0
            wins = sdata.get('winning_trades', 0) or 0
            losses = sdata.get('losing_trades', 0) or 0
            # Permite cierta tolerancia si alguna métrica no se almacena
            if total_trades > 0 and wins + losses > 0:
                assert abs(total_trades - (wins + losses)) <= 1, f"Inconsistencia trades en {sym}-{sname}: {total_trades} != {wins}+{losses}"
            wr = sdata.get('win_rate', 0) or 0
            if wr > 1:  # Si viene en porcentaje
                assert wr <= 100, f"win_rate fuera de rango (porcentaje) {wr}"
            else:
                assert 0 <= wr <= 1, f"win_rate decimal fuera de rango {wr}"

def test_database_integrity_and_metadata():
    """Verifica integridad básica de la base de datos y metadata (si existe)."""
    assert DB_FILE.exists(), "Base de datos no encontrada"
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Verificar tablas clave si existen (no todas son obligatorias, así que se ignora ausencia)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert tables, "No hay tablas en la base de datos"
    # Metadata
    if 'data_metadata' in tables:
        cur.execute("PRAGMA table_info(data_metadata)")
        cols = [r[1] for r in cur.fetchall()]
        expected = {'symbol','timeframe','start_ts','end_ts','records','coverage_pct','asset_class','source_exchange','last_update_ts'}
        assert expected.issubset(cols), f"Faltan columnas de metadata: {expected - set(cols)}"
        # Muestreo de filas
        cur.execute("SELECT symbol,timeframe,start_ts,end_ts,records FROM data_metadata LIMIT 5")
        for row in cur.fetchall():
            sym, tf, start_ts, end_ts, recs = row
            assert sym and tf, "Symbol/timeframe inválidos en metadata"
            if start_ts and end_ts:
                assert end_ts >= start_ts, "Rango temporal invertido en metadata"
            if recs:
                assert recs > 0, "Records debe ser >0 en metadata"
    conn.close()

def test_global_summary_alignment():
    """Alinea global_summary con agregación calculada a partir de resultados por estrategia."""
    from utils.dashboard import load_results, summarize_results_structured
    results, global_summary = load_results()  # type: ignore
    assert 'metrics' in global_summary, "global_summary carece de sección metrics"
    df = summarize_results_structured(results)
    # Agregados calculados
    calc_total_pnl = float(df['total_pnl'].sum())
    calc_total_trades = int(df['total_trades'].sum())
    # Win rate promedio simple (no ponderado) de estrategias
    if len(df) > 0:
        calc_avg_win_rate = float(df['win_rate'].mean())
    else:
        calc_avg_win_rate = 0.0
    metrics = global_summary.get('metrics', {})
    # Tolerancias amplias por diferentes métodos de agregación (p.ej. win rate ponderado)
    assert abs(metrics.get('total_pnl', 0) - calc_total_pnl) < 1e-6, "P&L total en global_summary no coincide"
    assert metrics.get('total_trades', 0) == calc_total_trades, "Total trades global_summary no coincide"
    # Win rate: permitir diferencia <= 5 puntos porcentuales
    reported_wr = metrics.get('avg_win_rate', 0)
    if reported_wr > 1:  # si está como porcentaje
        reported_wr = reported_wr / 100.0
    assert abs(reported_wr - calc_avg_win_rate) <= 0.05, "Win rate promedio global inconsistente (>5pp)"

def test_no_synthetic_data_in_results():
    """Asegura que los archivos de resultados no contienen marcadores de datos sintéticos."""
    for f in DATA_DIR.glob('*_results.json'):
        with open(f, 'r', encoding='utf-8') as fh:
            txt = fh.read().lower()
            assert 'synthetic' not in txt, f"Marcador 'synthetic' encontrado en {f.name}"
            assert 'mock' not in txt, f"Marcador 'mock' encontrado en {f.name}"
            assert 'fake' not in txt, f"Marcador 'fake' encontrado en {f.name}"

def test_dashboard_summary_function_matches_manual():
    """Verifica que summarize_results_structured genere columnas esperadas y coherentes."""
    from utils.dashboard import load_results, summarize_results_structured
    results, _ = load_results()  # type: ignore
    df = summarize_results_structured(results)
    expected_cols = {'symbol','strategy','total_trades','win_rate','total_pnl','max_drawdown'}
    assert expected_cols.issubset(df.columns), f"Columnas faltantes en summary DF: {expected_cols - set(df.columns)}"
    # Reglas básicas
    assert (df['win_rate'] >= 0).all() and (df['win_rate'] <= 1).all(), "win_rate fuera de rango"
    assert not df.duplicated(['symbol','strategy']).any(), "Duplicados symbol/strategy en resumen"

# Nota: Se podrían añadir tests adicionales para validar fórmulas (Sharpe, etc.)
# si el motor de backtest expone cálculos deterministas y controlables en entorno de test.
