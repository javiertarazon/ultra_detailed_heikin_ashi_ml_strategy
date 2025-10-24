#!/usr/bin/env python3
"""
Live Trading Data Reader - Lee datos reales de operaciones ejecutadas en Binance.

Este módulo se conecta directamente a Binance (tanto testnet como cuenta real)
y lee el historial de operaciones ejecutadas para calcular métricas en tiempo real.

Author: GitHub Copilot
Date: Octubre 2025
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import os
import ccxt
from utils.logger import setup_logger

logger = setup_logger('LiveTradingDataReader')

class LiveTradingDataReader:
    """
    Lee datos reales de operaciones ejecutadas en Binance para métricas en tiempo real.
    """

    def __init__(self, config_path: str = None, exchange_name: str = 'binance', testnet: bool = True):
        """
        Inicializa el lector de datos de live trading.

        Args:
            config_path: Ruta al archivo de configuración
            exchange_name: Nombre del exchange (binance, bybit, etc.)
            testnet: True para testnet, False para cuenta real
        """
        self.exchange_name = exchange_name
        self.testnet = testnet

        # Cargar configuración
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = Path(__file__).parent.parent / "config" / "config.yaml"

        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            self.config = {}

        # Configuración del exchange
        self.exchange_config = self.config.get('exchanges', {}).get(exchange_name, {})

        # Credenciales
        self.api_key = os.getenv('BINANCE_API_KEY') or self.exchange_config.get('api_key')
        self.api_secret = os.getenv('BINANCE_API_SECRET') or self.exchange_config.get('api_secret')

        if not self.api_key or not self.api_secret:
            logger.error("Credenciales de Binance no encontradas")
            self.exchange = None
            return

        # Inicializar exchange
        try:
            if exchange_name.lower() == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',  # o 'future' para futuros
                    }
                })

                # Configurar testnet si es necesario
                if testnet:
                    self.exchange.urls['api'] = self.exchange.urls['test']

            logger.info(f"Exchange {exchange_name} inicializado {'(TESTNET)' if testnet else '(REAL)'}")

        except Exception as e:
            logger.error(f"Error inicializando exchange: {e}")
            self.exchange = None

    def fetch_recent_trades(self, symbol: str = 'BTC/USDT', days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene trades recientes ejecutados en Binance.

        Args:
            symbol: Símbolo a consultar (ej: 'BTC/USDT')
            days_back: Días hacia atrás para buscar trades

        Returns:
            Lista de trades ejecutados
        """
        if not self.exchange:
            logger.error("Exchange no inicializado")
            return []

        try:
            # Calcular timestamp desde cuando buscar
            since = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

            # Obtener historial de trades
            trades = self.exchange.fetch_my_trades(symbol, since=since)

            logger.info(f"Obtenidos {len(trades)} trades para {symbol} en los últimos {days_back} días")

            # Convertir a formato estandarizado
            standardized_trades = []
            for trade in trades:
                standardized_trade = {
                    'id': trade.get('id'),
                    'order_id': trade.get('order'),
                    'timestamp': datetime.fromtimestamp(trade['timestamp'] / 1000),
                    'symbol': trade['symbol'],
                    'side': trade['side'],  # 'buy' o 'sell'
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'cost': trade['cost'],
                    'fee': trade.get('fee', {}),
                    'taker_or_maker': trade.get('takerOrMaker'),
                    'type': trade.get('type', 'limit'),
                    'datetime': trade['datetime']
                }
                standardized_trades.append(standardized_trade)

            return standardized_trades

        except Exception as e:
            logger.error(f"Error obteniendo trades: {e}")
            return []

    def fetch_recent_orders(self, symbol: str = 'BTC/USDT', days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene órdenes recientes ejecutadas en Binance.

        Args:
            symbol: Símbolo a consultar
            days_back: Días hacia atrás para buscar

        Returns:
            Lista de órdenes ejecutadas
        """
        if not self.exchange:
            logger.error("Exchange no inicializado")
            return []

        try:
            # Calcular timestamp
            since = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

            # Obtener historial de órdenes
            orders = self.exchange.fetch_closed_orders(symbol, since=since)

            logger.info(f"Obtenidas {len(orders)} órdenes cerradas para {symbol}")

            # Filtrar solo órdenes filled
            filled_orders = [order for order in orders if order['status'] == 'closed' and order['filled'] > 0]

            # Convertir a formato estandarizado
            standardized_orders = []
            for order in filled_orders:
                standardized_order = {
                    'id': order.get('id'),
                    'client_order_id': order.get('clientOrderId'),
                    'timestamp': datetime.fromtimestamp(order['timestamp'] / 1000),
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'filled': order['filled'],
                    'remaining': order['remaining'],
                    'price': order['price'],
                    'cost': order.get('cost', 0),
                    'fee': order.get('fee', {}),
                    'status': order['status'],
                    'datetime': order['datetime']
                }
                standardized_orders.append(standardized_order)

            return standardized_orders

        except Exception as e:
            logger.error(f"Error obteniendo órdenes: {e}")
            return []

    def calculate_live_metrics_from_binance(self, symbol: str = 'BTC/USDT', days_back: int = 30) -> Dict[str, Any]:
        """
        Calcula métricas de live trading directamente desde datos de Binance.

        Args:
            symbol: Símbolo a analizar
            days_back: Días hacia atrás para analizar

        Returns:
            Diccionario con métricas calculadas desde datos reales de Binance
        """
        try:
            # Obtener trades y órdenes
            trades = self.fetch_recent_trades(symbol, days_back)
            orders = self.fetch_recent_orders(symbol, days_back)

            if not trades and not orders:
                logger.warning("No se encontraron trades u órdenes en Binance")
                return self._get_empty_metrics()

            # Combinar y procesar datos
            all_operations = self._combine_trades_and_orders(trades, orders)

            if not all_operations:
                return self._get_empty_metrics()

            # Calcular métricas
            metrics = self._calculate_metrics_from_operations(all_operations)

            logger.info(f"Métricas calculadas desde {len(all_operations)} operaciones reales en Binance")

            return metrics

        except Exception as e:
            logger.error(f"Error calculando métricas desde Binance: {e}")
            return self._get_empty_metrics()

    def _combine_trades_and_orders(self, trades: List[Dict], orders: List[Dict]) -> List[Dict]:
        """
        Combina trades y órdenes en operaciones completas.
        """
        operations = []

        # Procesar órdenes (más completas)
        for order in orders:
            if order['filled'] > 0:
                operation = {
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'entry_price': order['price'],
                    'quantity': order['filled'],
                    'cost': order['cost'],
                    'timestamp': order['timestamp'],
                    'type': 'order',
                    'order_id': order['id']
                }
                operations.append(operation)

        # Agregar trades adicionales si no están en órdenes
        order_ids = {op['order_id'] for op in operations}
        for trade in trades:
            if trade['order_id'] not in order_ids:
                operation = {
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'entry_price': trade['price'],
                    'quantity': trade['amount'],
                    'cost': trade['cost'],
                    'timestamp': trade['timestamp'],
                    'type': 'trade',
                    'order_id': trade['order_id']
                }
                operations.append(operation)

        # Ordenar por timestamp
        operations.sort(key=lambda x: x['timestamp'])

        return operations

    def _calculate_metrics_from_operations(self, operations: List[Dict]) -> Dict[str, Any]:
        """
        Calcula métricas desde operaciones ejecutadas.
        """
        if not operations:
            return self._get_empty_metrics()

        # Calcular P&L básico (simplificado - en realidad necesitaríamos emparejar buy/sell)
        total_trades = len(operations)
        total_volume = sum(op['cost'] for op in operations)

        # Para métricas más avanzadas necesitaríamos lógica de matching buy/sell
        # Por ahora, calculamos métricas básicas

        metrics = {
            'total_trades': total_trades,
            'total_volume': total_volume,
            'start_time': operations[0]['timestamp'].isoformat() if operations else datetime.now().isoformat(),
            'end_time': operations[-1]['timestamp'].isoformat() if operations else datetime.now().isoformat(),
            'symbols_traded': list(set(op['symbol'] for op in operations)),
            'data_source': 'BINANCE_DIRECT',
            'is_live_data': True,
            'last_update': datetime.now().isoformat(),

            # Métricas que requieren matching buy/sell (placeholder por ahora)
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'expectancy': 0.0,
            'sharpe_ratio': 0.0,
            'current_balance': 0.0,  # Necesitaría balance actual
            'initial_balance': 0.0
        }

        return metrics

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas vacías cuando no hay datos.
        """
        return {
            'total_trades': 0,
            'total_volume': 0.0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'expectancy': 0.0,
            'sharpe_ratio': 0.0,
            'current_balance': 0.0,
            'initial_balance': 0.0,
            'start_time': datetime.now().isoformat(),
            'end_time': datetime.now().isoformat(),
            'symbols_traded': [],
            'data_source': 'BINANCE_DIRECT',
            'is_live_data': True,
            'last_update': datetime.now().isoformat()
        }

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Obtiene el balance actual de la cuenta de Binance.

        Returns:
            Diccionario con información de balance
        """
        if not self.exchange:
            return {}

        try:
            balance = self.exchange.fetch_balance()

            # Extraer balances relevantes
            account_balance = {
                'total_usdt': balance.get('total', {}).get('USDT', 0),
                'free_usdt': balance.get('free', {}).get('USDT', 0),
                'used_usdt': balance.get('used', {}).get('USDT', 0),
                'total_btc': balance.get('total', {}).get('BTC', 0),
                'free_btc': balance.get('free', {}).get('BTC', 0),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Balance obtenido: {account_balance['free_usdt']:.2f} USDT disponible")

            return account_balance

        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {}

    def test_connection(self) -> bool:
        """
        Prueba la conexión con Binance.

        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        if not self.exchange:
            return False

        try:
            # Intentar obtener balance (operación simple)
            balance = self.exchange.fetch_balance()
            logger.info("✅ Conexión con Binance exitosa")
            return True

        except Exception as e:
            logger.error(f"❌ Error de conexión con Binance: {e}")
            return False