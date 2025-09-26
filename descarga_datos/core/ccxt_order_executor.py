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
import logging
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
            exchange_config = self.config.get(self.exchange_name, {})
            if not exchange_config.get('enabled', False):
                self.logger.warning(f"Exchange {self.exchange_name} no está habilitado en configuración")
                return False

            # Configurar exchange síncrono
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'apiKey': exchange_config.get('api_key', ''),
                'secret': exchange_config.get('api_secret', ''),
                'sandbox': exchange_config.get('sandbox', False),
                'timeout': exchange_config.get('timeout', 30000),
                'enableRateLimit': True,
            })

            # Configurar exchange asíncrono
            async_exchange_class = getattr(ccxt_async, self.exchange_name)
            self.async_exchange = async_exchange_class({
                'apiKey': exchange_config.get('api_key', ''),
                'secret': exchange_config.get('api_secret', ''),
                'sandbox': exchange_config.get('sandbox', False),
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
                            stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """
        Aplica gestión de riesgo a la orden.

        Args:
            symbol: Símbolo del par
            order_type: Tipo de orden (BUY/SELL)
            entry_price: Precio de entrada
            stop_loss: Stop loss opcional
            take_profit: Take profit opcional

        Returns:
            Dict con parámetros de riesgo aplicados
        """
        try:
            # Obtener balance actual
            balance_info = self.exchange.fetch_balance()
            total_balance = balance_info.get('total', {}).get('USDT', 0)

            if total_balance <= 0:
                raise ValueError("Balance insuficiente")

            # Calcular tamaño de posición basado en riesgo
            risk_amount = total_balance * self.risk_per_trade

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

            # Calcular cantidad basada en riesgo
            if order_type == OrderType.BUY:
                risk_distance = entry_price - stop_loss
            else:
                risk_distance = stop_loss - entry_price

            if risk_distance <= 0:
                raise ValueError("Stop loss inválido")

            quantity = risk_amount / risk_distance

            return {
                'quantity': quantity,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_amount': risk_amount,
                'risk_percent': self.risk_per_trade
            }

        except Exception as e:
            self.logger.error(f"Error aplicando gestión de riesgo: {e}")
            return {}

    def open_position(self, symbol: str, order_type: OrderType, quantity: float = None,
                     stop_loss: float = None, take_profit: float = None,
                     price: float = None) -> Optional[Dict[str, Any]]:
        """
        Abre una nueva posición.

        Args:
            symbol: Símbolo del par
            order_type: Tipo de orden (BUY/SELL)
            quantity: Cantidad a operar (opcional, se calcula por riesgo)
            stop_loss: Precio de stop loss
            take_profit: Precio de take profit
            price: Precio límite (para órdenes limit)

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

            # Aplicar gestión de riesgo si no se proporciona cantidad
            if quantity is None:
                risk_params = self.apply_risk_management(symbol, order_type, price, stop_loss, take_profit)
                if not risk_params:
                    return None
                quantity = risk_params['quantity']
                stop_loss = risk_params['stop_loss']
                take_profit = risk_params['take_profit']

            # Verificar límites de posición
            if len(self.open_positions) >= self.max_positions:
                self.logger.warning(f"Límite de posiciones alcanzado ({self.max_positions})")
                return None

            # Crear orden
            order_params = {
                'symbol': symbol,
                'type': 'market' if price is None else 'limit',
                'side': order_type.value,
                'amount': quantity,
            }

            if price is not None:
                order_params['price'] = price

            # Ejecutar orden
            order = self.exchange.create_order(**order_params)

            # Crear registro de posición
            position_info = {
                'ticket': str(uuid.uuid4()),
                'order_id': order['id'],
                'symbol': symbol,
                'type': order_type.value,
                'quantity': quantity,
                'entry_price': order.get('price', price),
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'open_time': datetime.now(),
                'status': 'open'
            }

            self.open_positions[position_info['ticket']] = position_info
            self.logger.info(f"Posición abierta: {position_info}")

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
        Obtiene todas las posiciones abiertas.

        Returns:
            List: Lista de posiciones abiertas
        """
        return list(self.open_positions.values())

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