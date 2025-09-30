"""\nAuditoría de calidad de datos históricos.\n\nObjetivo: Detectar problemas de integridad que puedan distorsionar resultados de backtesting\nentre diferentes clases de activos (acciones, forex, cripto).\n\nMétricas por símbolo:\n- status: ok | missing | insufficient | empty\n- records: número total de velas\n- period_start / period_end\n- timeframe\n- expected_candles / actual_candles / coverage_pct\n- gaps: total_gaps, max_gap (en múltiplos del intervalo), first_gap_examples (hasta 3)\n- duplicates: count\n- volume: mean, median, std, zero_count, zero_pct, p95, p99, outliers_iqr, outliers_zscore\n- price_range: avg_true_range_pct (ATR relativo), close_volatility_pct (desv std / media)\n- density: candles_per_day (estimado)\n\nSalida: JSON en data/dashboard_results/data_audit.json y diccionario retornado.\n\nUso programático:\nfrom utils.data_audit import run_data_audit\nreport = run_data_audit(config, symbols=None, timeframe=None)\n"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from utils.storage import DataStorage
from utils.market_sessions import get_asset_class, expected_candles_for_range, timeframe_to_seconds
import asyncio
try:
    from core.downloader import AdvancedDataDownloader
except Exception:
    # Fallback si se usa import absoluto fuera del paquete
    from descarga_datos.core.downloader import AdvancedDataDownloader

logger = logging.getLogger(__name__)

TIMEFRAME_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
}


def _infer_timeframe_seconds(df: pd.DataFrame) -> Optional[int]:
    """Intenta inferir el tamaño del timeframe en segundos a partir de los primeros deltas."""
    if df is None or df.empty:
        return None
    ts = pd.to_datetime(df["timestamp"])
    deltas = ts.diff().dropna().dt.total_seconds()
    if deltas.empty:
        return None
    # Tomar el modo aproximado (delta más frecuente)
    mode_delta = deltas.round().value_counts().idxmax()
    return int(mode_delta)


def _expected_candle_count(start: pd.Timestamp, end: pd.Timestamp, interval_seconds: int) -> int:
    total_seconds = (end - start).total_seconds()
    if interval_seconds <= 0:
        return 0
    return int(total_seconds // interval_seconds) + 1  # incluir vela inicial


def _detect_gaps(ts: pd.Series, interval_seconds: int, max_examples: int = 3):
    gaps = []
    if len(ts) < 2 or interval_seconds <= 0:
        return {"total_gaps": 0, "max_gap_multiple": 0, "gap_examples": []}
    deltas = ts.diff().dt.total_seconds().fillna(0)
    expected = interval_seconds
    gap_rows = deltas[deltas > expected * 1.5]  # tolerancia 50%
    max_gap_multiple = 0
    examples = []
    for idx, delta in gap_rows.items():
        multiple = round(delta / expected, 2) if expected else 0
        max_gap_multiple = max(max_gap_multiple, multiple)
        if len(examples) < max_examples:
            prev_time = ts.loc[idx - 1] if (idx - 1) in ts.index else None
            examples.append({
                "prev": str(prev_time),
                "current": str(ts.loc[idx]),
                "delta_sec": int(delta),
                "multiple": multiple,
            })
    return {
        "total_gaps": int(len(gap_rows)),
        "max_gap_multiple": float(max_gap_multiple),
        "gap_examples": examples,
    }


def _apply_gap_fill(df: pd.DataFrame, gaps_info: dict, interval_sec: int, method: str, max_consec: int) -> int:
    """Aplica gap fill sintético al DataFrame"""
    if not gaps_info or gaps_info['total_gaps'] == 0:
        return 0

    synthetic_rows = []
    ts_series = df.set_index('timestamp')['close']

    for gap in gaps_info['gap_examples']:
        prev_ts = pd.Timestamp(gap['prev'])
        curr_ts = pd.Timestamp(gap['current'])
        multiple = gap['multiple']

        if multiple > max_consec:
            continue  # No rellenar gaps demasiado largos

        # Generar timestamps sintéticos
        synthetic_timestamps = []
        current_ts = prev_ts + pd.Timedelta(seconds=interval_sec)
        while current_ts < curr_ts:
            synthetic_timestamps.append(current_ts)
            current_ts += pd.Timedelta(seconds=interval_sec)

        # Crear velas sintéticas
        for ts in synthetic_timestamps:
            if method == 'forward':
                # Usar close de la vela previa
                prev_close = ts_series.asof(prev_ts)
                synthetic_rows.append({
                    'timestamp': ts,
                    'open': prev_close,
                    'high': prev_close,
                    'low': prev_close,
                    'close': prev_close,
                    'volume': 0.0,
                    'synthetic': 1
                })
            elif method == 'nan':
                # Velas con NaN
                synthetic_rows.append({
                    'timestamp': ts,
                    'open': np.nan,
                    'high': np.nan,
                    'low': np.nan,
                    'close': np.nan,
                    'volume': 0.0,
                    'synthetic': 1
                })

    if synthetic_rows:
        synth_df = pd.DataFrame(synthetic_rows)
        df = pd.concat([df, synth_df], ignore_index=True).sort_values('timestamp').reset_index(drop=True)

    return len(synthetic_rows)


def _analyze_volume(df: pd.DataFrame) -> Dict[str, Any]:
    if "volume" not in df.columns or df.empty:
        return {
            "mean": 0,
            "median": 0,
            "std": 0,
            "zero_count": 0,
            "zero_pct": 0.0,
            "p95": 0,
            "p99": 0,
            "outliers_iqr": 0,
            "outliers_zscore": 0,
        }
    v = df["volume"].astype(float)
    mean_v = v.mean()
    std_v = v.std(ddof=0)
    median_v = v.median()
    zero_count = int((v == 0).sum())
    zero_pct = float(zero_count / len(v) * 100)
    p95 = v.quantile(0.95)
    p99 = v.quantile(0.99)
    # Outliers IQR
    q1, q3 = v.quantile(0.25), v.quantile(0.75)
    iqr = q3 - q1
    upper_iqr = q3 + 1.5 * iqr
    outliers_iqr = int((v > upper_iqr).sum())
    # Outliers Z-score > 3 (evitar div/0)
    if std_v > 0:
        zscores = (v - mean_v) / std_v
        outliers_z = int((zscores.abs() > 3).sum())
    else:
        outliers_z = 0
    return {
        "mean": float(mean_v),
        "median": float(median_v),
        "std": float(std_v),
        "zero_count": zero_count,
        "zero_pct": round(zero_pct, 2),
        "p95": float(p95),
        "p99": float(p99),
        "outliers_iqr": outliers_iqr,
        "outliers_zscore": outliers_z,
    }


def _price_volatility_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"atr_pct": 0.0, "close_volatility_pct": 0.0}
    # ATR simple (true range rolling)
    high_low = (df["high"] - df["low"]).abs()
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    close_mean = df["close"].mean() or 0
    atr_pct = float((atr.mean() / close_mean * 100) if close_mean else 0)
    close_vol = df["close"].std(ddof=0)
    close_vol_pct = float((close_vol / close_mean * 100) if close_mean else 0)
    return {"atr_pct": round(atr_pct, 3), "close_volatility_pct": round(close_vol_pct, 3)}


def audit_symbol(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    requested_start: Optional[pd.Timestamp] = None,
    requested_end: Optional[pd.Timestamp] = None,
    session_aware: bool = True,
    gap_fill_cfg: Optional[dict] = None,
) -> Dict[str, Any]:
    """Audita un símbolo incluyendo:
    - Cobertura real vs rango contenido y vs rango solicitado (si se provee)
    - Gaps / duplicados
    - Consistencia de timeframe (deltas irregulares)
    - Validación de columnas normalizadas (rango 0..1 +/- tolerancia)
    - Métricas de volatilidad y volumen
    - Score de integridad sintético (0-100)
    """
    if df is None:
        return {"symbol": symbol, "timeframe": timeframe, "status": "missing"}
    if df.empty:
        return {"symbol": symbol, "timeframe": timeframe, "status": "empty"}

    # Normalizar timestamp a datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    start = df["timestamp"].min()
    end = df["timestamp"].max()
    inferred_sec = _infer_timeframe_seconds(df)
    configured_sec = TIMEFRAME_SECONDS.get(timeframe)
    interval_sec = configured_sec or inferred_sec or 0

    # Expected & coverage (sobre rango contenido únicamente) - session aware
    asset_class = get_asset_class(symbol)
    if session_aware and interval_sec:
        expected_internal = expected_candles_for_range(start, end, timeframe, asset_class)
    else:
        expected_internal = _expected_candle_count(start, end, interval_sec) if interval_sec else len(df)
    actual = len(df)
    coverage_internal = (actual / expected_internal * 100) if expected_internal else 100.0

    # Cobertura vs rango solicitado
    requested_start_ts = pd.to_datetime(requested_start) if requested_start else None
    requested_end_ts = pd.to_datetime(requested_end) if requested_end else None

    if requested_start_ts and requested_end_ts and interval_sec:
        if session_aware:
            expected_requested = expected_candles_for_range(requested_start_ts, requested_end_ts, timeframe, asset_class)
        else:
            expected_requested = _expected_candle_count(requested_start_ts, requested_end_ts, interval_sec)
        # Candles efectivamente dentro del rango solicitado
        df_requested_window = df[(df["timestamp"] >= requested_start_ts) & (df["timestamp"] <= requested_end_ts)]
        actual_requested = len(df_requested_window)
        coverage_requested = (actual_requested / expected_requested * 100) if expected_requested else 100.0
        # Missing leading / trailing
        missing_leading_sec = max(0, (start - requested_start_ts).total_seconds()) if start > requested_start_ts else 0
        missing_trailing_sec = max(0, (requested_end_ts - end).total_seconds()) if end < requested_end_ts else 0
        missing_leading_candles = int(missing_leading_sec // interval_sec) if interval_sec else 0
        missing_trailing_candles = int(missing_trailing_sec // interval_sec) if interval_sec else 0
    else:
        expected_requested = expected_internal
        actual_requested = actual
        coverage_requested = coverage_internal
        missing_leading_candles = 0
        missing_trailing_candles = 0

    # Deltas y mismatches timeframe
    if interval_sec and actual > 1:
        deltas = df["timestamp"].diff().dt.total_seconds().dropna()
        tolerance = interval_sec * 0.05  # 5% tolerancia
        mismatch = deltas[(deltas - interval_sec).abs() > tolerance]
        mismatch_pct = round((len(mismatch) / len(deltas)) * 100, 3)
    else:
        mismatch_pct = 0.0

    # Duplicados
    dup_count = int(df["timestamp"].duplicated().sum())

    # Gaps (internos)
    gaps_info = _detect_gaps(df["timestamp"], interval_sec) if interval_sec else {"total_gaps": 0, "max_gap_multiple": 0, "gap_examples": []}

    # Gap fill si está habilitado
    synthetic_filled = 0
    if gap_fill_cfg and gap_fill_cfg.get('enabled', False) and gaps_info['total_gaps'] > 0:
        method = gap_fill_cfg.get('method', 'forward')
        max_consec = gap_fill_cfg.get('max_consecutive', 6)
        synthetic_filled = _apply_gap_fill(df, gaps_info, interval_sec, method, max_consec)
        # Recalcular gaps después del fill
        if synthetic_filled > 0:
            gaps_info = _detect_gaps(df["timestamp"], interval_sec) if interval_sec else {"total_gaps": 0, "max_gap_multiple": 0, "gap_examples": []}

    # Volumen y volatilidad
    volume_stats = _analyze_volume(df)
    vol_metrics = _price_volatility_metrics(df)

    # Densidad (velas por día) basada en rango solicitado si existe, sino interno
    base_start_for_density = requested_start_ts or start
    base_end_for_density = requested_end_ts or end
    total_days_req = max((base_end_for_density - base_start_for_density).days, 1)
    candles_per_day_req = actual_requested / total_days_req

    # Validación de columnas normalizadas (0..1) excluyendo columnas absolutas
    exclude_cols = {
        'open','high','low','close','volume',
        'atr','adx','sar','rsi','macd','macd_signal',
        'bb_upper','bb_lower','ema_10','ema_20','ema_200','timestamp'
    }
    normalized_columns = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    out_of_range_cols = []
    for c in normalized_columns:
        col_min = df[c].min()
        col_max = df[c].max()
        if (col_min < -0.05) or (col_max > 1.05):  # tolerancia +/-5%
            out_of_range_cols.append({"column": c, "min": float(col_min), "max": float(col_max)})

    # Penalización de gaps se reduce si se rellenó sintéticamente
    remaining_gaps_penalty = gaps_info.get('total_gaps', 0) * 0.1

    # Score de integridad - AJUSTADO PARA DIFERENTES CLASES DE ACTIVOS
    integrity = 100.0

    # Obtener clase de activo para ajustar penalizaciones
    asset_class = get_asset_class(symbol)

    # Penalizaciones ajustadas por clase de activo
    if asset_class == 'crypto':
        # Cripto: espera cobertura casi perfecta
        integrity -= max(0, 100 - coverage_requested) * 0.8        # Penalización fuerte por falta de cobertura
        integrity -= remaining_gaps_penalty * 2                    # Gaps son raros en crypto
    elif asset_class == 'forex':
        # Forex: cobertura buena pero permite algunos gaps por mantenimiento
        # AJUSTE: Reducir penalización para aceptar 80%+ como suficiente
        integrity -= max(0, 100 - coverage_requested) * 0.5        # Penalización reducida
        integrity -= remaining_gaps_penalty * 1.0                  # Gaps menos penalizados
        # Bonus por buena cobertura forex
        if coverage_requested >= 80:
            integrity += 15  # Bonus mayor para compensar
    elif asset_class == 'equities_us':
        # Acciones US: cobertura limitada a horario bursátil, gaps fuera de sesión son normales
        integrity -= max(0, 100 - coverage_requested) * 0.3        # Penalización leve - horario limitado
        integrity -= remaining_gaps_penalty * 0.5                  # Gaps fuera de sesión no penalizan mucho
        # Bonus por datos dentro de sesión bursátil
        if coverage_requested >= 80:
            integrity += 10  # Bonus por buena cobertura en horario bursátil
    else:
        # Default: penalizaciones estándar
        integrity -= max(0, 100 - coverage_requested) * 0.5
        integrity -= remaining_gaps_penalty

    # Penalizaciones comunes a todas las clases
    integrity -= dup_count * 0.5                               # Duplicados siempre malos
    integrity -= mismatch_pct * 0.5                            # Deltas irregulares siempre malos
    integrity -= (len(out_of_range_cols) * 2)                  # Normalización fuera de rango siempre mala
    integrity -= (missing_leading_candles + missing_trailing_candles) * 0.05  # Falta bordes leve

    integrity = max(0.0, round(integrity, 2))

    status = "ok"
    if coverage_requested < 60 or integrity < 50:
        status = "insufficient"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": status,
        "records": actual,
        "synthetic_filled": synthetic_filled,
        "synthetic_pct": round((synthetic_filled / (actual + synthetic_filled) * 100),2) if synthetic_filled else 0.0,
        "period_start": str(start),
        "period_end": str(end),
        "requested_start": str(requested_start_ts) if requested_start_ts else None,
        "requested_end": str(requested_end_ts) if requested_end_ts else None,
        "interval_seconds": interval_sec,
        "expected_candles_internal": int(expected_internal),
        "actual_candles_internal": int(actual),
        "coverage_internal_pct": round(coverage_internal, 2),
        "expected_candles_requested": int(expected_requested),
        "actual_candles_requested": int(actual_requested),
        "coverage_requested_pct": round(coverage_requested, 2),
        "missing_leading_candles": missing_leading_candles,
        "missing_trailing_candles": missing_trailing_candles,
        "duplicates": dup_count,
    "gaps": gaps_info,
        "timeframe_mismatch_pct": mismatch_pct,
        "normalized_columns": normalized_columns,
        "normalized_out_of_range": out_of_range_cols,
        "volume": volume_stats,
        "volatility": vol_metrics,
        "candles_per_day_requested": round(candles_per_day_req, 2),
        "integrity_score": integrity,
    }


def run_data_audit(
    config,
    symbols: Optional[List[str]] = None,
    timeframe: Optional[str] = None,
    auto_fetch_missing: bool = True,
    incremental_edges: bool = True,
    session_aware: bool = True,
    min_coverage_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Ejecuta auditoría de datos para los símbolos y timeframe especificados.

    Args:
        config: Objeto de configuración cargado desde YAML.
        symbols: Lista opcional de símbolos a auditar; si None usa config.symbols.list.
        timeframe: Timeframe a auditar; si None usa config.data.timeframe (o config.backtesting.timeframe si existe).
    Returns:
        Diccionario con resultados por símbolo y agregados.
    """
    storage_path = f"{config.storage.path}/data.db"
    storage = DataStorage(storage_path)

    # Determinar símbolos y timeframe (prioridad: backtesting.symbols -> symbols.list -> data.symbols)
    cfg_symbols: List[str] = []
    if hasattr(config, 'backtesting') and hasattr(config.backtesting, 'symbols') and config.backtesting.symbols:
        try:
            # backtesting.symbols puede ser list ya parseada
            cfg_symbols = list(config.backtesting.symbols)
        except Exception:
            pass
    if not cfg_symbols and hasattr(config, "symbols") and hasattr(config.symbols, "list"):
        try:
            cfg_symbols = list(config.symbols.list)
        except Exception:
            pass
    if not cfg_symbols and hasattr(config, "data") and hasattr(config.data, "symbols"):
        try:
            cfg_symbols = list(config.data.symbols)
        except Exception:
            pass

    symbols = symbols or cfg_symbols
    if not symbols:
        raise ValueError("No se encontraron símbolos para auditoría")

    # Prioridad de timeframe: argumento -> backtesting -> data
    if timeframe is None:
        if hasattr(config, "backtesting") and hasattr(config.backtesting, "timeframe"):
            timeframe = config.backtesting.timeframe
        elif hasattr(config, "data") and hasattr(config.data, "timeframe"):
            timeframe = config.data.timeframe
        else:
            timeframe = "4h"

    results = {}
    summary = {
        "symbols_total": len(symbols),
        "symbols_ok": 0,
        "symbols_insufficient": 0,
        "symbols_missing": 0,
        "total_records": 0,
    }

    # Rango solicitado (backtesting)
    req_start = None
    req_end = None
    if hasattr(config, 'backtesting'):
        req_start = getattr(config.backtesting, 'start_date', None)
        req_end = getattr(config.backtesting, 'end_date', None)
    if req_start:
        req_start = pd.to_datetime(req_start)
    if req_end:
        req_end = pd.to_datetime(req_end)

    # Umbral cobertura (de config si existe)
    if min_coverage_pct is None:
        try:
            dq_cfg = getattr(getattr(config, 'backtesting', None), 'data_quality', None)
            min_coverage_pct = getattr(dq_cfg, 'min_coverage_pct', 95) if dq_cfg else 95
        except Exception:
            min_coverage_pct = 95

    # Paso 1: Auditoría inicial (sin descargas) para evaluar estado actual
    # Config gap fill desde config si existe
    gap_fill_cfg = None
    try:
        dq_cfg = getattr(getattr(config, 'backtesting', None), 'data_quality', None)
        if dq_cfg and getattr(dq_cfg, 'gap_fill', None):
            # gap_fill es dict (al cargar YAML tipo objeto simple); intentar convertir
            gf = dq_cfg.gap_fill
            gap_fill_cfg = {
                'enabled': getattr(gf, 'enabled', False),
                'method': getattr(gf, 'method', 'forward'),
                'max_consecutive': getattr(gf, 'max_consecutive', 6)
            }
    except Exception:
        gap_fill_cfg = None

    initial_audits = {}
    for sym in symbols:
        table_name = f"{sym.replace('/', '_').replace('.', '_')}_{timeframe}"
        df = storage.query_data(table_name)
        audit = audit_symbol(df, sym, timeframe, requested_start=req_start, requested_end=req_end, session_aware=session_aware, gap_fill_cfg=gap_fill_cfg)
        initial_audits[sym] = audit

    # Determinar símbolos missing/empty
    symbols_missing = [s for s, a in initial_audits.items() if a['status'] in ('missing','empty')]

    # Inicializar downloader si se requiere alguna acción
    downloader: Optional[AdvancedDataDownloader] = None
    if (auto_fetch_missing and symbols_missing) or incremental_edges:
        try:
            # Cargar config completo (ya provisto) y preparar downloader
            downloader = AdvancedDataDownloader(config)
            # Ejecutar asincronía de inicialización
            asyncio.run(downloader.initialize())
        except Exception as e:
            logger.warning(f"No se pudo inicializar downloader para acciones correctivas: {e}")
            downloader = None

    # Paso 2: Descargar símbolos totalmente missing
    if auto_fetch_missing and symbols_missing and downloader:
        try:
            req_start_str = req_start.strftime('%Y-%m-%d') if req_start else (pd.Timestamp.utcnow() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')
            req_end_str = req_end.strftime('%Y-%m-%d') if req_end else pd.Timestamp.utcnow().strftime('%Y-%m-%d')
            logger.info(f"Auto-descargando símbolos missing: {symbols_missing}")
            data_dict = asyncio.run(downloader.download_multiple_symbols(symbols_missing, timeframe, req_start_str, req_end_str))
            asyncio.run(downloader.process_and_save_data(data_dict, timeframe, save_csv=False))
        except Exception as e:
            logger.error(f"Error auto-descargando símbolos missing: {e}")

    # Paso 3: Incremental edges para símbolos insufficient con bordes faltantes
    if incremental_edges and downloader:
        edge_targets = [s for s, a in initial_audits.items() if a['status'] == 'insufficient' and (a.get('missing_leading_candles',0) > 0 or a.get('missing_trailing_candles',0) > 0)]
        if edge_targets:
            logger.info(f"Intentando mejora incremental de bordes para: {edge_targets}")
        for sym in edge_targets:
            audit = initial_audits[sym]
            missing_lead = audit.get('missing_leading_candles',0)
            missing_trail = audit.get('missing_trailing_candles',0)
            if missing_lead==0 and missing_trail==0:
                continue
            table_name = f"{sym.replace('/', '_').replace('.', '_')}_{timeframe}"
            existing_df = storage.query_data(table_name)
            if existing_df is None or existing_df.empty:
                continue
            existing_df = existing_df.sort_values('timestamp')
            existing_start = existing_df['timestamp'].min()
            existing_end = existing_df['timestamp'].max()
            leading_df = None
            trailing_df = None
            try:
                if missing_lead > 0 and req_start and existing_start > req_start:
                    lead_start = req_start
                    lead_end = existing_start - pd.Timedelta(seconds=timeframe_to_seconds(timeframe))
                    if lead_end > lead_start:
                        logger.info(f"{sym}: descargando tramo leading {lead_start.date()} -> {lead_end.date()}")
                        lead_data = asyncio.run(downloader.download_multiple_symbols([sym], timeframe, lead_start.strftime('%Y-%m-%d'), lead_end.strftime('%Y-%m-%d')))
                        leading_df = lead_data.get(sym)
                if missing_trail > 0 and req_end and existing_end < req_end:
                    trail_start = existing_end + pd.Timedelta(seconds=timeframe_to_seconds(timeframe))
                    trail_end = req_end
                    if trail_end > trail_start:
                        logger.info(f"{sym}: descargando tramo trailing {trail_start.date()} -> {trail_end.date()}")
                        trail_data = asyncio.run(downloader.download_multiple_symbols([sym], timeframe, trail_start.strftime('%Y-%m-%d'), trail_end.strftime('%Y-%m-%d')))
                        trailing_df = trail_data.get(sym)
            except Exception as e:
                logger.warning(f"{sym}: error descarga incremental edges: {e}")
            # Combinar si hay nuevos datos
            add_frames = [f for f in [leading_df, existing_df, trailing_df] if f is not None and not f.empty]
            if len(add_frames) > 1:
                combined = pd.concat(add_frames, ignore_index=True)
                combined = combined.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
                try:
                    asyncio.run(downloader.process_and_save_data({sym: combined}, timeframe, save_csv=False))
                except Exception as e:
                    logger.warning(f"{sym}: fallo al guardar combinación edges: {e}")

    # Paso 4: Segunda pasada de auditoría tras acciones correctivas
    for sym in symbols:
        table_name = f"{sym.replace('/', '_').replace('.', '_')}_{timeframe}"
        df = storage.query_data(table_name)
        audit = audit_symbol(df, sym, timeframe, requested_start=req_start, requested_end=req_end, session_aware=session_aware, gap_fill_cfg=gap_fill_cfg)
        # Evaluar status con umbral de cobertura solicitado
        if audit.get('coverage_requested_pct',0) < min_coverage_pct and audit['status'] == 'ok':
            audit['status'] = 'insufficient'
        results[sym] = audit
        summary["total_records"] += audit.get("records", 0)
        st = audit.get("status")
        if st == "ok":
            summary["symbols_ok"] += 1
        elif st == "insufficient":
            summary["symbols_insufficient"] += 1
        else:
            summary["symbols_missing"] += 1

    # Cerrar downloader si se abrió
    if downloader:
        try:
            asyncio.run(downloader.shutdown())
        except Exception:
            pass

    # Estadísticas agregadas de integridad
    integrity_scores = [r.get('integrity_score', 0) for r in results.values() if r.get('status') != 'missing']
    if integrity_scores:
        summary['integrity_score_avg'] = round(float(np.mean(integrity_scores)), 2)
        summary['integrity_score_min'] = round(float(np.min(integrity_scores)), 2)
    else:
        summary['integrity_score_avg'] = 0.0
        summary['integrity_score_min'] = 0.0

    # Agregados de volumen (comparar escalas relativas entre activos)
    volume_means = [r["volume"]["mean"] for r in results.values() if r.get("status") in ("ok", "insufficient") and r.get("volume", {}).get("mean", 0) > 0]
    if volume_means:
        median_mean = float(np.median(volume_means))
        dispersion = float(np.std(volume_means) / (median_mean or 1) * 100)
    else:
        median_mean = 0.0
        dispersion = 0.0

    summary["volume_mean_median_of_means"] = round(median_mean, 3)
    summary["volume_means_dispersion_pct"] = round(dispersion, 2)

    report = {"summary": summary, "results": results, "timeframe": timeframe}

    # Guardar JSON
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "dashboard_results")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "data_audit.json")
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Auditoría guardada en {out_file}")
    except Exception as e:
        logger.error(f"No se pudo guardar auditoría: {e}")

    return report


if __name__ == "__main__":  # Ejecución directa para pruebas rápidas
    from config.config_loader import load_config_from_yaml
    cfg = load_config_from_yaml()
    rep = run_data_audit(cfg)
    print(json.dumps(rep["summary"], indent=2))
