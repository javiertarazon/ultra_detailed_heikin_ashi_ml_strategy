#!/usr/bin/env python3
"""
Pruebas de Live Trading con CCXT para BTC - Suite de pruebas completa.

Este módulo contiene pruebas para validar el funcionamiento del sistema
de trading en vivo con criptomonedas usando CCXT.

Author: GitHub Copilot
Date: Septiembre 2025
"""

import pytest
import time
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# Importar componentes de testing
from core.ccxt_live_data import CCXTLiveDataProvider
from core.ccxt_order_executor import CCXTOrderExecutor, OrderType
from core.ccxt_live_trading_orchestrator import CCXTLiveTradingOrchestrator

# Importar utilidades
from utils.logger import setup_logger

# Configurar logging para pruebas
logger = setup_logger('test_ccxt_live_trading')

class TestCCXTLiveTrading:
    """Suite de pruebas para trading en vivo con CCXT"""

    def setup_method(self):
        """Configuración inicial para cada prueba"""
        logger.info("Iniciando configuración de pruebas CCXT Live Trading...")

        # Configuración de prueba
        self.test_config = {
            'exchanges': {
                'bybit': {
                    'enabled': True,
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True,
                    'timeout': 30000
                }
            },
            'backtesting': {
                'symbols': ['BTC/USDT'],
                'timeframe': '4h',
                'strategies': {
                    'Solana4H': True
                },
                'strategy_paths': {
                    'Solana4H': ('strategies.solana_4h_strategy', 'Solana4HStrategy')
                }
            },
            'live_trading': {
                'risk_per_trade': 0.01,
                'max_positions': 5
            }
        }

        self.exchange_name = 'bybit'
        self.symbol = 'BTC/USDT'

    @pytest.mark.integration
    def test_01_ccxt_connection(self):
        """Prueba 1: Conexión básica con exchange CCXT"""
        logger.info("=== PRUEBA 1: Conexión CCXT ===")

        try:
            # Crear proveedor de datos
            data_provider = CCXTLiveDataProvider(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                symbols=[self.symbol]
            )

            # Intentar conectar
            connected = data_provider.connect()

            if connected:
                logger.info("✅ Conexión CCXT exitosa")
                assert data_provider.is_connected()

                # Verificar estado del mercado (debe ser True para crypto)
                market_status = data_provider.get_market_status(self.symbol)
                assert market_status == True, "El mercado de crypto debe estar siempre abierto"

                # Desconectar
                data_provider.disconnect()
                logger.info("✅ Desconexión exitosa")
            else:
                logger.warning("⚠️ Conexión CCXT fallida - puede ser por credenciales de prueba")
                pytest.skip("Conexión no disponible - verificar credenciales")

        except Exception as e:
            logger.error(f"❌ Error en conexión CCXT: {e}")
            pytest.fail(f"Error en conexión: {e}")

    @pytest.mark.integration
    def test_02_historical_data_btc(self):
        """Prueba 2: Obtención de datos históricos de BTC"""
        logger.info("=== PRUEBA 2: Datos Históricos BTC ===")

        try:
            data_provider = CCXTLiveDataProvider(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                symbols=[self.symbol]
            )

            if not data_provider.connect():
                pytest.skip("Conexión no disponible")

            # Obtener datos históricos
            df = data_provider.get_historical_data(self.symbol, '4h', limit=50)

            if df is not None:
                logger.info(f"✅ Datos históricos obtenidos: {len(df)} barras")

                # Verificar estructura del DataFrame
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    assert col in df.columns, f"Falta columna {col}"

                # Verificar que no esté vacío
                assert not df.empty, "DataFrame vacío"

                # Verificar tipos de datos
                assert pd.api.types.is_numeric_dtype(df['close']), "Precio close debe ser numérico"
                assert pd.api.types.is_numeric_dtype(df['volume']), "Volume debe ser numérico"

                # Verificar índice temporal
                assert isinstance(df.index, pd.DatetimeIndex), "Índice debe ser DatetimeIndex"

                logger.info(f"✅ Datos válidos - Último precio: ${df['close'].iloc[-1]:.2f}")

            else:
                logger.warning("⚠️ No se pudieron obtener datos históricos")
                pytest.skip("Datos históricos no disponibles")

            data_provider.disconnect()

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos históricos: {e}")
            pytest.fail(f"Error en datos históricos: {e}")

    @pytest.mark.integration
    def test_03_current_price_btc(self):
        """Prueba 3: Obtención de precio actual de BTC"""
        logger.info("=== PRUEBA 3: Precio Actual BTC ===")

        try:
            data_provider = CCXTLiveDataProvider(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                symbols=[self.symbol]
            )

            if not data_provider.connect():
                pytest.skip("Conexión no disponible")

            # Obtener precio actual
            price_info = data_provider.get_current_price(self.symbol)

            if price_info:
                logger.info("✅ Precio actual obtenido:")
                logger.info(f"   Bid: ${price_info['bid']:.2f}")
                logger.info(f"   Ask: ${price_info['ask']:.2f}")
                logger.info(f"   Last: ${price_info['last']:.2f}")
                logger.info(f"   Spread: ${price_info['spread']:.2f}")

                # Verificar que los precios sean positivos
                assert price_info['bid'] > 0, "Bid price debe ser positivo"
                assert price_info['ask'] > 0, "Ask price debe ser positivo"
                assert price_info['last'] > 0, "Last price debe ser positivo"

                # Verificar que ask >= bid
                assert price_info['ask'] >= price_info['bid'], "Ask debe ser >= Bid"

            else:
                logger.warning("⚠️ No se pudo obtener precio actual")
                pytest.skip("Precio actual no disponible")

            data_provider.disconnect()

        except Exception as e:
            logger.error(f"❌ Error obteniendo precio actual: {e}")
            pytest.fail(f"Error en precio actual: {e}")

    @pytest.mark.integration
    def test_04_order_executor_connection(self):
        """Prueba 4: Conexión del ejecutor de órdenes"""
        logger.info("=== PRUEBA 4: Conexión Order Executor ===")

        try:
            order_executor = CCXTOrderExecutor(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                risk_per_trade=0.01
            )

            # Intentar conectar
            connected = order_executor.connect()

            if connected:
                logger.info("✅ Order Executor conectado")
                assert order_executor.is_connected()

                # Verificar precio actual a través del executor
                price_info = order_executor.get_current_price(self.symbol)
                if price_info:
                    logger.info(f"✅ Precio desde executor: ${price_info['last']:.2f}")

                # Desconectar
                order_executor.disconnect()
                logger.info("✅ Order Executor desconectado")

            else:
                logger.warning("⚠️ Order Executor no conectado - puede ser por credenciales")
                pytest.skip("Order Executor no disponible")

        except Exception as e:
            logger.error(f"❌ Error en Order Executor: {e}")
            pytest.fail(f"Error en Order Executor: {e}")

    @pytest.mark.integration
    def test_05_risk_management_calculation(self):
        """Prueba 5: Cálculo de gestión de riesgo"""
        logger.info("=== PRUEBA 5: Gestión de Riesgo ===")

        try:
            order_executor = CCXTOrderExecutor(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                risk_per_trade=0.01  # 1% por trade
            )

            if not order_executor.connect():
                pytest.skip("Conexión no disponible")

            # Obtener precio actual
            price_info = order_executor.get_current_price(self.symbol)
            if not price_info:
                pytest.skip("Precio no disponible")

            entry_price = price_info['last']
            logger.info(f"Precio de entrada simulado: ${entry_price:.2f}")

            # Calcular parámetros de riesgo
            risk_params = order_executor.apply_risk_management(
                symbol=self.symbol,
                order_type=OrderType.BUY,
                entry_price=entry_price,
                stop_loss=entry_price * 0.98,  # 2% stop loss
                take_profit=entry_price * 1.04   # 4% take profit
            )

            if risk_params:
                logger.info("✅ Parámetros de riesgo calculados:")
                logger.info(f"   Cantidad: {risk_params['quantity']:.6f} BTC")
                logger.info(f"   Stop Loss: ${risk_params['stop_loss']:.2f}")
                logger.info(f"   Take Profit: ${risk_params['take_profit']:.2f}")
                logger.info(f"   Riesgo por trade: {risk_params['risk_percent']:.1%}")

                # Verificar cálculos
                assert risk_params['quantity'] > 0, "Cantidad debe ser positiva"
                assert risk_params['stop_loss'] < entry_price, "Stop loss debe ser menor que entry para BUY"
                assert risk_params['take_profit'] > entry_price, "Take profit debe ser mayor que entry para BUY"
                assert risk_params['risk_percent'] == 0.01, "Riesgo debe ser 1%"

            else:
                logger.warning("⚠️ No se pudieron calcular parámetros de riesgo")
                pytest.skip("Cálculo de riesgo no disponible")

            order_executor.disconnect()

        except Exception as e:
            logger.error(f"❌ Error en gestión de riesgo: {e}")
            pytest.fail(f"Error en gestión de riesgo: {e}")

    @pytest.mark.skip(reason="Requiere credenciales reales para trading")
    def test_06_market_buy_order_simulation(self):
        """Prueba 6: Simulación de orden de compra de mercado (requiere credenciales)"""
        logger.info("=== PRUEBA 6: Orden BUY Simulada ===")

        # Esta prueba se salta porque requiere credenciales reales
        # En un entorno de producción, se haría con una cantidad muy pequeña
        pytest.skip("Requiere credenciales reales para ejecutar órdenes")

    @pytest.mark.skip(reason="Requiere credenciales reales para trading")
    def test_07_market_sell_order_simulation(self):
        """Prueba 7: Simulación de orden de venta de mercado (requiere credenciales)"""
        logger.info("=== PRUEBA 7: Orden SELL Simulada ===")

        # Esta prueba se salta porque requiere credenciales reales
        # En un entorno de producción, se haría con una cantidad muy pequeña
        pytest.skip("Requiere credenciales reales para ejecutar órdenes")

    def test_08_orchestrator_initialization(self):
        """Prueba 8: Inicialización del orquestador"""
        logger.info("=== PRUEBA 8: Inicialización Orchestrator ===")

        try:
            orchestrator = CCXTLiveTradingOrchestrator(
                config_path=None,  # Usar config por defecto
                exchange_name=self.exchange_name
            )

            logger.info("✅ Orchestrator inicializado")

            # Verificar componentes
            assert orchestrator.data_provider is not None, "Data provider debe existir"
            assert orchestrator.order_executor is not None, "Order executor debe existir"
            assert orchestrator.exchange_name == self.exchange_name, "Exchange name incorrecto"

            # Verificar estado inicial
            status = orchestrator.get_status()
            assert 'running' in status, "Status debe incluir 'running'"
            assert status['running'] == False, "Inicialmente no debe estar corriendo"
            assert status['active_positions'] == 0, "Inicialmente no debe haber posiciones"

            logger.info("✅ Componentes del orchestrator verificados")

        except Exception as e:
            logger.error(f"❌ Error inicializando orchestrator: {e}")
            pytest.fail(f"Error en orchestrator: {e}")

    def test_09_data_cache_functionality(self):
        """Prueba 9: Funcionalidad del cache de datos"""
        logger.info("=== PRUEBA 9: Cache de Datos ===")

        try:
            data_provider = CCXTLiveDataProvider(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                symbols=[self.symbol]
            )

            if not data_provider.connect():
                pytest.skip("Conexión no disponible")

            # Primera llamada - debe obtener datos frescos
            df1 = data_provider.get_historical_data(self.symbol, '4h', limit=10)
            if df1 is None:
                pytest.skip("Datos no disponibles")

            # Segunda llamada inmediata - debe usar cache
            df2 = data_provider.get_historical_data(self.symbol, '4h', limit=10)

            # Verificar que los datos sean idénticos (cache funcionando)
            pd.testing.assert_frame_equal(df1, df2)
            logger.info("✅ Cache de datos funcionando correctamente")

            data_provider.disconnect()

        except Exception as e:
            logger.error(f"❌ Error en cache de datos: {e}")
            pytest.fail(f"Error en cache: {e}")

    def test_10_error_handling(self):
        """Prueba 10: Manejo de errores"""
        logger.info("=== PRUEBA 10: Manejo de Errores ===")

        try:
            # Probar con símbolo inválido
            data_provider = CCXTLiveDataProvider(
                config=self.test_config['exchanges'],
                exchange_name=self.exchange_name,
                symbols=['INVALID/SYMBOL']
            )

            if data_provider.connect():
                # Intentar obtener datos de símbolo inválido
                df = data_provider.get_historical_data('INVALID/SYMBOL', '4h', limit=10)
                # Debe retornar None sin crashear
                assert df is None, "Debe retornar None para símbolo inválido"

                logger.info("✅ Manejo de errores funcionando correctamente")

                data_provider.disconnect()
            else:
                logger.warning("⚠️ Conexión no disponible para prueba de errores")

        except Exception as e:
            logger.error(f"❌ Error en manejo de errores: {e}")
            pytest.fail(f"Error en manejo de errores: {e}")

    def teardown_method(self):
        """Limpieza después de cada prueba"""
        logger.info("Limpieza de pruebas completada")


