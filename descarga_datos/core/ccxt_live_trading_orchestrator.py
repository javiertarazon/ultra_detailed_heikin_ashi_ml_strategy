#!/usr/bin/env python3
"""
CCXT Live Trading Orchestrator - Orquestador para trading en vivo con criptomonedas.

Este módulo coordina el flujo de trabajo completo para trading en vivo con exchanges CCXT:
1. Obtiene datos en tiempo real desde exchanges de cripto
2. Aplica estrategias configuradas
3. Ejecuta operaciones según las señales generadas
4. Monitorea posiciones abiertas y resultados

Author: GitHub Copilot
Date: Septiembre 2025
"""

import time
from utils.logger import get_logger
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import threading
from indicators.technical_indicators import TechnicalIndicators
import queue
import json
from pathlib import Path
import os

# Importar componentes CCXT
from core.ccxt_live_data import CCXTLiveDataProvider
from core.ccxt_order_executor import CCXTOrderExecutor, OrderType

# Importar utilidades
from config.config_loader import load_config
from utils.logger import setup_logger
from risk_management.risk_management import apply_risk_management

# Configurar logging
logger = setup_logger('CCXTLiveTradingOrchestrator')

class CCXTLiveTradingOrchestrator:
    """
    Orquestador principal para operaciones de trading en vivo con cripto.

    Esta clase coordina todos los componentes necesarios para el trading en vivo:
    - Proveedor de datos en tiempo real de CCXT
    - Ejecución de estrategias configuradas
    - Envío y gestión de órdenes a través de CCXT
    - Seguimiento de posiciones y rendimiento
    """

    def __init__(self, config_path: str = None, exchange_name: str = 'bybit'):
        """
        Inicializa el orquestador de trading en vivo para cripto.

        Args:
            config_path: Ruta al archivo de configuración YAML. Si es None, se usa la configuración predeterminada.
            exchange_name: Nombre del exchange a usar (bybit, binance, etc.)
        """
        # Cargar configuración
        self.config = load_config(config_path)
        self.exchange_name = exchange_name

        # Configuración de live trading
        self.live_config = self.config.get('live_trading', {})
        self.backtesting_config = self.config.get('backtesting', {})

        # Inicializar componentes de trading
        self.data_provider = CCXTLiveDataProvider(
            config=self.config.get('exchanges', {}),
            exchange_name=exchange_name,
            symbols=self.backtesting_config.get('symbols', ['BTC/USDT']),
            timeframes=[self.backtesting_config.get('timeframe', '4h')]
        )

        self.order_executor = CCXTOrderExecutor(
            config=self.config.get('exchanges', {}),
            live_data_provider=self.data_provider,
            exchange_name=exchange_name,
            risk_per_trade=self.live_config.get('risk_per_trade', 0.01),
            max_positions=self.live_config.get('max_positions', 5)
        )

        # Variables para tracking de operaciones
        self.active_positions = {}
        self.position_history = []
        self.running = False
        self.strategy_classes = {}
        self.strategy_instances = {}

        # Cola para procesamiento seguro de señales
        self.signal_queue = queue.Queue()

        # Métricas en vivo
        self.live_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'start_time': datetime.now(),
            'runtime_minutes': 0
        }

        logger.info("CCXTLiveTradingOrchestrator inicializado correctamente")

    def connect(self) -> bool:
        """
        Conecta todos los componentes necesarios para el trading en vivo.

        Returns:
            bool: True si todas las conexiones se establecieron correctamente
        """
        try:
            # Conectar proveedor de datos
            if not self.data_provider.connect():
                logger.error("Error conectando proveedor de datos")
                return False

            # Conectar ejecutor de órdenes
            if not self.order_executor.connect():
                logger.error("Error conectando ejecutor de órdenes")
                return False

            logger.info("Todos los componentes conectados correctamente")
            return True

        except Exception as e:
            logger.error(f"Error conectando componentes: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Desconecta todos los componentes.

        Returns:
            bool: True si la desconexión fue exitosa
        """
        try:
            self.data_provider.disconnect()
            self.order_executor.disconnect()
            logger.info("Todos los componentes desconectados correctamente")
            return True
        except Exception as e:
            logger.error(f"Error desconectando componentes: {e}")
            return False

    def load_strategies(self):
        """
        Carga dinámicamente las estrategias configuradas en el archivo de configuración.
        """
        strategy_config = self.backtesting_config.get('strategies', {})
        strategy_path_config = self.backtesting_config.get('strategy_paths', {})

        # Cargar las estrategias habilitadas
        for strategy_name, enabled in strategy_config.items():
            if enabled and strategy_name in strategy_path_config:
                module_path, class_name = strategy_path_config[strategy_name]
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    strategy_class = getattr(module, class_name)
                    self.strategy_classes[strategy_name] = (module_path, class_name)
                    logger.info(f"Estrategia {strategy_name} cargada correctamente")
                except Exception as e:
                    logger.error(f"Error cargando estrategia {strategy_name}: {e}")

    def start_trading(self, duration_minutes: int = None):
        """
        Inicia el proceso de trading en vivo.

        Args:
            duration_minutes: Duración en minutos (opcional, si es None corre indefinidamente)
        """
        if not self.connect():
            logger.error("No se pudieron conectar los componentes. Abortando.")
            return

        self.running = True
        self.live_metrics['start_time'] = datetime.now()

        # Cargar estrategias
        self.load_strategies()

        # Iniciar actualizaciones de datos en tiempo real
        self.data_provider.start_real_time_updates()

        logger.info("Iniciando trading en vivo...")

        try:
            start_time = time.time()
            cycle_count = 0

            while self.running:
                # Verificar límite de tiempo
                if duration_minutes and (time.time() - start_time) > (duration_minutes * 60):
                    logger.info(f"Duración límite alcanzada ({duration_minutes} minutos)")
                    break

                # Procesar señales de trading cada 60 segundos
                if cycle_count % 60 == 0:
                    self._process_trading_signals()

                    # Verificar y gestionar posiciones abiertas
                    self._manage_open_positions()

                    # Actualizar métricas
                    self._update_metrics()

                cycle_count += 1

                # Esperar 1 segundo y verificar señales de interrupción
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Trading detenido por usuario (Ctrl+C)")
        except Exception as e:
            logger.error(f"Error durante el trading: {e}")
        finally:
            self._cleanup_trading()

    def _process_trading_signals(self):
        """
        Procesa las señales de trading generadas por las estrategias.
        """
        logger.debug(f"🔍 Procesando señales de trading...")
        
        # Obtener datos actuales para cada símbolo
        symbols = self.backtesting_config.get('symbols', [])
        logger.debug(f"📊 Símbolos configurados: {symbols}")
        
        for symbol in symbols:
            logger.debug(f"📈 Analizando {symbol}...")
            
            # Verificar estado del mercado
            market_status = self.data_provider.get_market_status(symbol)
            logger.debug(f"🕒 Estado del mercado {symbol}: {market_status}")
            
            if not market_status:
                logger.debug(f"⏸️ Mercado {symbol} cerrado, saltando...")
                continue  # Mercado cerrado

            # Obtener datos históricos recientes
            logger.debug(f"📥 Obteniendo datos históricos para {symbol}...")
            # Usar timeframe configurado en lugar de hardcodeado
            timeframe = self.backtesting_config.get('timeframe', '4h')
            # Obtener suficientes barras para compensar NaN iniciales después de calcular indicadores
            data = self.data_provider.get_historical_data(symbol, timeframe, limit=80)
            
            if data is None or data.empty:
                logger.warning(f"⚠️ No hay datos disponibles para {symbol}")
                continue
            
            logger.info(f"✅ Datos obtenidos para {symbol}: {len(data)} barras")

            # CALCULAR INDICADORES TÉCNICOS ANTES DE PASAR A ESTRATEGIAS
            logger.debug(f"🔧 Calculando indicadores técnicos para {symbol}...")
            try:
                indicators = TechnicalIndicators()
                data_with_indicators = indicators.calculate_all_indicators_unified(data.copy())
                logger.info(f"✅ Indicadores calculados para {symbol}: {len(data_with_indicators)} barras")
                
                # GUARDAR DATOS CON INDICADORES PARA ANÁLISIS POSTERIOR
                self._save_data_with_indicators(symbol, timeframe, data_with_indicators)
                
            except Exception as e:
                logger.error(f"❌ Error calculando indicadores para {symbol}: {e}")
                continue

            # Aplicar cada estrategia habilitada
            logger.debug(f"🎯 Estrategias disponibles: {list(self.strategy_classes.keys())}")
            
            for strategy_name, (module_path, class_name) in self.strategy_classes.items():
                try:
                    logger.info(f"🔄 Ejecutando estrategia {strategy_name} para {symbol}...")
                    
                    # Instanciar estrategia si no existe
                    if strategy_name not in self.strategy_instances:
                        logger.debug(f"📦 Instanciando estrategia {strategy_name}...")
                        module = __import__(module_path, fromlist=[class_name])
                        strategy_class = getattr(module, class_name)
                        self.strategy_instances[strategy_name] = strategy_class()
                        logger.debug(f"✅ Estrategia {strategy_name} instanciada")

                    strategy = self.strategy_instances[strategy_name]

                    # Ejecutar estrategia usando LIVE SIGNAL METHOD
                    logger.debug(f"⚙️ Ejecutando strategy.get_live_signal() para {symbol}...")
                    result = strategy.get_live_signal(data_with_indicators, symbol)
                    logger.info(f"📊 Resultado de {strategy_name}: {result.get('signal', 'NO_SIGNAL') if result else 'NONE'}")

                    # Procesar señales con instancia de estrategia
                    self._handle_strategy_signal(strategy_name, symbol, result, strategy)

                except Exception as e:
                    logger.error(f"Error procesando estrategia {strategy_name} para {symbol}: {e}")

    def _handle_strategy_signal(self, strategy_name: str, symbol: str, result: Dict[str, Any], strategy_instance=None):
        """
        Maneja las señales generadas por una estrategia con información completa de risk management.

        Args:
            strategy_name: Nombre de la estrategia
            symbol: Símbolo del par
            result: Resultado de la estrategia con signal_data
            strategy_instance: Instancia de la estrategia para consultas futuras
        """
        try:
            # Verificar si hay señal de entrada
            signal = result.get('signal', 'NO_SIGNAL')
            signal_data = result.get('signal_data', {})

            if signal in ['BUY', 'SELL'] and signal_data.get('current_signal') == signal:
                logger.info(f"Abrir nueva posición {signal} para {symbol} - Estrategia: {strategy_name}")

                # Extraer parámetros de risk management de la estrategia
                order_type = OrderType.BUY if signal == 'BUY' else OrderType.SELL

                # Usar parámetros proporcionados por la estrategia
                stop_loss_price = signal_data.get('stop_loss_price')
                take_profit_price = signal_data.get('take_profit_price')
                trailing_stop_pct = signal_data.get('trailing_stop_pct')
                risk_per_trade = signal_data.get('risk_per_trade')
                entry_price = signal_data.get('entry_price')

                # Verificar si ya tenemos una posición abierta para este símbolo
                existing_position = None
                for ticket, position in self.active_positions.items():
                    if position['symbol'] == symbol:
                        existing_position = position
                        break

                # Si hay posición abierta en dirección opuesta, cerrarla primero
                if existing_position and existing_position['type'] != signal.lower():
                    logger.info(f"Cerrando posición opuesta para {symbol}")
                    self.order_executor.close_position(existing_position['ticket'])

                # Si no hay posición abierta, abrir nueva
                if not existing_position:
                    logger.info(f"Abrir nueva posición {signal} para {symbol} con risk management de estrategia")

                    # Abrir posición con parámetros de risk management de la estrategia
                    position = self.order_executor.open_position(
                        symbol=symbol,
                        order_type=order_type,
                        stop_loss_price=stop_loss_price,
                        take_profit_price=take_profit_price,
                        trailing_stop_pct=trailing_stop_pct,
                        risk_per_trade=risk_per_trade,
                        price=entry_price
                    )

                    if position:
                        position['strategy'] = strategy_name
                        position['ml_confidence'] = result.get('ml_confidence', 0.5)
                        position['atr'] = signal_data.get('atr')
                        self.active_positions[position['ticket']] = position
                        self.live_metrics['total_trades'] += 1
                        logger.info(f"Posición abierta con risk management: {position}")

        except Exception as e:
            logger.error(f"Error manejando señal de estrategia {strategy_name}: {e}")

    def _manage_open_positions(self):
        """
        Gestiona las posiciones abiertas consultando a la estrategia sobre cierres.
        La estrategia maneja trailing stops, stop loss y take profit.
        """
        positions_to_close = []

        for ticket, position in self.active_positions.items():
            try:
                # Obtener precio actual
                current_price_info = self.order_executor.get_current_price(position['symbol'])
                if not current_price_info:
                    continue

                current_price = current_price_info['last']

                # Consultar a la estrategia sobre si debe cerrar la posición
                strategy_name = position.get('strategy', 'default')
                if strategy_name in self.strategy_instances:
                    strategy = self.strategy_instances[strategy_name]

                    # Verificar si la estrategia tiene método para gestionar posiciones
                    if hasattr(strategy, 'should_close_position'):
                        close_decision = strategy.should_close_position(
                            position_data=position,
                            current_price=current_price,
                            entry_price=position['entry_price'],
                            take_profit_price=position.get('take_profit')
                        )

                        if close_decision.get('should_close', False):
                            reason = close_decision.get('reason', 'strategy_decision')
                            logger.info(f"Posición {ticket} debe cerrarse por: {reason}")
                            positions_to_close.append((ticket, close_decision))
                            continue

                # Fallback: verificar stop loss básico si la estrategia no puede decidir
                else:
                    stop_loss = position.get('stop_loss')
                    if stop_loss:
                        if position['type'] == 'buy' and current_price <= stop_loss:
                            logger.info(f"Stop loss alcanzado para posición {ticket}")
                            positions_to_close.append((ticket, {'reason': 'stop_loss_fallback'}))
                            continue
                        elif position['type'] == 'sell' and current_price >= stop_loss:
                            logger.info(f"Stop loss alcanzado para posición {ticket}")
                            positions_to_close.append((ticket, {'reason': 'stop_loss_fallback'}))
                            continue

            except Exception as e:
                logger.error(f"Error gestionando posición {ticket}: {e}")

        # Cerrar posiciones identificadas
        for ticket, close_info in positions_to_close:
            if self.order_executor.close_position(ticket):
                position = self.active_positions[ticket]
                pnl = position.get('pnl', 0)
                self.live_metrics['total_pnl'] += pnl

                if pnl > 0:
                    self.live_metrics['winning_trades'] += 1
                else:
                    self.live_metrics['losing_trades'] += 1

                position['exit_reason'] = close_info.get('reason', 'unknown')
                self.position_history.append(position)
                del self.active_positions[ticket]

    def _update_metrics(self):
        """
        Actualiza las métricas de rendimiento en vivo.
        """
        try:
            # Calcular win rate
            total_closed = self.live_metrics['winning_trades'] + self.live_metrics['losing_trades']
            if total_closed > 0:
                self.live_metrics['win_rate'] = self.live_metrics['winning_trades'] / total_closed

            # Calcular profit factor
            winning_pnl = sum(p.get('pnl', 0) for p in self.position_history if p.get('pnl', 0) > 0)
            losing_pnl = abs(sum(p.get('pnl', 0) for p in self.position_history if p.get('pnl', 0) < 0))

            if losing_pnl > 0:
                self.live_metrics['profit_factor'] = winning_pnl / losing_pnl

            # Calcular tiempo de ejecución
            self.live_metrics['runtime_minutes'] = (datetime.now() - self.live_metrics['start_time']).total_seconds() / 60

        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")

    def _cleanup_trading(self):
        """
        Limpia y guarda el estado final del trading.
        """
        logger.info("Realizando limpieza final...")

        # Cerrar todas las posiciones abiertas
        for ticket in list(self.active_positions.keys()):
            logger.info(f"Cerrando posición abierta {ticket}")
            self.order_executor.close_position(ticket)

        # Guardar resultados
        self._save_trading_results()

        # Desconectar componentes
        self.disconnect()

        self.running = False
        logger.info("Limpieza completada")

    def _save_trading_results(self):
        """
        Guarda los resultados del trading en vivo en un archivo JSON.
        """
        try:
            # Crear directorio si no existe
            results_dir = Path("data/live_trading_results")
            results_dir.mkdir(parents=True, exist_ok=True)

            # Preparar datos para guardar
            results = {
                'live_metrics': self.live_metrics,
                'position_history': self.position_history,
                'active_positions': list(self.active_positions.values()),
                'config': {
                    'exchange': self.exchange_name,
                    'symbols': self.backtesting_config.get('symbols', []),
                    'strategies': list(self.strategy_classes.keys())
                },
                'end_time': datetime.now().isoformat()
            }

            # Guardar archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crypto_live_results_{timestamp}.json"
            filepath = results_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"Resultados guardados en {filepath}")

        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del orquestador.

        Returns:
            Dict con información del estado
        """
        return {
            'running': self.running,
            'connected': self.data_provider.is_connected() and self.order_executor.is_connected(),
            'active_positions': len(self.active_positions),
            'total_trades': self.live_metrics['total_trades'],
            'win_rate': self.live_metrics['win_rate'],
            'total_pnl': self.live_metrics['total_pnl'],
            'runtime_minutes': self.live_metrics['runtime_minutes']
        }

    def _save_data_with_indicators(self, symbol: str, timeframe: str, data: pd.DataFrame) -> None:
        """
        Guarda los datos con indicadores calculados para análisis posterior.
        Se guarda periódicamente durante el live trading.
        """
        try:
            from pathlib import Path
            import os
            
            # Crear directorio si no existe
            data_dir = Path("data/live_data_with_indicators")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear nombre de archivo seguro
            safe_symbol = symbol.replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_symbol}_{timeframe}_indicators_{timestamp}.csv"
            filepath = data_dir / filename
            
            # Guardar datos con indicadores
            data.to_csv(filepath)
            logger.debug(f"✅ Datos con indicadores guardados: {filepath}")
            
        except Exception as e:
            logger.error(f"Error guardando datos con indicadores para {symbol} {timeframe}: {e}")


