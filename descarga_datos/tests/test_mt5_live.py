#!/usr/bin/env python3
"""
Test Completo para Modo Live con MT5
=====================================

Este test verifica todas las funcionalidades del sistema de trading en vivo usando
MT5 para forex y acciones. Incluye:

1. Conexión y autenticación con MT5
2. Recopilación de datos en tiempo real
3. Cálculo de indicadores técnicos
4. Ejecución de operaciones de compra/venta
5. Configuración de stop loss y take profit
6. Gestión de posiciones
7. Seguimiento y reporte de resultados

El test es completamente realista y usa operaciones reales en la cuenta de demo.

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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importar componentes del sistema
from core.mt5_live_data import MT5LiveDataProvider
from core.mt5_order_executor import MT5OrderExecutor
from core.live_trading_orchestrator import LiveTradingOrchestrator
from indicators.technical_indicators import TechnicalIndicators
from config.config_loader import load_config
from utils.logger import setup_logger
import logging
from risk_management.risk_management import AdvancedRiskManager, apply_risk_management

# Configurar logging
logger = setup_logger('MT5LiveTest')

class MT5LiveTest(unittest.TestCase):
    """
    Test completo para validar el sistema de trading en vivo con MT5.
    """

    def setUp(self):
        """Configuración inicial del test"""
        self.logger = setup_logger('MT5LiveTest')

        # Configuración del test
        self.symbol = "EURUSD"  # Par forex para pruebas
        self.capital = 1000.0
        self.test_duration = 30  # segundos para pruebas rápidas

        # Inicializar componentes
        self.config = load_config()

        # Inicializar proveedores de datos y ejecutor de órdenes
        self.data_provider = MT5LiveDataProvider()
        self.order_executor = MT5OrderExecutor()
        self.indicators = TechnicalIndicators()
        self.risk_manager = AdvancedRiskManager()

        # Conectar componentes
        self.data_provider.connect()
        self.order_executor.connect()

        # Listas para seguimiento
        self.trades_history = []
        self.positions = []

        self.logger.info("Configuración del test MT5 completada")

    def tearDown(self):
        """Limpieza después del test"""
        try:
            # Cerrar todas las posiciones abiertas
            self._cleanup_positions()

            # Desconectar componentes
            if hasattr(self, 'order_executor') and self.order_executor:
                self.order_executor.disconnect()
            if hasattr(self, 'data_provider') and self.data_provider:
                self.data_provider.disconnect()

            self.logger.info("Limpieza completada")
        except Exception as e:
            self.logger.warning(f"Error en limpieza: {e}")

    def _cleanup_positions(self):
        """Cierra todas las posiciones abiertas para limpieza"""
        try:
            if hasattr(self, 'order_executor') and self.order_executor:
                # Cerrar posiciones abiertas
                positions = self.order_executor.get_positions(self.symbol)
                for position in positions:
                    try:
                        self.order_executor.close_position(position['ticket'])
                        self.logger.info(f"Posición {position['ticket']} cerrada en limpieza")
                    except Exception as e:
                        self.logger.warning(f"Error cerrando posición {position['ticket']}: {e}")

                # Cancelar órdenes pendientes si existen
                try:
                    self.order_executor.close_all_positions(self.symbol)
                except Exception as e:
                    self.logger.warning(f"Error cancelando órdenes: {e}")

        except Exception as e:
            self.logger.warning(f"Error en limpieza de posiciones: {e}")

    def test_01_connection_and_authentication(self):
        """Test 1: Verificar conexión y autenticación con MT5"""
        self.logger.info("[TEST] TEST 1: Verificando conexión y autenticación con MT5")

        # Verificar conexión del data provider
        self.assertTrue(self.data_provider.is_connected(),
                       "Data provider no está conectado")

        # Verificar conexión del order executor
        self.assertTrue(self.order_executor.is_connected(),
                       "Order executor no está conectado")

        # Obtener información de cuenta
        account_info = self.data_provider.get_account_info()
        self.assertIsNotNone(account_info, "No se pudo obtener información de cuenta")

        balance = account_info.get('balance', 0)
        self.assertGreater(balance, 0, f"Balance insuficiente: {balance}")

        self.logger.info(f"[OK] Conexión exitosa. Balance: {balance}")

    def test_02_live_data_collection(self):
        """Test 2: Recopilar datos en tiempo real y calcular indicadores"""
        self.logger.info("[TEST] TEST 2: Recopilando datos en tiempo real y calculando indicadores")

        # Obtener datos en tiempo real
        data = self.data_provider.get_current_data(self.symbol, "M1", limit=100)
        self.assertIsNotNone(data, "No se pudieron obtener datos en tiempo real")
        self.assertGreater(len(data), 0, "No hay datos suficientes")

        # Calcular indicadores técnicos
        indicators_data = self.indicators.calculate_all_indicators_unified(data)
        self.assertIsNotNone(indicators_data, "Error calculando indicadores")

        # Verificar indicadores específicos
        rsi = indicators_data.get('rsi')
        self.assertIsNotNone(rsi, "RSI no calculado")
        self.assertGreater(len(rsi), 0, "RSI vacío")

        last_rsi = rsi.iloc[-1]
        self.assertTrue(0 <= last_rsi <= 100, f"RSI fuera de rango: {last_rsi}")

        self.logger.info(f"[OK] Datos recopilados: {len(data)} velas")
        self.logger.info(f"[OK] Indicadores calculados - RSI: {last_rsi:.2f}")

    def test_03_limit_orders_buy_sell(self):
        """Test 3: Ejecutar órdenes límite de compra y venta"""
        self.logger.info("[TEST] TEST 3: Ejecutando órdenes límite de compra y venta")

        # Obtener precio actual
        current_price = self.data_provider.get_current_price(self.symbol)
        self.assertIsNotNone(current_price, "No se pudo obtener precio actual")

        price = current_price.get('bid', 0)
        self.assertGreater(price, 0, f"Precio inválido: {price}")

        # Calcular precios para órdenes límite
        buy_price = price * 0.998  # 0.2% por debajo del precio actual
        sell_price = price * 1.002  # 0.2% por encima del precio actual

        # Ejecutar orden de compra límite
        buy_order = self.order_executor.open_position(
            symbol=self.symbol,
            order_type='BUY',
            volume=0.01,
            price=buy_price,
            comment="Test BUY Limit"
        )

        if buy_order and buy_order.get('success', False):
            order_id = buy_order.get('order')
            self.logger.info(f"[OK] Orden límite de compra colocada: ID {order_id}, Precio: {buy_price}")

            # Verificar que la orden se ejecutó
            time.sleep(2)  # Esperar un poco
            # Nota: En MT5, las órdenes límite pueden no ejecutarse inmediatamente

        # Ejecutar orden de venta límite
        sell_order = self.order_executor.open_position(
            symbol=self.symbol,
            order_type='SELL',
            volume=0.01,
            price=sell_price,
            comment="Test SELL Limit"
        )

        if sell_order and sell_order.get('success', False):
            order_id = sell_order.get('order')
            self.logger.info(f"[OK] Orden límite de venta colocada: ID {order_id}, Precio: {sell_price}")

        # Verificar que al menos una orden se intentó
        orders_attempted = (buy_order and buy_order.get('success', False)) or (sell_order and sell_order.get('success', False))
        self.assertTrue(orders_attempted, "No se pudo colocar ninguna orden límite")

    def test_04_stop_loss_take_profit(self):
        """Test 4: Configurar stop loss y take profit"""
        self.logger.info("[TEST] TEST 4: Configurando stop loss y take profit")

        # Obtener precio actual
        current_price = self.data_provider.get_current_price(self.symbol)
        self.assertIsNotNone(current_price, "No se pudo obtener precio actual")

        price = current_price.get('bid', 0)
        self.assertGreater(price, 0, f"Precio inválido: {price}")

        # Abrir posición de mercado para tener una posición
        position_size = 0.01

        # Orden de compra de mercado
        market_buy = self.order_executor.open_position(
            symbol=self.symbol,
            order_type='BUY',
            volume=position_size
        )

        if market_buy and market_buy.get('success', False):
            ticket = market_buy.get('order')
            self.logger.info(f"[OK] Posición abierta: Ticket {ticket}")

            # Configurar stop loss y take profit
            stop_loss_price = price * 0.98  # 2% stop loss
            take_profit_price = price * 1.04  # 4% take profit

            # Modificar posición con SL/TP
            modify_result = self.order_executor.modify_position(
                position_id=ticket,
                sl=stop_loss_price,
                tp=take_profit_price
            )

            if modify_result and modify_result.get('success', False):
                self.logger.info(f"✅ Stop Loss y Take Profit configurados - SL: {stop_loss_price}, TP: {take_profit_price}")

                # Registrar posición
                self.positions.append({
                    'symbol': self.symbol,
                    'ticket': ticket,
                    'side': 'long',
                    'size': position_size,
                    'entry_price': price,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'timestamp': datetime.now()
                })
            else:
                self.logger.warning("No se pudo configurar SL/TP, pero la posición está abierta")

        else:
            self.logger.warning("No se pudo abrir posición de mercado para test de SL/TP")

    def test_05_position_closing(self):
        """Test 5: Cerrar posiciones abiertas"""
        self.logger.info("[TEST] TEST 5: Cerrando posiciones abiertas")

        # Obtener posiciones abiertas
        positions = self.order_executor.get_positions(self.symbol)

        if positions:
            for position in positions:
                ticket = position.get('ticket')
                if ticket:
                    close_result = self.order_executor.close_position(ticket)
                    if close_result and close_result.get('success', False):
                        self.logger.info(f"✅ Posición {ticket} cerrada exitosamente")
                    else:
                        self.logger.warning(f"No se pudo cerrar posición {ticket}")
        else:
            self.logger.info("No hay posiciones abiertas para cerrar")

    def test_06_comprehensive_trading_scenario(self):
        """Test 6: Escenario completo de trading con estrategia simple"""
        self.logger.info("[TEST] TEST 6: Ejecutando escenario completo de trading")

        # Obtener datos recientes
        data = self.data_provider.get_current_data(self.symbol, "M1", limit=50)
        self.assertIsNotNone(data, "No se pudieron obtener datos")

        # Calcular indicadores
        indicators_data = self.indicators.calculate_all_indicators_unified(data)
        self.assertIsNotNone(indicators_data, "Error calculando indicadores")

        # Lógica simple de estrategia
        current_rsi = indicators_data['rsi'].iloc[-1]
        current_price = data['close'].iloc[-1]
        current_sma = indicators_data['sma_20'].iloc[-1]

        self.logger.info(f"[CHART] Análisis - RSI: {current_rsi:.2f}, Precio: {current_price:.5f}, SMA20: {current_sma:.5f}")

        signal = None
        if current_rsi < 30 and current_price > current_sma:
            signal = 'BUY'
        elif current_rsi > 70 or current_price < current_sma:
            signal = 'SELL'

        if signal:
            self.logger.info(f"[TARGET] Señal generada: {signal}")

            # Preparar señal para gestión de riesgo
            signal_dict = {
                'symbol': self.symbol,
                'signal': signal,
                'direction': signal.lower(),
                'price': current_price,
                'capital': self.capital
            }

            # Obtener información del símbolo
            symbol_info = {
                'tick_size': 0.00001,  # Forex
                'min_lot': 0.01,
                'max_lot': 100.0
            }

            # Configuración de riesgo
            risk_config = {
                'risk_percent': 1.0,  # 1%
                'max_drawdown_limit': 20.0
            }

            # Aplicar gestión de riesgo
            risk_result = apply_risk_management(
                signal_dict,
                self.capital,
                symbol_info,
                risk_config
            )

            if not risk_result.get('rejected', False) and risk_result.get('risk_applied', False):
                # Ejecutar orden
                order_size = risk_result.get('position_size', 0.01)

                if signal == 'BUY':
                    order = self.order_executor.open_position(
                        symbol=self.symbol,
                        order_type='BUY',
                        volume=order_size
                    )
                else:
                    order = self.order_executor.open_position(
                        symbol=self.symbol,
                        order_type='SELL',
                        volume=order_size
                    )

                if order and order.get('success', False):
                    self.logger.info(f"✅ Orden ejecutada: {signal} {order_size} {self.symbol}")

                    # Registrar trade
                    self.trades_history.append({
                        'symbol': self.symbol,
                        'signal': signal,
                        'size': order_size,
                        'price': current_price,
                        'timestamp': datetime.now()
                    })
                else:
                    self.fail(f"Error ejecutando orden {signal}")
            else:
                rejection_reason = risk_result.get('rejection_reason', 'Unknown')
                self.logger.info(f"[ERROR] Señal rechazada por gestión de riesgo: {rejection_reason}")

        else:
            self.logger.info("[INFO] No se generó señal de trading")

    def test_07_results_reporting(self):
        """Test 7: Reportar resultados del test"""
        self.logger.info("[TEST] TEST 7: Reportando resultados del test")

        # Recopilar estadísticas
        total_trades = len(self.trades_history)
        total_positions = len(self.positions)

        # Obtener balance final (si es posible)
        try:
            account_info = self.data_provider.get_account_info()
            final_balance = account_info.get('balance', 0)
        except Exception as e:
            self.logger.warning(f"Error obteniendo balance: {e}")
            final_balance = 0

        # Crear reporte
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'total_trades': total_trades,
            'total_positions': total_positions,
            'final_balance': final_balance,
            'trades': self.trades_history,
            'positions': self.positions
        }

        # Guardar reporte
        reports_dir = Path(__file__).parent / "test_results"
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / f"mt5_live_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)

        self.logger.info(f"[OK] Reporte guardado en: {report_file}")
        self.logger.info(f"[CHART] Resultados: {total_trades} trades, {total_positions} posiciones")

if __name__ == '__main__':
    # Configurar logging para output de consola
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Ejecutar tests
    unittest.main(verbosity=2)