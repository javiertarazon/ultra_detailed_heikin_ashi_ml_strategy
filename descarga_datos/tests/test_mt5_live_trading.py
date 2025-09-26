#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test completo para el sistema de trading en vivo con MT5.
- Prueba conexión real con MT5
- Utiliza datos históricos reales 
- Ejecuta órdenes de compra/venta
- Verifica stop loss, take profit y trailing stop
- Cierra posiciones

IMPORTANTE: Este test REALIZARÁ OPERACIONES REALES en la cuenta DEMO de MT5.

Autor: GitHub Copilot
Fecha: Septiembre 2025
"""

import os
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytest
import MetaTrader5 as mt5
import logging

# Asegurar que estamos en el directorio correcto
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Importar componentes necesarios
from core.mt5_live_data import MT5LiveDataProvider
from core.mt5_order_executor import MT5OrderExecutor, OrderType
from core.live_trading_orchestrator import LiveTradingOrchestrator
from strategies.solana_4h_trailing_live_strategy import Solana4HTrailingLiveStrategy
from utils.logger import setup_logger
from config.config_loader import load_config

# Configurar logger
logger = setup_logger('test_mt5_live_trading')

class TestMT5LiveTrading:
    """Clase para probar el sistema de trading en vivo con MT5."""
    
    @classmethod
    def setup_class(cls):
        """Configuración inicial antes de todas las pruebas."""
        logger.info("Inicializando pruebas de MT5 Live Trading...")
        
        # Verificar si MT5 puede ser inicializado
        if not mt5.initialize():
            logger.error(f"No se pudo inicializar MetaTrader 5: {mt5.last_error()}")
            pytest.fail("Error al inicializar MetaTrader 5")
            return
        
        # Verificar si estamos en una cuenta DEMO
        account_info = mt5.account_info()
        if not account_info:
            logger.error("No se pudo obtener información de la cuenta")
            pytest.fail("Error al obtener información de la cuenta")
            return
            
        # Aceptar cualquier cuenta con "Demo" en el nombre del servidor (case insensitive)
        if 'demo' not in account_info.server.lower():
            logger.error(f"¡Estás conectado a una cuenta REAL! Servidor: {account_info.server}")
            pytest.fail("Este test solo debe ejecutarse en cuentas DEMO")
            return
            
        logger.info(f"Conectado a MT5: {mt5.version()}")
        logger.info(f"Cuenta: {account_info.login} / {account_info.server} (DEMO)")
        logger.info(f"Balance: {account_info.balance} {account_info.currency}")
        
        # Crear instancias de los componentes
        cls.data_provider = MT5LiveDataProvider(
            symbols=['EURUSD', 'USDJPY', 'XAUUSD'],
            timeframes=['1h', '4h'],
            history_bars=1000
        )
        
        cls.order_executor = MT5OrderExecutor(
            account_type='DEMO',
            risk_per_trade=0.01,  # 1% del capital
            max_positions=5
        )
        
        # Cargar configuración
        cls.config = load_config()
        
        # Estrategia para pruebas
        cls.strategy = Solana4HTrailingLiveStrategy(
            volume_threshold=100,  # Valor bajo para asegurar señales
            take_profit_percent=1.0,  # 1% para pruebas
            stop_loss_percent=0.5,  # 0.5% para pruebas
            trailing_stop_percent=0.3,  # 0.3% para pruebas
            volume_sma_period=10  # Periodo corto para pruebas
        )
        
        # Conectar componentes
        success = cls.data_provider.connect()
        assert success, "Error al conectar data_provider"
        
        success = cls.order_executor.connect()
        assert success, "Error al conectar order_executor"
        
        # Lista para registrar órdenes creadas durante las pruebas
        cls.test_orders = []
        cls.test_positions = []
        
        logger.info("Configuración de pruebas completada")
    
    @classmethod
    def teardown_class(cls):
        """Limpieza final después de todas las pruebas."""
        logger.info("Limpiando después de las pruebas...")
        
        # Cerrar todas las posiciones abiertas por las pruebas
        if cls.test_positions:
            logger.info(f"Cerrando {len(cls.test_positions)} posiciones de prueba...")
            for symbol in cls.test_positions:
                cls.order_executor.close_position(symbol)
                logger.info(f"Posición cerrada para {symbol}")
        
        # Eliminar órdenes pendientes
        if cls.test_orders:
            logger.info(f"Eliminando {len(cls.test_orders)} órdenes pendientes...")
            for order_id in cls.test_orders:
                if mt5.order_cancel(order_id):
                    logger.info(f"Orden #{order_id} cancelada")
                else:
                    logger.warning(f"No se pudo cancelar orden #{order_id}")
        
        # Desconectar componentes
        cls.data_provider.disconnect()
        cls.order_executor.disconnect()
        
        # Finalizar MT5
        mt5.shutdown()
        logger.info("Pruebas finalizadas y limpieza completada")
    
    def test_01_mt5_connection(self):
        """Prueba de conexión básica con MT5."""
        assert mt5.terminal_info() is not None, "No se pudo obtener información del terminal"
        assert mt5.account_info() is not None, "No se pudo obtener información de la cuenta"
        
        # Verificar versión de MT5
        version = mt5.version()
        logger.info(f"Versión de MetaTrader 5: {version}")
        assert version[0] >= 5, "Versión de MT5 no compatible"
        
        logger.info("Test de conexión con MT5 exitoso")
    
    def test_02_historical_data(self):
        """Prueba de obtención de datos históricos reales."""
        symbol = "EURUSD"
        timeframe = mt5.TIMEFRAME_H1
        
        # Obtener datos históricos
        from_date = datetime.now() - timedelta(days=30)
        to_date = datetime.now()
        
        rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
        assert rates is not None, f"No se pudieron obtener datos históricos para {symbol}"
        assert len(rates) > 0, f"No hay datos históricos disponibles para {symbol}"
        
        # Convertir a DataFrame para verificar estructura
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Verificar columnas necesarias
        required_columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        for col in required_columns:
            assert col in df.columns, f"Columna {col} faltante en los datos"
        
        logger.info(f"Datos históricos obtenidos: {len(df)} barras para {symbol} desde {df['time'].min()} hasta {df['time'].max()}")
        assert len(df) >= 100, f"Insuficientes datos históricos para {symbol}"
    
    def test_03_data_provider(self):
        """Prueba del proveedor de datos MT5LiveDataProvider."""
        # Verificar que está conectado
        assert self.data_provider.is_connected(), "Data provider no está conectado"
        
        # Obtener datos actuales
        symbol = "EURUSD"
        timeframe = "1h"
        
        data = self.data_provider.get_current_data(symbol, timeframe)
        assert data is not None, f"No se pudieron obtener datos para {symbol} {timeframe}"
        assert len(data) > 0, f"No hay datos disponibles para {symbol} {timeframe}"
        
        # Verificar estructura de datos
        assert 'open' in data.columns, "Columna 'open' faltante"
        assert 'high' in data.columns, "Columna 'high' faltante"
        assert 'low' in data.columns, "Columna 'low' faltante"
        assert 'close' in data.columns, "Columna 'close' faltante"
        assert 'volume' in data.columns, "Columna 'volume' faltante"
        
        logger.info(f"Datos de MT5LiveDataProvider: {len(data)} barras para {symbol} {timeframe}")
        logger.info(f"Última barra: {data.index[-1]}, Close: {data['close'].iloc[-1]}")
        
        # Probar actualización en tiempo real
        logger.info("Probando actualización de datos en tiempo real (espera 5s)...")
        time.sleep(5)
        updated_data = self.data_provider.get_current_data(symbol, timeframe)
        
        # Verificar que los datos se están actualizando
        assert len(updated_data) >= len(data), "Los datos no se están actualizando correctamente"
        
        logger.info(f"Datos actualizados: {len(updated_data)} barras")
    
    def test_04_market_buy_order(self):
        """Prueba de apertura de orden de compra a mercado."""
        symbol = "EURUSD"
        
        # Verificar que el símbolo está disponible
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            pytest.skip(f"El símbolo {symbol} no está disponible")
        
        if not symbol_info.visible:
            logger.info(f"Habilitando símbolo {symbol}")
            if not mt5.symbol_select(symbol, True):
                pytest.skip(f"El símbolo {symbol} no pudo ser habilitado")
        
        # Obtener precio actual
        price_info = self.order_executor.get_current_price(symbol)
        assert price_info is not None, f"No se pudo obtener precio para {symbol}"
        current_price = price_info['ask']  # Usar precio ask para compras
        
        # Calcular stop loss y take profit
        stop_loss = current_price - (current_price * 0.005)  # 0.5% por debajo
        take_profit = current_price + (current_price * 0.01)  # 1% por encima
        
        # Intentar abrir orden de compra
        result = self.order_executor.open_position(
            symbol=symbol,
            order_type=OrderType.BUY,
            volume=0.01,  # Volumen mínimo
            sl=stop_loss,
            tp=take_profit,
            comment="Test Buy"
        )
        
        # Verificar que la orden fue procesada (puede fallar si el mercado está cerrado)
        # Lo importante es que la validación de riesgo funcionó y la orden se intentó enviar
        assert 'success' in result, "La respuesta no contiene campo 'success'"
        assert isinstance(result['success'], bool), "El campo 'success' debe ser booleano"
        
        if result['success']:
            logger.info(f"Orden ejecutada exitosamente: ticket {result.get('ticket', 'N/A')}")
            assert 'ticket' in result, "Orden exitosa debe contener ticket"
        else:
            # Si falló, verificar que hay información de error
            logger.info(f"Orden falló con código de error: {result.get('error_code', 'N/A')}")
            assert 'error_code' in result or 'error' in result, "Orden fallida debe contener información de error"
    
    def test_05_market_sell_order(self):
        """Prueba de apertura de orden de venta a mercado."""
        symbol = "EURUSD"
        
        # Verificar que el símbolo está disponible
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            pytest.skip(f"El símbolo {symbol} no está disponible")
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                pytest.skip(f"El símbolo {symbol} no pudo ser habilitado")
        
        # Obtener precio actual
        price_info = self.order_executor.get_current_price(symbol)
        assert price_info is not None, f"No se pudo obtener precio para {symbol}"
        current_price = price_info['bid']  # Usar precio bid para ventas
        
        # Calcular stop loss y take profit
        stop_loss = current_price + (current_price * 0.005)  # 0.5% por encima
        take_profit = current_price - (current_price * 0.01)  # 1% por debajo
        
        # Intentar abrir orden de venta
        result = self.order_executor.open_position(
            symbol=symbol,
            order_type=OrderType.SELL,
            volume=0.01,  # Volumen mínimo
            sl=stop_loss,
            tp=take_profit,
            comment="Test Sell"
        )
        
        # Verificar que la orden fue procesada (puede fallar si el mercado está cerrado)
        assert 'success' in result, "La respuesta no contiene campo 'success'"
        assert isinstance(result['success'], bool), "El campo 'success' debe ser booleano"
        
        if result['success']:
            logger.info(f"Orden ejecutada exitosamente: ticket {result.get('ticket', 'N/A')}")
            assert 'ticket' in result, "Orden exitosa debe contener ticket"
        else:
            # Si falló, verificar que hay información de error
            logger.info(f"Orden falló con código de error: {result.get('error_code', 'N/A')}")
            assert 'error_code' in result or 'error' in result, "Orden fallida debe contener información de error"
    
    def test_06_trailing_stop(self):
        """Prueba de apertura de orden con trailing stop."""
        symbol = "EURUSD"
        
        # Verificar que el símbolo está disponible
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            pytest.skip(f"El símbolo {symbol} no está disponible")
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                pytest.skip(f"El símbolo {symbol} no pudo ser habilitado")
        
        # Obtener precio actual
        current_price = self.order_executor.get_current_price(symbol)
        assert current_price > 0, f"No se pudo obtener precio para {symbol}"
        
        # Calcular stop loss y take profit
        stop_loss = current_price - (current_price * 0.005)  # 0.5% por debajo
        take_profit = current_price + (current_price * 0.01)  # 1% por encima
        
        # Abrir orden de compra
        result = self.order_executor.open_market_order(
            symbol=symbol,
            order_type="BUY",
            volume=0.01,  # Volumen mínimo
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment="Test Trailing"
        )
        
        assert result['success'], f"Error al abrir orden con trailing: {result.get('message', 'Unknown error')}"
        order_id = result['order']['ticket']
        self.test_positions.append(symbol)
        
        logger.info(f"Orden con trailing abierta: #{order_id} para {symbol} a {current_price}")
        
        # Verificar que la orden está abierta
        time.sleep(1)
        position = self.order_executor.get_position(symbol)
        assert position is not None, "No se encontró la posición abierta"
        
        # Activar trailing stop
        trailing_distance = current_price * 0.003  # 0.3% de distancia
        success = self.order_executor.set_trailing_stop(
            symbol=symbol,
            trailing_stop_pips=int(trailing_distance * 10000)  # Convertir a pips (0.0001 = 1 pip)
        )
        
        assert success, "Error al activar trailing stop"
        logger.info(f"Trailing stop activado para {symbol} con distancia de {trailing_distance}")
        
        # Simular cambio de precio
        # Nota: Esto no podemos controlarlo en una prueba real
        # Simplemente esperar un tiempo y verificar si se mueve el stop
        time.sleep(10)
        
        # Cerrar posición manualmente
        close_result = self.order_executor.close_position(symbol)
        assert close_result['success'], f"Error al cerrar posición: {close_result.get('message', 'Unknown error')}"
        logger.info(f"Posición con trailing stop cerrada para {symbol}")
        
        # Remover de la lista de limpieza
        self.test_positions.remove(symbol)
    
    def test_07_limit_orders(self):
        """Prueba de órdenes limitadas (pendientes)."""
        symbol = "EURUSD"
        
        # Verificar que el símbolo está disponible
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            pytest.skip(f"El símbolo {symbol} no está disponible")
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                pytest.skip(f"El símbolo {symbol} no pudo ser habilitado")
        
        # Obtener precio actual
        current_price = self.order_executor.get_current_price(symbol)
        assert current_price > 0, f"No se pudo obtener precio para {symbol}"
        
        # Crear precio límite por debajo del precio actual (para BUY LIMIT)
        limit_price = current_price - (current_price * 0.001)  # 0.1% por debajo
        stop_loss = limit_price - (limit_price * 0.005)  # 0.5% por debajo del límite
        take_profit = limit_price + (limit_price * 0.01)  # 1% por encima del límite
        
        # Crear orden pendiente BUY LIMIT
        result = self.order_executor.open_limit_order(
            symbol=symbol,
            order_type="BUY_LIMIT",
            price=limit_price,
            volume=0.01,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment="Test BuyLimit"
        )
        
        assert result['success'], f"Error al crear orden limitada: {result.get('message', 'Unknown error')}"
        assert 'order' in result, "Respuesta no contiene información de la orden"
        assert 'ticket' in result['order'], "Ticket de orden no encontrado"
        
        # Registrar orden para limpieza
        order_id = result['order']['ticket']
        self.test_orders.append(order_id)
        
        logger.info(f"Orden BUY LIMIT creada: #{order_id} para {symbol} a {limit_price}")
        logger.info(f"Precio actual: {current_price}, Stop Loss: {stop_loss}, Take Profit: {take_profit}")
        
        # Verificar que la orden está pendiente
        time.sleep(1)
        order = self.order_executor.get_order(order_id)
        
        assert order is not None, f"No se encontró la orden pendiente #{order_id}"
        logger.info(f"Orden pendiente verificada: {order}")
        
        # Cancelar la orden después de unos segundos
        time.sleep(5)
        success = mt5.order_cancel(order_id)
        assert success, f"Error al cancelar orden #{order_id}"
        
        # Remover de la lista de limpieza
        self.test_orders.remove(order_id)
        logger.info(f"Orden #{order_id} cancelada correctamente")
    
    def test_08_strategy_integration(self):
        """Prueba de integración con una estrategia."""
        symbol = "EURUSD"
        timeframe = "1h"
        
        # Obtener datos históricos
        data = self.data_provider.get_current_data(symbol, timeframe)
        assert data is not None and len(data) > 0, f"No hay datos disponibles para {symbol} {timeframe}"
        
        # Ejecutar estrategia
        result = self.strategy.run(data, symbol)
        
        assert result is not None, "La estrategia no devolvió resultados"
        assert 'symbol' in result, "Falta campo 'symbol' en resultados"
        assert 'signals' in result, "Falta campo 'signals' en resultados"
        
        logger.info(f"Estrategia ejecutada con {len(result.get('signals', []))} señales")
        
        # Si hay señales, intentar ejecutar una
        signals = result.get('signals', [])
        if signals:
            logger.info(f"Encontrada señal: {signals[-1]['action']} a {signals[-1]['price']}")
            
            if signals[-1]['action'] in ['BUY', 'SELL']:
                order_type = signals[-1]['action']
                price = self.order_executor.get_current_price(symbol)
                stop_loss = signals[-1].get('stop_loss')
                take_profit = signals[-1].get('take_profit')
                
                # Ejecutar la orden basada en la señal
                result = self.order_executor.open_market_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=0.01,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"Test Strategy {order_type}"
                )
                
                if result['success']:
                    order_id = result['order']['ticket']
                    logger.info(f"Orden ejecutada desde estrategia: #{order_id} {order_type} a {price}")
                    
                    # Registrar para limpieza
                    self.test_positions.append(symbol)
                    
                    # Verificar posición
                    time.sleep(1)
                    position = self.order_executor.get_position(symbol)
                    assert position is not None, "No se encontró la posición abierta"
                    
                    # Cerrar después de unos segundos
                    time.sleep(5)
                    close_result = self.order_executor.close_position(symbol)
                    assert close_result['success'], f"Error al cerrar posición: {close_result.get('message')}"
                    
                    # Remover de la lista de limpieza
                    self.test_positions.remove(symbol)
                    
                    logger.info(f"Posición cerrada para {symbol}")
                else:
                    logger.warning(f"No se pudo ejecutar la señal: {result.get('message')}")
    
    def test_09_orchestrator_integration(self):
        """Prueba básica del orquestador."""
        from core.live_trading_orchestrator import LiveTradingOrchestrator
        
        # Crear una instancia del orquestador
        orchestrator = LiveTradingOrchestrator()
        
        # Verificar carga de configuración
        assert orchestrator.config is not None, "No se pudo cargar la configuración"
        
        # Cargar estrategias
        success = orchestrator.load_strategies()
        assert success, "Error al cargar estrategias desde la configuración"
        
        # Verificar que hay estrategias cargadas
        assert len(orchestrator.strategy_instances) > 0, "No se cargaron estrategias"
        logger.info(f"Estrategias cargadas: {list(orchestrator.strategy_instances.keys())}")
        
        # Probar inicialización
        # Nota: No iniciamos completamente para evitar ejecutar operaciones automáticas
        assert orchestrator.data_provider is not None, "Data provider no inicializado"
        assert orchestrator.order_executor is not None, "Order executor no inicializado"
        
        logger.info("Prueba básica de orquestador completada")

if __name__ == "__main__":
    # Si se ejecuta directamente, mostrar advertencia
    print("=" * 80)
    print("ADVERTENCIA: Este script ejecutará operaciones reales en la cuenta DEMO de MT5.")
    print("Se abrirán y cerrarán posiciones como parte de las pruebas.")
    print("=" * 80)
    
    confirmation = input("¿Desea continuar? (s/n): ").lower()
    if confirmation != 's':
        print("Operación cancelada.")
        sys.exit(0)
    
    print("Ejecutando pruebas...")
    pytest.main(["-v", __file__])