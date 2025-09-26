"""
Sistema orquestador de trading en vivo para el sistema modular.

Este módulo coordina el flujo de trabajo completo para trading en vivo:
1. Obtiene datos en tiempo real desde MT5
2. Aplica estrategias configuradas
3. Ejecuta operaciones según las señales generadas
4. Monitorea posiciones abiertas y resultados

Author: GitHub Copilot
Date: Septiembre 2025
"""

import time
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import threading
import queue

# Importar usando rutas absolutas
from config.config_loader import load_config
from core.mt5_live_data import MT5LiveDataProvider
from core.mt5_order_executor import MT5OrderExecutor
from utils.logger import setup_logger
from risk_management.risk_management import apply_risk_management

# Configurar logging
logger = setup_logger('LiveTradingOrchestrator')

class LiveTradingOrchestrator:
    """
    Orquestador principal para operaciones de trading en vivo.
    
    Esta clase coordina todos los componentes necesarios para el trading en vivo:
    - Proveedor de datos en tiempo real de MT5
    - Ejecución de estrategias configuradas
    - Envío y gestión de órdenes a través de MT5
    - Seguimiento de posiciones y rendimiento
    """
    
    def __init__(self, config_path: str = None):
        """
        Inicializa el orquestador de trading en vivo.
        
        Args:
            config_path: Ruta al archivo de configuración YAML. Si es None, se usa la configuración predeterminada.
        """
        # Cargar configuración
        self.config = load_config(config_path)
        self.live_config = self.config.get('live_trading', {})
        
        # Inicializar componentes de trading
        self.data_provider = MT5LiveDataProvider(config=self.config['mt5'])
        
        self.order_executor = MT5OrderExecutor(
            account_type=self.live_config.get('account_type', 'DEMO'),
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
        
        logger.info("LiveTradingOrchestrator inicializado correctamente")
    
    def load_strategies(self):
        """
        Carga dinámicamente las estrategias configuradas en el archivo de configuración.
        """
        strategy_config = self.config.get('backtesting', {}).get('strategies', {})
        strategy_path_config = self.config.get('backtesting', {}).get('strategy_paths', {})
        
        # Cargar las estrategias habilitadas
        for strategy_name, enabled in strategy_config.items():
            if enabled and strategy_name in strategy_path_config:
                module_path, class_name = strategy_path_config[strategy_name]
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    strategy_class = getattr(module, class_name)
                    self.strategy_classes[strategy_name] = strategy_class
                    self.strategy_instances[strategy_name] = strategy_class()
                    logger.info(f"Estrategia '{strategy_name}' cargada correctamente")
                except (ImportError, AttributeError) as e:
                    logger.error(f"Error al cargar estrategia '{strategy_name}': {str(e)}")
        
        if not self.strategy_instances:
            logger.warning("¡Ninguna estrategia ha sido cargada! Verificar configuración")
            return False
        
        logger.info(f"Se cargaron {len(self.strategy_instances)} estrategias correctamente")
        return True
    
    def start(self):
        """
        Inicia el orquestador de trading en vivo.
        """
        if self.running:
            logger.warning("El orquestador ya está en ejecución")
            return False
        
        # Cargar estrategias
        if not self.load_strategies():
            logger.error("No se pudieron cargar las estrategias. Abortando inicio.")
            return False
        
        # Conectar con MT5
        if not self.data_provider.connect():
            logger.error("No se pudo establecer conexión con MetaTrader 5")
            return False
        
        if not self.order_executor.connect():
            logger.error("No se pudo establecer conexión para ejecutar órdenes")
            self.data_provider.disconnect()
            return False
        
        # Iniciar hilos
        self.running = True
        self.data_thread = threading.Thread(target=self._data_processing_loop)
        self.signal_thread = threading.Thread(target=self._signal_processing_loop)
        
        self.data_thread.daemon = True
        self.signal_thread.daemon = True
        
        self.data_thread.start()
        self.signal_thread.start()
        
        logger.info("Orquestador de trading en vivo iniciado correctamente")
        return True
    
    def stop(self):
        """
        Detiene el orquestador de trading en vivo.
        """
        if not self.running:
            logger.warning("El orquestador no está en ejecución")
            return False
        
        self.running = False
        
        # Esperar a que terminen los hilos
        self.data_thread.join(timeout=10)
        self.signal_thread.join(timeout=10)
        
        # Cerrar conexiones
        self.data_provider.disconnect()
        self.order_executor.disconnect()
        
        # Actualizar métricas finales
        self._update_metrics()
        
        logger.info("Orquestador de trading en vivo detenido correctamente")
        return True
    
    def _data_processing_loop(self):
        """
        Bucle principal para procesar datos en tiempo real.
        Este método se ejecuta en un hilo separado.
        """
        logger.info("Hilo de procesamiento de datos iniciado")
        
        while self.running:
            try:
                # Obtener datos más recientes para todos los símbolos y timeframes
                for symbol in self.live_config.get('symbols', []):
                    for timeframe in self.live_config.get('timeframes', []):
                        # Obtener datos más recientes
                        data = self.data_provider.get_current_data(symbol, timeframe)
                        
                        if data is None or len(data) < 100:  # Mínimo de datos necesarios
                            logger.warning(f"Datos insuficientes para {symbol} {timeframe}")
                            continue
                            
                        # Procesar con cada estrategia habilitada
                        self._process_data_with_strategies(symbol, timeframe, data)
                
                # Actualizar métricas
                self._update_metrics()
                
                # Dormir según el intervalo configurado
                time.sleep(self.live_config.get('update_interval_seconds', 5))
                
            except Exception as e:
                logger.error(f"Error en el bucle de procesamiento de datos: {str(e)}")
                time.sleep(10)  # Esperar y reintentar
    
    def _signal_processing_loop(self):
        """
        Bucle para procesar señales de trading de forma segura.
        Este método se ejecuta en un hilo separado.
        """
        logger.info("Hilo de procesamiento de señales iniciado")
        
        while self.running:
            try:
                # Obtener señal de la cola (esperar hasta que haya una)
                try:
                    signal = self.signal_queue.get(timeout=1)
                    self._execute_trading_signal(signal)
                    self.signal_queue.task_done()
                except queue.Empty:
                    pass  # No hay señales para procesar
                    
            except Exception as e:
                logger.error(f"Error en el bucle de procesamiento de señales: {str(e)}")
                time.sleep(5)  # Esperar y reintentar
    
    def _process_data_with_strategies(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """
        Procesa los datos con las estrategias cargadas y genera señales de trading.
        
        Args:
            symbol: Símbolo a procesar
            timeframe: Timeframe a procesar
            data: DataFrame con datos OHLCV
        """
        for strategy_name, strategy in self.strategy_instances.items():
            try:
                # Verificar si esta estrategia debe procesar este símbolo/timeframe
                strategy_config = self.live_config.get('strategy_mapping', {}).get(strategy_name, {})
                if symbol not in strategy_config.get('symbols', []) or timeframe not in strategy_config.get('timeframes', []):
                    continue
                
                # Ejecutar estrategia
                result = strategy.run(data, symbol)
                
                if result and 'signals' in result and result['signals']:
                    # Obtener solo la última señal (más reciente)
                    latest_signal = result['signals'][-1]
                    
                    # Aplicar gestión de riesgo
                    if self.live_config.get('apply_risk_management', True):
                        risk_result = apply_risk_management(latest_signal, data, self.active_positions)
                        if not risk_result.get('valid', False):
                            logger.info(f"Señal rechazada por gestión de riesgo: {risk_result.get('reason', 'Unknown')}")
                            continue
                    
                    # Enviar señal a la cola para procesamiento
                    signal_data = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'strategy': strategy_name,
                        'signal': latest_signal,
                        'timestamp': datetime.now(),
                        'data': data.tail(1).to_dict('records')[0]
                    }
                    
                    self.signal_queue.put(signal_data)
                    logger.info(f"Nueva señal de {strategy_name} para {symbol} ({timeframe}): {latest_signal['action']}")
                    
            except Exception as e:
                logger.error(f"Error al procesar datos con {strategy_name} para {symbol} ({timeframe}): {str(e)}")
    
    def _execute_trading_signal(self, signal_data: Dict[str, Any]):
        """
        Ejecuta una señal de trading enviando órdenes a MT5.
        
        Args:
            signal_data: Diccionario con información de la señal
        """
        symbol = signal_data['symbol']
        action = signal_data['signal']['action']
        strategy_name = signal_data['strategy']
        current_price = signal_data['data'].get('close', None)
        
        if not current_price:
            logger.error(f"Precio actual no disponible para {symbol}")
            return
        
        try:
            # Verificar si ya tenemos una posición abierta para este símbolo
            existing_position = self.order_executor.get_position(symbol)
            position_action = None
            
            if action == 'BUY':
                if existing_position:
                    if existing_position['type'] == 'SELL':
                        # Cerrar posición corta existente y abrir larga
                        self.order_executor.close_position(symbol)
                        position_action = "cerrada posición SELL existente"
                    else:
                        # Ya tenemos una posición larga, no hacer nada
                        logger.info(f"Ignorando señal BUY para {symbol}: ya existe posición LONG")
                        return
                
                # Calcular stop loss y take profit
                stop_loss = signal_data['signal'].get('stop_loss', current_price * 0.95)
                take_profit = signal_data['signal'].get('take_profit', current_price * 1.1)
                
                # Abrir posición larga
                result = self.order_executor.open_market_order(
                    symbol=symbol,
                    order_type='BUY',
                    volume=signal_data['signal'].get('volume', None),  # Volumen automático si es None
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"LiveTrading-{strategy_name}"
                )
                
                if result['success']:
                    logger.info(f"Posición LONG abierta para {symbol} a {current_price}" + 
                              (f" después de {position_action}" if position_action else ""))
                    self._record_trade_opened(result['order'], signal_data)
                else:
                    logger.error(f"Error al abrir posición LONG para {symbol}: {result['message']}")
                    
            elif action == 'SELL':
                if existing_position:
                    if existing_position['type'] == 'BUY':
                        # Cerrar posición larga existente y abrir corta
                        self.order_executor.close_position(symbol)
                        position_action = "cerrada posición BUY existente"
                    else:
                        # Ya tenemos una posición corta, no hacer nada
                        logger.info(f"Ignorando señal SELL para {symbol}: ya existe posición SHORT")
                        return
                
                # Calcular stop loss y take profit
                stop_loss = signal_data['signal'].get('stop_loss', current_price * 1.05)
                take_profit = signal_data['signal'].get('take_profit', current_price * 0.9)
                
                # Abrir posición corta
                result = self.order_executor.open_market_order(
                    symbol=symbol,
                    order_type='SELL',
                    volume=signal_data['signal'].get('volume', None),  # Volumen automático si es None
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"LiveTrading-{strategy_name}"
                )
                
                if result['success']:
                    logger.info(f"Posición SHORT abierta para {symbol} a {current_price}" + 
                              (f" después de {position_action}" if position_action else ""))
                    self._record_trade_opened(result['order'], signal_data)
                else:
                    logger.error(f"Error al abrir posición SHORT para {symbol}: {result['message']}")
                    
            elif action == 'CLOSE':
                if existing_position:
                    result = self.order_executor.close_position(symbol)
                    if result['success']:
                        logger.info(f"Posición cerrada para {symbol} a {current_price}")
                        self._record_trade_closed(result['position'], signal_data)
                    else:
                        logger.error(f"Error al cerrar posición para {symbol}: {result['message']}")
                else:
                    logger.info(f"Ignorando señal CLOSE para {symbol}: no hay posición abierta")
                    
        except Exception as e:
            logger.error(f"Error al ejecutar señal de trading para {symbol}: {str(e)}")
    
    def _record_trade_opened(self, order_info: Dict[str, Any], signal_data: Dict[str, Any]):
        """
        Registra información de una operación abierta.
        
        Args:
            order_info: Información de la orden ejecutada
            signal_data: Datos de la señal que generó la orden
        """
        # Registrar en active_positions
        position_id = order_info.get('ticket', 0)
        self.active_positions[position_id] = {
            'symbol': signal_data['symbol'],
            'strategy': signal_data['strategy'],
            'type': order_info.get('order_type', ''),
            'open_price': order_info.get('price', 0.0),
            'volume': order_info.get('volume', 0.0),
            'stop_loss': order_info.get('stop_loss', 0.0),
            'take_profit': order_info.get('take_profit', 0.0),
            'open_time': datetime.now(),
            'signal_data': signal_data
        }
        
        logger.info(f"Nueva posición registrada: {position_id} para {signal_data['symbol']}")
    
    def _record_trade_closed(self, position_info: Dict[str, Any], signal_data: Dict[str, Any]):
        """
        Registra información de una operación cerrada.
        
        Args:
            position_info: Información de la posición cerrada
            signal_data: Datos de la señal que generó el cierre
        """
        position_id = position_info.get('ticket', 0)
        if position_id in self.active_positions:
            position_data = self.active_positions[position_id]
            position_data['close_price'] = position_info.get('price_close', 0.0)
            position_data['close_time'] = datetime.now()
            position_data['profit'] = position_info.get('profit', 0.0)
            position_data['duration_minutes'] = (position_data['close_time'] - position_data['open_time']).total_seconds() / 60
            
            # Mover a historial
            self.position_history.append(position_data)
            del self.active_positions[position_id]
            
            # Actualizar métricas
            self.live_metrics['total_trades'] += 1
            if position_data['profit'] > 0:
                self.live_metrics['winning_trades'] += 1
            else:
                self.live_metrics['losing_trades'] += 1
            self.live_metrics['total_pnl'] += position_data['profit']
            
            logger.info(f"Posición {position_id} cerrada con P&L: {position_data['profit']}")
    
    def _update_metrics(self):
        """
        Actualiza las métricas en vivo del sistema.
        """
        try:
            # Actualizar tiempo de ejecución
            self.live_metrics['runtime_minutes'] = (datetime.now() - self.live_metrics['start_time']).total_seconds() / 60
            
            # Actualizar tasa de victorias
            total_trades = self.live_metrics['winning_trades'] + self.live_metrics['losing_trades']
            if total_trades > 0:
                self.live_metrics['win_rate'] = self.live_metrics['winning_trades'] / total_trades
            
            # Actualizar factor de beneficio
            total_profit = sum(p['profit'] for p in self.position_history if p['profit'] > 0)
            total_loss = abs(sum(p['profit'] for p in self.position_history if p['profit'] < 0))
            if total_loss > 0:
                self.live_metrics['profit_factor'] = total_profit / total_loss
            
            # Calcular drawdown
            if self.position_history:
                cumulative_pnl = [0]
                for p in sorted(self.position_history, key=lambda x: x['close_time']):
                    cumulative_pnl.append(cumulative_pnl[-1] + p['profit'])
                
                # Calcular drawdown máximo
                max_dd = 0
                peak = cumulative_pnl[0]
                for value in cumulative_pnl:
                    if value > peak:
                        peak = value
                    dd = peak - value
                    if dd > max_dd:
                        max_dd = dd
                
                self.live_metrics['max_drawdown'] = max_dd
        
        except Exception as e:
            logger.error(f"Error al actualizar métricas: {str(e)}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas actuales del sistema de trading en vivo.
        
        Returns:
            Diccionario con métricas de rendimiento
        """
        # Actualizar métricas antes de devolver
        self._update_metrics()
        return self.live_metrics
    
    def get_active_positions(self) -> Dict[str, Any]:
        """
        Obtiene las posiciones actualmente abiertas.
        
        Returns:
            Diccionario con posiciones activas
        """
        # Actualizar desde MT5 para asegurar datos correctos
        mt5_positions = self.order_executor.get_all_positions()
        
        # Sincronizar con nuestro seguimiento interno
        position_tickets = set(p.get('ticket') for p in mt5_positions)
        for ticket in list(self.active_positions.keys()):
            if ticket not in position_tickets:
                # La posición ya no está activa en MT5, probablemente cerrada por SL/TP
                logger.warning(f"Posición {ticket} cerrada externamente (SL/TP activado)")
                position_info = next((p for p in mt5_positions if p.get('ticket') == ticket), None)
                if position_info:
                    self._record_trade_closed(position_info, self.active_positions[ticket].get('signal_data', {}))
                else:
                    # Si no tenemos la info de MT5, eliminar de todas formas
                    del self.active_positions[ticket]
        
        return self.active_positions
    
    def get_position_history(self) -> List[Dict[str, Any]]:
        """
        Obtiene el historial completo de posiciones cerradas.
        
        Returns:
            Lista con historial de posiciones
        """
        return self.position_history

    def export_results(self, filepath: str = None) -> bool:
        """
        Exporta los resultados del trading en vivo a un archivo JSON.
        
        Args:
            filepath: Ruta donde guardar el archivo de resultados
            
        Returns:
            True si se exportó correctamente, False en caso contrario
        """
        import json
        from datetime import datetime
        
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"data/live_trading_results/live_results_{timestamp}.json"
        
        try:
            # Preparar resultados
            results = {
                'metrics': self.get_current_metrics(),
                'position_history': self.get_position_history(),
                'active_positions': self.get_active_positions(),
                'runtime_info': {
                    'start_time': self.live_metrics['start_time'].isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'strategies_used': list(self.strategy_instances.keys()),
                    'symbols_traded': self.live_config.get('symbols', []),
                    'timeframes_used': self.live_config.get('timeframes', [])
                }
            }
            
            # Convertir objetos datetime a strings para serialización JSON
            results_serializable = json.loads(
                json.dumps(results, default=lambda o: o.isoformat() if isinstance(o, datetime) else None)
            )
            
            # Crear directorio si no existe
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Guardar resultados
            with open(filepath, 'w') as f:
                json.dump(results_serializable, f, indent=4)
            
            logger.info(f"Resultados exportados a: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error al exportar resultados: {str(e)}")
            return False

# Función auxiliar para ejecutar en modo standalone
def run_live_trading(config_path: str = None, duration_minutes: int = None):
    """
    Ejecuta el sistema de trading en vivo.
    
    Args:
        config_path: Ruta al archivo de configuración YAML
        duration_minutes: Duración en minutos (None para ejecución indefinida)
    """
    logger.info(f"Iniciando sistema de trading en vivo...")
    
    orchestrator = LiveTradingOrchestrator(config_path)
    
    if orchestrator.start():
        try:
            if duration_minutes:
                logger.info(f"Trading en vivo programado para {duration_minutes} minutos")
                time.sleep(duration_minutes * 60)
                logger.info(f"Duración completada, deteniendo sistema...")
            else:
                logger.info("Trading en vivo iniciado. Presione Ctrl+C para detener.")
                while True:
                    time.sleep(60)
                    metrics = orchestrator.get_current_metrics()
                    logger.info(f"Métricas actuales - P&L: {metrics['total_pnl']}, "
                               f"Trades: {metrics['total_trades']}, Win Rate: {metrics['win_rate']:.2f}")
                    
        except KeyboardInterrupt:
            logger.info("Interrupción del usuario recibida. Deteniendo...")
        finally:
            orchestrator.export_results()
            orchestrator.stop()
            logger.info("Sistema de trading en vivo finalizado")
    else:
        logger.error("No se pudo iniciar el sistema de trading en vivo")

if __name__ == "__main__":
    import sys
    
    config_path = None
    duration = None
    
    # Procesar argumentos de línea de comandos
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            duration = int(sys.argv[2])
        except ValueError:
            print("La duración debe ser un número entero de minutos")
            sys.exit(1)
    
    # Ejecutar trading en vivo
    run_live_trading(config_path, duration)