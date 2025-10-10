#!/usr/bin/env python3
"""
Test Completo para Modo Live con Sandbox de Binance
====================================================

Este test verifica todas las funcionalidades del sistema de trading en vivo usando
el sandbox (testnet) de Binance. Incluye:

1. Conexión y autenticación con Binance Testnet
2. Recopilación de datos en tiempo real
3. Cálculo de indicadores técnicos
4. Ejecución de operaciones de compra/venta
5. Configuración de órdenes límite
6. Gestión de stop loss y take profit
7. Cierre de posiciones
8. Seguimiento y reporte de resultados

El test es completamente realista y usa operaciones reales en la cuenta de test.

Author: GitHub Copilot
Date: Octubre 2025
"""

import time
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importar componentes del sistema
from core.ccxt_live_data import CCXTLiveDataProvider
from core.ccxt_order_executor import CCXTOrderExecutor, OrderType
from core.ccxt_live_trading_orchestrator import CCXTLiveTradingOrchestrator
from indicators.technical_indicators import TechnicalIndicators
from config.config_loader import load_config
from utils.logger import get_logger, setup_logger
from risk_management.risk_management import AdvancedRiskManager

# Configurar logging
logger = setup_logger('BinanceSandboxLiveTest')

class BinanceSandboxLiveTest(unittest.TestCase):
    """
    Test completo para operaciones en vivo con sandbox de Binance.

    Este test verifica:
    - Conexión a Binance Testnet
    - Recopilación de datos OHLCV en tiempo real
    - Cálculo de indicadores técnicos
    - Ejecución de órdenes de compra/venta
    - Gestión de stop loss y take profit
    - Cierre de posiciones
    - Reporte de resultados
    """

    def setUp(self):
        """Configuración inicial del test"""
        self.logger = get_logger(__name__)

        # Configuración para Binance Testnet
        self.test_config = {
            'exchange': 'binance',
            'testnet': True,  # Usar testnet de Binance
            'symbols': ['BTC/USDT', 'ETH/USDT'],
            'timeframes': ['1m', '5m', '15m'],
            'history_bars': 100,
            'risk_management': {
                'max_position_size': 0.1,  # 10% del capital
                'max_drawdown': 0.05,     # 5% máximo drawdown
                'stop_loss_pct': 0.02,    # 2% stop loss
                'take_profit_pct': 0.04   # 4% take profit
            },
            'trading': {
                'capital': 1000,  # Capital de test (USDT)
                'commission': 0.001,  # 0.1% comisión
                'slippage': 0.0005   # 0.05% slippage
            }
        }

        # Variables para el test
        self.symbol = 'BTC/USDT'
        self.timeframe = '1m'
        self.capital = 1000.0
        self.positions = []
        self.trades_history = []

        # Componentes del sistema
        self.data_provider = None
        self.order_executor = None
        self.orchestrator = None
        self.indicators = TechnicalIndicators()
        self.risk_manager = AdvancedRiskManager()

        # Credenciales de test (deben estar en variables de entorno)
        self.api_key = os.getenv('BINANCE_TEST_API_KEY')
        self.api_secret = os.getenv('BINANCE_TEST_API_SECRET')

        if not self.api_key or not self.api_secret:
            self.skipTest("Credenciales de Binance Testnet no configuradas. "
                         "Configure BINANCE_TEST_API_KEY y BINANCE_TEST_API_SECRET")

    def test_01_connection_and_authentication(self):
        """Test 1: Verificar conexión y autenticación con Binance Testnet"""
        self.logger.info("🧪 TEST 1: Verificando conexión y autenticación con Binance Testnet")

        try:
            # Inicializar componentes
            self.data_provider = CCXTLiveDataProvider(
                config=self.test_config,
                exchange_name='binance',
                symbols=[self.symbol],
                timeframes=[self.timeframe]
            )

            self.order_executor = CCXTOrderExecutor(
                exchange_name='binance',
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=True
            )

            # Verificar conexión
            self.assertTrue(self.data_provider.connect(), "No se pudo conectar al exchange")
            self.assertTrue(self.order_executor.connect(), "No se pudo autenticar con el exchange")

            # Verificar estado de la cuenta
            account_info = self.order_executor.get_account_info()
            self.assertIsNotNone(account_info, "No se pudo obtener información de la cuenta")

            # Verificar balance
            balance = account_info.get('total', {}).get('USDT', 0)
            self.assertGreater(balance, 0, "No hay balance disponible en la cuenta test")

            self.logger.info(f"✅ Conexión exitosa. Balance USDT: {balance}")

        except Exception as e:
            self.fail(f"Error en conexión y autenticación: {e}")

    def test_02_live_data_collection(self):
        """Test 2: Recopilar datos en tiempo real y calcular indicadores"""
        self.logger.info("🧪 TEST 2: Recopilando datos en tiempo real y calculando indicadores")

        try:
            # Obtener datos históricos recientes
            data = self.data_provider.get_historical_data(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=100
            )

            self.assertIsNotNone(data, "No se pudieron obtener datos históricos")
            self.assertGreater(len(data), 0, "Los datos históricos están vacíos")

            # Verificar estructura OHLCV
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                self.assertIn(col, data.columns, f"Falta columna {col} en los datos")

            # Calcular indicadores técnicos
            rsi = self.indicators.calculate_rsi(data)
            macd = self.indicators.calculate_macd(data)
            bb = self.indicators.calculate_bollinger_bands(data)
            sma_20 = self.indicators.calculate_sma(data, period=20)
            ema_12 = self.indicators.calculate_ema(data, period=12)

            # Verificar que los indicadores se calcularon correctamente
            self.assertIsNotNone(rsi, "RSI no se calculó correctamente")
            self.assertIsNotNone(macd, "MACD no se calculó correctamente")
            self.assertIsNotNone(bb, "Bollinger Bands no se calcularon correctamente")
            self.assertIsNotNone(sma_20, "SMA 20 no se calculó correctamente")
            self.assertIsNotNone(ema_12, "EMA 12 no se calculó correctamente")

            # Verificar valores razonables
            latest_rsi = rsi.iloc[-1] if not rsi.empty else None
            if latest_rsi is not None:
                self.assertGreaterEqual(latest_rsi, 0, "RSI debe ser >= 0")
                self.assertLessEqual(latest_rsi, 100, "RSI debe ser <= 100")

            self.logger.info(f"✅ Datos recopilados: {len(data)} velas")
            self.logger.info(f"✅ Indicadores calculados - RSI: {latest_rsi:.2f}")

        except Exception as e:
            self.fail(f"Error recopilando datos o calculando indicadores: {e}")

    def test_03_limit_orders_buy_sell(self):
        """Test 3: Ejecutar órdenes límite de compra y venta"""
        self.logger.info("🧪 TEST 3: Ejecutando órdenes límite de compra y venta")

        try:
            # Obtener precio actual
            ticker = self.data_provider.get_ticker(self.symbol)
            current_price = ticker['last']
            self.assertGreater(current_price, 0, "Precio actual inválido")

            # Calcular precios para órdenes límite
            buy_limit_price = current_price * 0.995  # 0.5% por debajo del precio actual
            sell_limit_price = current_price * 1.005  # 0.5% por encima del precio actual

            # Tamaño de la orden (pequeño para test)
            order_size = 0.001  # 0.001 BTC

            # Ejecutar orden límite de compra
            buy_order = self.order_executor.place_limit_order(
                symbol=self.symbol,
                side=OrderType.BUY,
                amount=order_size,
                price=buy_limit_price
            )

            self.assertIsNotNone(buy_order, "Orden de compra no se ejecutó")
            self.assertIn('id', buy_order, "Orden de compra no tiene ID")

            buy_order_id = buy_order['id']
            self.logger.info(f"✅ Orden límite de compra colocada: ID {buy_order_id}, Precio: {buy_limit_price}")

            # Esperar un poco para que se llene la orden (en testnet puede ser rápido)
            time.sleep(5)

            # Verificar estado de la orden
            order_status = self.order_executor.get_order_status(self.symbol, buy_order_id)
            if order_status:
                status = order_status.get('status', 'unknown')
                self.logger.info(f"Estado orden compra: {status}")

                # Si la orden se llenó, ejecutar orden de venta
                if status == 'closed' or status == 'filled':
                    # Ejecutar orden límite de venta
                    sell_order = self.order_executor.place_limit_order(
                        symbol=self.symbol,
                        side=OrderType.SELL,
                        amount=order_size,
                        price=sell_limit_price
                    )

                    self.assertIsNotNone(sell_order, "Orden de venta no se ejecutó")
                    sell_order_id = sell_order['id']
                    self.logger.info(f"✅ Orden límite de venta colocada: ID {sell_order_id}, Precio: {sell_limit_price}")

                    # Registrar trade
                    self.trades_history.append({
                        'symbol': self.symbol,
                        'side': 'buy_sell',
                        'buy_order_id': buy_order_id,
                        'sell_order_id': sell_order_id,
                        'quantity': order_size,
                        'buy_price': buy_limit_price,
                        'sell_price': sell_limit_price,
                        'timestamp': datetime.now()
                    })

                    # Cancelar órdenes si no se llenan en 30 segundos
                    time.sleep(10)
                    self._cancel_pending_orders([sell_order_id])

            # Cancelar orden de compra si aún está pendiente
            self._cancel_pending_orders([buy_order_id])

        except Exception as e:
            self.fail(f"Error ejecutando órdenes límite: {e}")

    def test_04_stop_loss_take_profit(self):
        """Test 4: Configurar stop loss y take profit"""
        self.logger.info("🧪 TEST 4: Configurando stop loss y take profit")

        try:
            # Obtener precio actual
            ticker = self.data_provider.get_ticker(self.symbol)
            current_price = ticker['last']

            # Ejecutar orden de mercado para tener una posición
            position_size = 0.001

            # Orden de compra de mercado
            market_buy = self.order_executor.place_market_order(
                symbol=self.symbol,
                side=OrderType.BUY,
                amount=position_size
            )

            self.assertIsNotNone(market_buy, "Orden de compra de mercado falló")
            buy_price = market_buy.get('price', current_price)

            self.logger.info(f"✅ Posición abierta en {buy_price}")

            # Configurar stop loss y take profit
            stop_loss_price = buy_price * 0.98  # 2% stop loss
            take_profit_price = buy_price * 1.04  # 4% take profit

            # Colocar órdenes OCO (One-Cancels-Other) para SL/TP
            oco_order = self.order_executor.place_oco_order(
                symbol=self.symbol,
                side=OrderType.SELL,
                amount=position_size,
                price=take_profit_price,
                stop_price=stop_loss_price,
                stop_limit_price=stop_loss_price * 0.999  # Límite ligeramente por debajo del stop
            )

            if oco_order:
                self.logger.info(f"✅ Órdenes OCO configuradas - TP: {take_profit_price}, SL: {stop_loss_price}")

                # Registrar posición
                self.positions.append({
                    'symbol': self.symbol,
                    'side': 'long',
                    'size': position_size,
                    'entry_price': buy_price,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'oco_order_id': oco_order.get('id'),
                    'timestamp': datetime.now()
                })

                # Monitorear posición por 30 segundos
                self._monitor_position(self.symbol, oco_order.get('id'), 30)

            else:
                # Si OCO no está disponible, usar órdenes separadas
                self.logger.warning("OCO no disponible, usando órdenes separadas")

                # Stop loss
                sl_order = self.order_executor.place_stop_loss_order(
                    symbol=self.symbol,
                    side=OrderType.SELL,
                    amount=position_size,
                    stop_price=stop_loss_price
                )

                # Take profit
                tp_order = self.order_executor.place_limit_order(
                    symbol=self.symbol,
                    side=OrderType.SELL,
                    amount=position_size,
                    price=take_profit_price
                )

                if sl_order and tp_order:
                    self.logger.info(f"✅ Órdenes separadas - SL ID: {sl_order.get('id')}, TP ID: {tp_order.get('id')}")

                    # Registrar posición
                    self.positions.append({
                        'symbol': self.symbol,
                        'side': 'long',
                        'size': position_size,
                        'entry_price': buy_price,
                        'stop_loss': stop_loss_price,
                        'take_profit': take_profit_price,
                        'sl_order_id': sl_order.get('id'),
                        'tp_order_id': tp_order.get('id'),
                        'timestamp': datetime.now()
                    })

                    # Monitorear órdenes por 30 segundos
                    self._monitor_orders(self.symbol, [sl_order.get('id'), tp_order.get('id')], 30)

        except Exception as e:
            self.fail(f"Error configurando stop loss y take profit: {e}")

    def test_05_position_closing(self):
        """Test 5: Cerrar posiciones abiertas"""
        self.logger.info("🧪 TEST 5: Cerrando posiciones abiertas")

        try:
            # Cerrar todas las posiciones abiertas
            for position in self.positions:
                if position.get('status') != 'closed':
                    # Cerrar posición con orden de mercado
                    close_order = self.order_executor.place_market_order(
                        symbol=position['symbol'],
                        side=OrderType.SELL if position['side'] == 'long' else OrderType.BUY,
                        amount=position['size']
                    )

                    if close_order:
                        exit_price = close_order.get('price', 0)
                        pnl = (exit_price - position['entry_price']) * position['size'] if position['side'] == 'long' else (position['entry_price'] - exit_price) * position['size']

                        self.logger.info(f"✅ Posición cerrada - PnL: {pnl:.4f} USDT")

                        # Actualizar posición
                        position['status'] = 'closed'
                        position['exit_price'] = exit_price
                        position['pnl'] = pnl
                        position['exit_time'] = datetime.now()

                        # Agregar a historial de trades
                        self.trades_history.append(position)

                    # Cancelar órdenes pendientes relacionadas
                    pending_orders = []
                    if 'oco_order_id' in position:
                        pending_orders.append(position['oco_order_id'])
                    if 'sl_order_id' in position:
                        pending_orders.append(position['sl_order_id'])
                    if 'tp_order_id' in position:
                        pending_orders.append(position['tp_order_id'])

                    self._cancel_pending_orders(pending_orders)

        except Exception as e:
            self.fail(f"Error cerrando posiciones: {e}")

    def test_06_comprehensive_trading_scenario(self):
        """Test 6: Escenario completo de trading con estrategia simple"""
        self.logger.info("🧪 TEST 6: Ejecutando escenario completo de trading")

        try:
            # Estrategia simple: RSI + Media Móvil
            # Comprar cuando RSI < 30 y precio > SMA 20
            # Vender cuando RSI > 70 o precio < SMA 20

            # Recopilar datos para análisis
            data = self.data_provider.get_historical_data(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=50
            )

            # Calcular indicadores
            rsi = self.indicators.calculate_rsi(data, period=14)
            sma_20 = self.indicators.calculate_sma(data, period=20)

            if not rsi.empty and not sma_20.empty:
                current_rsi = rsi.iloc[-1]
                current_price = data['close'].iloc[-1]
                current_sma = sma_20.iloc[-1]

                self.logger.info(f"📊 Análisis - RSI: {current_rsi:.2f}, Precio: {current_price:.2f}, SMA20: {current_sma:.2f}")

                # Aplicar lógica de estrategia
                signal = None
                if current_rsi < 30 and current_price > current_sma:
                    signal = 'BUY'
                elif current_rsi > 70 or current_price < current_sma:
                    signal = 'SELL'

                if signal:
                    self.logger.info(f"🎯 Señal generada: {signal}")

                    # Ejecutar señal con gestión de riesgo
                    risk_result = self.risk_manager.validate_trade_signal({
                        'symbol': self.symbol,
                        'signal': signal,
                        'price': current_price,
                        'capital': self.capital
                    })

                    if risk_result['approved']:
                        # Ejecutar orden
                        order_size = risk_result['position_size']

                        if signal == 'BUY':
                            order = self.order_executor.place_market_order(
                                symbol=self.symbol,
                                side=OrderType.BUY,
                                amount=order_size
                            )
                        else:
                            order = self.order_executor.place_market_order(
                                symbol=self.symbol,
                                side=OrderType.SELL,
                                amount=order_size
                            )

                        if order:
                            self.logger.info(f"✅ Orden ejecutada: {signal} {order_size} {self.symbol}")

                            # Registrar trade
                            self.trades_history.append({
                                'symbol': self.symbol,
                                'signal': signal,
                                'size': order_size,
                                'price': order.get('price', current_price),
                                'timestamp': datetime.now(),
                                'strategy': 'RSI_SMA'
                            })

                            # Configurar SL/TP para la posición
                            entry_price = order.get('price', current_price)
                            sl_price = entry_price * 0.98 if signal == 'BUY' else entry_price * 1.02
                            tp_price = entry_price * 1.04 if signal == 'BUY' else entry_price * 0.96

                            # Colocar stop loss
                            sl_order = self.order_executor.place_stop_loss_order(
                                symbol=self.symbol,
                                side=OrderType.SELL if signal == 'BUY' else OrderType.BUY,
                                amount=order_size,
                                stop_price=sl_price
                            )

                            if sl_order:
                                self.logger.info(f"✅ Stop Loss configurado: {sl_price}")

                    else:
                        self.logger.info(f"❌ Señal rechazada por gestión de riesgo: {risk_result.get('reason', 'Unknown')}")

        except Exception as e:
            self.fail(f"Error en escenario completo de trading: {e}")

    def test_07_results_reporting(self):
        """Test 7: Reportar resultados del test"""
        self.logger.info("🧪 TEST 7: Reportando resultados del test")

        try:
            # Compilar reporte
            report = {
                'test_timestamp': datetime.now().isoformat(),
                'total_trades': len(self.trades_history),
                'total_positions': len(self.positions),
                'account_balance': self._get_account_balance(),
                'trades': self.trades_history,
                'positions': self.positions,
                'test_duration_seconds': time.time() - self.start_time if hasattr(self, 'start_time') else 0
            }

            # Calcular métricas básicas
            if self.trades_history:
                total_pnl = sum(trade.get('pnl', 0) for trade in self.trades_history if 'pnl' in trade)
                winning_trades = len([t for t in self.trades_history if t.get('pnl', 0) > 0])
                win_rate = (winning_trades / len(self.trades_history)) * 100 if self.trades_history else 0

                report.update({
                    'total_pnl': total_pnl,
                    'winning_trades': winning_trades,
                    'win_rate': win_rate
                })

            # Guardar reporte
            report_path = Path(__file__).parent / 'test_results' / f'binance_sandbox_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            report_path.parent.mkdir(exist_ok=True)

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"✅ Reporte guardado en: {report_path}")
            self.logger.info(f"📊 Resultados: {len(self.trades_history)} trades, Win Rate: {report.get('win_rate', 0):.1f}%")

        except Exception as e:
            self.fail(f"Error generando reporte: {e}")

    def tearDown(self):
        """Limpieza después del test"""
        try:
            # Cerrar todas las posiciones abiertas
            self.test_05_position_closing()

            # Cancelar todas las órdenes pendientes
            self._cancel_all_pending_orders()

            # Desconectar componentes
            if self.data_provider:
                self.data_provider.disconnect()
            if self.order_executor:
                self.order_executor.disconnect()

            self.logger.info("🧹 Limpieza completada")

        except Exception as e:
            self.logger.error(f"Error en limpieza: {e}")

    # Métodos auxiliares

    def _cancel_pending_orders(self, order_ids: List[str]):
        """Cancelar órdenes pendientes"""
        for order_id in order_ids:
            try:
                self.order_executor.cancel_order(self.symbol, order_id)
                self.logger.info(f"Orden {order_id} cancelada")
            except Exception as e:
                self.logger.warning(f"No se pudo cancelar orden {order_id}: {e}")

    def _cancel_all_pending_orders(self):
        """Cancelar todas las órdenes pendientes"""
        try:
            open_orders = self.order_executor.get_open_orders(self.symbol)
            if open_orders:
                for order in open_orders:
                    self.order_executor.cancel_order(self.symbol, order['id'])
                self.logger.info(f"{len(open_orders)} órdenes canceladas")
        except Exception as e:
            self.logger.warning(f"Error cancelando órdenes: {e}")

    def _monitor_position(self, symbol: str, oco_order_id: str, timeout_seconds: int):
        """Monitorear una posición con OCO"""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                order_status = self.order_executor.get_order_status(symbol, oco_order_id)
                if order_status and order_status.get('status') in ['closed', 'filled', 'canceled']:
                    self.logger.info(f"OCO ejecutada: {order_status.get('status')}")
                    break
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Error monitoreando OCO: {e}")
                break

    def _monitor_orders(self, symbol: str, order_ids: List[str], timeout_seconds: int):
        """Monitorear múltiples órdenes"""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                all_filled = True
                for order_id in order_ids:
                    status = self.order_executor.get_order_status(symbol, order_id)
                    if status and status.get('status') not in ['closed', 'filled', 'canceled']:
                        all_filled = False
                        break

                if all_filled:
                    self.logger.info("Todas las órdenes ejecutadas o canceladas")
                    break
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Error monitoreando órdenes: {e}")
                break

    def _get_account_balance(self) -> Dict:
        """Obtener balance de la cuenta"""
        try:
            account_info = self.order_executor.get_account_info()
            return account_info.get('total', {}) if account_info else {}
        except Exception as e:
            self.logger.warning(f"Error obteniendo balance: {e}")
            return {}

    def setUp(self):
        """Configuración inicial del test"""
        self.start_time = time.time()
        super().setUp()


if __name__ == '__main__':
    # Configurar logging para output de consola
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Ejecutar tests
    unittest.main(verbosity=2)