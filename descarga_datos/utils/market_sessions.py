"""Market session utilities.

Proporciona funciones para clasificar símbolos por clase de activo y calcular
expected candles en un rango temporal considerando horario de negociación.

Clases soportadas:
- crypto: 24/7
- forex: 24/5 (cierra fin de semana aprox. viernes 21:00 UTC a domingo 21:00 UTC)
- equities_us: 13:30-20:00 UTC (6.5h) días hábiles (lunes-viernes, excepto fines de semana)

Estas funciones se usan para:
- Ajustar expected_candles en auditoría (evitando penalizar acciones fuera de sesión)
- Evaluar cobertura real y decidir descargas incrementales
"""
from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional

EQUITY_SUFFIXES = ("_US", ".US")
FOREX_PAIRS = {"EURUSD","USDJPY","GBPUSD","USDCHF","AUDUSD","USDCAD","NZDUSD","EURGBP","EURJPY","GBPJPY"}

# Cache simple para performance
_CLASS_CACHE = {}


def get_asset_class(symbol: str) -> str:
    if symbol in _CLASS_CACHE:
        return _CLASS_CACHE[symbol]
    asset_class = "crypto"
    if symbol.replace('_','').upper() in FOREX_PAIRS or symbol.upper() in FOREX_PAIRS:
        asset_class = "forex"
    elif any(symbol.endswith(suf) for suf in EQUITY_SUFFIXES):
        asset_class = "equities_us"
    elif '/' in symbol:  # heurística: BASE/QUOTE => crypto
        asset_class = "crypto"
    _CLASS_CACHE[symbol] = asset_class
    return asset_class


def timeframe_to_seconds(timeframe: str) -> int:
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == 'm':
        return value * 60
    if unit == 'h':
        return value * 3600
    if unit == 'd':
        return value * 86400
    raise ValueError(f"Timeframe no soportado: {timeframe}")


def expected_candles_for_range(start: pd.Timestamp, end: pd.Timestamp, timeframe: str, asset_class: str) -> int:
    """Calcula número esperado de velas respetando horario de mercado.

    Para equities_us se cuenta solo el bloque 13:30-20:00 UTC (6.5h) en días hábiles.
    Para forex se omiten fines de semana (sábado completo y domingo hasta 21:00 UTC aprox.).
    Para crypto se asume 24/7.
    """
    if end <= start:
        return 0
    tf_sec = timeframe_to_seconds(timeframe)

    if asset_class == 'crypto':
        total_sec = (end - start).total_seconds()
        return int(total_sec // tf_sec) + 1

    total_candles = 0
    current = start.floor('D')
    end_day = end.floor('D')
    loop_count = 0  # Protección contra bucles infinitos
    days_diff = (end_day - current).days

    # Log para debug si el rango es muy amplio
    if days_diff > 1000:
        print(f"WARNING: Rango muy amplio para {asset_class}: {days_diff} días de {start} a {end}")

    while current <= end_day:
        loop_count += 1
        if loop_count > 10000:  # Límite de seguridad
            print(f"ERROR: Bucle infinito detectado para {asset_class}, abortando")
            break
        weekday = current.weekday()  # 0 lunes ... 6 domingo
        day_start = current
        day_end = current + pd.Timedelta(days=1)

        if asset_class == 'equities_us':
            if weekday < 5:  # solo lunes-viernes
                session_open = current + pd.Timedelta(hours=13, minutes=30)
                session_close = current + pd.Timedelta(hours=20)
                seg_start = max(session_open, start)
                seg_end = min(session_close, end)
                if seg_end > seg_start:
                    span_sec = (seg_end - seg_start).total_seconds()
                    total_candles += int(span_sec // tf_sec) + 1
        elif asset_class == 'forex':
            # Forex 24h días hábiles. Fines de semana se excluyen.
            if weekday < 5:  # lunes-viernes
                seg_start = max(day_start, start)
                seg_end = min(day_end, end)
                if seg_end > seg_start:
                    span_sec = (seg_end - seg_start).total_seconds()
                    total_candles += int(span_sec // tf_sec) + 1
        else:  # fallback
            seg_start = max(day_start, start)
            seg_end = min(day_end, end)
            if seg_end > seg_start:
                span_sec = (seg_end - seg_start).total_seconds()
                total_candles += int(span_sec // tf_sec) + 1

        current += pd.Timedelta(days=1)

    return total_candles

__all__ = ["get_asset_class","expected_candles_for_range","timeframe_to_seconds"]
