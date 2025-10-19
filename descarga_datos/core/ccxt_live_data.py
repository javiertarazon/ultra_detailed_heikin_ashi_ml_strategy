#!/usr/bin/env python3
"""
CCXT Live Data Provider - Componente para obtener datos en tiempo real de criptomonedas
usando CCXT para operaciones de trading en vivo 24/7.
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple
import threading
from pathlib import Path
import os
import asyncio

# Intentar cargar variables de entorno desde .env (opcional)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv('descarga_datos/.env')
except ImportError:
    # Si python-dotenv no está disponible, continuar sin él
    # Las variables de entorno pueden estar configuradas directamente
    pass

# Intentar importar CCXT
try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logging.warning("CCXT no disponible - Se requiere para trading en vivo de cripto")

class CCXTLiveDataProvider:
    """
    Proveedor de datos en tiempo real desde exchanges CCXT para trading en vivo de cripto.

    Esta clase se encarga de:
    1. Conectar con exchanges CCXT y mantener la conexión activa
    2. Obtener datos OHLCV actualizados para múltiples símbolos y timeframes
    3. Verificar el estado del mercado (cripto siempre abierto)
    4. Proporcionar información en tiempo real sobre precios y volumen
    """

    def __init__(self, config=None, exchange_name='bybit', symbols=None, timeframes=None, history_bars=100):
        """
        Inicializa el proveedor de datos en vivo de CCXT.

        Args:
            config: Configuración desde config.yaml (sección exchanges)
            exchange_name: Nombre del exchange a usar (bybit, binance, etc.)
            symbols: Lista de símbolos a procesar (ej: ['BTC/USDT', 'ETH/USDT'])
            timeframes: Lista de timeframes a procesar (ej: ['1h', '4h'])
            history_bars: Número de barras históricas a descargar inicialmente
        """
        # Cargar configuración si no se proporciona
        if config is None:
            from config.config_loader import load_config
            config = load_config().get('exchanges', {})

        self.config = config
        self.exchange_name = exchange_name
        self.symbols = symbols or ['BTC/USDT']
        self.timeframes = timeframes or ['4h']
        self.history_bars = history_bars
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.connection_lock = threading.Lock()
        self.data_cache = {}  # Cache de datos por símbolo y timeframe
        self.market_status = {}  # Estado del mercado por símbolo (siempre True para crypto)

        # Configuración de reintentos
        self.max_retries = 3
        self.retry_delay = 5

        # Exchange CCXT
        self.exchange = None
        self.async_exchange = None

        # Rutas para almacenamiento de datos en vivo
        self.data_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "live_data"
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Inicializar conexión
        if CCXT_AVAILABLE:
            self._initialize_exchange()

    def _initialize_exchange(self):
        """Inicializa la conexión con el exchange CCXT"""
        try:
            exchange_config = self.config.get(self.exchange_name, {})
            if not exchange_config.get('enabled', False):
                self.logger.warning(f"Exchange {self.exchange_name} no está habilitado en configuración")
                return False

            # Obtener API keys desde variables de entorno o config
            api_key = os.getenv(f'{self.exchange_name.upper()}_API_KEY') or exchange_config.get('api_key', '')
            api_secret = os.getenv(f'{self.exchange_name.upper()}_API_SECRET') or exchange_config.get('api_secret', '')
            
            # Obtener configuración de sandbox
            sandbox_mode = os.getenv('SANDBOX_MODE', 'false').lower() == 'true' or exchange_config.get('sandbox', False)
            
            self.logger.info(f"Inicializando {self.exchange_name} - Sandbox: {sandbox_mode}")
            self.logger.info(f"API Key disponible: {'Sí' if api_key else 'No'}")

            # Configurar exchange síncrono
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': sandbox_mode,
                'timeout': exchange_config.get('timeout', 30000),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # Forzar spot trading en lugar de futures
                },
            })

            # Configurar exchange asíncrono
            async_exchange_class = getattr(ccxt_async, self.exchange_name)
            self.async_exchange = async_exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': sandbox_mode,
                'timeout': exchange_config.get('timeout', 30000),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # Forzar spot trading en lugar de futures
                },
            })

            self.logger.info(f"Exchange {self.exchange_name} inicializado correctamente")
            return True

        except Exception as e:
            self.logger.error(f"Error inicializando exchange {self.exchange_name}: {e}")
            return False

    def connect(self) -> bool:
        """
        Establece conexión con el exchange CCXT y prepara el proveedor para su uso.

        Returns:
            bool: True si la conexión se estableció correctamente
        """
        if self._initialize_exchange():
            try:
                # Verificar conexión cargando mercados
                markets = self.exchange.load_markets()
                self.logger.info(f"Conectado a {self.exchange_name} - {len(markets)} mercados disponibles")

                self.connected = True

                # Pre-cargar datos históricos si se proporcionaron símbolos y timeframes
                if self.symbols and self.timeframes:
                    for symbol in self.symbols:
                        for tf in self.timeframes:
                            try:
                                self.get_historical_data(symbol, tf, self.history_bars)
                            except Exception as e:
                                self.logger.warning(f"Error cargando datos históricos para {symbol} {tf}: {e}")

                # Marcar todos los mercados de crypto como abiertos (24/7)
                for symbol in self.symbols:
                    self.market_status[symbol] = True

                self.logger.info("CCXTLiveDataProvider conectado correctamente")
                return True

            except Exception as e:
                self.logger.error(f"Error conectando a {self.exchange_name}: {e}")
                return False

        return False

    def disconnect(self) -> bool:
        """
        Desconecta el proveedor de datos del exchange CCXT.

        Returns:
            bool: True si la desconexión fue exitosa
        """
        try:
            if self.async_exchange:
                asyncio.run(self.async_exchange.close())
            self.connected = False
            self.logger.info("CCXTLiveDataProvider desconectado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error desconectando CCXTLiveDataProvider: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Verifica si hay conexión activa con el exchange

        Returns:
            bool: True si está conectado
        """
        return self.connected and self.exchange is not None

    def get_last_price(self, symbol: str) -> Optional[float]:
        """
        Obtiene el último precio (precio actual) para un símbolo.
        
        Args:
            symbol: Símbolo del par (ej: 'BTC/USDT')
            
        Returns:
            float: Precio actual o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            # Preferir 'last' price, si no está disponible usar 'close'
            last_price = ticker.get('last') or ticker.get('close')
            if last_price:
                return float(last_price)
            else:
                self.logger.warning(f"No se pudo obtener precio para {symbol}")
                return None
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {symbol}: {e}")
            return None

    def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100, with_indicators: bool = True) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos OHLCV para un símbolo y timeframe específico.
        Si no hay suficientes barras disponibles, usa timeframe más bajo y agrupa.

        Args:
            symbol: Símbolo del par (ej: 'BTC/USDT')
            timeframe: Timeframe (ej: '1h', '4h', '1d')
            limit: Número de barras a obtener
            with_indicators: Si es True, calcula indicadores técnicos

        Returns:
            DataFrame con datos OHLCV e indicadores técnicos o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None

        cache_key = f"{symbol}_{timeframe}_{with_indicators}"
        try:
            # Verificar cache primero
            if cache_key in self.data_cache:
                cached_data = self.data_cache[cache_key]
                # Si los datos son recientes (menos de 5 minutos), devolver cache
                if (datetime.now() - cached_data['timestamp']).seconds < 300:
                    return cached_data['data']

            # PARA TIMEFRAMES CORTOS, SIEMPRE USAR AGRUPACIÓN PARA OBTENER MÁS DATOS HISTÓRICOS
            if timeframe in ['15m', '5m']:
                self.logger.info(f"Usando agrupación para {timeframe} para obtener más datos históricos...")
                df = self._get_data_with_aggregation_enhanced(symbol, timeframe, limit)
                if df is not None and len(df) >= (limit * 0.8):  # Aceptar al menos 80% de las barras mínimas
                    # Cachear datos agrupados
                    self.data_cache[cache_key] = {
                        'data': df.copy(),
                        'timestamp': datetime.now()
                    }
                    # GUARDAR DATOS EN VIVO AUTOMÁTICAMENTE
                    self._save_live_data(symbol, timeframe, df)
                    self.logger.info(f"Datos históricos agrupados obtenidos: {symbol} {timeframe} - {len(df)} barras")
                    return df

            # INTENTAR OBTENER DATOS EN TIMEFRAME SOLICITADO
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

            if not ohlcv or len(ohlcv) < limit:
                self.logger.warning(f"Insuficientes datos en {timeframe} ({len(ohlcv) if ohlcv else 0}/{limit}). Intentando agrupar desde timeframe más bajo...")

                # ESTRATEGIA DE RESPALDO: Usar timeframe más bajo y agrupar
                df = self._get_data_with_aggregation(symbol, timeframe, limit)
                if df is not None and len(df) >= limit:
                    # Cachear datos agrupados
                    self.data_cache[cache_key] = {
                        'data': df.copy(),
                        'timestamp': datetime.now()
                    }
                    # GUARDAR DATOS EN VIVO AUTOMÁTICAMENTE
                    self._save_live_data(symbol, timeframe, df)
                    self.logger.info(f"Datos históricos agrupados obtenidos: {symbol} {timeframe} - {len(df)} barras")
                    return df
                else:
                    self.logger.error(f"No se pudieron obtener suficientes datos ni con agrupación para {symbol} {timeframe}")
                    return None

            # Convertir a DataFrame (caso normal)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            # Añadir columna 'timestamp' además del índice para compatibilidad
            # con las utilidades que esperan una columna llamada 'timestamp'.
            df['timestamp'] = df.index

            # Normalizar nombres de columnas
            df.rename(columns={'volume': 'volume'}, inplace=True)
            
            # Calcular indicadores técnicos si se solicitan
            if with_indicators:
                try:
                    from indicators.technical_indicators import TechnicalIndicators
                    from config.config_loader import load_config_from_yaml
                    
                    config = load_config_from_yaml()
                    indicators = TechnicalIndicators(config)
                    df = indicators.calculate_all_indicators_unified(df)
                    self.logger.info(f"✅ Indicadores técnicos calculados para {symbol} {timeframe}")
                except Exception as ind_error:
                    self.logger.error(f"Error calculando indicadores para {symbol} {timeframe}: {ind_error}")

            # Cachear datos
            self.data_cache[cache_key] = {
                'data': df.copy(),
                'timestamp': datetime.now()
            }

            # GUARDAR DATOS EN VIVO AUTOMÁTICAMENTE
            self._save_live_data(symbol, timeframe, df)

            self.logger.info(f"Datos históricos obtenidos: {symbol} {timeframe} - {len(df)} barras")
            return df

        except Exception as e:
            self.logger.error(f"Error obteniendo datos históricos para {symbol} {timeframe}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Obtiene el precio actual (bid/ask/last) para un símbolo.

        Args:
            symbol: Símbolo del par (ej: 'BTC/USDT')

        Returns:
            Dict con precios o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'last': ticker.get('last', 0),
                'spread': ticker.get('ask', 0) - ticker.get('bid', 0) if ticker.get('ask') and ticker.get('bid') else 0
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo precio actual para {symbol}: {e}")
            return None

    def get_market_status(self, symbol: str) -> bool:
        """
        Verifica si el mercado está abierto para un símbolo.
        Para criptomonedas, siempre retorna True (mercados 24/7).

        Args:
            symbol: Símbolo del par

        Returns:
            bool: True si el mercado está abierto
        """
        # Los mercados de cripto están siempre abiertos
        return True

    def get_latest_bar(self, symbol: str, timeframe: str) -> Optional[pd.Series]:
        """
        Obtiene la barra más reciente para un símbolo y timeframe.

        Args:
            symbol: Símbolo del par
            timeframe: Timeframe

        Returns:
            Series con la barra más reciente o None
        """
        df = self.get_historical_data(symbol, timeframe, limit=1)
        if df is not None and not df.empty:
            return df.iloc[-1]
        return None

    def update_data_cache(self):
        """
        Actualiza el cache de datos para todos los símbolos y timeframes configurados.
        Método diseñado para ser ejecutado en un hilo separado.
        """
        while self.connected:
            try:
                for symbol in self.symbols:
                    for tf in self.timeframes:
                        self.get_historical_data(symbol, tf, self.history_bars)
                time.sleep(60)  # Actualizar cada minuto
            except Exception as e:
                self.logger.error(f"Error actualizando cache de datos: {e}")
                time.sleep(30)  # Esperar 30 segundos en caso de error

    def start_real_time_updates(self):
        """
        Inicia actualizaciones en tiempo real en un hilo separado.
        """
        if not self.connected:
            self.logger.error("No se puede iniciar actualizaciones - no conectado")
            return

        update_thread = threading.Thread(target=self.update_data_cache, daemon=True)
        update_thread.start()
        self.logger.info("Actualizaciones en tiempo real iniciadas")

    def get_account_balance(self) -> Optional[Dict]:
        """
        Obtiene el balance de la cuenta del exchange.

        Returns:
            Dict con balances o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None

        try:
            balance = self.exchange.fetch_balance()
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {})
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo balance de cuenta: {e}")
            return None

    def _save_live_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> None:
        """
        Guarda los datos recolectados en live en la carpeta live_data
        Calcula indicadores técnicos antes de guardar para compatibilidad con backtest
        """
        try:
            # Crear nombre de archivo seguro
            safe_symbol = symbol.replace('/', '_')
            filename = f"{safe_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = self.data_path / filename

            # Importar los indicadores técnicos
            from indicators.technical_indicators import TechnicalIndicators
            from config.config_loader import load_config_from_yaml
            
            # Copiar los datos para no modificar los originales
            df_with_indicators = data.copy()
            
            # Calcular todos los indicadores técnicos
            try:
                config = load_config_from_yaml()
                indicators = TechnicalIndicators(config)
                df_with_indicators = indicators.calculate_all_indicators_unified(df_with_indicators)
                self.logger.info(f"✅ Indicadores técnicos calculados para {symbol} {timeframe}")
            except Exception as ind_error:
                self.logger.error(f"Error calculando indicadores para {symbol} {timeframe}: {ind_error}")
            
            # Guardar datos con indicadores
            df_with_indicators.to_csv(filepath)
            self.logger.debug(f"✅ Datos live guardados con indicadores: {filepath}")
            
            # También guardamos en carpeta live_data_with_indicators para mejor organización
            indicators_data_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "live_data_with_indicators"
            indicators_data_path.mkdir(exist_ok=True, parents=True)
            indicators_filepath = indicators_data_path / filename
            df_with_indicators.to_csv(indicators_filepath)

        except Exception as e:
            self.logger.error(f"Error guardando datos live para {symbol} {timeframe}: {e}")

    def _get_data_with_aggregation(self, symbol: str, target_timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Obtiene datos usando timeframe más bajo y los agrupa para formar el timeframe objetivo.
        Ejemplo: Si target_timeframe='4h', usa '15m' y agrupa 16 barras de 15m en 1 barra de 4h.

        Args:
            symbol: Símbolo del par
            target_timeframe: Timeframe objetivo (ej: '4h')
            limit: Número de barras objetivo

        Returns:
            DataFrame con datos agrupados o None si hay error
        """
        try:
            # MAPA DE TIMEFRAMES PARA AGRUPACIÓN
            timeframe_map = {
                '1d': ('4h', 6),      # 1 día = 6 barras de 4h
                '4h': ('15m', 16),    # 4h = 16 barras de 15m
                '1h': ('5m', 12),     # 1h = 12 barras de 5m
                '30m': ('5m', 6),     # 30m = 6 barras de 5m
                '15m': ('1m', 15),    # 15m = 15 barras de 1m
            }

            if target_timeframe not in timeframe_map:
                self.logger.error(f"No hay estrategia de agrupación definida para {target_timeframe}")
                return None

            source_timeframe, bars_per_group = timeframe_map[target_timeframe]

            # Calcular cuántas barras del timeframe fuente necesitamos
            source_limit = limit * bars_per_group

            self.logger.info(f"Obteniendo {source_limit} barras de {source_timeframe} para agrupar en {limit} barras de {target_timeframe}")

            # Obtener datos del timeframe fuente
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=source_timeframe, limit=source_limit)

            if not ohlcv or len(ohlcv) < source_limit:
                self.logger.warning(f"Insuficientes datos fuente: {len(ohlcv) if ohlcv else 0}/{source_limit} barras de {source_timeframe}")
                return None

            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # AGRUPAR DATOS: Combinar 'bars_per_group' barras en una
            grouped_data = []

            for i in range(0, len(df), bars_per_group):
                group = df.iloc[i:i+bars_per_group]
                if len(group) == bars_per_group:  # Solo grupos completos
                    # Crear barra agrupada
                    aggregated_bar = {
                        'timestamp': group.index[0],  # Timestamp del inicio del grupo
                        'open': group['open'].iloc[0],  # Open del primer precio
                        'high': group['high'].max(),   # Máximo high del grupo
                        'low': group['low'].min(),     # Mínimo low del grupo
                        'close': group['close'].iloc[-1],  # Close del último precio
                        'volume': group['volume'].sum()    # Suma de volúmenes
                    }
                    grouped_data.append(aggregated_bar)

            if len(grouped_data) < limit:
                self.logger.warning(f"Agrupación incompleta: {len(grouped_data)}/{limit} barras")
                return None

            # Crear DataFrame final
            result_df = pd.DataFrame(grouped_data)
            result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
            result_df.set_index('timestamp', inplace=True)
            # Mantener copia de la columna 'timestamp' además del índice
            result_df['timestamp'] = result_df.index

            self.logger.info(f"✅ Datos agrupados exitosamente: {len(result_df)} barras de {target_timeframe} desde {source_timeframe}")
            return result_df

        except Exception as e:
            self.logger.error(f"Error en agrupación de datos para {symbol} {target_timeframe}: {e}")
            return None

    def _get_data_with_aggregation_enhanced(self, symbol: str, target_timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Versión mejorada de agrupación que obtiene más datos históricos para timeframes cortos.
        Usa timeframe fuente más bajo y multiplica por un factor para tener suficientes datos.

        Args:
            symbol: Símbolo del par
            target_timeframe: Timeframe objetivo (ej: '15m')
            limit: Número mínimo de barras objetivo

        Returns:
            DataFrame con más datos agrupados o None si hay error
        """
        try:
            # CONFIGURACIÓN MEJORADA PARA TIMEFRAMES CORTOS
            enhanced_config = {
                '15m': ('5m', 3, 5),   # 15m = 3 barras de 5m, multiplicar x5 para más datos (antes x10)
                '5m': ('1m', 5, 8),    # 5m = 5 barras de 1m, multiplicar x8 para más datos
            }

            if target_timeframe not in enhanced_config:
                # Fallback a la función original
                return self._get_data_with_aggregation(symbol, target_timeframe, limit)

            source_timeframe, bars_per_group, multiplier = enhanced_config[target_timeframe]

            # Calcular barras fuente necesarias (multiplicar para tener más datos históricos)
            enhanced_limit = limit * multiplier  # Más barras objetivo
            source_limit = enhanced_limit * bars_per_group

            self.logger.info(f"Obteniendo {source_limit} barras de {source_timeframe} para crear {enhanced_limit} barras de {target_timeframe} (multiplicador x{multiplier})")

            # Obtener datos del timeframe fuente
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=source_timeframe, limit=source_limit)

            if not ohlcv or len(ohlcv) < (source_limit * 0.5):  # Permitir 50% de los datos para más flexibilidad
                self.logger.warning(f"Insuficientes datos fuente: {len(ohlcv) if ohlcv else 0}/{source_limit} barras de {source_timeframe}")
                return None

            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # AGRUPAR DATOS: Combinar 'bars_per_group' barras en una
            grouped_data = []

            for i in range(0, len(df), bars_per_group):
                group = df.iloc[i:i+bars_per_group]
                if len(group) == bars_per_group:  # Solo grupos completos
                    # Crear barra agrupada
                    aggregated_bar = {
                        'timestamp': group.index[0],  # Timestamp del inicio del grupo
                        'open': group['open'].iloc[0],  # Open del primer precio
                        'high': group['high'].max(),   # Máximo high del grupo
                        'low': group['low'].min(),     # Mínimo low del grupo
                        'close': group['close'].iloc[-1],  # Close del último precio
                        'volume': group['volume'].sum()    # Suma de volúmenes
                    }
                    grouped_data.append(aggregated_bar)

            if len(grouped_data) < (limit * 0.8):  # Aceptar al menos 80% de las barras objetivo mínimas
                self.logger.warning(f"Agrupación incompleta: {len(grouped_data)}/{limit} barras mínimas")
                return None

            # Crear DataFrame final
            result_df = pd.DataFrame(grouped_data)
            result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
            result_df.set_index('timestamp', inplace=True)
            # Mantener copia de la columna 'timestamp' además del índice
            result_df['timestamp'] = result_df.index

            self.logger.info(f"✅ Datos agrupados mejorados: {len(result_df)} barras de {target_timeframe} desde {source_timeframe}")
            return result_df

        except Exception as e:
            self.logger.error(f"Error en agrupación mejorada para {symbol} {target_timeframe}: {e}")
            return None