#!/usr/bin/env python3
"""
Advanced Data Downloader - Sistema completo para descarga de datos
Soporta CCXT (criptomonedas) y MT5 (acciones) con paralelización,
manejo de errores, normalización y almacenamiento múltiple.
"""
import ccxt
import ccxt.async_support as ccxt_async
import asyncio  # necesario para capturar asyncio.CancelledError en shutdown
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import logging
import os

from utils.logger import get_logger

from .mt5_downloader import MT5Downloader
from utils.storage import DataStorage, save_to_csv
from utils.market_sessions import get_asset_class, expected_candles_for_range, timeframe_to_seconds
# from utils.normalization import DataNormalizer  # TEMP: Comentado por scipy issue en Python 3.13

class AdvancedDataDownloader:
    """
    Downloader avanzado que maneja múltiples fuentes de datos:
    - CCXT para criptomonedas (Bybit, Binance, etc.)
    - MT5 para acciones (AAPL.US, TSLA.US, etc.)
    """

    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__)

        # Componentes
        self.ccxt_exchanges = {}
        self.mt5_downloader = MT5Downloader(config.mt5) if hasattr(config, 'mt5') else None
        self.storage = DataStorage(f"{config.storage.path}/data.db")
        # self.normalizer = DataNormalizer()  # TEMP: Comentado por scipy issue

        # Configuración
        self.max_retries = getattr(config, 'max_retries', 3)
        self.retry_delay = getattr(config, 'retry_delay', 5)
        self.max_workers = 4  # Para paralelización
        # Parámetros de calidad de datos (config opcional)
        dq_cfg = getattr(getattr(config, 'backtesting', None), 'data_quality', None)
        self.min_coverage_pct = getattr(dq_cfg, 'min_coverage_pct', 95) if dq_cfg else 95
        self.enable_gap_fill = getattr(dq_cfg, 'gap_fill', False) if dq_cfg else False
        self.auto_retry = getattr(dq_cfg, 'auto_retry', True) if dq_cfg else True
        # Exchange activo preferido (prioridad en fallback)
        self.active_exchange = getattr(config, 'active_exchange', None)

    # ===================== SOPORTE Fallback Exchanges =====================
    def _get_exchange_priority_list(self) -> List[str]:
        """Devuelve la lista ordenada de exchanges a intentar.

        Prioriza el exchange configurado como activo si está disponible,
        seguido por el resto en el orden de self.ccxt_exchanges.
        """
        available = list(self.ccxt_exchanges.keys())
        if self.active_exchange and self.active_exchange in available:
            return [self.active_exchange] + [e for e in available if e != self.active_exchange]
        return available

    def _is_retryable_exchange_error(self, e: Exception) -> bool:
        """Clasifica errores que justifican intentar un fallback a otro exchange."""
        import ccxt
        msg = str(e).lower()
        retryable_substrings = [
            '403', 'forbidden', 'ddos', 'blocked', 'country', 'unavailable', 'temporarily', '429'
        ]
        if any(s in msg for s in retryable_substrings):
            return True
        retryable_types = (
            getattr(ccxt, 'DDoSProtection', Exception),
            getattr(ccxt, 'ExchangeNotAvailable', Exception),
            getattr(ccxt, 'NetworkError', Exception),
            getattr(ccxt, 'RequestTimeout', Exception),
            getattr(ccxt, 'PermissionDenied', Exception)
        )
        return isinstance(e, retryable_types)

    async def _fetch_crypto_paginated(self, exchange, exchange_name: str, symbol: str, timeframe: str,
                                      start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Realiza la descarga paginada para un (exchange, symbol). Se separa para reutilizar en fallback."""
        start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end_date).timestamp() * 1000)
        frame_sec = timeframe_to_seconds(timeframe)
        frame_ms = frame_sec * 1000
        limit = 1000
        since = start_ms
        all_rows: List[List[Any]] = []
        last_progress_ts = None
        stalls = 0

        while since < end_ms:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
            if not ohlcv:
                self.logger.warning(f"{symbol} sin datos adicionales (paginación detenida) [{exchange_name}]")
                break
            if last_progress_ts is not None and ohlcv[-1][0] <= last_progress_ts:
                stalls += 1
                if stalls >= 2:
                    self.logger.warning(f"{symbol} paginación estancada, se detiene [{exchange_name}]")
                    break
            else:
                stalls = 0
            all_rows.extend(ohlcv)
            last_progress_ts = ohlcv[-1][0]
            since = last_progress_ts + frame_ms
            if last_progress_ts >= end_ms:
                break
            await asyncio.sleep(0.05)

        if not all_rows:
            return None
        df = pd.DataFrame(all_rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[(df['timestamp'] >= pd.Timestamp(start_date)) & (df['timestamp'] <= pd.Timestamp(end_date))]
        df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
        # Marcar exchange origen (atributo para metadata; no guardamos la columna en tabla OHLCV)
        df.attrs['source_exchange'] = exchange_name
        return df

    def _metadata_covers_range(self, symbol: str, timeframe: str, start_ts: int, end_ts: int) -> bool:
        """Verifica mediante metadata si se puede reutilizar completamente el dataset existente.

        Condiciones:
          - Existe metadata
          - coverage_pct >= min_coverage_pct
          - start_ts >= stored_start_ts y end_ts <= stored_end_ts (el rango solicitado está contenido)
        """
        meta = self.storage.get_metadata(symbol, timeframe)
        if not meta:
            return False
        if meta.get('coverage_pct', 0) < self.min_coverage_pct:
            return False
        stored_start = meta.get('start_ts') or 0
        stored_end = meta.get('end_ts') or 0
        return stored_start <= start_ts and stored_end >= end_ts

    def _mt5_data_covers_range(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> tuple[bool, Optional[pd.DataFrame]]:
        """Verifica si existen datos MT5 suficientes para el rango solicitado.

        Returns:
            tuple: (covers_range, dataframe) - True si cubre el rango completo, False si necesita descarga
        """
        try:
            # Verificar metadata primero (si existe)
            start_ts = int(pd.Timestamp(start_date).timestamp())
            end_ts = int(pd.Timestamp(end_date).timestamp())

            meta = self.storage.get_metadata(symbol, timeframe)
            if meta and meta.get('coverage_pct', 0) >= self.min_coverage_pct:
                stored_start = meta.get('start_ts') or 0
                stored_end = meta.get('end_ts') or 0
                if stored_start <= start_ts and stored_end >= end_ts:
                    # Metadata indica cobertura completa, intentar cargar desde DB
                    df = self.get_data_from_db(symbol, timeframe, start_date, end_date)
                    if df is not None and not df.empty:
                        actual_records = len(df)
                        expected_records = self._estimate_expected_records(symbol, timeframe, start_date, end_date)
                        actual_coverage = (actual_records / expected_records) * 100 if expected_records > 0 else 0

                        if actual_coverage >= self.min_coverage_pct:
                            self.logger.info(f"💾 MT5 Cache HIT {symbol}: {actual_records} velas existentes (>= {self.min_coverage_pct:.0f}% cobertura)")
                            return True, df

            return False, None

        except Exception as e:
            self.logger.warning(f"Error verificando datos MT5 existentes para {symbol}: {e}")
            return False, None

    def _estimate_expected_records(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> int:
        """Estima el número esperado de registros para un rango temporal"""
        from utils.market_sessions import expected_candles_for_range, get_asset_class

        asset_class = get_asset_class(symbol)
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)

        return expected_candles_for_range(start_ts, end_ts, timeframe, asset_class)

    async def initialize(self) -> bool:
        """Inicializa todas las conexiones"""
        try:
            # Inicializar CCXT exchanges
            ccxt_success = await self._setup_ccxt_exchanges()

            # Inicializar MT5
            mt5_success = self.mt5_downloader.initialize() if self.mt5_downloader else False

            if ccxt_success or mt5_success:
                self.logger.info("AdvancedDataDownloader inicializado correctamente")
                return True
            else:
                self.logger.error("No se pudo inicializar ningún downloader")
                return False

        except Exception as e:
            self.logger.error(f"Error en inicialización: {e}")
            return False

    async def _setup_ccxt_exchanges(self) -> bool:
        """Configura exchanges CCXT activos"""
        try:
            success_count = 0

            # Configurar Bybit
            if 'bybit' in self.config.exchanges and self.config.exchanges['bybit'].enabled:
                exchange_config = self.config.exchanges['bybit']
                self.ccxt_exchanges['bybit'] = ccxt_async.bybit({
                    'apiKey': exchange_config.api_key or '',
                    'secret': exchange_config.api_secret or '',
                    'sandbox': exchange_config.sandbox,
                    'timeout': exchange_config.timeout,
                })
                success_count += 1
                self.logger.info("Bybit configurado")

            # Configurar Binance
            if 'binance' in self.config.exchanges and self.config.exchanges['binance'].enabled:
                exchange_config = self.config.exchanges['binance']
                self.ccxt_exchanges['binance'] = ccxt_async.binance({
                    'apiKey': exchange_config.api_key or '',
                    'secret': exchange_config.api_secret or '',
                    'sandbox': exchange_config.sandbox,
                    'timeout': exchange_config.timeout,
                })
                success_count += 1
                self.logger.info("Binance configurado")

            # Configurar KuCoin
            if 'kucoin' in self.config.exchanges and self.config.exchanges['kucoin'].enabled:
                exchange_config = self.config.exchanges['kucoin']
                self.ccxt_exchanges['kucoin'] = ccxt_async.kucoin({
                    'apiKey': exchange_config.api_key or '',
                    'secret': exchange_config.api_secret or '',
                    'sandbox': exchange_config.sandbox,
                    'timeout': exchange_config.timeout,
                })
                success_count += 1
                self.logger.info("KuCoin configurado")

            # Configurar OKX
            if 'okx' in self.config.exchanges and self.config.exchanges['okx'].enabled:
                exchange_config = self.config.exchanges['okx']
                self.ccxt_exchanges['okx'] = ccxt_async.okx({
                    'apiKey': exchange_config.api_key or '',
                    'secret': exchange_config.api_secret or '',
                    'sandbox': exchange_config.sandbox,
                    'timeout': exchange_config.timeout,
                })
                success_count += 1
                self.logger.info("OKX configurado")

            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error configurando CCXT: {e}")
            return False

    async def download_multiple_symbols(self, symbols: List[str], timeframe: str = "1h",
                                      start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        Descarga datos de múltiples símbolos en paralelo con soporte para lotes

        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe para descarga
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)

        Returns:
            Diccionario símbolo -> DataFrame
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        self.logger.info(f"Descargando {len(symbols)} símbolos en paralelo...")

        symbol_data: Dict[str, pd.DataFrame] = {}

        # Intentar usar metadata + caché (coverage session-aware) antes de descargar
        start_ts_dt = pd.Timestamp(start_date)
        end_ts_dt = pd.Timestamp(end_date)
        start_ts_int = int(start_ts_dt.timestamp())
        end_ts_int = int(end_ts_dt.timestamp())
        for symbol in symbols:
            # Para timeframe 1h y 4h, primero intentar cargar desde CSV sintético
            if timeframe in ['1h', '4h']:
                csv_df = await self.get_data_from_csv(symbol, timeframe, start_date, end_date)
                if csv_df is not None and not csv_df.empty:
                    self.logger.info(f"📄 CSV HIT {symbol}: {len(csv_df)} velas sintéticas de {timeframe}")
                    symbol_data[symbol] = csv_df
                    continue

            # Primero evaluar metadata para decidir si se puede saltar descarga
            if self._metadata_covers_range(symbol, timeframe, start_ts_int, end_ts_int):
                cached_df = await self.get_data_from_db(symbol, timeframe, start_date, end_date)
                if cached_df is not None and not cached_df.empty:
                    self.logger.info(f"💾 Metadata HIT {symbol}: reuse completo (>= {self.min_coverage_pct}% cobertura)")
                    symbol_data[symbol] = cached_df
                    continue
                # Si metadata dice que hay cobertura pero la consulta falla, forzar descarga
                self.logger.warning(f"⚠️ Metadata indica cobertura pero no se pudo cargar datos para {symbol}, se descargará")
            else:
                # Comprobar caché directamente en caso de no cumplir metadata (quizá metadata inexistente o rango diferente)
                cached_df = await self.get_data_from_db(symbol, timeframe, start_date, end_date)
                if cached_df is not None and not cached_df.empty:
                    asset_class = get_asset_class(symbol)
                    expected = expected_candles_for_range(start_ts_dt, end_ts_dt, timeframe, asset_class)
                    actual = len(cached_df)
                    coverage = (actual / expected * 100) if expected else 100
                    if coverage >= self.min_coverage_pct:
                        self.logger.info(f"💾 Cache HIT {symbol}: {actual} velas (coverage {coverage:.1f}% >= {self.min_coverage_pct}%)")
                        symbol_data[symbol] = cached_df
                        continue
                    else:
                        self.logger.info(f"🆕 Cache PARTIAL {symbol}: {coverage:.1f}% < {self.min_coverage_pct}% -> re-descarga")
                else:
                    self.logger.info(f"🆕 Cache MISS {symbol}: se descargará")

        symbols_to_download = [s for s in symbols if s not in symbol_data]
        if not symbols_to_download:
            return symbol_data

        tasks = [self._download_symbol_with_batches(s, timeframe, start_date, end_date) for s in symbols_to_download]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            symbol = symbols_to_download[i]
            if isinstance(result, Exception):
                self.logger.error(f"Error descargando {symbol}: {result}")
                # Fallback: intentar cargar datos cached si existen
                cached_fallback = await self.get_data_from_db(symbol, timeframe, start_date, end_date)
                if cached_fallback is not None and not cached_fallback.empty:
                    self.logger.warning(f"⚠️ Usando datos cached como fallback para {symbol} ({len(cached_fallback)} velas)")
                    symbol_data[symbol] = cached_fallback
                    # Alertar sobre el fallback
                    self._alert_download_fallback(symbol, timeframe, str(result))
                else:
                    self.logger.error(f"❌ No hay datos cached disponibles para {symbol}")
            elif result is not None and not result.empty:
                symbol_data[symbol] = result
                self.logger.info(f"✅ {symbol}: {len(result)} velas descargadas")
            else:
                # Marcamos símbolo como missing en metadata mínima para que auditoría lo identifique
                self.logger.warning(f"⚠️ {symbol}: descarga vacía (marcado missing)")
                try:
                    self.storage.upsert_metadata({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'start_ts': None,
                        'end_ts': None,
                        'records': 0,
                        'coverage_pct': 0,
                        'asset_class': get_asset_class(symbol),
                        'source_exchange': None
                    })
                except Exception as me:
                    self.logger.debug(f"No se pudo registrar missing metadata {symbol}: {me}")

        return symbol_data

    def _calculate_download_batches(self, start_date: str, end_date: str, batch_size_days: int = 90) -> List[Tuple[str, str]]:
        """
        Divide el período total en lotes más pequeños para evitar límites de MT5

        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            batch_size_days: Tamaño de cada lote en días (default: 90 días = 3 meses)

        Returns:
            Lista de tuplas (start_batch, end_batch)
        """
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)

        batches = []
        current_start = start_dt

        while current_start < end_dt:
            current_end = min(current_start + pd.Timedelta(days=batch_size_days), end_dt)
            batches.append((current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")))
            current_start = current_end

        return batches

    async def _download_symbol_with_batches(self, symbol: str, timeframe: str,
                                          start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Descarga un símbolo dividiendo el período en lotes para evitar límites de MT5
        """
        # Calcular lotes de 3 meses cada uno
        batches = self._calculate_download_batches(start_date, end_date, batch_size_days=90)

        if len(batches) == 1:
            # Si solo hay un lote, usar el método normal
            return await self._download_symbol_with_retry(symbol, timeframe, start_date, end_date)

        self.logger.info(f"📦 {symbol}: Descargando en {len(batches)} lotes de ~3 meses cada uno")

        all_data_frames = []

        for i, (batch_start, batch_end) in enumerate(batches, 1):
            self.logger.info(f"📦 {symbol}: Lote {i}/{len(batches)} - {batch_start} a {batch_end}")

            try:
                batch_data = await self._download_symbol_with_retry(symbol, timeframe, batch_start, batch_end)
                if batch_data is not None and not batch_data.empty:
                    all_data_frames.append(batch_data)
                    self.logger.info(f"✅ {symbol}: Lote {i} completado - {len(batch_data)} velas")
                else:
                    self.logger.warning(f"⚠️ {symbol}: Lote {i} vacío")
            except Exception as e:
                self.logger.error(f"❌ {symbol}: Error en lote {i}: {e}")
                # Continuar con el siguiente lote en lugar de fallar completamente
                continue

        if not all_data_frames:
            self.logger.error(f"❌ {symbol}: Todos los lotes fallaron")
            return None

        # Combinar todos los DataFrames
        try:
            combined_df = pd.concat(all_data_frames, ignore_index=True)

            # Eliminar duplicados basados en timestamp
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='first')

            # Ordenar por timestamp
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)

            self.logger.info(f"📦 {symbol}: Combinados {len(all_data_frames)} lotes → {len(combined_df)} velas totales")

            return combined_df

        except Exception as e:
            self.logger.error(f"❌ {symbol}: Error combinando lotes: {e}")
            return None

    async def _download_symbol_with_retry(self, symbol: str, timeframe: str,
                                        start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Descarga un símbolo con manejo de errores, reintentos y FALLBACK automático MT5 ↔ CCXT
        
        ESTRATEGIA v2.8:
          1. Detectar fuente primaria (crypto → CCXT, stocks/forex → MT5)
          2. Intentar descarga desde fuente primaria con reintentos
          3. Si falla, hacer FALLBACK automático a fuente secundaria
          4. Registrar fuente exitosa
        """
        
        # Detectar fuente primaria
        is_crypto = self._is_crypto_symbol(symbol)
        primary_source = 'ccxt' if is_crypto else 'mt5'
        fallback_source = 'mt5' if primary_source == 'ccxt' else 'ccxt'
        
        self.logger.info(f"📥 {symbol}: Primario={primary_source}, Fallback={fallback_source}")
        
        # ========== INTENTO PRIMARIO CON REINTENTOS ==========
        for attempt in range(self.max_retries):
            try:
                if primary_source == 'ccxt':
                    df = await self._download_crypto_symbol(symbol, timeframe, start_date, end_date)
                else:
                    df = self._download_stock_symbol(symbol, timeframe, start_date, end_date)
                
                if df is not None and len(df) > 0:
                    self.logger.info(f"✅ {symbol}: {len(df)} velas desde {primary_source}")
                    return df
                
                self.logger.warning(f"⚠️ {symbol}: Intento {attempt+1}/{self.max_retries} en {primary_source} retornó vacío")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Backoff exponencial
            
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"⚠️ {symbol}: Error intento {attempt+1}/{self.max_retries} en {primary_source}: {error_msg}")
                
                # Si es crypto y no hay exchanges configurados, no reintentar ni hacer fallback
                if is_crypto and "No hay exchanges CCXT configurados" in error_msg:
                    self.logger.error(f"❌ {symbol}: CCXT no configurado, abortando descarga")
                    return None
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    self.logger.warning(f"⚠️ {symbol}: Todos los intentos en {primary_source} fallaron")
        
        # ========== FALLBACK AUTOMÁTICO ==========
        self.logger.info(f"🔄 {symbol}: Intentando fallback a {fallback_source}")
        
        try:
            if fallback_source == 'ccxt':
                # Convertir símbolo de MT5 a CCXT si es necesario
                ccxt_symbol = self._convert_to_ccxt_format(symbol)
                self.logger.info(f"🔄 Convertido para CCXT: {symbol} → {ccxt_symbol}")
                df = await self._download_crypto_symbol(ccxt_symbol, timeframe, start_date, end_date)
            else:
                # Convertir símbolo de CCXT a MT5 si es necesario  
                mt5_symbol = self._convert_to_mt5_format(symbol)
                self.logger.info(f"🔄 Convertido para MT5: {symbol} → {mt5_symbol}")
                df = self._download_stock_symbol(mt5_symbol, timeframe, start_date, end_date)
            
            if df is not None and len(df) > 0:
                self.logger.info(f"✅ {symbol}: Fallback exitoso desde {fallback_source} ({len(df)} velas)")
                return df
            else:
                self.logger.warning(f"⚠️ {symbol}: Fallback retornó vacío")
        
        except Exception as e:
            self.logger.error(f"❌ {symbol}: Fallback falló: {e}")
        
        # ========== FALLO TOTAL ==========
        self.logger.error(f"❌ {symbol}: Todas las fuentes fallaron (primario={primary_source}, fallback={fallback_source})")
        return None
    
    def _convert_to_ccxt_format(self, symbol: str) -> str:
        """
        Convierte símbolo de MT5 a formato CCXT
        
        Ejemplos:
          TSLA.US → TSLA/USD (no existe en CCXT, pero intenta)
          BTCUSD → BTC/USD
          EUR_USD → EUR/USD
          EURUSD → EUR/USD
        """
        if '/' in symbol:
            return symbol  # Ya está en formato CCXT
        
        # Manejar acciones (AAPL.US → AAPL/USD)
        if '.' in symbol:
            parts = symbol.split('.')
            if len(parts) == 2 and parts[1].upper() in ['US', 'UK']:
                return f"{parts[0]}/USD"
        
        # Manejar símbolos con '_' (EUR_USD → EUR/USD)
        if '_' in symbol:
            return symbol.replace('_', '/')
        
        # Intentar split automático para crypto/forex comunes
        common_quotes = ['USD', 'EUR', 'GBP', 'JPY', 'USDT', 'BTC', 'ETH', 'BUSD']
        for quote in common_quotes:
            if symbol.upper().endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        
        return symbol
    
    def _convert_to_mt5_format(self, symbol: str) -> str:
        """
        Convierte símbolo de CCXT a formato MT5
        
        Ejemplos:
          BTC/USD → BTCUSD
          DOGE/USDT → No existe en MT5 (devuelve DOGEUSDT)
          EUR/USD → EURUSD
        """
        if '/' not in symbol:
            return symbol  # Ya está sin separador
        
        # Remover '/' para formato MT5 estándar
        return symbol.replace('/', '')

    def _is_crypto_symbol(self, symbol: str) -> bool:
        """
        Determina si un símbolo es de criptomoneda (debe usar CCXT)
        
        REGLA PRINCIPAL: Si la BASE es crypto, SIEMPRE usar CCXT
        CORRECCIÓN v2.8: crypto/USD ahora va a CCXT (no a MT5)
        """
        if '/' not in symbol:
            return False

        base, quote = symbol.split('/', 1)

        # ✅ Lista completa de criptomonedas (bases)
        CRYPTO_BASES = {
            'BTC', 'ETH', 'DOGE', 'SHIB', 'ADA', 'DOT', 'MATIC', 'AVAX',
            'LINK', 'UNI', 'AAVE', 'SOL', 'LUNA', 'ATOM', 'ALGO', 'VET',
            'TRX', 'EOS', 'XLM', 'XTZ', 'DASH', 'ZEC', 'XMR', 'LTC', 'XRP',
            'BNB', 'FTT', 'CRO', 'LEO', 'HT', 'OKB', 'MKR', 'COMP', 'SNX',
            'SUSHI', 'CAKE', 'NEAR', 'FTM', 'SAND', 'MANA', 'AXS', 'THETA'
        }
        
        # ✅ Lista de cotizaciones crypto/stablecoins
        CRYPTO_QUOTES = {'USDT', 'BUSD', 'USDC', 'DAI', 'TUSD', 'UST', 'BTC', 'ETH', 'BNB'}
        
        # ✅ CORRECCIÓN CRÍTICA: Si la base es crypto, USAR CCXT
        # Esto incluye BTC/USD, DOGE/USD, ETH/USD, etc.
        if base.upper() in CRYPTO_BASES:
            self.logger.debug(f"🔍 {symbol}: Base '{base}' es crypto → CCXT")
            return True
        
        # ✅ Si la cotización es stablecoin/crypto, usar CCXT
        if quote.upper() in CRYPTO_QUOTES:
            self.logger.debug(f"🔍 {symbol}: Quote '{quote}' es crypto → CCXT")
            return True
        
        # ✅ Excepción: Si cotización es 'US', es acción (MT5)
        if quote.upper() == 'US':
            self.logger.debug(f"🔍 {symbol}: Quote 'US' → MT5 (stock)")
            return False
        
        # ✅ Divisas forex estándar → MT5
        FOREX_CURRENCIES = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 
            'CNY', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'TRY', 
            'ZAR', 'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN'
        }
        
        if base.upper() in FOREX_CURRENCIES and quote.upper() in FOREX_CURRENCIES:
            self.logger.debug(f"🔍 {symbol}: Forex pair → MT5")
            return False
        
        # Por defecto: si no es claramente forex/stock, asumir crypto
        self.logger.debug(f"🔍 {symbol}: Default → CCXT (crypto)")
        return True


    async def _download_crypto_symbol(self, symbol: str, timeframe: str,
                                    start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Descarga datos de criptomoneda con fallback entre múltiples exchanges.

        Estrategia:
          - Construir lista de prioridad (active_exchange primero si existe)
          - Intentar cada exchange hasta obtener dataset válido (>=1 vela)
          - Clasificar errores retryable (403, DDoS, 429, bloqueo geográfico) para intentar fallback
          - Si todos fallan, relanzar último error
        """
        if not self.ccxt_exchanges:
            raise Exception("No hay exchanges CCXT configurados")

        priority = self._get_exchange_priority_list()
        last_error: Optional[Exception] = None
        for ex_name in priority:
            exchange = self.ccxt_exchanges[ex_name]
            try:
                self.logger.info(f"{symbol}: intentando descarga en {ex_name}")
                df = await self._fetch_crypto_paginated(exchange, ex_name, symbol, timeframe, start_date, end_date)
                if df is None or df.empty:
                    self.logger.warning(f"{symbol}: dataset vacío desde {ex_name}, intentando siguiente exchange")
                    continue
                self.logger.info(f"{symbol}: descarga exitosa en {ex_name} ({len(df)} velas)")
                return df
            except Exception as e:
                last_error = e
                if self._is_retryable_exchange_error(e):
                    self.logger.warning(f"{symbol}: error retryable en {ex_name} -> fallback ({e})")
                    continue
                else:
                    self.logger.error(f"{symbol}: error no retryable en {ex_name} -> aborta ({e})")
                    break
        if last_error:
            raise last_error
        return None

    def _download_stock_symbol(self, symbol: str, timeframe: str,
                             start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Descarga datos de acciones desde MT5 con verificación de caché"""
        # Primero verificar si ya tenemos datos suficientes
        covers_range, existing_df = self._mt5_data_covers_range(symbol, timeframe, start_date, end_date)
        if covers_range and existing_df is not None:
            return existing_df

        # Si no hay datos suficientes, proceder con descarga desde MT5
        if not self.mt5_downloader or not self.mt5_downloader.connected:
            raise Exception("MT5 no está disponible")

        self.logger.info(f"📥 MT5 Download {symbol}: descargando nuevos datos ({start_date} a {end_date})")
        return self.mt5_downloader.download_symbol_data(symbol, timeframe, start_date, end_date)

    async def process_and_save_data(self, symbol_data: Dict[str, pd.DataFrame],
                                  timeframe: str, save_csv: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Procesa, normaliza y guarda los datos descargados

        Args:
            symbol_data: Diccionario símbolo -> DataFrame
            timeframe: Timeframe de los datos
            save_csv: Si guardar también en CSV

        Returns:
            Diccionario con los datos procesados (símbolo -> DataFrame normalizado)
        """
        processed_data = {}
        
        try:
            for symbol, df in symbol_data.items():
                if df is None or df.empty:
                    continue

                # Calcular indicadores técnicos (solo para procesamiento, NO para guardar en DB)
                df_with_indicators = self._calculate_technical_indicators(df)

                # Normalizar y escalar (para procesamiento interno)
                df_normalized = self._normalize_and_scale(df_with_indicators)

                # Añadir volumen escalado (median rolling 50) antes de guardado
                if 'volume' in df_with_indicators.columns:
                    vol_series = df_with_indicators['volume'].astype(float)
                    med50 = vol_series.rolling(50, min_periods=10).median()
                    df_with_indicators['volume_median_50'] = med50
                    ratio = vol_series / med50.replace(0, np.nan)
                    ratio = ratio.replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 10)
                    df_with_indicators['volume_scaled'] = ratio

                # 🔧 FIX: Guardar SOLO datos OHLCV básicos en SQLite (sin indicadores)
                # Los indicadores se calculan en tiempo real cuando se necesitan
                df_for_sqlite = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
                
                # Guardar en SQLite (SOLO datos crudos OHLCV)
                table_name = f"{symbol.replace('/', '_').replace('.', '_')}_{timeframe}"
                success_sql = self.storage.save_to_sqlite(df_for_sqlite, table_name)

                # Metadata básica (coverage session-aware)
                try:
                    asset_class = get_asset_class(symbol)
                    start_req = pd.Timestamp(df_normalized['timestamp'].min(), unit='s') if df_normalized['timestamp'].dtype != 'datetime64[ns]' else df_normalized['timestamp'].min()
                    end_req = pd.Timestamp(df_normalized['timestamp'].max(), unit='s') if df_normalized['timestamp'].dtype != 'datetime64[ns]' else df_normalized['timestamp'].max()
                    # NOTA: Para una estimación más precisa se debería usar el rango solicitado original; aquí se usa rango de datos disponibles.
                    expected = expected_candles_for_range(start_req, end_req, timeframe, asset_class)
                    coverage = (len(df_normalized) / expected * 100) if expected else 100
                    source_exchange = df_normalized.attrs.get('source_exchange') if hasattr(df_normalized, 'attrs') else None
                    self.storage.upsert_metadata({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'start_ts': int(start_req.timestamp()),
                        'end_ts': int(end_req.timestamp()),
                        'records': len(df_normalized),
                        'coverage_pct': round(coverage, 2),
                        'asset_class': asset_class,
                        'source_exchange': source_exchange
                    })
                except Exception as me:
                    self.logger.debug(f"No se pudo registrar metadata {symbol}: {me}")

                # Guardar en CSV (para verificación visual)
                if save_csv and success_sql:
                    csv_path = f"{self.config.storage.path}/csv"
                    os.makedirs(csv_path, exist_ok=True)
                    csv_file = f"{csv_path}/{table_name}.csv"
                    success_csv = save_to_csv(df_normalized, csv_file)

                    if success_csv:
                        self.logger.info(f"✅ {symbol}: Datos guardados en SQLite y CSV")
                    else:
                        self.logger.warning(f"⚠️ {symbol}: Datos guardados en SQLite, error en CSV")

                # Almacenar datos procesados para devolver
                processed_data[symbol] = df_normalized

            return processed_data

        except Exception as e:
            self.logger.error(f"Error procesando datos: {e}")
            return False

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos completos usando la clase centralizada TechnicalIndicators"""
        try:
            # Importar método centralizado
            from indicators.technical_indicators import TechnicalIndicators
            
            # Crear instancia y calcular todos los indicadores
            indicators = TechnicalIndicators()
            result_df = indicators.calculate_all_indicators_unified(df)
            
            # Llenar NaN con 0
            result_df = result_df.fillna(0)
            
            self.logger.info(f"✅ Indicadores calculados (centralizado) para {len(result_df)} filas")
            return result_df

        except Exception as e:
            self.logger.error(f"Error calculando indicadores: {e}")
            return df

    def _calculate_sar(self, df: pd.DataFrame) -> pd.Series:
        """
        ⚠️ MÉTODO OBSOLETO: Use TechnicalIndicators.calculate_sar en su lugar
        
        Este método se mantiene solo para compatibilidad con código existente.
        Será eliminado en futuras versiones.
        """
        from indicators.technical_indicators import TechnicalIndicators
        indicators = TechnicalIndicators()
        return indicators.calculate_sar(df)

    def _normalize_and_scale(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza y escala los datos"""
        try:
            # Columnas que NO deben ser normalizadas (valores absolutos para estrategias)
            exclude_cols = [
                'open', 'high', 'low', 'close', 'volume',  # Precios y volumen
                'atr', 'adx', 'sar', 'rsi', 'macd', 'macd_signal',  # Indicadores técnicos
                'bb_upper', 'bb_lower',  # Bandas de Bollinger
                'ema_10', 'ema_20', 'ema_200'  # EMAs necesarias para estrategias
            ]

            # Identificar columnas numéricas (excluir timestamp y columnas excluidas)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_cols = [col for col in numeric_cols if col not in exclude_cols and col != 'timestamp']

            if not numeric_cols:
                return df

            # Normalizar solo columnas que no afectan las estrategias
            df_normalized = df.copy()
            for col in numeric_cols:
                # Min-Max scaling solo para columnas permitidas
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val > min_val:
                    df_normalized[col] = (df[col] - min_val) / (max_val - min_val)

            return df_normalized

        except Exception as e:
            self.logger.error(f"Error en normalización: {e}")
            return df

    async def get_data_from_db(self, symbol: str, timeframe: str,
                             start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Obtiene datos desde la base de datos SQLite

        Args:
            symbol: Símbolo
            timeframe: Timeframe
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)

        Returns:
            DataFrame con datos o None
        """
        try:
            table_name = f"{symbol.replace('/', '_').replace('.', '_')}_{timeframe}"
            if not self.storage.table_exists(table_name):
                return None

            # Convertir fechas a timestamps si se proporcionan
            start_ts = int(pd.Timestamp(start_date).timestamp()) if start_date else None
            end_ts = int(pd.Timestamp(end_date).timestamp()) if end_date else None

            df = self.storage.query_data(table_name, start_ts=start_ts, end_ts=end_ts)
            if df is None or df.empty:
                return None

            # Asegurar columnas estándar (en caso de columnas adicionales se mantienen)
            required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
            missing = required_cols - set(df.columns)
            if missing:
                self.logger.warning(f"Tabla {table_name} faltan columnas {missing}, no se usará caché")
                return None

            # Filtrar rango por seguridad
            if start_date:
                df = df[df['timestamp'] >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.Timestamp(end_date)]

            if df.empty:
                return None

            # Validar cobertura temporal mínima (al menos 70% del rango solicitado)
            if start_date and end_date:
                total_seconds = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).total_seconds()
                cached_seconds = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
                coverage = cached_seconds / total_seconds if total_seconds > 0 else 0
                if coverage < 0.7:
                    self.logger.info(f"Cobertura caché insuficiente {symbol}: {coverage:.1%} < 70% -> forzar descarga")
                    return None

            return df.reset_index(drop=True)

        except Exception as e:
            self.logger.error(f"Error obteniendo datos de DB: {e}")
            return None

    async def get_data_from_csv(self, symbol: str, timeframe: str,
                              start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Obtiene datos desde archivos CSV (usado principalmente para datos sintéticos de 1h)

        Args:
            symbol: Símbolo
            timeframe: Timeframe
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)

        Returns:
            DataFrame con datos o None
        """
        try:
            # Solo buscar CSV para timeframe de 1h y 4h
            if timeframe not in ['1h', '4h']:
                return None

            csv_path = f"data/csv/{symbol.replace('/', '_')}_{timeframe}.csv"

            if not os.path.exists(csv_path):
                return None

            self.logger.info(f"📄 CSV encontrado para {symbol}: {csv_path}")
            df = pd.read_csv(csv_path)

            if df.empty:
                return None

            # Asegurar columna timestamp
            if 'timestamp' not in df.columns:
                if 'time' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['time'])
                elif 'Timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['Timestamp'])
                else:
                    self.logger.error(f"No se encontró columna de timestamp en {csv_path}")
                    return None
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Filtrar por rango de fechas si se especifica
            if start_date:
                df = df[df['timestamp'] >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.Timestamp(end_date)]

            if df.empty:
                return None

            # Asegurar columnas estándar
            required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
            missing = required_cols - set(df.columns)
            if missing:
                self.logger.warning(f"CSV {csv_path} faltan columnas {missing}")
                return None

            # Ordenar por timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)

            self.logger.info(f"✅ CSV cargado {symbol}: {len(df)} velas desde {df['timestamp'].min()} hasta {df['timestamp'].max()}")
            return df

        except Exception as e:
            self.logger.warning(f"Error cargando CSV para {symbol}: {e}")
            return None

    async def shutdown(self):
        """Cierra todas las conexiones"""
        try:
            # Cerrar exchanges CCXT
            for exchange in self.ccxt_exchanges.values():
                try:
                    await exchange.close()
                except Exception as ex:
                    # Captura de errores de cierre individuales para no abortar el resto
                    self.logger.warning(f"Error cerrando exchange {getattr(exchange, 'id', '?')}: {ex}")

            # Cerrar MT5
            if self.mt5_downloader:
                self.mt5_downloader.shutdown()

            self.logger.info("AdvancedDataDownloader cerrado correctamente")

        except asyncio.CancelledError:
            # Evitar propagar CancelledError para no generar KeyboardInterrupt aguas arriba
            self.logger.warning("Shutdown cancelado (asyncio.CancelledError) - forzando cierre suave")
            try:
                for exchange in self.ccxt_exchanges.values():
                    try:
                        await exchange.close()
                    except Exception:
                        pass
                if self.mt5_downloader:
                    try:
                        self.mt5_downloader.shutdown()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error en shutdown: {e}")

    async def async_download_ohlcv(self, symbol: str, exchange_name: str,
                                 timeframe: str = '1h', limit: int = 1000) -> tuple:
        """
        Descarga datos OHLCV de un exchange
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} no configurado")

        exchange = self.exchanges[exchange_name]

        try:
            # Descargar datos
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

            if not ohlcv:
                return None, {"error": "No data received"}

            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            # No establecer timestamp como índice para mantenerlo como columna
            # df.set_index('timestamp', inplace=True)

            # Convertir tipos de datos
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            stats = {
                'exchange': exchange_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'records': len(df),
                'start_date': df.index.min(),
                'end_date': df.index.max()
            }

            return df, stats

        except Exception as e:
            self.logger.error(f"[ERROR] Error descargando {symbol} desde {exchange_name}: {e}")
            return None, {"error": str(e)}

    async def close_exchanges(self):
        """Cierra todas las conexiones de exchanges"""
        for exchange_name, exchange in self.ccxt_exchanges.items():
            try:
                await exchange.close()
                self.logger.info(f"[INFO] Exchange {exchange_name} cerrado")
            except Exception as e:
                self.logger.error(f"[ERROR] Error cerrando {exchange_name}: {e}")

        self.ccxt_exchanges.clear()

    def _get_exchange_priority_list(self) -> List[str]:
        """Retorna lista de exchanges en orden de prioridad para fallback.

        Prioridad:
        1. active_exchange (de config) si está disponible
        2. Otros exchanges disponibles
        """
        available = list(self.ccxt_exchanges.keys())
        if not available:
            return []

        # Exchange activo primero si existe
        active = getattr(self.config, 'active_exchange', 'bybit')
        if active in available:
            priority = [active] + [ex for ex in available if ex != active]
        else:
            priority = available

        self.logger.debug(f"Exchange priority: {priority}")
        return priority

    def _is_retryable_exchange_error(self, error: Exception) -> bool:
        """Determina si un error de exchange permite intentar fallback.

        Errores retryable: bloqueos geográficos, rate limits, DDoS, etc.
        Errores no retryable: símbolos inválidos, problemas de autenticación, etc.
        """
        error_str = str(error).lower()

        # Errores que permiten fallback (retryable)
        retryable_patterns = [
            '403', 'forbidden', 'blocked', 'geoblock', 'geo-block',
            '429', 'rate limit', 'too many requests',
            'ddos', 'service unavailable', 'bad gateway', 'gateway timeout',
            'connection reset', 'connection refused', 'timeout',
            'cloudflare', 'access denied'
        ]

        # Errores que NO permiten fallback (no retryable)
        non_retryable_patterns = [
            'invalid symbol', 'symbol not found', 'market not found',
            'authentication', 'api key', 'invalid credentials',
            'permission denied', 'insufficient funds'
        ]

        # Verificar patrones no retryable primero
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False

        # Verificar patrones retryable
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Por defecto, considerar retryable (para errores genéricos)
        return True


# ===================== FUNCIÓN DE COMPATIBILIDAD =====================
def download_and_cache_data(symbol: str, timeframe: str, start_date: str, end_date: str, exchange: str = "bybit") -> Optional[pd.DataFrame]:
    """
    Función de compatibilidad para el sistema de optimización.
    Descarga y cachea datos usando el AdvancedDataDownloader.

    Args:
        symbol: Símbolo del activo (ej: 'SOL/USDT')
        timeframe: Timeframe (ej: '4h', '1h', '1d')
        start_date: Fecha de inicio en formato YYYY-MM-DD
        end_date: Fecha de fin en formato YYYY-MM-DD
        exchange: Exchange a usar (por defecto 'bybit')

    Returns:
        DataFrame con datos OHLCV o None si falla
    """
    try:
        # Importar configuración
        from config.config_loader import load_config_from_yaml

        # Cargar configuración
        config = load_config_from_yaml()

        # Crear instancia del downloader
        downloader = AdvancedDataDownloader(config)

        # Usar un enfoque más simple: intentar obtener datos de la DB primero
        # sin inicializar exchanges complejos que pueden causar problemas
        table_name = f"{symbol.replace('/', '_').replace('.', '_')}_{timeframe}"

        if downloader.storage.table_exists(table_name):
            # Convertir fechas a timestamps
            start_ts = int(pd.Timestamp(start_date).timestamp()) if start_date else None
            end_ts = int(pd.Timestamp(end_date).timestamp()) if end_date else None

            df = downloader.storage.query_data(table_name, start_ts=start_ts, end_ts=end_ts)
            if df is not None and not df.empty and len(df) > 10:
                logging.info(f"✅ Datos obtenidos de caché para {symbol}: {len(df)} velas")
                return df

        # Si no hay datos en caché, devolver None por ahora
        # La optimización debería manejar este caso
        logging.warning(f"⚠️ No hay datos en caché para {symbol}, intentando descarga...")

        # Intentar descarga simple sin async complications
        try:
            # Crear un nuevo loop si no existe
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Ejecutar descarga
            result = loop.run_until_complete(
                downloader.download_multiple_symbols(
                    symbols=[symbol],
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    exchanges=[exchange]
                )
            )

            if result and symbol in result and result[symbol] is not None:
                data = result[symbol]
                logging.info(f"✅ Datos descargados para {symbol}: {len(data)} velas")
                return data

        except Exception as download_error:
            logging.error(f"❌ Error en descarga para {symbol}: {str(download_error)}")

        logging.warning(f"⚠️ No hay datos suficientes en caché para {symbol}, intentando descarga...")
        return None

    except Exception as e:
        logging.error(f"❌ Error en download_and_cache_data para {symbol}: {str(e)}")
        return None


def _alert_download_fallback(self, symbol: str, timeframe: str, error_msg: str):
    """
    Alerta sobre uso de datos cached como fallback debido a errores de descarga.

    Args:
        symbol: Símbolo que falló
        timeframe: Timeframe solicitado
        error_msg: Mensaje de error original
    """
    from utils.monitoring import DownloadMonitor

    monitor = DownloadMonitor()
    monitor.alert_download_issue(symbol, timeframe, f"Fallback a datos cached: {error_msg}")

    # Log detallado
    self.logger.warning(f"🚨 ALERTA: {symbol} ({timeframe}) usando datos cached debido a: {error_msg}")
    self.logger.warning(f"   Recomendación: Verificar conectividad de red o límites de API")