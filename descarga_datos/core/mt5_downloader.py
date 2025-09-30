#!/usr/bin/env python3
"""
MT5 Data Downloader - Descarga datos de acciones desde MetaTrader 5
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging
import time
import asyncio

# Intentar importar MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 no disponible - solo se usarán datos de CCXT")

class MT5Downloader:
    """Downloader para datos de acciones desde MT5"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.max_retries = getattr(config, 'max_retries', 3) if hasattr(config, 'max_retries') else 3
        self.retry_delay = getattr(config, 'retry_delay', 5) if hasattr(config, 'retry_delay') else 5

    def initialize(self) -> bool:
        """Inicializa la conexión con MT5"""
        if not MT5_AVAILABLE:
            self.logger.warning("MT5 no disponible")
            return False

        try:
            if not mt5.initialize():
                self.logger.error(f"Error al inicializar MT5: {mt5.last_error()}")
                return False

            # Login si se proporcionan credenciales
            if hasattr(self.config, 'mt5') and self.config.mt5.login:
                if not mt5.login(
                    self.config.mt5.login,
                    password=self.config.mt5.password,
                    server=self.config.mt5.server
                ):
                    self.logger.error(f"Error en login MT5: {mt5.last_error()}")
                    return False

            self.connected = True
            self.logger.info("MT5 conectado correctamente")
            # Loguear cantidad de símbolos disponibles para diagnóstico
            try:
                symbols = mt5.symbols_get()
                if symbols:
                    self.logger.info(f"MT5 símbolos disponibles: {len(symbols)}")
                    # Muestra algunos ejemplos para debugging rápido
                    sample = [s.name for s in symbols[:10]]
                    self.logger.debug(f"Ejemplos símbolos MT5: {sample}")
            except Exception as lsym:
                self.logger.debug(f"No se pudieron listar símbolos MT5: {lsym}")
            return True

        except Exception as e:
            self.logger.error(f"Error inicializando MT5: {e}")
            return False

    def shutdown(self):
        """Cierra la conexión con MT5"""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("MT5 desconectado")

    def _retry_operation(self, operation, *args, **kwargs):
        """Ejecuta una operación con reintentos"""
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Intento {attempt + 1} falló: {e}. Reintentando en {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"Todos los intentos fallaron: {e}")
                    raise e

    def download_symbol_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Descarga datos históricos de un símbolo desde MT5 con estrategia mejorada

        Args:
            symbol: Símbolo (ej: "AAPL.US", "TSLA.US")
            timeframe: Timeframe (ej: "1h", "1d")
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)

        Returns:
            DataFrame con datos OHLCV o None si falla
        """
        if not self.connected:
            self.logger.error("MT5 no está conectado")
            return None

        try:
            # Convertir timeframe a MT5
            mt5_timeframe = self._convert_timeframe(timeframe)
            if mt5_timeframe is None:
                self.logger.error(f"Timeframe no soportado: {timeframe}")
                return None

            # Convertir fechas
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # ESTRATEGIA MEJORADA: Extender rangos de manera inteligente
            # Para acciones, extender 1 año antes del inicio solicitado para obtener contexto,
            # pero no tanto como para descargar datos irrelevantes
            if symbol.endswith(('_US', '.US')) or '.' in symbol:
                # Para acciones: 1 año antes del inicio solicitado
                extended_start = start_dt - timedelta(days=365)
                self.logger.info(f"MT5 Acciones: Extendiendo 1 año: {start_date} a {end_date} → {extended_start.strftime('%Y-%m-%d')} a {end_date}")
            else:
                # Para forex: mantener 1 año de extensión
                extended_start = start_dt - timedelta(days=365)
                self.logger.info(f"MT5 Forex: Extendiendo 1 año: {start_date} a {end_date} → {extended_start.strftime('%Y-%m-%d')} a {end_date}")

            # Verificar símbolo disponible y realizar alias si es necesario
            original_symbol = symbol
            available_symbols = set(self.get_available_symbols())
            if symbol not in available_symbols:
                # Estrategias de alias mejoradas para acciones
                alias_candidates = []

                # 1. Reemplazar '_' por '.' (ej: AAPL_US -> AAPL.US)
                if '_' in symbol:
                    alias_candidates.append(symbol.replace('_', '.'))

                # 2. Para acciones, intentar sin sufijo (ej: NVDA_US -> NVDA)
                if symbol.endswith('_US'):
                    base_symbol = symbol[:-3]  # Remover '_US'
                    alias_candidates.extend([base_symbol, f"{base_symbol}.US", f"{base_symbol}."])

                # 3. Para forex, intentar variaciones
                elif symbol.replace('_', '').upper() in ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY']:
                    # Forex normalmente no necesita alias, pero algunos brokers usan diferentes formatos
                    pass

                # Intentar cada alias candidato
                for alias in alias_candidates:
                    if alias in available_symbols:
                        self.logger.info(f"Alias MT5: usando '{alias}' en lugar de '{symbol}'")
                        symbol = alias
                        break
                else:
                    self.logger.warning(f"Símbolo {symbol} no encontrado en MT5 después de probar {len(alias_candidates)} aliases. Total símbolos disponibles: {len(available_symbols)}")
                    # Log algunos símbolos disponibles para debug
                    sample_symbols = sorted(list(available_symbols))[:10]
                    self.logger.info(f"Símbolos disponibles (muestra): {sample_symbols}")
                    return None

            # Seleccionar símbolo (algunos brokers requieren symbol_select)
            try:
                if MT5_AVAILABLE:
                    mt5.symbol_select(symbol, True)
            except Exception as se:
                self.logger.debug(f"symbol_select fallo para {symbol}: {se}")

            # ESTRATEGIA MEJORADA: Intentar descarga con estrategias optimizadas
            # Para acciones necesitamos más datos en el período solicitado
            if symbol.endswith(('_US', '.US')) or '.' in symbol:
                # Estrategias agresivas para acciones enfocadas en período actual
                download_strategies = [
                    (extended_start, end_dt, "rango extendido 1 año"),
                    (start_dt - timedelta(days=180), end_dt, "6 meses extendidos"),
                    (start_dt - timedelta(days=90), end_dt, "3 meses extendidos"),
                    (start_dt, end_dt, "rango solicitado"),
                    # Estrategia adicional: intentar rangos más amplios si MT5 tiene limitaciones
                    (start_dt - timedelta(days=545), end_dt, "18 meses extendidos"),
                ]
            else:
                # Estrategias estándar para forex
                download_strategies = [
                    (extended_start, end_dt, "rango extendido"),
                    (start_dt - timedelta(days=180), end_dt, "6 meses extendidos"),
                    (start_dt - timedelta(days=90), end_dt, "3 meses extendidos"),
                    (start_dt, end_dt, "rango solicitado")
                ]

            best_result = None
            max_candles = 0

            for attempt_start, attempt_end, strategy_name in download_strategies:
                try:
                    self.logger.info(f"MT5: Intentando estrategia '{strategy_name}' para {symbol}")

                    # Descargar datos con reintentos
                    rates = self._retry_operation(
                        mt5.copy_rates_range,
                        symbol,
                        mt5_timeframe,
                        attempt_start,
                        attempt_end
                    )

                    if rates is None or len(rates) == 0:
                        self.logger.warning(f"No se encontraron datos para {symbol} con estrategia '{strategy_name}'")
                        continue

                    # Convertir a DataFrame
                    df = pd.DataFrame(rates)
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s')

                    # Filtrar solo el rango solicitado original
                    df_filtered = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)].copy()

                    if df_filtered.empty:
                        self.logger.warning(f"Estrategia '{strategy_name}': No hay datos en el rango solicitado")
                        continue

                    # Renombrar columnas para consistencia
                    df_filtered = df_filtered.rename(columns={
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'tick_volume': 'volume'
                    })

                    # Mantener solo columnas necesarias
                    df_filtered = df_filtered[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

                    # Verificar que tenemos datos válidos
                    if len(df_filtered) > max_candles:
                        max_candles = len(df_filtered)
                        best_result = df_filtered
                        self.logger.info(f"Estrategia '{strategy_name}': {len(df_filtered)} velas (MEJOR RESULTADO)")

                    # Si ya tenemos suficientes datos, no continuar
                    if len(df_filtered) >= 1000:  # Umbral arbitrario de "suficientes datos"
                        self.logger.info(f"Estrategia '{strategy_name}': Suficientes datos obtenidos, deteniendo búsqueda")
                        break

                except Exception as e:
                    self.logger.warning(f"Error en estrategia '{strategy_name}' para {symbol}: {e}")
                    continue

            if best_result is None or best_result.empty:
                self.logger.error(f"No se pudieron obtener datos para {symbol} con ninguna estrategia")
                return None

            self.logger.info(f"Datos descargados: {symbol} - {len(best_result)} velas (original: {original_symbol}) usando mejor estrategia")
            return best_result

        except Exception as e:
            self.logger.error(f"Error descargando {symbol}: {e}")
            return None

    def _convert_timeframe(self, timeframe: str) -> Optional[int]:
        """Convierte timeframe string a constante MT5"""
        if not MT5_AVAILABLE:
            return None

        mapping = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
            '1w': mt5.TIMEFRAME_W1,
            '1M': mt5.TIMEFRAME_MN1
        }
        return mapping.get(timeframe)

    def get_available_symbols(self) -> List[str]:
        """Obtiene lista de símbolos disponibles"""
        if not self.connected:
            return []

        try:
            symbols = mt5.symbols_get()
            return [s.name for s in symbols] if symbols else []
        except Exception as e:
            self.logger.error(f"Error obteniendo símbolos: {e}")
            return []
