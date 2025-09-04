"""
Downloader refactorizado usando las nuevas interfaces y elimina duplicaciones.
"""
import ccxt
import ccxt.async_support as ccxt_async
import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from datetime import datetime, timedelta
import logging

from ..core.interfaces import IDataDownloader, IOHLCVData
from ..core.config_manager import ConfigManager, SystemConfig
from ..core.data_adapters import AdapterFactory
from ..core.data_validator import DataValidator
from ..core.cache_manager import SmartCacheManager

class OptimizedDataDownloader(IDataDownloader):
    """Downloader optimizado con interfaces limpias"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        self.adapter_factory = AdapterFactory()
        self.validator = DataValidator(self.logger)
        self.cache = SmartCacheManager()
        
        # Exchange management
        self.exchange = None
        self.exchange_name = self.config.exchange.name
        
        # Performance tracking
        self.download_stats = {
            'total_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'total_symbols': 0
        }
    
    async def setup_exchange(self) -> bool:
        """Configura el exchange según la configuración"""
        try:
            exchange_config = self.config.exchange
            
            # Obtener clase del exchange
            exchange_class = getattr(ccxt_async, exchange_config.name)
            
            # Configuración básica
            ccxt_config = {
                'enableRateLimit': True,
                'timeout': exchange_config.timeout * 1000,  # Convert to ms
                'rateLimit': 60000 / exchange_config.rate_limit,  # ms between requests
            }
            
            # Agregar credenciales si están disponibles
            if exchange_config.api_key and exchange_config.api_key != 'your_api_key_here':
                ccxt_config['apiKey'] = exchange_config.api_key
            
            if exchange_config.secret and exchange_config.secret != 'your_secret_here':
                ccxt_config['secret'] = exchange_config.secret
            
            if exchange_config.sandbox:
                ccxt_config['sandbox'] = True
            
            self.exchange = exchange_class(ccxt_config)
            
            # Verificar conexión
            await self.exchange.load_markets()
            self.logger.info(f"Exchange {exchange_config.name} configurado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configurando exchange: {e}")
            return False
    
    async def download_symbol_data(self, symbol: str, timeframe: str, 
                                 start_date: str, end_date: str) -> IOHLCVData:
        """
        Descarga datos de un símbolo específico con manejo inteligente de caché.
        
        Args:
            symbol: Símbolo a descargar (ej: 'BTC/USDT')
            timeframe: Intervalo de tiempo (ej: '1h')
            start_date: Fecha inicial en formato 'YYYY-MM-DD'
            end_date: Fecha final en formato 'YYYY-MM-DD'
            
        Returns:
            IOHLCVData: Datos OHLCV descargados
        """
        # Verificar caché primero
        cache_key = self.cache.get_cache_key(symbol, timeframe, start_date, end_date)
        cached_data = self.cache.get_dataframe(cache_key)
        
        if cached_data is not None and not cached_data.empty:
            self.download_stats['cache_hits'] += 1
            self.logger.info(f"Datos de {symbol} obtenidos del caché")
            adapter = self.adapter_factory.create_adapter('dataframe', self.logger)
            return adapter.adapt_ohlcv(cached_data, symbol, timeframe)
        
        # Descargar datos frescos
        try:
            if not self.exchange:
                raise RuntimeError("Exchange no configurado. Ejecute setup_exchange() primero.")
            
            # Convertir fechas a timestamps
            since = self._date_to_timestamp(start_date)
            until = self._date_to_timestamp(end_date, end_of_day=True)
            
            self.logger.info(f"Descargando {symbol} {timeframe} desde {start_date} hasta {end_date}")
            
            # Descargar con paginación
            raw_data = await self._download_paginated(symbol, timeframe, since, until)
            
            if not raw_data:
                self.logger.warning(f"No se obtuvieron datos para {symbol}")
                return self.adapter_factory.create_adapter('ccxt').adapt_ohlcv([], symbol, timeframe)
            
            self.download_stats['total_requests'] += 1
            
            # Adaptar datos
            adapter = self.adapter_factory.create_adapter('ccxt', self.logger)
            ohlcv_data = adapter.adapt_ohlcv(raw_data, symbol, timeframe)
            
            # Validar datos
            validation_result = self.validator.validate_ohlcv_data(ohlcv_data.get_dataframe())
            if not validation_result.is_valid:
                self.logger.error(f"Datos inválidos para {symbol}: {validation_result.errors}")
                return ohlcv_data
            
            # Guardar en caché
            self.cache.set_dataframe(cache_key, ohlcv_data.get_dataframe(), persist=True)
            
            self.logger.info(f"Descargados {len(ohlcv_data.get_dataframe())} registros para {symbol}")
            return ohlcv_data
            
        except Exception as e:
            self.download_stats['failed_requests'] += 1
            self.logger.error(f"Error descargando {symbol}: {e}")
            # Retornar datos vacíos en caso de error
            adapter = self.adapter_factory.create_adapter('ccxt')
            return adapter.adapt_ohlcv([], symbol, timeframe)
    
    async def download_multiple_symbols(self, symbols: List[str], timeframe: str,
                                      start_date: str, end_date: str) -> Dict[str, IOHLCVData]:
        """
        Descarga datos para múltiples símbolos de forma eficiente.
        
        Args:
            symbols: Lista de símbolos a descargar
            timeframe: Intervalo de tiempo
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            Dict[str, IOHLCVData]: Diccionario con datos por símbolo
        """
        self.download_stats['total_symbols'] = len(symbols)
        results = {}
        
        # Descargar en paralelo pero con límite de concurrencia
        semaphore = asyncio.Semaphore(self.config.parallel_downloads)
        
        async def download_single(symbol: str) -> Tuple[str, IOHLCVData]:
            async with semaphore:
                data = await self.download_symbol_data(symbol, timeframe, start_date, end_date)
                return symbol, data
        
        # Ejecutar descargas en paralelo
        tasks = [download_single(symbol) for symbol in symbols]
        completed_downloads = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        for result in completed_downloads:
            if isinstance(result, Exception):
                self.logger.error(f"Error en descarga paralela: {result}")
                continue
            
            symbol, data = result
            results[symbol] = data
        
        self.logger.info(f"Descarga múltiple completada: {len(results)}/{len(symbols)} símbolos")
        return results
    
    async def _download_paginated(self, symbol: str, timeframe: str, 
                                since: int, until: int) -> List[List]:
        """
        Descarga datos usando paginación para obtener el rango completo.
        
        Args:
            symbol: Símbolo a descargar
            timeframe: Intervalo de tiempo
            since: Timestamp inicial en milisegundos
            until: Timestamp final en milisegundos
            
        Returns:
            List[List]: Datos OHLCV raw de CCXT
        """
        all_data = []
        current_since = since
        page_limit = self.config.data.max_candles_per_request
        timeframe_ms = self._get_timeframe_ms(timeframe)
        
        retry_count = 0
        max_retries = self.config.exchange.retry_attempts
        
        while current_since < until:
            try:
                # Descargar página actual
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=page_limit
                )
                
                if not ohlcv:
                    break
                
                # Filtrar datos dentro del rango
                filtered_data = [
                    candle for candle in ohlcv 
                    if since <= candle[0] <= until
                ]
                
                all_data.extend(filtered_data)
                
                # Actualizar timestamp para siguiente página
                last_timestamp = ohlcv[-1][0]
                
                # Si no hay más datos o hemos llegado al final, terminar
                if len(ohlcv) < page_limit or last_timestamp >= until:
                    break
                
                current_since = last_timestamp + timeframe_ms
                retry_count = 0  # Reset retry count on success
                
                # Rate limiting
                await asyncio.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.error(f"Max retries alcanzado para {symbol}: {e}")
                    break
                
                # Backoff exponencial
                delay = self.config.exchange.retry_delay * (2 ** (retry_count - 1))
                self.logger.warning(f"Error descargando {symbol}, reintentando en {delay}s: {e}")
                await asyncio.sleep(delay)
        
        return all_data
    
    def _get_timeframe_ms(self, timeframe: str) -> int:
        """Convierte timeframe a milisegundos"""
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        
        multipliers = {
            'm': 60 * 1000,          # minutos
            'h': 60 * 60 * 1000,     # horas
            'd': 24 * 60 * 60 * 1000, # días
            'w': 7 * 24 * 60 * 60 * 1000  # semanas
        }
        
        return value * multipliers.get(unit, 60 * 1000)
    
    def _date_to_timestamp(self, date_str: str, end_of_day: bool = False) -> int:
        """Convierte fecha string a timestamp en milisegundos"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            if end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59)
            
            return int(dt.timestamp() * 1000)
            
        except ValueError as e:
            raise ValueError(f"Formato de fecha inválido '{date_str}'. Use YYYY-MM-DD: {e}")
    
    async def cleanup(self):
        """Limpia recursos del downloader"""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None
        
        self.logger.info("Downloader limpiado correctamente")
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de descarga"""
        stats = self.download_stats.copy()
        
        if stats['total_requests'] > 0:
            stats['success_rate'] = ((stats['total_requests'] - stats['failed_requests']) / 
                                   stats['total_requests']) * 100
        else:
            stats['success_rate'] = 0
        
        if stats['total_requests'] + stats['cache_hits'] > 0:
            total_operations = stats['total_requests'] + stats['cache_hits']
            stats['cache_hit_rate'] = (stats['cache_hits'] / total_operations) * 100
        else:
            stats['cache_hit_rate'] = 0
        
        # Agregar estadísticas de caché
        cache_stats = self.cache.get_stats()
        stats['cache_info'] = cache_stats
        
        return stats

class DownloaderFactory:
    """Factory para crear downloaders optimizados"""
    
    @staticmethod
    def create_downloader(config_path: Optional[str] = None) -> OptimizedDataDownloader:
        """
        Crea un downloader configurado.
        
        Args:
            config_path: Ruta al archivo de configuración
            
        Returns:
            OptimizedDataDownloader: Downloader configurado
        """
        from ..core.config_manager import get_config_manager
        
        config_manager = get_config_manager(config_path)
        return OptimizedDataDownloader(config_manager)
