import ccxt
import time
import asyncio
import os
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import ccxt.async_support as ccxt  # Import async version
from datetime import datetime
from ..config.config import Config
from ..utils.logger import setup_logging, get_logger
from ..utils.storage import save_to_csv, DataStorage
from ..utils.retry_manager import RetryManager, with_retry
from ..utils.monitoring import PerformanceMonitor
from ..utils.data_validator import DataValidator
from ..utils.cache_manager import CacheManager
from datetime import timedelta

class DataDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.exchanges = {}
        setup_logging(config)
        self.logger = get_logger(__name__)
        
        # Inicializar sistemas de soporte
        self.retry_manager = RetryManager(
            max_retries=config.max_retries,
            base_delay=config.retry_delay,
            max_delay=60.0
        )
        self.monitor = PerformanceMonitor(
            metrics_dir=os.path.join(config.storage.path, "metrics")
        )
        self.validator = DataValidator(config)
        self.cache = CacheManager(
            cache_dir=os.path.join(config.storage.path, "cache"),
            max_age=timedelta(minutes=30)  # Configurable según necesidades
        )

    async def setup_exchanges(self):
        """Initialize exchange instances based on the configuration."""
        for ex_name, ex_config in self.config.exchanges.items():
            try:
                exchange_class = getattr(ccxt, ex_name)
                
                # Start with basic config
                ccxt_config = {
                    'enableRateLimit': ex_config.get('enableRateLimit', True),
                }

                # Add API keys only if they are provided and not placeholders
                api_key = ex_config.get('api_key')
                secret = ex_config.get('secret')

                if api_key and api_key != 'your_api_key_here':
                    ccxt_config['apiKey'] = api_key
                
                if secret and secret != 'your_secret_here':
                    ccxt_config['secret'] = secret

                self.exchanges[ex_name] = exchange_class(ccxt_config)
                self.logger.info(f"Initialized {ex_name} exchange.")
            except AttributeError:
                self.logger.error(f"Exchange {ex_name} not found in ccxt.")
            except Exception as e:
                self.logger.error(f"Error initializing {ex_name}: {e}")

    async def close_exchanges(self):
        """Close all active exchange sessions."""
        for exchange in self.exchanges.values():
            if hasattr(exchange, 'close'):
                await exchange.close()
        self.logger.info("All exchange sessions closed.")

    def _get_exchange(self, exchange_name: str):
        """Get an initialized exchange instance."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not initialized.")
        return exchange
        
    async def _download_paginated(self, symbol: str, exchange_name: str, timeframe: str = '1h',
                                since: Optional[int] = None, until: Optional[int] = None) -> List[Dict]:
        """
        Descarga datos de un símbolo usando paginación para obtener el rango completo.
        
        Args:
            symbol: Símbolo a descargar
            exchange_name: Nombre del exchange
            timeframe: Intervalo de tiempo
            since: Timestamp inicial en milisegundos
            until: Timestamp final en milisegundos
            
        Returns:
            List[Dict]: Lista de datos OHLCV
        """
        exchange = self._get_exchange(exchange_name)
        all_data = []
        
        # Obtener la duración del timeframe en milisegundos
        timeframe_ms = self._get_timeframe_ms(timeframe)
        
        # Configurar el tamaño de página y límite
        page_limit = 1000  # Número máximo de registros por petición
        current_since = since
        
        while True:
            try:
                # Descargar datos para el período actual
                ohlcv = await exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=page_limit
                )
                
                if not ohlcv:
                    break
                    
                # Añadir datos a la lista
                all_data.extend(ohlcv)
                
                # Actualizar el timestamp inicial para la siguiente página
                last_timestamp = ohlcv[-1][0]
                
                # Si hemos llegado al final del período o no hay más datos, terminar
                if last_timestamp >= until or len(ohlcv) < page_limit:
                    break
                    
                # Avanzar al siguiente período
                current_since = last_timestamp + timeframe_ms
                
                # Esperar un poco para no sobrecargar la API
                await asyncio.sleep(exchange.rateLimit / 1000)
                
            except Exception as e:
                self.logger.error(f"Error downloading data for {symbol}: {str(e)}")
                break
                
        return all_data
        
    def _get_timeframe_ms(self, timeframe: str) -> int:
        """
        Convierte un timeframe (e.g., '1h', '1d') a milisegundos.
        """
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        
        if unit == 'm':
            return value * 60 * 1000
        elif unit == 'h':
            return value * 60 * 60 * 1000
        elif unit == 'd':
            return value * 24 * 60 * 60 * 1000
        else:
            raise ValueError(f"Unsupported timeframe unit: {unit}")
        
    async def download_multiple_symbols(self, symbols: List[str], exchange_name: str, 
                                     timeframe: str = '1h', since: Optional[int] = None, 
                                     until: Optional[int] = None, batch_size: int = 5) -> Dict[str, pd.DataFrame]:
        """
        Descarga datos para múltiples símbolos en paralelo usando paginación.
        
        Args:
            symbols: Lista de símbolos a descargar
            exchange_name: Nombre del exchange
            timeframe: Intervalo de tiempo
            since: Timestamp inicial en milisegundos
            until: Timestamp final en milisegundos (opcional, por defecto hasta el presente)
            batch_size: Número máximo de descargas simultáneas
            
        Returns:
            Dict[str, DataFrame]: Diccionario con los datos por símbolo
        """
        # Si until no está especificado, usar el tiempo actual
        if until is None:
            until = int(datetime.now().timestamp() * 1000)
            
        results = {}
        tasks = []
        
        for symbol in symbols:
            task = asyncio.create_task(self._download_paginated(
                symbol=symbol,
                exchange_name=exchange_name,
                timeframe=timeframe,
                since=since,
                until=until
            ))
            tasks.append(task)
            
            # Procesar en lotes para no sobrecargar el exchange
            if len(tasks) >= batch_size:
                completed = await asyncio.gather(*tasks)
                for symbol_data, symbol_name in zip(completed, symbols[-batch_size:]):
                    if symbol_data is not None and len(symbol_data) > 0:
                        results[symbol_name] = pd.DataFrame(symbol_data)
                tasks = []
        
        # Procesar el resto de las tareas si las hay
        if tasks:
            completed = await asyncio.gather(*tasks)
            for symbol_data, symbol_name in zip(completed, symbols[-len(tasks):]):
                if symbol_data is not None and len(symbol_data) > 0:
                    results[symbol_name] = pd.DataFrame(symbol_data)
        
        return results

    @with_retry()
    async def async_download_ohlcv(self, symbol: str, exchange_name: str, timeframe: str = '1d', 
                                 since: Optional[int] = None, limit: int = 1000, 
                                 params: dict = {}, use_cache: bool = True) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Descarga datos OHLCV con manejo de reintentos, monitoreo y validación.
        Implementa paginación para obtener todos los datos del rango solicitado.
        
        Returns:
            Tuple[DataFrame, Dict]: DataFrame con datos y diccionario con métricas
        """
        # Iniciar monitoreo de la operación
        operation_id = self.monitor.start_operation(symbol, exchange_name)
        
        # Si since no está definido, usar la fecha de inicio de la configuración
        if since is None:
            config = self.config.exchanges.get(exchange_name, {})
            start_date = config.get('start_date')
            if start_date:
                since = int(pd.Timestamp(start_date).timestamp() * 1000)
        
        try:
            # Verificar si necesitamos datos completos basados en la configuración
            config = self.config.exchanges.get(exchange_name, {})
            start_date = config.get('start_date')
            end_date = config.get('end_date')
            if start_date and end_date:
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                # Si el rango es más de 7 días, no usar caché
                if (end_ts - start_ts).days > 7:
                    use_cache = False
            
            # Intentar obtener datos del caché si está habilitado
            if use_cache:
                cached_data = self.cache.get_from_cache(exchange_name, symbol, timeframe)
                if cached_data is not None:
                    self.logger.info(f"Datos obtenidos del caché para {symbol}")
                    validation_result = self.validator.validate_ohlcv_data(cached_data)
                    return cached_data, validation_result.stats
            
            exchange = self._get_exchange(exchange_name)
            
            # Si no se proporciona since, usar un tiempo por defecto
            if since is None:
                # Calcular timestamp para los últimos períodos
                now = pd.Timestamp.now()
                if timeframe == '1h':
                    # Para datos horarios, obtener las últimas 100 horas
                    since = int((now - pd.Timedelta(hours=limit)).timestamp() * 1000)
                else:
                    # Para otros timeframes, obtener los últimos días
                    since = int((now - pd.Timedelta(days=limit)).timestamp() * 1000)
            
            # Implementar paginación para obtener todos los datos
            all_ohlcv = []
            current_since = since
            config = self.config.exchanges.get(exchange_name, {})
            end_date = config.get('end_date')
            end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000) if end_date else None
            
            while True:
                try:
                    # Descargar datos con paginación
                    ohlcv = await exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        since=current_since,
                        limit=1000  # Máximo permitido por la API
                    )
                    
                    if not ohlcv:
                        break
                        
                    # Filtrar datos por fecha final si está especificada
                    if end_timestamp:
                        ohlcv = [candle for candle in ohlcv if candle[0] <= end_timestamp]
                        if not ohlcv:
                            break
                    
                    all_ohlcv.extend(ohlcv)
                    
                    # Si hemos alcanzado o superado la fecha final, terminar
                    last_timestamp = ohlcv[-1][0]
                    if end_timestamp and last_timestamp >= end_timestamp:
                        break
                    
                    # Calcular el siguiente timestamp basado en el último recibido
                    timeframe_ms = self._get_timeframe_ms(timeframe)
                    current_since = last_timestamp + timeframe_ms
                    
                    # Esperar para respetar los límites de la API
                    await asyncio.sleep(exchange.rateLimit / 1000)
                except Exception as e:
                    self.logger.error(f"Error descargando datos para {symbol}: {str(e)}")
                    break
            
            if not all_ohlcv:
                self.monitor.update_metrics(
                    operation_id,
                    errors=["No data received from exchange"]
                )
                return None, {}

            # Crear DataFrame y validar datos
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Asegurarnos de que el timestamp sea entero
            df['timestamp'] = df['timestamp'].astype('int64')
            validation_result = self.validator.validate_ohlcv_data(df)
            
            # Actualizar métricas con resultados de validación
            self.monitor.update_metrics(
                operation_id,
                rows_downloaded=len(df),
                data_validation_passed=validation_result.passed,
                errors=validation_result.errors,
                stats=validation_result.stats
            )

            if not validation_result.passed:
                self.logger.warning(
                    f"Validación fallida para {symbol} en {exchange_name}: "
                    f"{', '.join(validation_result.errors)}"
                )
            
            # Guardar datos si pasan validación
            if validation_result.passed:
                self._save_data(df, exchange_name, symbol, 'ohlcv', timeframe)
                
                # Guardar en caché si está habilitado
                if use_cache:
                    self.cache.save_to_cache(df, exchange_name, symbol, timeframe)
                
                self.monitor.complete_operation(operation_id, success=True)
                return df, validation_result.stats
            else:
                self.monitor.complete_operation(operation_id, success=False)
                return None, validation_result.stats

        except Exception as e:
            self.monitor.update_metrics(
                operation_id,
                errors=[str(e)]
            )
            self.monitor.complete_operation(operation_id, success=False)
            raise  # RetryManager manejará la excepción

    async def async_download_trades(self, symbol: str, exchange_name: str, since: Optional[int] = None, limit: int = 100, params: dict = {}):
        """Download trade data asynchronously with retries and automatic storage."""
        for attempt in range(self.config.max_retries):
            try:
                exchange = self._get_exchange(exchange_name)
                trades = await exchange.fetch_trades(symbol, since=since, limit=limit, params=params)

                if trades:
                    df = pd.DataFrame(trades)
                    self._save_data(df, exchange_name, symbol, 'trades')
                    return df

                return pd.DataFrame()
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {symbol} on {exchange_name}: {e}")
                await asyncio.sleep(self.config.retry_delay)
        self.logger.error(f"Failed to download trades for {symbol} after {self.config.max_retries} attempts.")
        return None

    def _save_data(self, data: pd.DataFrame, exchange_name: str, symbol: str, data_type: str, timeframe: Optional[str] = None):
        """Save data to CSV and SQLite."""
        try:
            # Crear una copia del DataFrame para no modificar el original
            df_to_save = data.copy()
            
            # Asegurarse de que los timestamps estén en el formato correcto
            if 'timestamp' in df_to_save.columns:
                if isinstance(df_to_save['timestamp'].iloc[0], (int, float)):
                    df_to_save['timestamp'] = pd.to_datetime(df_to_save['timestamp'], unit='ms')
            
            # Generate filename
            symbol_safe = symbol.replace('/', '_')
            timeframe_safe = f"_{timeframe}" if timeframe else ""
            csv_filename = f"{exchange_name}_{symbol_safe}{timeframe_safe}_{data_type}.csv"

            # Get storage path from config
            storage_path = self.config.storage.path
            
            # Create CSV directory if it doesn't exist
            csv_dir = os.path.join(storage_path, 'csv')
            os.makedirs(csv_dir, exist_ok=True)
            csv_path = os.path.join(csv_dir, csv_filename)

            # Para SQLite, mantener timestamps en milisegundos
            df_sqlite = df_to_save.copy()
            if isinstance(df_sqlite['timestamp'].iloc[0], pd.Timestamp):
                df_sqlite['timestamp'] = df_sqlite['timestamp'].astype(np.int64) // 10**6
            
            # Save to CSV (con timestamps legibles)
            save_to_csv(df_to_save, csv_path)

            # Save to SQLite (con timestamps en milisegundos)
            table_name = f"{exchange_name}_{symbol_safe}{timeframe_safe}_{data_type}"
            db_path = os.path.join(storage_path, 'data.db')
            storage = DataStorage(db_path)
            storage.save_to_sqlite(df_sqlite, table_name)

            self.logger.info(f"{data_type} data saved for {symbol} on {exchange_name}")

        except Exception as e:
            self.logger.error(f"Error saving {data_type} data for {symbol}: {e}")