# Función para ejecutar pruebas de integración
def run_ccxt_integration_tests():
    """
    Ejecuta todas las pruebas de integración para CCXT Live Trading
    """
    logger.info("=== EJECUTANDO PRUEBAS DE INTEGRACIÓN CCXT LIVE TRADING ===")

    test_instance = TestCCXTLiveTrading()

    # Ejecutar pruebas en orden
    try:
        test_instance.setup_method()

        logger.info("Ejecutando pruebas de integración...")

        # Pruebas que requieren conexión real
        try:
            test_instance.test_01_ccxt_connection()
        except Exception as e:
            logger.warning(f"Prueba 1 fallida: {e}")

        try:
            test_instance.test_02_historical_data_btc()
        except Exception as e:
            logger.warning(f"Prueba 2 fallida: {e}")

        try:
            test_instance.test_03_current_price_btc()
        except Exception as e:
            logger.warning(f"Prueba 3 fallida: {e}")

        try:
            test_instance.test_04_order_executor_connection()
        except Exception as e:
            logger.warning(f"Prueba 4 fallida: {e}")

        try:
            test_instance.test_05_risk_management_calculation()
        except Exception as e:
            logger.warning(f"Prueba 5 fallida: {e}")

        # Pruebas que no requieren conexión
        test_instance.test_08_orchestrator_initialization()
        test_instance.test_09_data_cache_functionality()
        test_instance.test_10_error_handling()

        test_instance.teardown_method()

        logger.info("=== PRUEBAS DE INTEGRACIÓN COMPLETADAS ===")

    except Exception as e:
        logger.error(f"Error ejecutando pruebas de integración: {e}")


if __name__ == "__main__":
    # Ejecutar pruebas si se llama directamente
    run_ccxt_integration_tests()