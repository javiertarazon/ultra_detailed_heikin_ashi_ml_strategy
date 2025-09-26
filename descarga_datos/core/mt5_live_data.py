#!/usr/bin/env python3
"""
MT5 Live Data Provider - Componente para obtener datos en tiempo real de MetaTrader 5
para operaciones de trading en vivo con actualización continua.
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

# Intentar importar MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 no disponible - Se requiere para trading en vivo")

class MT5LiveDataProvider:
    """
    Proveedor de datos en tiempo real desde MetaTrader 5 para trading en vivo.
    
    Esta clase se encarga de:
    1. Conectar con MT5 y mantener la conexión activa
    2. Obtener datos OHLCV actualizados para múltiples símbolos y timeframes
    3. Verificar el estado del mercado (abierto/cerrado)
    4. Proporcionar información en tiempo real sobre el saldo de la cuenta
    """
    
    def __init__(self, config=None, account_info=None, symbols=None, timeframes=None, history_bars=1000):
        """
        Inicializa el proveedor de datos en vivo de MT5.
        
        Args:
            config: Configuración desde config.yaml (sección mt5)
            account_info: Información adicional de la cuenta si es necesaria
            symbols: Lista de símbolos a procesar (ej: ['EURUSD', 'USDJPY'])
            timeframes: Lista de timeframes a procesar (ej: ['1h', '4h'])
            history_bars: Número de barras históricas a descargar inicialmente
        """
        # Cargar configuración si no se proporciona
        if config is None:
            from config.config_loader import load_config
            config = load_config().get('mt5', {})
            
        self.config = config
        self.account_info = account_info or {}
        self.symbols = symbols or []
        self.timeframes = timeframes or []
        self.history_bars = history_bars
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.connection_lock = threading.Lock()
        self.data_cache = {}  # Cache de datos por símbolo y timeframe
        self.market_status = {}  # Estado del mercado por símbolo
        
        # Configuración de reintentos
        self.max_retries = getattr(config, 'max_retries', 3) if hasattr(config, 'max_retries') else 3
        self.retry_delay = getattr(config, 'retry_delay', 5) if hasattr(config, 'retry_delay') else 5
        
        # Rutas para almacenamiento de datos en vivo
        self.data_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "live_data"
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Inicializar conexión
        if MT5_AVAILABLE:
            self._initialize_mt5()
    
    def connect(self) -> bool:
        """
        Establece conexión con MT5 y prepara el proveedor para su uso.
        
        Returns:
            bool: True si la conexión se estableció correctamente
        """
        if self._initialize_mt5():
            self.connected = True
            self.logger.info("MT5LiveDataProvider conectado correctamente")
            
            # Pre-cargar datos históricos si se proporcionaron símbolos y timeframes
            if self.symbols and self.timeframes:
                for symbol in self.symbols:
                    for tf in self.timeframes:
                        self.get_historical_data(symbol, tf, self.history_bars)
            
            return True
        
        return False
        
    def disconnect(self) -> bool:
        """
        Desconecta el proveedor de datos de MT5.
        
        Returns:
            bool: True si la desconexión fue exitosa
        """
        with self.connection_lock:
            self.connected = False
            self.logger.info("MT5LiveDataProvider desconectado")
            return True
            
    def is_connected(self) -> bool:
        """
        Verifica si el proveedor está conectado a MT5.
        
        Returns:
            bool: True si está conectado
        """
        return self.connected and MT5_AVAILABLE and mt5.terminal_info() is not None
        
    def get_current_data(self, symbol: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """
        Obtiene los datos actuales para un símbolo y timeframe específicos.
        
        Args:
            symbol: Símbolo a consultar (ej: "EURUSD")
            timeframe: Timeframe en formato string ("1m", "5m", "1h", "4h", "1d")
            bars: Número de barras a recuperar
            
        Returns:
            DataFrame con datos OHLCV o None si hay error
        """
        return self.get_historical_data(symbol, timeframe, bars)
            
    def get_historical_data(self, symbol: str, timeframe: str, bars: int = 1000) -> pd.DataFrame:
        """
        Obtiene datos históricos para un símbolo y timeframe específicos.
        
        Args:
            symbol: Símbolo a consultar (ej: "EURUSD")
            timeframe: Timeframe en formato string ("1m", "5m", "1h", "4h", "1d")
            bars: Número de barras a recuperar
            
        Returns:
            DataFrame con datos OHLCV o None si hay error
        """
        self.logger.info(f"Obteniendo datos históricos para {symbol} {timeframe} ({bars} barras)")
        
        # Convertir timeframe de string a constante MT5
        tf_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
            "1w": mt5.TIMEFRAME_W1,
        }
        
        mt5_tf = tf_map.get(timeframe.lower())
        if mt5_tf is None:
            self.logger.error(f"Timeframe no válido: {timeframe}")
            return None
            
        try:
            # Obtener datos históricos recientes
            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
            if rates is None or len(rates) == 0:
                self.logger.error(f"No se pudieron obtener datos para {symbol} {timeframe}")
                return None
                
            # Convertir a DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Renombrar columnas para consistencia
            df = df.rename(columns={
                'tick_volume': 'volume'
            })
            
            # Mantener solo columnas necesarias
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Cachear datos
            cache_key = f"{symbol}_{timeframe}"
            self.data_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error al obtener datos para {symbol} {timeframe}: {str(e)}")
            return None
    
    def _initialize_mt5(self) -> bool:
        """
        Inicializa la conexión con MetaTrader 5.
        
        Returns:
            bool: True si la conexión se estableció correctamente
        """
        with self.connection_lock:
            if not MT5_AVAILABLE:
                self.logger.error("MT5 no está disponible. Instale el paquete MetaTrader5.")
                return False
            
            try:
                # Inicializar MT5 si no está inicializado
                if not mt5.initialize():
                    self.logger.error(f"Error al inicializar MT5: {mt5.last_error()}")
                    return False
                
                # Login si se proporcionan credenciales
                if hasattr(self.config, 'login') and self.config.login:
                    if not mt5.login(
                        self.config.login,
                        password=self.config.password,
                        server=self.config.server
                    ):
                        self.logger.error(f"Error en login MT5: {mt5.last_error()}")
                        return False
                
                # Verificar conexión
                account_info = mt5.account_info()
                if account_info is None:
                    self.logger.error("No se pudo obtener información de la cuenta MT5")
                    return False
                
                # Almacenar información de la cuenta
                self.account_info = {
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'leverage': account_info.leverage,
                    'name': account_info.name,
                    'server': account_info.server
                }
                
                self.connected = True
                self.logger.info(f"MT5 conectado: {self.account_info['name']} @ {self.account_info['server']}")
                self.logger.info(f"Balance: {self.account_info['balance']}, Equity: {self.account_info['equity']}")
                
                return True
            
            except Exception as e:
                self.logger.error(f"Error inicializando MT5: {e}")
                return False
    
    def ensure_connection(self) -> bool:
        """
        Asegura que hay una conexión activa con MT5, reconectando si es necesario.
        
        Returns:
            bool: True si la conexión está activa
        """
        with self.connection_lock:
            if self.connected:
                # Verificar si la conexión sigue activa
                if not mt5.terminal_info():
                    self.logger.warning("Conexión MT5 perdida. Intentando reconectar...")
                    self.connected = False
            
            if not self.connected:
                return self._initialize_mt5()
            
            return True
    
    def get_live_data(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtiene datos en tiempo real para un símbolo y timeframe específico.
        
        Args:
            symbol: Símbolo para obtener datos (ej: "EURUSD", "AAPL.US")
            timeframe: Timeframe en formato MT5 (ej: "1h", "4h", "1d")
            bars: Número de barras a obtener
        
        Returns:
            DataFrame con datos OHLCV o None si falla
        """
        if not self.ensure_connection():
            self.logger.error("No hay conexión con MT5")
            return None
        
        try:
            # Convertir timeframe a formato MT5
            mt5_timeframe = self._convert_timeframe(timeframe)
            if mt5_timeframe is None:
                self.logger.error(f"Timeframe no soportado: {timeframe}")
                return None
            
            # Obtener datos
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No hay datos para {symbol} en timeframe {timeframe}")
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            
            # Renombrar columnas para consistencia
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            })
            
            # Mantener solo columnas necesarias
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Actualizar caché
            cache_key = f"{symbol}_{timeframe}"
            self.data_cache[cache_key] = {
                'data': df,
                'last_update': datetime.now()
            }
            
            # Guardar datos para análisis
            self._save_live_data(symbol, timeframe, df)
            
            self.logger.debug(f"Datos en vivo obtenidos: {symbol} {timeframe} - {len(df)} barras")
            return df
        
        except Exception as e:
            self.logger.error(f"Error obteniendo datos en vivo para {symbol} {timeframe}: {e}")
            return None
    
    def get_market_status(self, symbol: str) -> Dict:
        """
        Verifica el estado del mercado para un símbolo.
        
        Args:
            symbol: Símbolo a verificar
        
        Returns:
            Diccionario con información del estado del mercado
        """
        if not self.ensure_connection():
            return {'is_open': False, 'reason': 'No hay conexión con MT5'}
        
        try:
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return {
                    'is_open': False,
                    'reason': f"Símbolo {symbol} no encontrado",
                    'next_open': None,
                    'session_remains': 0
                }
            
            # Determinar si el mercado está abierto
            # Verificar si el símbolo está habilitado para trading y si hay precios disponibles
            is_enabled = symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED
            has_prices = symbol_info.bid > 0 and symbol_info.ask > 0
            is_open = is_enabled and has_prices
            
            # Calcular próxima apertura y tiempo restante si está disponible
            current_time = datetime.now()
            next_open = None
            session_remains = 0
            
            # Almacenar resultado
            status = {
                'is_open': is_open,
                'reason': "Mercado abierto" if is_open else "Mercado cerrado",
                'next_open': next_open,
                'session_remains': session_remains,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'spread': symbol_info.spread,
                'digits': symbol_info.digits,
                'last_update': current_time
            }
            
            # Actualizar caché
            self.market_status[symbol] = status
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del mercado para {symbol}: {e}")
            return {'is_open': False, 'reason': f"Error: {str(e)}"}
    
    def get_account_info(self) -> Dict:
        """
        Obtiene información actualizada de la cuenta.
        
        Returns:
            Diccionario con información de la cuenta
        """
        if not self.ensure_connection():
            return self.account_info or {}
        
        try:
            account_info = mt5.account_info()
            if account_info:
                self.account_info = {
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'leverage': account_info.leverage,
                    'name': account_info.name,
                    'server': account_info.server,
                    'last_update': datetime.now()
                }
            
            return self.account_info
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de la cuenta: {e}")
            return self.account_info or {}
    
    def get_symbols_info(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Obtiene información detallada sobre múltiples símbolos.
        
        Args:
            symbols: Lista de símbolos
        
        Returns:
            Diccionario con información de cada símbolo
        """
        if not self.ensure_connection():
            return {}
        
        result = {}
        for symbol in symbols:
            try:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info:
                    result[symbol] = {
                        'bid': symbol_info.bid,
                        'ask': symbol_info.ask,
                        'spread': symbol_info.spread,
                        'digits': symbol_info.digits,
                        'min_lot': symbol_info.volume_min,
                        'max_lot': symbol_info.volume_max,
                        'lot_step': symbol_info.volume_step,
                        'point': symbol_info.point,
                        'tick_size': symbol_info.trade_tick_size,
                        'tick_value': symbol_info.trade_tick_value,
                        'contract_size': symbol_info.trade_contract_size,
                        'currency_base': symbol_info.currency_base,
                        'currency_profit': symbol_info.currency_profit
                    }
            except Exception as e:
                self.logger.error(f"Error obteniendo información para {symbol}: {e}")
        
        return result
    
    def _convert_timeframe(self, timeframe: str) -> Optional[int]:
        """
        Convierte timeframe string a constante MT5.
        
        Args:
            timeframe: String con el timeframe (ej: "1m", "5m", "1h", "4h", "1d")
        
        Returns:
            Constante MT5 correspondiente o None si no es válido
        """
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
    
    def _save_live_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> None:
        """
        Guarda los datos en vivo para análisis posterior.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            data: DataFrame con datos
        """
        try:
            # Crear nombre de archivo seguro
            safe_symbol = symbol.replace("/", "_").replace(".", "_")
            filename = self.data_path / f"{safe_symbol}_{timeframe}_live.csv"
            
            # Guardar datos
            data.to_csv(filename, index=False)
            
        except Exception as e:
            self.logger.warning(f"Error guardando datos en vivo: {e}")
    
    def shutdown(self) -> None:
        """
        Cierra la conexión con MT5.
        """
        if MT5_AVAILABLE and self.connected:
            with self.connection_lock:
                mt5.shutdown()
                self.connected = False
                self.logger.info("MT5 desconectado")
    
    def __del__(self):
        """
        Asegura que la conexión se cierre al destruir el objeto.
        """
        self.shutdown()
    
    # === Métodos adicionales para facilitar el trading en vivo ===
    
    def get_recent_ohlcv_with_indicators(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtiene datos recientes con indicadores calculados para toma de decisiones.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            bars: Número de barras
        
        Returns:
            DataFrame con OHLCV e indicadores o None si falla
        """
        df = self.get_live_data(symbol, timeframe, bars)
        if df is None or len(df) < 20:  # Mínimo necesario para indicadores
            return None
        
        try:
            # Importar calculador de indicadores
            from indicators.technical_indicators import add_indicators
            
            # Añadir indicadores al DataFrame
            df_with_indicators = add_indicators(df)
            
            return df_with_indicators
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores para {symbol} {timeframe}: {e}")
            return df  # Devolver al menos los datos sin indicadores
    
    def start_data_stream(self, symbols: List[str], timeframe: str, callback=None, 
                         update_interval: int = 10) -> threading.Thread:
        """
        Inicia un stream continuo de datos en segundo plano.
        
        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe
            callback: Función a llamar con nuevos datos (symbol, df)
            update_interval: Intervalo de actualización en segundos
        
        Returns:
            Thread que está ejecutando el stream
        """
        def data_stream_worker():
            while self._streaming_active:
                for symbol in symbols:
                    try:
                        df = self.get_live_data(symbol, timeframe)
                        if df is not None and callback is not None:
                            callback(symbol, df)
                    except Exception as e:
                        self.logger.error(f"Error en stream de datos para {symbol}: {e}")
                
                # Esperar hasta la próxima actualización
                time.sleep(update_interval)
        
        # Iniciar thread
        self._streaming_active = True
        stream_thread = threading.Thread(target=data_stream_worker)
        stream_thread.daemon = True
        stream_thread.start()
        
        self.logger.info(f"Stream de datos iniciado para {symbols} en {timeframe}")
        return stream_thread
    
    def stop_data_stream(self) -> None:
        """
        Detiene el stream de datos.
        """
        self._streaming_active = False
        self.logger.info("Stream de datos detenido")