#!/usr/bin/env python3
"""
CCXT Order Executor - Componente para ejecutar operaciones de trading en exchanges CCXT.

Este módulo se encarga de ejecutar órdenes de trading en exchanges de criptomonedas usando CCXT,
incluyendo apertura y cierre de posiciones, gestión de stop loss y take profit.

Author: GitHub Copilot
Date: Septiembre 2025
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.logger import get_logger
import threading
from typing import Dict, List, Optional, Union, Tuple, Any
from enum import Enum
import json
from pathlib import Path
import os
import uuid

# Intentar importar CCXT
try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logging.warning("CCXT no disponible - Se requiere para ejecutar órdenes de cripto")

# Importar utilidades usando paths absolutos
from utils.logger import setup_logger
from utils.retry_manager import retry_operation
from risk_management.risk_management import apply_risk_management
import logging

# Enums para órdenes
class OrderType(Enum):
    """Tipos de órdenes soportados en CCXT"""
    BUY = 'buy'
    SELL = 'sell'
    LIMIT_BUY = 'limit_buy'
    LIMIT_SELL = 'limit_sell'
    STOP_BUY = 'stop_buy'
    STOP_SELL = 'stop_sell'

class CCXTOrderExecutor:
    """
    Ejecutor de órdenes para exchanges CCXT que permite:
    1. Abrir posiciones de compra/venta
    2. Establecer stop loss y take profit
    3. Cerrar posiciones existentes
    4. Gestionar trailing stops
    """

    def __init__(self, config=None, live_data_provider=None, exchange_name='bybit',
                 risk_per_trade=None, max_positions=None):
        """
        Inicializa el ejecutor de órdenes.

        Args:
            config: Configuración desde config.yaml
            live_data_provider: Opcional, instancia de CCXTLiveDataProvider
            exchange_name: Nombre del exchange (bybit, binance, etc.)
            risk_per_trade: Porcentaje de riesgo por operación (0.01 = 1%)
            max_positions: Número máximo de posiciones abiertas simultáneamente
        """
        # Cargar configuración si no se proporciona
        if config is None:
            from config.config_loader import load_config
            config_data = load_config()
            config = config_data.get('exchanges', {})

        self.config = config
        self.exchange_name = exchange_name
        self.live_data_provider = live_data_provider

        # Usar valores proporcionados o valores por defecto
        self.risk_per_trade = risk_per_trade or 0.01  # 1% por defecto
        self.max_positions = max_positions or 5

        # Configurar logger
        self.logger = setup_logger('CCXTOrderExecutor')
        self.connected = False
        self.connection_lock = threading.Lock()

        # Exchange CCXT
        self.exchange = None
        self.async_exchange = None

        # Órdenes y posiciones
        self.open_positions = {}  # ticket -> position_info
        self.pending_orders = {}  # order_id -> order_info
        self.position_history = []

        # Gestión de riesgo
        self.risk_manager = None

        # Inicializar exchange
        if CCXT_AVAILABLE:
            self._initialize_exchange()

    def _initialize_exchange(self):
        """Inicializa la conexión con el exchange CCXT"""
        try:
            exchange_config = self.config.get('exchanges', {}).get(self.exchange_name, {})
            # Intentar cargar .env local si está presente (fallback seguro)
            try:
                from dotenv import load_dotenv
                import os
                # Buscar .env en múltiples ubicaciones
                possible_paths = [
                    Path(__file__).parent.parent / '.env',  # descarga_datos/.env
                    Path(__file__).parent.parent.parent / '.env',  # raíz/.env
                    Path.cwd() / '.env',  # directorio actual
                    Path.cwd() / 'descarga_datos' / '.env',  # descarga_datos desde cwd
                ]
                
                dotenv_loaded = False
                for dotenv_path in possible_paths:
                    if dotenv_path.exists():
                        load_dotenv(dotenv_path)
                        self.logger.info(f".env cargado desde: {dotenv_path}")
                        dotenv_loaded = True
                        break
                
                if not dotenv_loaded:
                    self.logger.warning("No se encontró archivo .env en las rutas esperadas")
                    
            except Exception as e:
                self.logger.error(f"Error cargando .env: {e}")
                # no hay dotenv o falla la carga, continuar

            # Priorizar claves en config.yaml, si no existen, usar variables de entorno
            env_api_key = os.getenv(f"{self.exchange_name.upper()}_API_KEY") or os.getenv('BINANCE_API_KEY') or os.getenv('BYBIT_API_KEY')
            env_api_secret = os.getenv(f"{self.exchange_name.upper()}_API_SECRET") or os.getenv('BINANCE_API_SECRET') or os.getenv('BYBIT_API_SECRET')
            api_key = exchange_config.get('api_key') or env_api_key or ''
            api_secret = exchange_config.get('api_secret') or env_api_secret or ''
            
            # Logging para debug
            self.logger.info(f"Exchange {self.exchange_name} - API key desde config: {'***' if exchange_config.get('api_key') else 'VACÍA'}")
            self.logger.info(f"Exchange {self.exchange_name} - API key desde env: {'***' if env_api_key else 'VACÍA'}")
            self.logger.info(f"Exchange {self.exchange_name} - Usando API key: {'***' if api_key else 'VACÍA'}")
            
            if not exchange_config.get('enabled', False):
                self.logger.warning(f"Exchange {self.exchange_name} no está habilitado en configuración")
                return False

            # Configurar exchange síncrono
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': exchange_config.get('sandbox', False),
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
                'sandbox': exchange_config.get('sandbox', False),
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
        Establece conexión con el exchange CCXT.

        Returns:
            bool: True si la conexión se estableció correctamente
        """
        if self._initialize_exchange():
            try:
                # Verificar conexión cargando mercados
                markets = self.exchange.load_markets()
                self.logger.info(f"Conectado a {self.exchange_name} - {len(markets)} mercados disponibles")

                self.connected = True
                self.logger.info("CCXTOrderExecutor conectado correctamente")
                return True

            except Exception as e:
                self.logger.error(f"Error conectando a {self.exchange_name}: {e}")
                return False

        return False

    def disconnect(self) -> bool:
        """
        Desconecta del exchange CCXT.

        Returns:
            bool: True si la desconexión fue exitosa
        """
        try:
            if self.async_exchange:
                import asyncio
                asyncio.run(self.async_exchange.close())
            self.connected = False
            self.logger.info("CCXTOrderExecutor desconectado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error desconectando CCXTOrderExecutor: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Verifica si está conectado al exchange.

        Returns:
            bool: True si está conectado
        """
        return self.connected and self.exchange is not None

    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Obtiene el precio actual para un símbolo.

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

    def apply_risk_management(self, symbol: str, order_type: OrderType, entry_price: float,
                            stop_loss: float = None, take_profit: float = None, risk_per_trade: float = None,
                            portfolio_value: float = None) -> Dict[str, Any]:
        """
        Aplica gestión de riesgo a la orden usando parámetros proporcionados por la estrategia.

        Args:
            symbol: Símbolo del par
            order_type: Tipo de orden (BUY/SELL)
            entry_price: Precio de entrada
            stop_loss: Stop loss opcional (proporcionado por estrategia)
            take_profit: Take profit opcional (proporcionado por estrategia)
            risk_per_trade: Porcentaje de riesgo por trade (proporcionado por estrategia)
            portfolio_value: Valor total del portfolio para cálculo consistente con backtest

        Returns:
            Dict con parámetros de riesgo aplicados
        """
        try:
            # Usar risk_per_trade proporcionado por estrategia o valor por defecto
            risk_pct = risk_per_trade if risk_per_trade is not None else self.risk_per_trade

            # Determinar qué moneda necesitamos según el tipo de orden
            base_currency, quote_currency = symbol.split('/')
            if order_type == OrderType.BUY:
                # Para BUY necesitamos la moneda de cotización (ej: USDT en BTC/USDT)
                required_currency = quote_currency
            else:  # SELL
                # Para SELL necesitamos la moneda base (ej: BTC en BTC/USDT)
                required_currency = base_currency

            # Obtener balance disponible de la moneda requerida
            balance_info = self.exchange.fetch_balance()
            available_balance = balance_info.get('free', {}).get(required_currency, 0)

            if available_balance <= 0:
                raise ValueError(f"Saldo insuficiente en {required_currency}: {available_balance}")

            # Usar portfolio_value si se proporciona, sino estimar basado en balance disponible
            # Esto mantiene consistencia con el backtest donde portfolio_value es fijo
            if portfolio_value is None:
                # Estimar capital total basado en balance disponible + margen de seguridad
                # Para crypto, asumimos que el balance disponible representa ~80% del capital total
                portfolio_value = available_balance / 0.8 if order_type == OrderType.SELL else available_balance

            # Calcular stop loss si no se proporciona
            if stop_loss is None:
                if order_type == OrderType.BUY:
                    stop_loss = entry_price * 0.98  # 2% stop loss por defecto
                else:
                    stop_loss = entry_price * 1.02  # 2% stop loss por defecto

            # Calcular take profit si no se proporciona
            if take_profit is None:
                risk_distance = abs(entry_price - stop_loss)
                if order_type == OrderType.BUY:
                    take_profit = entry_price + (risk_distance * 2)  # Risk:Reward 1:2
                else:
                    take_profit = entry_price - (risk_distance * 2)

            # Calcular cantidad basada en riesgo usando el porcentaje proporcionado
            # CONSISTENTE CON BACKTEST: risk_amount = portfolio_value * risk_pct
            if order_type == OrderType.BUY:
                risk_distance = entry_price - stop_loss
            else:
                risk_distance = stop_loss - entry_price

            if risk_distance <= 0:
                raise ValueError("Stop loss inválido")

            # CÁLCULO CONSISTENTE CON BACKTEST
            risk_amount = portfolio_value * risk_pct
            position_size = risk_amount / risk_distance

            # Para BUY: position_size ya está en unidades base (BTC)
            # Para SELL: position_size ya está en unidades base (BTC)
            # Pero necesitamos verificar que no exceda el balance disponible
            if order_type == OrderType.SELL and position_size > available_balance:
                # Reducir position_size para que no exceda el balance disponible
                position_size = available_balance * 0.95  # 95% del balance disponible
            elif order_type == OrderType.BUY:
                # Para BUY, verificar que el costo no exceda el balance disponible
                estimated_cost = position_size * entry_price
                if estimated_cost > available_balance:
                    position_size = (available_balance * 0.95) / entry_price  # 95% del balance disponible

            # Ajustar a la precisión del mercado
            try:
                market_info = self.exchange.market(symbol)
                precision = market_info.get('precision', {}).get('amount')
                if precision is not None:
                    # Si precision es numérico (decimales), usarlo directamente
                    if isinstance(precision, (int, float)):
                        if precision >= 1:
                            # Precision entera (decimales)
                            position_size = round(position_size, int(precision))
                        else:
                            # Precision como step size (ej: 0.001)
                            position_size = round(position_size / precision) * precision
                    else:
                        # Fallback si precision tiene formato inesperado
                        position_size = float(f"{position_size:.8f}")

                # Verificar límites de cantidad mínima
                min_amount = market_info.get('limits', {}).get('amount', {}).get('min')
                if min_amount and position_size < min_amount:
                    self.logger.warning(f"Cantidad calculada {position_size} menor que el mínimo {min_amount}")
                    position_size = min_amount
            except Exception as e:
                self.logger.warning(f"Error ajustando precisión: {e}")

            return {
                'quantity': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_amount': risk_amount,
                'risk_percent': risk_pct,
                'required_currency': required_currency,
                'available_balance': available_balance,
                'portfolio_value': portfolio_value
            }

        except Exception as e:
            self.logger.error(f"Error aplicando gestión de riesgo: {e}")
            return {}

    def open_position(self, symbol: str, order_type: OrderType, quantity: float = None,
                     stop_loss_price: float = None, take_profit_price: float = None,
                     trailing_stop_pct: float = None, risk_per_trade: float = None,
                     price: float = None, portfolio_value: float = None) -> Optional[Dict[str, Any]]:
        """
        Abre una nueva posición usando parámetros de risk management proporcionados por la estrategia.

        Args:
            symbol: Símbolo del par
            order_type: Tipo de orden (BUY/SELL)
            quantity: Cantidad a operar (opcional, se calcula por riesgo si no se proporciona)
            stop_loss_price: Precio exacto de stop loss (proporcionado por estrategia)
            take_profit_price: Precio exacto de take profit (proporcionado por estrategia)
            trailing_stop_pct: Porcentaje para trailing stop (proporcionado por estrategia)
            risk_per_trade: Porcentaje de riesgo por trade (proporcionado por estrategia)
            price: Precio límite (para órdenes limit)
            portfolio_value: Valor total del portfolio para cálculo consistente con backtest

        Returns:
            Dict con información de la orden o None si hay error
        """
        if not self.is_connected():
            self.logger.error("No conectado al exchange")
            return None

        try:
            # Obtener precio actual si no se proporciona
            if price is None:
                current_price = self.get_current_price(symbol)
                if not current_price:
                    return None
                price = current_price['ask'] if order_type == OrderType.BUY else current_price['bid']

            # Si no se proporciona quantity, calcular basado en riesgo
            if quantity is None:
                if risk_per_trade is None:
                    risk_per_trade = self.risk_per_trade  # Usar valor por defecto

                # Usar portfolio_value proporcionado por el orquestador, o calcular si no se proporciona
                if portfolio_value is None:
                    # Calcular portfolio_value para consistencia con backtest
                    # Obtener balance total de la cuenta (estimación del portfolio)
                    try:
                        balance_info = self.exchange.fetch_balance()
                        # Para crypto, el portfolio_value es el balance en USDT + valor de otras criptos
                        # Como aproximación, usamos el balance de la moneda de cotización (USDT)
                        quote_currency = symbol.split('/')[1]  # USDT para BTC/USDT
                        portfolio_value = balance_info.get('free', {}).get(quote_currency, 0)

                        # Si no hay suficiente balance en quote currency, usar una estimación conservadora
                        if portfolio_value < 100:  # Umbral mínimo
                            portfolio_value = 2500  # Valor por defecto similar al backtest
                            self.logger.warning(f"Balance insuficiente en {quote_currency}, usando valor por defecto: {portfolio_value}")
                    except Exception as e:
                        self.logger.warning(f"Error obteniendo balance para portfolio_value: {e}, usando valor por defecto")
                        portfolio_value = 2500  # Fallback al valor del backtest

                risk_params = self.apply_risk_management(symbol, order_type, price,
                                                       stop_loss_price, take_profit_price, risk_per_trade, portfolio_value)
                if not risk_params:
                    return None
                quantity = risk_params['quantity']
                # Usar stop_loss y take_profit proporcionados por estrategia, o calculados
                if stop_loss_price is None:
                    stop_loss_price = risk_params['stop_loss']
                if take_profit_price is None:
                    take_profit_price = risk_params['take_profit']

            # Verificar límites de posición
            if len(self.open_positions) >= self.max_positions:
                self.logger.warning(f"Límite de posiciones alcanzado ({self.max_positions})")
                return None

            # Crear orden
            
            # Verificar balance disponible antes de crear la orden
            try:
                # Determinar qué moneda necesitamos según el tipo de orden
                if order_type == OrderType.BUY:
                    # Para BUY necesitamos la moneda de cotización (USDT)
                    currency = symbol.split('/')[1]  # USDT para BTC/USDT
                    balance_info = self.exchange.fetch_balance()
                    available_balance = balance_info.get('free', {}).get(currency, 0)
                    
                    # Calcular costo aproximado de la orden (quantity * price)
                    estimated_cost = quantity * price
                    estimated_cost_with_fees = estimated_cost * 1.01
                    
                    if available_balance < estimated_cost_with_fees:
                        self.logger.error(f"Saldo insuficiente: {available_balance} {currency}, necesario ~{estimated_cost_with_fees} {currency}")
                        self.logger.warning("Reduciendo cantidad para ajustar al saldo disponible")
                        
                        # Reducir la cantidad al 90% del saldo disponible para dejar margen
                        safe_quantity = (available_balance * 0.9) / price
                        
                        # Validar con los límites del mercado
                        market_info = self.exchange.market(symbol)
                        min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0)
                        
                        if safe_quantity < min_amount:
                            self.logger.error(f"No hay saldo suficiente para una orden mínima: {safe_quantity} < {min_amount}")
                            return None
                        
                        quantity = safe_quantity
                        self.logger.info(f"Cantidad ajustada a {quantity} para operar con el saldo disponible")
                
                else:  # SELL
                    # Para SELL necesitamos la moneda base (BTC)
                    currency = symbol.split('/')[0]  # BTC para BTC/USDT
                    balance_info = self.exchange.fetch_balance()
                    available_balance = balance_info.get('free', {}).get(currency, 0)
                    
                    # Para SELL, la cantidad es directamente en la moneda base
                    if available_balance < quantity:
                        self.logger.error(f"Saldo insuficiente: {available_balance} {currency}, necesario {quantity} {currency}")
                        self.logger.warning("Reduciendo cantidad para ajustar al saldo disponible")
                        
                        # Validar con los límites del mercado
                        market_info = self.exchange.market(symbol)
                        min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0)
                        
                        safe_quantity = available_balance * 0.9  # 90% del saldo disponible
                        
                        if safe_quantity < min_amount:
                            self.logger.error(f"No hay saldo suficiente para una orden mínima: {safe_quantity} < {min_amount}")
                            return None
                        
                        quantity = safe_quantity
                        self.logger.info(f"Cantidad ajustada a {quantity} para operar con el saldo disponible")
                        
            except Exception as e:
                self.logger.warning(f"Error verificando balance: {e}")
            
            # Determinar el tipo de orden correcto para CCXT
            ccxt_order_type = 'market'  # Por defecto usar órdenes de mercado
            if price is not None and order_type in [OrderType.LIMIT_BUY, OrderType.LIMIT_SELL]:
                ccxt_order_type = 'limit'
            
            # Determinar el lado de la orden
            ccxt_side = 'buy' if order_type in [OrderType.BUY, OrderType.LIMIT_BUY, OrderType.STOP_BUY] else 'sell'
            
            order_params = {
                'symbol': symbol,
                'type': ccxt_order_type,  # 'market' o 'limit'
                'side': ccxt_side,        # 'buy' o 'sell'
                'amount': quantity
            }

            if price is not None:
                order_params['price'] = price

            # Ejecutar orden
            order = self.exchange.create_order(**order_params)

            # ✅ VERIFICAR EJECUCIÓN REAL EN BINANCE TESTNET
            order_verification = self.verify_order_execution(order['id'], symbol)

            if order_verification['execution_status'] not in ['filled', 'pending']:
                self.logger.error(f"Orden {order['id']} no se ejecutó correctamente: {order_verification}")
                # Intentar cancelar la orden si está pendiente
                try:
                    self.exchange.cancel_order(order['id'], symbol)
                    self.logger.info(f"Orden {order['id']} cancelada por verificación fallida")
                except Exception as cancel_error:
                    self.logger.warning(f"No se pudo cancelar orden {order['id']}: {cancel_error}")
                return None

            # Crear registro de posición con información completa de risk management
            position_info = {
                'ticket': str(order['id']),  # ✅ USAR ID REAL DE BINANCE
                'order_id': order['id'],
                'symbol': symbol,
                'type': order_type.value,
                'quantity': quantity,
                'size': quantity,  # Alias para compatibilidad
                'entry_price': order.get('price', price) or order_verification.get('price', price),
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'trailing_stop_pct': trailing_stop_pct,
                'risk_per_trade': risk_per_trade or self.risk_per_trade,
                'open_time': datetime.now(),
                'status': 'open',
                'verified_execution': True,  # ✅ CONFIRMA EJECUCIÓN REAL
                'execution_details': order_verification
            }

            self.open_positions[position_info['ticket']] = position_info
            self.logger.info(f"✅ Posición REAL abierta en testnet - Ticket: {order['id']} - "
                           f"Verificada: {order_verification['execution_status']} - "
                           f"Filled: {order_verification.get('filled', 0)}/{order_verification.get('amount', 0)}")

            return position_info

        except Exception as e:
            self.logger.error(f"Error abriendo posición: {e}")
            return None

    def close_position(self, ticket: str, quantity: float = None) -> bool:
        """
        Cierra una posición abierta.

        Args:
            ticket: ID de la posición
            quantity: Cantidad a cerrar (opcional, cierra toda la posición)

        Returns:
            bool: True si se cerró correctamente
        """
        if ticket not in self.open_positions:
            self.logger.error(f"Posición {ticket} no encontrada")
            return False

        position = self.open_positions[ticket]

        try:
            # Determinar tipo de orden de cierre
            close_side = 'sell' if position['type'] == 'buy' else 'buy'
            close_quantity = quantity or position['quantity']

            # Crear orden de cierre
            order = self.exchange.create_order(
                symbol=position['symbol'],
                type='market',
                side=close_side,
                amount=close_quantity
            )

            # Actualizar posición
            position['close_price'] = order.get('price', 0)
            position['close_time'] = datetime.now()
            position['status'] = 'closed'
            position['pnl'] = self._calculate_pnl(position)

            # Mover a historial
            self.position_history.append(position)
            del self.open_positions[ticket]

            self.logger.info(f"Posición cerrada: {ticket} - PnL: {position['pnl']}")
            return True

        except Exception as e:
            self.logger.error(f"Error cerrando posición {ticket}: {e}")
            return False

    def _calculate_pnl(self, position: Dict) -> float:
        """
        Calcula el PnL de una posición cerrada.

        Args:
            position: Información de la posición

        Returns:
            float: Profit/Loss
        """
        try:
            entry_price = position['entry_price']
            close_price = position.get('close_price', 0)
            quantity = position['quantity']

            if position['type'] == 'buy':
                return (close_price - entry_price) * quantity
            else:
                return (entry_price - close_price) * quantity

        except Exception as e:
            self.logger.error(f"Error calculando PnL: {e}")
            return 0.0

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Obtiene posiciones REALES abiertas desde Binance testnet.

        Returns:
            List: Lista de posiciones abiertas reales en el exchange
        """
        if not self.is_connected():
            self.logger.warning("Exchange no conectado, usando posiciones locales")
            return list(self.open_positions.values())

        try:
            positions = []

            # Obtener órdenes abiertas reales desde el exchange
            # Especificar símbolos para evitar límites de rate estrictos
            symbols_to_check = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Símbolos comunes

            for symbol in symbols_to_check:
                try:
                    open_orders = self.exchange.fetch_open_orders(symbol)
                    for order in open_orders:
                        if order['status'] in ['open', 'partially_filled']:
                            # Convertir orden a formato de posición
                            position = {
                                'ticket': str(order['id']),  # ID real de Binance
                                'symbol': order['symbol'],
                                'type': order['side'],  # 'buy' o 'sell'
                                'quantity': float(order['amount']),
                                'entry_price': float(order['price']) if order['price'] else 0.0,
                                'status': 'open',
                                'timestamp': order.get('timestamp', 0),
                                'filled': float(order.get('filled', 0)),
                                'remaining': float(order.get('remaining', order['amount'])),
                                'source': 'exchange'  # Indica que viene del exchange real
                            }
                            positions.append(position)
                except Exception as e:
                    self.logger.debug(f"Error obteniendo órdenes para {symbol}: {e}")
                    continue

            # Para futuros/perpetual swaps si están disponibles
            try:
                futures_positions = self.exchange.fetch_positions()
                for pos in futures_positions:
                    if abs(float(pos.get('contracts', 0))) > 0:
                        position = {
                            'ticket': f"futures_{pos['symbol'].replace('/', '_')}",
                            'symbol': pos['symbol'],
                            'type': 'long' if float(pos.get('contracts', 0)) > 0 else 'short',
                            'quantity': abs(float(pos.get('contracts', 0))),
                            'entry_price': float(pos.get('entryPrice', 0)),
                            'status': 'open',
                            'pnl': float(pos.get('unrealizedPnl', 0)),
                            'source': 'futures'
                        }
                        positions.append(position)
            except Exception as e:
                # Futures no disponible o error, continuar
                self.logger.debug(f"Futures positions no disponibles: {e}")

            self.logger.info(f"Obtenidas {len(positions)} posiciones reales desde testnet")
            return positions

        except Exception as e:
            self.logger.error(f"Error obteniendo posiciones reales desde exchange: {e}")
            self.logger.warning("Usando posiciones locales como fallback")
            # Fallback: devolver posiciones locales pero marcar como simuladas
            local_positions = list(self.open_positions.values())
            for pos in local_positions:
                pos['source'] = 'local_fallback'
            return local_positions

    def verify_order_execution(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Verifica el estado real de una orden en Binance testnet.

        Args:
            order_id: ID de la orden a verificar
            symbol: Símbolo del par de trading (ej: 'BTC/USDT')

        Returns:
            Dict con información del estado de la orden
        """
        if not self.is_connected():
            return {'status': 'unknown', 'error': 'exchange_not_connected'}

        try:
            order = self.exchange.fetch_order(order_id, symbol)

            result = {
                'order_id': order_id,
                'status': order.get('status', 'unknown'),
                'symbol': order.get('symbol', ''),
                'side': order.get('side', ''),
                'amount': float(order.get('amount', 0)),
                'filled': float(order.get('filled', 0)),
                'remaining': float(order.get('remaining', 0)),
                'price': float(order.get('price', 0)) if order.get('price') else None,
                'cost': float(order.get('cost', 0)) if order.get('cost') else None,
                'fee': order.get('fee', {}),
                'timestamp': order.get('timestamp', 0),
                'verified_at': datetime.now().isoformat()
            }

            # Determinar si la orden se ejecutó completamente
            if result['status'] == 'closed' and result['filled'] > 0:
                result['execution_status'] = 'filled'
            elif result['status'] == 'open':
                result['execution_status'] = 'pending'
            elif result['status'] == 'canceled':
                result['execution_status'] = 'cancelled'
            else:
                result['execution_status'] = 'unknown'

            self.logger.info(f"Orden {order_id} verificada: {result['execution_status']} - "
                           f"Filled: {result['filled']}/{result['amount']}")

            return result

        except Exception as e:
            self.logger.error(f"Error verificando orden {order_id}: {e}")
            return {
                'order_id': order_id,
                'status': 'error',
                'error': str(e),
                'verified_at': datetime.now().isoformat()
            }

    def get_account_balance(self) -> Optional[Dict]:
        """
        Obtiene el balance de la cuenta.

        Returns:
            Dict con balances o None si hay error
        """
        if not self.is_connected():
            return None

        try:
            balance = self.exchange.fetch_balance()
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {})
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo balance: {e}")
            return None