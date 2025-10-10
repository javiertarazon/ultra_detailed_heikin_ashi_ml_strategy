#!/usr/bin/env python3
"""
MT5 Order Executor - Componente para ejecutar operaciones de trading en MetaTrader 5.

Este módulo se encarga de ejecutar órdenes de trading en MetaTrader 5, incluyendo
apertura y cierre de posiciones, gestión de stop loss y take profit, trailing stops,
y seguimiento de posiciones abiertas.

Author: GitHub Copilot
Date: Septiembre 2025
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.logger import get_logger
import logging
import threading
from typing import Dict, List, Optional, Union, Tuple, Any
from enum import Enum
import json
from pathlib import Path
import os
import uuid


# Excepciones personalizadas
class OrderExecutionError(Exception):
    """Excepción para errores en la ejecución de órdenes MT5."""

    def __init__(self, message: str, error_code: int = None, symbol: str = None):
        self.message = message
        self.error_code = error_code
        self.symbol = symbol
        super().__init__(f"{message} (Código: {error_code}, Símbolo: {symbol})")


# Intentar importar MT5
try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 no disponible - Se requiere para ejecutar órdenes")

# Importar utilidades usando paths absolutos
from utils.logger import setup_logger
from utils.retry_manager import retry_operation


# Enums para órdenes
class OrderType(Enum):
    """Tipos de órdenes soportados"""

    BUY = mt5.ORDER_TYPE_BUY if MT5_AVAILABLE else 0
    SELL = mt5.ORDER_TYPE_SELL if MT5_AVAILABLE else 1
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT if MT5_AVAILABLE else 2
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT if MT5_AVAILABLE else 3
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP if MT5_AVAILABLE else 4
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP if MT5_AVAILABLE else 5


class OrderFilling(Enum):
    """Tipos de ejecución de órdenes"""

    FOK = mt5.ORDER_FILLING_FOK if MT5_AVAILABLE else 0  # Fill or Kill
    IOC = mt5.ORDER_FILLING_IOC if MT5_AVAILABLE else 1  # Immediate or Cancel
    RETURN = mt5.ORDER_FILLING_RETURN if MT5_AVAILABLE else 2  # Return


class TimeInForce(Enum):
    """Tiempo en vigor de las órdenes"""

    GTC = mt5.ORDER_TIME_GTC if MT5_AVAILABLE else 0  # Good Till Cancelled
    DAY = mt5.ORDER_TIME_DAY if MT5_AVAILABLE else 1  # Día
    SPECIFIED = mt5.ORDER_TIME_SPECIFIED if MT5_AVAILABLE else 2  # Hasta fecha específica
    SPECIFIED_DAY = mt5.ORDER_TIME_SPECIFIED_DAY if MT5_AVAILABLE else 3  # Hasta día específico


class MT5OrderExecutor:
    """
    Ejecutor de órdenes para MT5 que permite:
    1. Abrir posiciones de compra/venta
    2. Establecer stop loss y take profit
    3. Cerrar posiciones existentes
    4. Modificar órdenes pendientes
    5. Gestionar trailing stops
    """

    def __init__(
        self,
        config=None,
        live_data_provider=None,
        account_type=None,
        risk_per_trade=None,
        max_positions=None,
    ):
        """
        Inicializa el ejecutor de órdenes.

        Args:
            config: Configuración desde config.yaml
            live_data_provider: Opcional, instancia de MT5LiveDataProvider
            account_type: Tipo de cuenta ('DEMO' o 'REAL')
            risk_per_trade: Porcentaje de riesgo por operación (0.01 = 1%)
            max_positions: Número máximo de posiciones abiertas simultáneamente
        """
        # Cargar configuración si no se proporciona
        if config is None:
            from config.config_loader import load_config

            config_data = load_config()
            config = config_data.get("live_trading", {})

        self.config = config
        self.live_data_provider = live_data_provider

        # Usar valores proporcionados o valores por defecto de la configuración
        self.account_type = account_type or self.config.get("account_type", "DEMO")
        self.risk_per_trade = risk_per_trade or self.config.get("risk_per_trade", 0.01)
        self.max_positions = max_positions or self.config.get("max_positions", 5)
        # Configurar logger
        self.logger = setup_logger("MT5OrderExecutor")
        self.connected = False
        self.connection_lock = threading.Lock()

        # Órdenes y posiciones
        self.positions = {}
        self.orders = {}

        # Risk management
        self.default_sl_pips = 50
        self.default_tp_pips = 100
        self.max_risk_percent = 2.0  # Porcentaje máximo de riesgo por operación
        self.max_open_positions = 10  # Máximo de posiciones abiertas

        # Carpeta para almacenar historial de operaciones
        self.trades_path = (
            Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "live_trades"
        )
        self.trades_path.mkdir(parents=True, exist_ok=True)

    def connect(self) -> bool:
        """
        Establece conexión con MT5 y prepara el ejecutor para su uso.

        Returns:
            bool: True si la conexión se estableció correctamente
        """
        with self.connection_lock:
            if not MT5_AVAILABLE:
                self.logger.error("MT5 no está disponible. Instale el paquete MetaTrader5.")
                return False

            try:
                # Inicializar MT5 si no está ya inicializado
                if not mt5.initialize():
                    self.logger.error(f"Error al inicializar MT5: {mt5.last_error()}")
                    return False

                # Verificar que estamos en el tipo de cuenta correcto (DEMO/REAL)
                account_info = mt5.account_info()
                if not account_info:
                    self.logger.error("No se pudo obtener información de la cuenta")
                    return False

                if self.account_type == "DEMO" and "demo" not in account_info.server.lower():
                    self.logger.error(
                        f"Se requiere una cuenta DEMO pero estás conectado a: {account_info.server}"
                    )
                    return False

                if self.account_type == "REAL" and "demo" in account_info.server.lower():
                    self.logger.error(
                        f"Se requiere una cuenta REAL pero estás conectado a: {account_info.server}"
                    )
                    return False

                self.connected = True
                self.logger.info(
                    f"MT5OrderExecutor conectado a cuenta {account_info.login} ({account_info.server})"
                )
                return True

            except Exception as e:
                self.logger.error(f"Error al conectar MT5OrderExecutor: {str(e)}")
                return False

    def disconnect(self) -> bool:
        """
        Desconecta el ejecutor de órdenes de MT5.

        Returns:
            bool: True si la desconexión fue exitosa
        """
        with self.connection_lock:
            self.connected = False
            self.logger.info("MT5OrderExecutor desconectado")
            return True

    def is_connected(self) -> bool:
        """
        Verifica si el ejecutor está conectado a MT5.

        Returns:
            bool: True si está conectado
        """
        return self.connected and MT5_AVAILABLE and mt5.terminal_info() is not None

    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Obtiene el precio actual (bid/ask) para un símbolo.

        Args:
            symbol: Símbolo a consultar (ej: "EURUSD")

        Returns:
            Diccionario con precios bid, ask y spread
        """
        if not self.ensure_connection():
            self.logger.error("No hay conexión con MT5")
            return None

        try:
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Símbolo {symbol} no encontrado")
                return None

            return {
                "bid": symbol_info.bid,
                "ask": symbol_info.ask,
                "spread": symbol_info.spread,
                "digits": symbol_info.digits,
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {symbol}: {e}")
            return None
        self.active_positions = {}
        self.orders_history = {}
        self.last_errors = {}

        # Risk management
        self.default_sl_pips = 50
        self.default_tp_pips = 100
        self.max_risk_percent = 2.0  # Porcentaje máximo de riesgo por operación
        self.max_open_positions = 10  # Máximo de posiciones abiertas

        # Carpeta para almacenar historial de operaciones
        self.trades_path = (
            Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "live_trades"
        )
        self.trades_path.mkdir(parents=True, exist_ok=True)

        # Inicializar conexión
        if MT5_AVAILABLE:
            self._initialize_mt5()

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
                if hasattr(self.config, "login") and self.config.login:
                    if not mt5.login(
                        self.config.login, password=self.config.password, server=self.config.server
                    ):
                        self.logger.error(f"Error en login MT5: {mt5.last_error()}")
                        return False

                self.connected = True
                self.logger.info(f"MT5 conectado para ejecución de órdenes")

                # Cargar posiciones existentes
                self.refresh_positions()

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

    def _check_market_gaps(self, symbol: str) -> Tuple[bool, str]:
        """
        Verifica si hay gaps de mercado que puedan causar pérdidas no controladas.

        Args:
            symbol: Símbolo a verificar

        Returns:
            Tuple[bool, str]: (hay_gap, mensaje_explicativo)
        """
        try:
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return False, "Símbolo no encontrado"

            # Obtener datos recientes para detectar gaps
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 48)  # Últimas 48 horas
            if rates is None or len(rates) < 2:
                return False, "Datos insuficientes para verificar gaps"

            # Convertir a DataFrame para análisis
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Calcular gaps entre velas consecutivas
            df = df.sort_values("time")
            df["gap_pct"] = abs(df["open"] - df["close"].shift(1)) / df["close"].shift(1) * 100

            # Detectar gaps significativos (>2% para forex, >5% para otros)
            asset_class = self._get_asset_class(symbol)
            gap_threshold = 2.0 if "forex" in asset_class.lower() else 5.0

            recent_gaps = df["gap_pct"].tail(24)  # Últimas 24 horas
            max_recent_gap = recent_gaps.max()

            if max_recent_gap > gap_threshold:
                return (
                    True,
                    f"Gap de mercado detectado: {max_recent_gap:.2f}% (threshold: {gap_threshold}%)",
                )

            # Verificar si el mercado está cerrado (fines de semana para forex)
            now = datetime.now()
            if now.weekday() >= 5:  # Sábado o Domingo
                return True, "Mercado cerrado (fin de semana)"

            # Verificar spreads anormalmente altos (indicador de baja liquidez)
            current_spread = symbol_info.spread * symbol_info.point
            average_price = (symbol_info.ask + symbol_info.bid) / 2
            spread_pct = (current_spread / average_price) * 100

            if spread_pct > 0.5:  # Spread > 0.5%
                return True, f"Spread anormalmente alto: {spread_pct:.2f}%"

            return False, "Sin gaps detectados"

        except Exception as e:
            self.logger.warning(f"Error verificando gaps para {symbol}: {e}")
            return False, f"Error en verificación: {e}"

    def _get_asset_class(self, symbol: str) -> str:
        """
        Determina la clase de activo del símbolo.
        """
        symbol_upper = symbol.upper()

        # Forex
        if (
            any(curr in symbol_upper for curr in ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"])
            and "/" in symbol
        ):
            return "forex"

        # Commodities
        if any(comm in symbol_upper for comm in ["XAU", "XAG", "WTI", "BRENT", "COFFEE"]):
            return "commodities"

        # Indices
        if any(idx in symbol_upper for idx in ["SPX", "NDX", "DJI", "FTSE", "DAX"]):
            return "indices"

        # Default
        return "unknown"

    def _check_slippage(
        self, symbol: str, requested_price: float, executed_price: float, order_type: OrderType
    ) -> float:
        """
        Calcula el porcentaje de slippage entre precio solicitado y ejecutado.

        Args:
            symbol: Símbolo operado
            requested_price: Precio solicitado
            executed_price: Precio ejecutado
            order_type: Tipo de orden

        Returns:
            float: Porcentaje de slippage
        """
        if requested_price <= 0 or executed_price <= 0:
            return 0.0

        try:
            slippage = abs(executed_price - requested_price) / requested_price * 100

            # Logging para mercados volátiles
            asset_class = self._get_asset_class(symbol)
            if asset_class in ["crypto", "commodities"] and slippage > 0.2:
                self.logger.info(f"Slippage en {asset_class}: {slippage:.2f}% para {symbol}")

            return slippage

        except Exception as e:
            self.logger.warning(f"Error calculando slippage para {symbol}: {e}")
            return 0.0

    def open_position(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        magic: int = 0,
    ) -> None:
        """
        Abre una nueva posición en el mercado.

        Args:
            symbol: Símbolo a operar
            order_type: Tipo de orden (BUY, SELL)
            volume: Volumen en lotes
            price: Precio (0 para mercado)
            sl: Stop Loss (0 para desactivar)
            tp: Take Profit (0 para desactivar)
            comment: Comentario para la orden
            magic: Número mágico para identificar la orden

        Raises:
            OrderExecutionError: Si la orden no puede ser ejecutada
        """
        if not self.ensure_connection():
            raise OrderExecutionError(
                message="No hay conexión con MT5",
                error_code=-2,
                symbol=symbol,
                order_type=order_type.name,
                volume=volume,
                price=price,
            )

        # Verificar gaps de mercado antes de abrir posición
        has_gap, gap_message = self._check_market_gaps(symbol)
        if has_gap:
            self.logger.warning(f"🚫 Orden rechazada para {symbol}: {gap_message}")
            raise OrderExecutionError(
                message=f"Gap de mercado detectado: {gap_message}",
                error_code=-3,
                symbol=symbol,
                order_type=order_type.name,
                volume=volume,
                price=price,
            )

        try:
            # Preparar estructura de la orden
            if not magic:
                magic = int(time.time()) % 1000000  # Número semi-aleatorio si no se proporciona

            # Añadir identificador de la estrategia al comentario
            if not comment:
                comment = "Bot Trader Copilot"

            # Si es una orden de mercado y el precio es 0, obtener el precio actual
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                raise OrderExecutionError(
                    message=f"Símbolo {symbol} no encontrado",
                    error_code=-4,
                    symbol=symbol,
                    order_type=order_type.name,
                    volume=volume,
                    price=price,
                )

            if price <= 0:
                if order_type == OrderType.BUY:
                    price = symbol_info.ask
                else:  # SELL
                    price = symbol_info.bid

            # Redondear el precio según los dígitos del símbolo
            price = round(price, symbol_info.digits)
            if sl > 0:
                sl = round(sl, symbol_info.digits)
            if tp > 0:
                tp = round(tp, symbol_info.digits)

            # Crear estructura de la orden
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type.value,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 10,  # Desviación máxima del precio
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate or Cancel
            }

            # Verificar límites de riesgo
            if not self._validate_risk(symbol, volume, sl, price):
                return self._create_error_result(
                    "La orden excede los límites de riesgo configurados"
                )

            # Registrar la orden para análisis
            trade_id = str(uuid.uuid4())
            order_data = {
                "trade_id": trade_id,
                "symbol": symbol,
                "type": order_type.name,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
                "magic": magic,
                "timestamp": datetime.now().isoformat(),
                "status": "SENDING",
            }

            # Enviar la orden
            self.logger.info(f"Enviando orden: {symbol} {order_type.name} {volume} lotes a {price}")
            result = mt5.order_send(request)

            if result is None:
                error_code = mt5.last_error()
                error_message = f"Error enviando orden: {error_code}"
                self.logger.error(error_message)

                # Actualizar datos de la orden
                order_data["status"] = "ERROR"
                order_data["error_code"] = error_code
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                raise OrderExecutionError(
                    message=error_message,
                    error_code=error_code,
                    trade_id=trade_id,
                    symbol=symbol,
                    order_type=order_type.name,
                    volume=volume,
                    price=price,
                )

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_message = f"Orden rechazada: {result.retcode} - {self._get_retcode_description(result.retcode)}"
                self.logger.error(error_message)

                # Actualizar datos de la orden
                order_data["status"] = "REJECTED"
                order_data["error_code"] = result.retcode
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                raise OrderExecutionError(
                    message=error_message,
                    error_code=result.retcode,
                    trade_id=trade_id,
                    symbol=symbol,
                    order_type=order_type.name,
                    volume=volume,
                    price=price,
                )

            # Orden ejecutada correctamente
            self.logger.info(
                f"Orden ejecutada: {result.order} {symbol} {order_type.name} {volume} lotes a {price}"
            )

            # Verificar slippage
            slippage_pct = self._check_slippage(symbol, price, result.price, order_type)
            if slippage_pct > 0.5:  # Slippage > 0.5%
                warning_msg = f"⚠️ Slippage alto detectado: {slippage_pct:.2f}% (solicitado: {price}, ejecutado: {result.price})"
                self.logger.warning(warning_msg)
                order_data["slippage_pct"] = slippage_pct
                order_data["slippage_warning"] = warning_msg

            # Actualizar datos de la orden
            order_data["status"] = "EXECUTED"
            order_data["order_id"] = result.order
            order_data["executed_price"] = result.price
            order_data["executed_volume"] = result.volume

            # Guardar para análisis
            self._save_trade_record(order_data)

            # Actualizar posiciones
            self.refresh_positions()

            # Orden ejecutada exitosamente
            self.logger.info(f"✅ Orden completada exitosamente: {result.order}")

        except Exception as e:
            error_message = f"Error ejecutando orden: {str(e)}"
            self.logger.error(error_message)
            raise OrderExecutionError(
                message=error_message,
                error_code=-1,
                trade_id=trade_id,
                symbol=symbol if "symbol" in locals() else None,
                order_type=order_type.name if "order_type" in locals() else None,
                volume=volume if "volume" in locals() else None,
                price=price if "price" in locals() else None,
            )

    def close_position(self, position_id: int, volume: float = 0.0) -> Dict:
        """
        Cierra una posición existente.

        Args:
            position_id: ID de la posición a cerrar
            volume: Volumen a cerrar (0 para cerrar toda la posición)

        Returns:
            Diccionario con resultado de la operación
        """
        if not self.ensure_connection():
            return self._create_error_result("No hay conexión con MT5")

        try:
            # Obtener información de la posición
            position = mt5.positions_get(position=position_id)
            if not position:
                return self._create_error_result(f"Posición {position_id} no encontrada")

            position = position[0]._asdict()

            # Si no se especifica volumen, cerrar toda la posición
            if volume <= 0 or volume > position["volume"]:
                volume = position["volume"]

            # Crear orden opuesta para cerrar
            symbol = position["symbol"]
            position_type = position["type"]
            close_type = OrderType.SELL if position_type == 0 else OrderType.BUY

            # Obtener precio actual
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return self._create_error_result(f"Símbolo {symbol} no encontrado")

            price = symbol_info.ask if close_type == OrderType.BUY else symbol_info.bid

            # Crear estructura de la orden
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": close_type.value,
                "position": position_id,
                "price": price,
                "deviation": 10,
                "magic": position["magic"],
                "comment": f"Close #{position_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Registrar la orden para análisis
            trade_id = str(uuid.uuid4())
            order_data = {
                "trade_id": trade_id,
                "position_id": position_id,
                "symbol": symbol,
                "type": "CLOSE_" + close_type.name,
                "volume": volume,
                "price": price,
                "comment": f"Close #{position_id}",
                "magic": position["magic"],
                "timestamp": datetime.now().isoformat(),
                "status": "SENDING",
            }

            # Enviar la orden
            self.logger.info(f"Cerrando posición: #{position_id} {symbol} {volume} lotes")
            result = mt5.order_send(request)

            if result is None:
                error_code = mt5.last_error()
                error_message = f"Error cerrando posición: {error_code}"
                self.logger.error(error_message)

                # Actualizar datos de la orden
                order_data["status"] = "ERROR"
                order_data["error_code"] = error_code
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                return {
                    "success": False,
                    "error": error_message,
                    "error_code": error_code,
                    "trade_id": trade_id,
                }

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_message = f"Cierre rechazado: {result.retcode} - {self._get_retcode_description(result.retcode)}"
                self.logger.error(error_message)

                # Actualizar datos de la orden
                order_data["status"] = "REJECTED"
                order_data["error_code"] = result.retcode
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                return {
                    "success": False,
                    "error": error_message,
                    "error_code": result.retcode,
                    "trade_id": trade_id,
                }

            # Cierre ejecutado correctamente
            self.logger.info(
                f"Posición cerrada: #{position_id} {symbol} {volume} lotes a {result.price}"
            )

            # Actualizar datos de la orden
            order_data["status"] = "EXECUTED"
            order_data["order_id"] = result.order
            order_data["executed_price"] = result.price
            order_data["executed_volume"] = result.volume

            # Calcular profit
            profit = (
                position["profit"] * (volume / position["volume"])
                if position["volume"] > 0
                else position["profit"]
            )
            order_data["profit"] = profit

            # Guardar para análisis
            self._save_trade_record(order_data)

            # Actualizar posiciones
            self.refresh_positions()

            return {
                "success": True,
                "order_id": result.order,
                "executed_price": result.price,
                "executed_volume": result.volume,
                "profit": profit,
                "trade_id": trade_id,
            }

        except Exception as e:
            error_message = f"Error cerrando posición: {str(e)}"
            self.logger.error(error_message)
            return self._create_error_result(error_message)

    def modify_position(self, position_id: int, sl: float = 0.0, tp: float = 0.0) -> Dict:
        """
        Modifica SL/TP de una posición existente.

        Args:
            position_id: ID de la posición
            sl: Nuevo Stop Loss (0 para no modificar)
            tp: Nuevo Take Profit (0 para no modificar)

        Returns:
            Diccionario con resultado de la operación
        """
        if not self.ensure_connection():
            return self._create_error_result("No hay conexión con MT5")

        try:
            # Obtener información de la posición
            position = mt5.positions_get(position=position_id)
            if not position:
                return self._create_error_result(f"Posición {position_id} no encontrada")

            position = position[0]._asdict()
            symbol = position["symbol"]

            # Si no se especifican SL/TP, usar los existentes
            if sl <= 0:
                sl = position["sl"]
            if tp <= 0:
                tp = position["tp"]

            # Si ambos son 0, no hay nada que modificar
            if sl == position["sl"] and tp == position["tp"]:
                return {
                    "success": True,
                    "message": "No hay cambios que aplicar",
                    "position_id": position_id,
                }

            # Obtener precio actual y dígitos
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return self._create_error_result(f"Símbolo {symbol} no encontrado")

            # Redondear según los dígitos del símbolo
            sl = round(sl, symbol_info.digits)
            tp = round(tp, symbol_info.digits)

            # Crear estructura de la modificación
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": position_id,
                "sl": sl,
                "tp": tp,
            }

            # Registrar la modificación para análisis
            trade_id = str(uuid.uuid4())
            order_data = {
                "trade_id": trade_id,
                "position_id": position_id,
                "symbol": symbol,
                "type": "MODIFY",
                "old_sl": position["sl"],
                "old_tp": position["tp"],
                "new_sl": sl,
                "new_tp": tp,
                "timestamp": datetime.now().isoformat(),
                "status": "SENDING",
            }

            # Enviar la modificación
            self.logger.info(f"Modificando posición: #{position_id} {symbol} SL:{sl} TP:{tp}")
            result = mt5.order_send(request)

            if result is None:
                error_code = mt5.last_error()
                error_message = f"Error modificando posición: {error_code}"
                self.logger.error(error_message)

                # Actualizar datos
                order_data["status"] = "ERROR"
                order_data["error_code"] = error_code
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                return {
                    "success": False,
                    "error": error_message,
                    "error_code": error_code,
                    "trade_id": trade_id,
                }

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_message = f"Modificación rechazada: {result.retcode} - {self._get_retcode_description(result.retcode)}"
                self.logger.error(error_message)

                # Actualizar datos
                order_data["status"] = "REJECTED"
                order_data["error_code"] = result.retcode
                order_data["error_message"] = error_message

                # Guardar para análisis
                self._save_trade_record(order_data)

                return {
                    "success": False,
                    "error": error_message,
                    "error_code": result.retcode,
                    "trade_id": trade_id,
                }

            # Modificación ejecutada correctamente
            self.logger.info(f"Posición modificada: #{position_id} {symbol} SL:{sl} TP:{tp}")

            # Actualizar datos
            order_data["status"] = "EXECUTED"

            # Guardar para análisis
            self._save_trade_record(order_data)

            # Actualizar posiciones
            self.refresh_positions()

            return {
                "success": True,
                "position_id": position_id,
                "sl": sl,
                "tp": tp,
                "trade_id": trade_id,
            }

        except Exception as e:
            error_message = f"Error modificando posición: {str(e)}"
            self.logger.error(error_message)
            return self._create_error_result(error_message)

    def refresh_positions(self) -> Dict:
        """
        Actualiza la lista de posiciones abiertas.

        Returns:
            Diccionario con posiciones por símbolo
        """
        if not self.ensure_connection():
            return {}

        try:
            positions = mt5.positions_get()
            if positions is None:
                self.logger.info("No hay posiciones abiertas")
                self.active_positions = {}
                return {}

            # Convertir posiciones a diccionario
            positions_dict = {}
            for position in positions:
                pos = position._asdict()
                symbol = pos["symbol"]
                if symbol not in positions_dict:
                    positions_dict[symbol] = []
                positions_dict[symbol].append(pos)

            self.active_positions = positions_dict
            self.logger.debug(f"Posiciones actualizadas: {len(positions)} posiciones abiertas")

            return positions_dict

        except Exception as e:
            self.logger.error(f"Error actualizando posiciones: {e}")
            return {}

    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        Obtiene posiciones abiertas, opcionalmente filtradas por símbolo.

        Args:
            symbol: Símbolo para filtrar (None para todos)

        Returns:
            Lista de posiciones abiertas
        """
        self.refresh_positions()

        if symbol:
            return self.active_positions.get(symbol, [])
        else:
            # Aplanar todas las posiciones
            return [pos for positions in self.active_positions.values() for pos in positions]

    def close_all_positions(self, symbol: str = None) -> Dict:
        """
        Cierra todas las posiciones abiertas, opcionalmente filtradas por símbolo.

        Args:
            symbol: Símbolo para filtrar (None para cerrar todas)

        Returns:
            Diccionario con resultados
        """
        positions = self.get_positions(symbol)

        results = {"total": len(positions), "success": 0, "failed": 0, "details": []}

        for position in positions:
            result = self.close_position(position["ticket"])
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1

            results["details"].append(
                {
                    "position_id": position["ticket"],
                    "symbol": position["symbol"],
                    "volume": position["volume"],
                    "profit": position["profit"],
                    "result": result,
                }
            )

        return results

    def calculate_optimal_lot_size(
        self, symbol: str, risk_percent: float, stop_loss_pips: float
    ) -> float:
        """
        Calcula el tamaño de lote óptimo según el porcentaje de riesgo y SL.

        Args:
            symbol: Símbolo
            risk_percent: Porcentaje de riesgo (1.0 = 1%)
            stop_loss_pips: Distancia del SL en pips

        Returns:
            Tamaño de lote óptimo
        """
        if not self.ensure_connection():
            return 0.01  # Mínimo por defecto

        try:
            # Obtener información de la cuenta
            account_info = mt5.account_info()
            if not account_info:
                self.logger.error("No se pudo obtener información de la cuenta")
                return 0.01

            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.logger.error(f"Símbolo {symbol} no encontrado")
                return 0.01

            # Calcular valor monetario de un pip
            pip_value = symbol_info.trade_tick_value / symbol_info.trade_tick_size

            # Calcular balance arriesgado
            balance = account_info.balance
            risk_amount = balance * (risk_percent / 100)

            # Calcular tamaño de lote
            lot_size = risk_amount / (stop_loss_pips * pip_value)

            # Redondear al tamaño de lote mínimo
            min_lot = symbol_info.volume_min
            lot_step = symbol_info.volume_step

            # Redondear a múltiplo de lot_step
            lot_size = round(lot_size / lot_step) * lot_step

            # Asegurar que está entre min_lot y max_lot
            lot_size = max(min_lot, min(lot_size, symbol_info.volume_max))

            self.logger.info(
                f"Tamaño de lote calculado para {symbol}: {lot_size:.2f} lotes "
                f"(Riesgo: {risk_percent}%, SL: {stop_loss_pips} pips)"
            )

            return lot_size

        except Exception as e:
            self.logger.error(f"Error calculando tamaño de lote: {e}")
            return 0.01  # Valor mínimo por defecto

    def update_trailing_stops(self) -> Dict:
        """
        Actualiza trailing stops para posiciones abiertas.

        Returns:
            Diccionario con resultados de la actualización
        """
        positions = self.get_positions()

        results = {
            "total": len(positions),
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
            "details": [],
        }

        for position in positions:
            # Solo procesar posiciones con magic number específico o comentario que indique trailing
            if not (position["magic"] > 0 or "trail" in position["comment"].lower()):
                results["unchanged"] += 1
                continue

            symbol = position["symbol"]
            position_type = position["type"]  # 0=BUY, 1=SELL
            current_price = position["price_current"]
            current_sl = position["sl"]

            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.logger.error(f"Símbolo {symbol} no encontrado")
                results["failed"] += 1
                continue

            # Calcular trailing stop
            new_sl = current_sl
            update_needed = False

            if position_type == 0:  # BUY
                # Para compras, el SL sube si el precio sube
                distance = (
                    position["tp"] - position["price_open"]
                    if position["tp"] > 0
                    else 100 * symbol_info.point
                )
                trailing_distance = distance * 0.5  # 50% de la distancia a TP

                if current_price > position["price_open"] and (
                    current_sl < position["price_open"] or current_sl == 0
                ):
                    # Mover SL al precio de entrada cuando estamos en ganancia
                    new_sl = position["price_open"]
                    update_needed = True

                elif current_price > current_sl + trailing_distance and current_sl > 0:
                    # Ajustar SL hacia arriba manteniendo la distancia de trailing
                    new_sl = current_price - trailing_distance
                    update_needed = True

            else:  # SELL
                # Para ventas, el SL baja si el precio baja
                distance = (
                    position["price_open"] - position["tp"]
                    if position["tp"] > 0
                    else 100 * symbol_info.point
                )
                trailing_distance = distance * 0.5  # 50% de la distancia a TP

                if current_price < position["price_open"] and (
                    current_sl > position["price_open"] or current_sl == 0
                ):
                    # Mover SL al precio de entrada cuando estamos en ganancia
                    new_sl = position["price_open"]
                    update_needed = True

                elif current_price < current_sl - trailing_distance and current_sl > 0:
                    # Ajustar SL hacia abajo manteniendo la distancia de trailing
                    new_sl = current_price + trailing_distance
                    update_needed = True

            # Si se necesita actualizar, modificar la posición
            if update_needed:
                result = self.modify_position(position["ticket"], sl=new_sl)
                if result["success"]:
                    results["updated"] += 1
                    results["details"].append(
                        {
                            "position_id": position["ticket"],
                            "symbol": symbol,
                            "old_sl": current_sl,
                            "new_sl": new_sl,
                        }
                    )
                else:
                    results["failed"] += 1
            else:
                results["unchanged"] += 1

        return results

    def _validate_risk(self, symbol: str, volume: float, sl: float, price: float) -> bool:
        """
        Valida si una operación cumple con los parámetros de riesgo.

        Args:
            symbol: Símbolo
            volume: Tamaño de lote
            sl: Stop Loss
            price: Precio de entrada

        Returns:
            True si la operación es válida
        """
        # Si no hay SL, rechazar
        if sl <= 0:
            self.logger.warning(f"Operación rechazada: Sin Stop Loss")
            return False

        try:
            # Obtener información de la cuenta
            account_info = mt5.account_info()
            if not account_info:
                self.logger.error("No se pudo obtener información de la cuenta")
                return False

            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.logger.error(f"Símbolo {symbol} no encontrado")
                return False

            # Calcular riesgo monetario
            sl_distance = abs(price - sl)
            pip_value = symbol_info.trade_tick_value / symbol_info.trade_tick_size
            risk_amount = sl_distance * volume * pip_value

            # Calcular porcentaje de riesgo
            balance = account_info.balance
            risk_percent = (risk_amount / balance) * 100

            # Validar contra límite de riesgo
            if risk_percent > self.max_risk_percent:
                self.logger.warning(
                    f"Operación rechazada: Riesgo {risk_percent:.2f}% > {self.max_risk_percent}%"
                )
                return False

            # Validar número máximo de posiciones
            positions = self.get_positions()
            if len(positions) >= self.max_open_positions:
                self.logger.warning(
                    f"Operación rechazada: Máximo de posiciones alcanzado ({self.max_open_positions})"
                )
                return False

            # Todo ok
            self.logger.info(f"Validación de riesgo pasada: {risk_percent:.2f}% de {balance:.2f}")
            return True

        except Exception as e:
            self.logger.error(f"Error en validación de riesgo: {e}")
            return False

    def _create_error_result(self, message: str) -> Dict:
        """
        Crea un resultado de error estándar.

        Args:
            message: Mensaje de error

        Returns:
            Diccionario con el error
        """
        error_code = mt5.last_error() if MT5_AVAILABLE and self.connected else -1
        return {"success": False, "error": message, "error_code": error_code}

    def _get_retcode_description(self, retcode: int) -> str:
        """
        Obtiene la descripción de un código de retorno.

        Args:
            retcode: Código de retorno

        Returns:
            Descripción del código
        """
        retcode_map = {
            10004: "Requote",
            10006: "Orden rechazada",
            10007: "Orden cancelada por cliente",
            10008: "Orden colocada",
            10009: "Orden ejecutada",
            10010: "Solo ejecución parcial",
            10011: "Error de ejecución",
            10012: "Requote",
            10013: "Comercio deshabilitado",
            10014: "Mercado cerrado",
            10015: "No hay suficientes fondos",
            10016: "Precio no especificado",
            10017: "Volumen no especificado",
            10018: "Solicitud no especificada",
            10019: "Volumen demasiado bajo",
            10020: "Volumen demasiado alto",
            10021: "Precio inválido",
            10022: "Stop out",
            10023: "No especificado",
            10024: "Trading deshabilitado",
            10025: "Frozen",
            10026: "No hay suficientes dinero",
            10027: "Mercado cerrado",
            10028: "Solo posiciones cerradas",
            10029: "No hay suficiente margen para volumen",
            10030: "Trade prohibido",
            10031: "No hay suficiente dinero para swap",
            10032: "Orden bloqueada",
            10033: "Demasiados pedidos",
            10034: "Trading deshabilitado para símbolo",
            10035: "Recolocación de orden",
            10036: "Recolocación de orden",
            10038: "Recolocación de orden",
            10039: "Solo posiciones cerradas",
            10040: "Solo posiciones cerradas",
            10041: "Solo posiciones cerradas",
            10042: "Solo posiciones cerradas",
            10043: "Solo posiciones cerradas",
            10044: "Close order",
            10045: "Posición cerrada",
            10046: "Posición cerrada parcialmente",
        }
        return retcode_map.get(retcode, f"Error desconocido: {retcode}")

    def _save_trade_record(self, trade_data: Dict) -> None:
        """
        Guarda registro de operación para análisis.

        Args:
            trade_data: Datos de la operación
        """
        try:
            # Crear nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trade_id = trade_data.get("trade_id", str(uuid.uuid4()))
            symbol = trade_data.get("symbol", "UNKNOWN")
            filename = self.trades_path / f"{timestamp}_{symbol}_{trade_id}.json"

            # Guardar como JSON
            with open(filename, "w") as f:
                json.dump(trade_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error guardando registro de operación: {e}")

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
