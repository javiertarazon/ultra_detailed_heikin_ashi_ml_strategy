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
    load_dotenv()
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
            })

            # Configurar exchange asíncrono
            async_exchange_class = getattr(ccxt_async, self.exchange_name)
            self.async_exchange = async_exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': sandbox_mode,
                'timeout': exchange_config.get('timeout', 30000),
                'enableRateLimit': True,
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
        Verifica si el proveedor está conectado al exchange.

        Returns:
            bool: True si está conectado
        """
        return self.connected and self.exchange is not None

    def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos OHLCV para un símbolo y timeframe específico.

        Args:
            symbol: Símbolo del par (ej: 'BTC/USDT')
            timeframe: Timeframe (ej: '1h', '4h', '1d')
            limit: Número de barras a obtener

        Returns:
            DataFrame con datos OHLCV o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None

        cache_key = f"{symbol}_{timeframe}"
        try:
            # Verificar cache primero
            if cache_key in self.data_cache:
                cached_data = self.data_cache[cache_key]
                # Si los datos son recientes (menos de 5 minutos), devolver cache
                if (datetime.now() - cached_data['timestamp']).seconds < 300:
                    return cached_data['data']

            # Obtener datos desde CCXT
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

            if not ohlcv:
                self.logger.warning(f"No se obtuvieron datos para {symbol} {timeframe}")
                return None

            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Normalizar nombres de columnas
            df.rename(columns={'volume': 'volume'}, inplace=True)

            # Cachear datos
            self.data_cache[cache_key] = {
                'data': df.copy(),
                'timestamp': datetime.now()
            }

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