def run_crypto_live_trading(config_path: str = None, exchange_name: str = 'bybit',
                           duration_minutes: int = None):
    """
    Función principal para ejecutar trading en vivo con cripto.

    Args:
        config_path: Ruta al archivo de configuración
        exchange_name: Nombre del exchange
        duration_minutes: Duración en minutos (opcional)
    """
    logger.info("=== INICIANDO TRADING EN VIVO CON CRIPTO ===")
    logger.info(f"Exchange: {exchange_name}")
    logger.info(f"Config: {config_path or 'default'}")
    logger.info(f"Duración: {duration_minutes or 'indefinida'} minutos")

    try:
        orchestrator = CCXTLiveTradingOrchestrator(config_path, exchange_name)
        orchestrator.start_trading(duration_minutes)

    except KeyboardInterrupt:
        logger.info("Trading detenido por usuario")
    except Exception as e:
        logger.error(f"Error en trading en vivo: {e}")
    finally:
        logger.info("=== TRADING EN VIVO FINALIZADO ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trading en vivo con criptomonedas")
    parser.add_argument('--config', help="Ruta al archivo de configuración")
    parser.add_argument('--exchange', default='bybit', help="Exchange a usar (bybit, binance, etc.)")
    parser.add_argument('--duration', type=int, help="Duración en minutos")

    args = parser.parse_args()

    run_crypto_live_trading(args.config, args.exchange, args.duration)