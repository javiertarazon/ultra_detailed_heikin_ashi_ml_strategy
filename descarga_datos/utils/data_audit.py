#!/usr/bin/env python3
"""
AUDITORÍA DE CALIDAD DE DATOS
=============================

Módulo para validar la calidad, integridad y consistencia de los datos históricos
descargados para backtesting. Verifica problemas comunes como:
- Datos faltantes o NaN
- Gaps temporales
- Anomalías en precios (OHLC)
- Volumen inconsistente
- Problemas de normalización
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
from datetime import datetime, timedelta
import os
import sys

# Agregar directorio padre al path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger
from utils.storage import DataStorage

# Configurar logging
logger = get_logger(__name__)

class DataAuditor:
    """
    Auditor de calidad de datos históricos
    """

    def __init__(self, config=None):
        self.config = config or load_config_from_yaml()
        self.storage = DataStorage()
        self.issues_found = []
        self.quality_score = 100.0

    def audit_symbol_data(self, symbol: str, timeframe: str = '1d') -> Dict[str, Any]:
        """
        Auditar datos de un símbolo específico
        """
        logger.info(f"🔍 Iniciando auditoría de {symbol} en {timeframe}")

        # Construir path del CSV
        csv_filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
        csv_path = Path(__file__).parent.parent / 'data' / 'csv' / csv_filename
        
        # Cargar datos desde CSV
        if not csv_path.exists():
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'MISSING',
                'issues': [f'Archivo CSV no encontrado: {csv_path}'],
                'quality_score': 0.0
            }
        
        try:
            data = pd.read_csv(csv_path)
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data.set_index('timestamp', inplace=True)
        except Exception as e:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'ERROR',
                'issues': [f'Error cargando CSV: {str(e)}'],
                'quality_score': 0.0
            }

        if data.empty:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'EMPTY',
                'issues': ['Archivo CSV está vacío'],
                'quality_score': 0.0
            }

        issues = []
        quality_score = 100.0

        # 1. Verificar estructura básica
        structure_issues = self._audit_data_structure(data, symbol)
        issues.extend(structure_issues)
        quality_score -= len(structure_issues) * 5

        # 2. Verificar integridad temporal
        temporal_issues = self._audit_temporal_integrity(data, timeframe, symbol)
        issues.extend(temporal_issues)
        quality_score -= len(temporal_issues) * 3

        # 3. Verificar calidad de precios
        price_issues = self._audit_price_quality(data, symbol)
        issues.extend(price_issues)
        quality_score -= len(price_issues) * 4

        # 4. Verificar volumen
        volume_issues = self._audit_volume_quality(data, symbol)
        issues.extend(volume_issues)
        quality_score -= len(volume_issues) * 2

        # 5. Verificar normalización
        normalization_issues = self._audit_normalization(data, symbol)
        issues.extend(normalization_issues)
        quality_score -= len(normalization_issues) * 3

        quality_score = max(0.0, min(100.0, quality_score))

        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_records': len(data),
            'date_range': f"{data.index.min()} to {data.index.max()}",
            'status': 'GOOD' if quality_score >= 80 else 'WARNING' if quality_score >= 60 else 'CRITICAL',
            'quality_score': round(quality_score, 1),
            'issues_count': len(issues),
            'issues': issues[:10],  # Limitar a 10 issues para reporte
            'recommendations': self._generate_recommendations(issues, quality_score)
        }

        logger.info(f"✅ Auditoría completada: {symbol} - Score: {quality_score:.1f}% - {len(issues)} issues")
        return result

    def _audit_data_structure(self, data: pd.DataFrame, symbol: str) -> List[str]:
        """Verificar estructura básica de datos"""
        issues = []

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                issues.append(f"Columna requerida faltante: {col}")

        # Verificar tipos de datos
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in data.columns:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    issues.append(f"Columna {col} no es numérica")

        # Verificar índice temporal
        if not isinstance(data.index, pd.DatetimeIndex):
            issues.append("Índice no es DatetimeIndex")

        return issues

    def _audit_temporal_integrity(self, data: pd.DataFrame, timeframe: str, symbol: str) -> List[str]:
        """Verificar integridad temporal"""
        issues = []

        if len(data) < 2:
            return issues

        # Calcular intervalos esperados
        if timeframe == '1d':
            expected_interval = pd.Timedelta(days=1)
        elif timeframe == '4h':
            expected_interval = pd.Timedelta(hours=4)
        elif timeframe == '1h':
            expected_interval = pd.Timedelta(hours=1)
        else:
            expected_interval = pd.Timedelta(hours=1)  # default

        # Calcular gaps
        time_diffs = data.index.to_series().diff()
        gaps = time_diffs[time_diffs > expected_interval * 1.5]  # 50% de tolerancia

        if len(gaps) > 0:
            issues.append(f"{len(gaps)} gaps temporales detectados (máx: {gaps.max()})")

        # Verificar duplicados
        duplicates = data.index.duplicated().sum()
        if duplicates > 0:
            issues.append(f"{duplicates} registros duplicados en timestamp")

        return issues

    def _audit_price_quality(self, data: pd.DataFrame, symbol: str) -> List[str]:
        """Verificar calidad de precios OHLC"""
        issues = []

        # Verificar valores NaN
        nan_counts = data[['open', 'high', 'low', 'close']].isna().sum()
        for col, count in nan_counts.items():
            if count > 0:
                issues.append(f"{count} valores NaN en columna {col}")

        # Verificar lógica OHLC
        invalid_ohlc = (
            (data['high'] < data['low']) |
            (data['high'] < data['open']) |
            (data['high'] < data['close']) |
            (data['low'] > data['open']) |
            (data['low'] > data['close'])
        ).sum()

        if invalid_ohlc > 0:
            issues.append(f"{invalid_ohlc} registros con OHLC inválido")

        # Verificar precios negativos o cero
        negative_prices = (data[['open', 'high', 'low', 'close']] <= 0).sum().sum()
        if negative_prices > 0:
            issues.append(f"{negative_prices} precios negativos o cero")

        # Verificar volatilidad extrema
        returns = data['close'].pct_change()
        extreme_returns = (returns.abs() > 0.5).sum()  # >50% cambio
        if extreme_returns > 0:
            issues.append(f"{extreme_returns} cambios de precio extremos (>50%)")

        return issues

    def _audit_volume_quality(self, data: pd.DataFrame, symbol: str) -> List[str]:
        """Verificar calidad del volumen"""
        issues = []

        if 'volume' not in data.columns:
            return issues

        # Verificar valores NaN en volumen
        nan_volume = data['volume'].isna().sum()
        if nan_volume > 0:
            issues.append(f"{nan_volume} valores NaN en volumen")

        # Verificar volumen cero
        zero_volume = (data['volume'] == 0).sum()
        if zero_volume > 0:
            issues.append(f"{zero_volume} registros con volumen cero")

        # Verificar volumen negativo
        negative_volume = (data['volume'] < 0).sum()
        if negative_volume > 0:
            issues.append(f"{negative_volume} registros con volumen negativo")

        return issues

    def _audit_normalization(self, data: pd.DataFrame, symbol: str) -> List[str]:
        """Verificar normalización de datos"""
        issues = []

        # Verificar columnas normalizadas faltantes
        expected_normalized_cols = ['atr', 'stoch_k', 'stoch_d', 'rsi', 'macd', 'macd_signal', 'macd_hist']
        missing_normalized = [col for col in expected_normalized_cols if col not in data.columns]
        if missing_normalized:
            issues.append(f"Columnas normalizadas faltantes: {missing_normalized}")

        # Verificar valores NaN en columnas normalizadas
        for col in expected_normalized_cols:
            if col in data.columns:
                nan_count = data[col].isna().sum()
                if nan_count > len(data) * 0.1:  # >10% NaN
                    issues.append(f"Columna {col} tiene {nan_count} NaN (>10%)")

        return issues

    def _generate_recommendations(self, issues: List[str], quality_score: float) -> List[str]:
        """Generar recomendaciones basadas en issues encontrados"""
        recommendations = []

        if quality_score < 60:
            recommendations.append("CRÍTICO: Re-descargar datos completos")
        elif quality_score < 80:
            recommendations.append("ADVERTENCIA: Revisar y corregir datos")

        if any('NaN' in issue for issue in issues):
            recommendations.append("Corregir valores NaN con interpolación o re-descarga")

        if any('gap' in issue.lower() for issue in issues):
            recommendations.append("Rellenar gaps temporales con datos históricos")

        if any('ohlc' in issue.lower() for issue in issues):
            recommendations.append("Corregir lógica OHLC inválida")

        if any('duplicado' in issue.lower() for issue in issues):
            recommendations.append("Eliminar registros duplicados")

        if not recommendations:
            recommendations.append("Datos de buena calidad - listo para backtesting")

        return recommendations

def run_data_audit(config=None, symbols: List[str] = None, timeframe: str = '1d',
                  skip_download: bool = False) -> Dict[str, Any]:
    """
    Ejecutar auditoría completa de datos

    Args:
        config: Configuración del sistema
        symbols: Lista de símbolos a auditar (None = usar config)
        timeframe: Timeframe a auditar
        skip_download: Si True, no intentar correcciones automáticas

    Returns:
        Dict con reporte completo de auditoría
    """
    logger.info("🚀 Iniciando auditoría completa de calidad de datos")

    auditor = DataAuditor(config)

    # Determinar símbolos a auditar
    if symbols is None:
        if hasattr(config, 'backtesting') and hasattr(config.backtesting, 'symbols'):
            symbols = config.backtesting.symbols
        else:
            symbols = ['BTC/USDT', 'TSLA/US']  # default

    if isinstance(symbols, str):
        symbols = [symbols]

    logger.info(f"📊 Auditando {len(symbols)} símbolos en {timeframe}")

    # Ejecutar auditoría por símbolo
    results = {}
    total_score = 0.0
    critical_issues = 0

    for symbol in symbols:
        try:
            result = auditor.audit_symbol_data(symbol, timeframe)
            results[symbol] = result
            total_score += result['quality_score']

            if result['status'] == 'CRITICAL':
                critical_issues += 1

            issues_count = result.get('issues_count', 0)
            logger.info(f"✅ {symbol}: Score {result['quality_score']:.1f}% - {issues_count} issues")

        except Exception as e:
            logger.error(f"❌ Error auditando {symbol}: {e}")
            results[symbol] = {
                'symbol': symbol,
                'status': 'ERROR',
                'error': str(e),
                'quality_score': 0.0,
                'issues_count': 0
            }

    # Calcular estadísticas globales
    avg_score = total_score / len(symbols) if symbols else 0.0
    
    # Contar símbolos por estado
    symbols_missing = sum(1 for r in results.values() if r.get('status') == 'MISSING')
    symbols_insufficient = sum(1 for r in results.values() if r.get('status') in ['CRITICAL', 'ERROR', 'EMPTY'])

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_symbols': len(symbols),
        'average_quality_score': round(avg_score, 1),
        'critical_issues': critical_issues,
        'symbols_missing': symbols_missing,
        'symbols_insufficient': symbols_insufficient,
        'symbols_audited': symbols,
        'timeframe': timeframe,
        'results': results
    }

    # Guardar reporte
    report_path = Path(__file__).parent.parent / "data" / "dashboard_results" / "data_audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"💾 Reporte guardado en {report_path}")
    logger.info(f"📊 Auditoría completada - Score promedio: {avg_score:.1f}%")

    return summary

if __name__ == '__main__':
    # Ejecutar auditoría cuando se llama directamente
    config = load_config_from_yaml()
    report = run_data_audit(config)
    print(f"\n📊 AUDITORÍA COMPLETADA")
    print(f"Score promedio: {report['average_quality_score']:.1f}%")
    print(f"Símbolos auditados: {report['total_symbols']}")
    print(f"Issues críticos: {report['critical_issues']}")
    print(f"Reporte guardado en data/dashboard_results/data_audit.json")