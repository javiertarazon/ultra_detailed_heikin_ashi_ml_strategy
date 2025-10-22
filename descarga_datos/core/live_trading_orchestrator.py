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
from utils.logger import get_logger
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
        self.strategy_live_configs = {}  # Configuraciones específicas de live trading por estrategia
        
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
        Carga dinámicamente TODAS las estrategias activas en backtesting.
        Sistema completamente modular - cualquier estrategia puede usarse en live trading.
        """
        # Obtener estrategias activas del backtesting
        backtesting_strategies = self.config.get('backtesting', {}).get('strategies', {})
        strategy_paths = self.config.get('backtesting', {}).get('strategy_paths', {})
        live_strategy_mapping = self.live_config.get('strategy_mapping', {})

        logger.info(f"🔍 Buscando estrategias activas en backtesting: {list(backtesting_strategies.keys())}")

        # Cargar TODAS las estrategias activas en backtesting
        for strategy_name, is_active in backtesting_strategies.items():
            if not is_active:
                logger.info(f"⏭️  {strategy_name} está desactivada en backtesting, omitiendo")
                continue

            logger.info(f"📦 Procesando estrategia: {strategy_name}")

            # Verificar si hay configuración específica para live trading
            live_config = live_strategy_mapping.get(strategy_name, {})

            # Si no hay configuración específica, crear configuración por defecto
            if not live_config:
                logger.info(f"⚙️  No hay configuración específica para {strategy_name}, creando configuración por defecto")
                live_config = self._create_default_live_config(strategy_name)

            # Verificar si la estrategia está activa para live trading
            if not live_config.get('active', False):
                logger.info(f"⏭️  {strategy_name} no está activa para live trading")
                continue

            # Cargar la estrategia usando el path configurado
            if strategy_name in strategy_paths:
                module_path, class_name = strategy_paths[strategy_name]
            else:
                logger.warning(f"❌ No se encontró path para estrategia '{strategy_name}' en strategy_paths")
                continue

            try:
                # Importar dinámicamente
                module = __import__(module_path, fromlist=[class_name])
                strategy_class = getattr(module, class_name)

                # Obtener parámetros de configuración
                strategy_params = live_config.get('parameters', {})

                # Instanciar estrategia con parámetros
                if strategy_params:
                    self.strategy_instances[strategy_name] = strategy_class(**strategy_params)
                    logger.info(f"✅ {strategy_name} cargada con parámetros: {list(strategy_params.keys())}")
                else:
                    self.strategy_instances[strategy_name] = strategy_class()
                    logger.info(f"✅ {strategy_name} cargada con parámetros por defecto")

                # Guardar configuración de live trading para esta estrategia
                self.strategy_live_configs[strategy_name] = live_config

            except (ImportError, AttributeError) as e:
                logger.error(f"❌ Error cargando {strategy_name}: {str(e)}")
                continue

        # Validar que se cargaron estrategias
        if not self.strategy_instances:
            logger.error("❌ No se pudo cargar ninguna estrategia para live trading")
            return False

        logger.info(f"🎯 Se cargaron {len(self.strategy_instances)} estrategias para live trading")
        for name in self.strategy_instances.keys():
            config = self.strategy_live_configs[name]
            symbols = config.get('symbols', [])
            timeframes = config.get('timeframes', [])
            logger.info(f"   📊 {name}: {len(symbols)} símbolos, {len(timeframes)} timeframes")

        return True
    
    def _create_default_live_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        Crea configuración por defecto para una estrategia en live trading.
        
        Args:
            strategy_name: Nombre de la estrategia
            
        Returns:
            Diccionario con configuración por defecto
        """
        # Símbolos por defecto basados en el tipo de estrategia
        if 'solana' in strategy_name.lower() or 'crypto' in strategy_name.lower():
            default_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            default_timeframes = ["4h", "1d"]
        else:
            # Forex por defecto
            default_symbols = ["EURUSD", "USDJPY"]
            default_timeframes = ["15m", "1h"]
        
        # Parámetros por defecto
        default_params = {
            'take_profit_percent': 3.0,
            'stop_loss_percent': 1.5
        }
        
        return {
            'active': True,
            'symbols': default_symbols,
            'timeframes': default_timeframes,
            'parameters': default_params
        }
    
    def _validate_live_config(self) -> bool:
        """
        Valida la configuración de live trading.
        
        Returns:
            True si la configuración es válida
        """
        logger.info("🔍 Validando configuración de live trading...")
        
        # Obtener símbolos disponibles
        mt5_symbols = self.live_config.get('mt5', {}).get('available_symbols', [])
        ccxt_symbols = self.live_config.get('ccxt', {}).get('available_symbols', [])
        available_symbols = mt5_symbols + ccxt_symbols
        
        # Obtener timeframes disponibles
        mt5_timeframes = self.live_config.get('mt5', {}).get('available_timeframes', [])
        ccxt_timeframes = self.live_config.get('ccxt', {}).get('available_timeframes', [])
        available_timeframes = list(set(mt5_timeframes + ccxt_timeframes))
        
        logger.info(f"📊 Símbolos disponibles: {len(available_symbols)}")
        logger.info(f"⏰ Timeframes disponibles: {available_timeframes}")
        
        # Validar cada estrategia cargada
        for strategy_name, live_config in self.strategy_live_configs.items():
            symbols = live_config.get('symbols', [])
            timeframes = live_config.get('timeframes', [])
            
            # Validar símbolos
            invalid_symbols = [s for s in symbols if s not in available_symbols]
            if invalid_symbols:
                logger.error(f"❌ Estrategia {strategy_name}: símbolos inválidos {invalid_symbols}")
                logger.error(f"   Símbolos disponibles: {available_symbols}")
                return False
            
            # Validar timeframes
            invalid_timeframes = [t for t in timeframes if t not in available_timeframes]
            if invalid_timeframes:
                logger.error(f"❌ Estrategia {strategy_name}: timeframes inválidos {invalid_timeframes}")
                logger.error(f"   Timeframes disponibles: {available_timeframes}")
                return False
            
            logger.info(f"✅ {strategy_name}: {len(symbols)} símbolos, {len(timeframes)} timeframes válidos")
        
        logger.info("✅ Configuración de live trading validada correctamente")
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
        
        # Validar configuración de live trading
        if not self._validate_live_config():
            logger.error("Configuración de live trading inválida. Abortando inicio.")
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
        Sistema completamente modular - procesa todos los símbolos/timeframes de cada estrategia.
        """
        logger.info("Hilo de procesamiento de datos iniciado")
        
        cycle_count = 0
        
        while self.running:
            cycle_count += 1
            logger.info(f"🚀 Iniciando ciclo #{cycle_count} - Sistema Modular Activo")
            
            try:
                # Procesar cada estrategia cargada con sus símbolos y timeframes específicos
                for strategy_name, strategy in self.strategy_instances.items():
                    live_config = self.strategy_live_configs[strategy_name]
                    symbols = live_config.get('symbols', [])
                    timeframes = live_config.get('timeframes', [])
                    
                    logger.info(f"🎯 Procesando {strategy_name}: {len(symbols)} símbolos, {len(timeframes)} timeframes")
                    
                    for symbol in symbols:
                        for timeframe in timeframes:
                            logger.info(f"📊 {strategy_name} -> {symbol} {timeframe}")
                            
                            # Obtener datos más recientes
                            data = self.data_provider.get_current_data(symbol, timeframe)
                            
                            if data is None or len(data) < 100:
                                logger.warning(f"❌ Datos insuficientes para {symbol} {timeframe}: {len(data) if data is not None else 0} filas")
                                continue
                            
                            logger.info(f"✅ Datos obtenidos: {len(data)} filas para {symbol} {timeframe}")
                            
                            # Procesar con la estrategia específica
                            self._process_data_with_strategy(strategy_name, strategy, symbol, timeframe, data)
                
                # Actualizar métricas
                self._update_metrics()
                
                logger.info(f"[CYCLE] Ciclo #{cycle_count} completado, esperando {self.live_config.get('update_interval_seconds', 5)} segundos")
                
                # Dormir según el intervalo configurado
                time.sleep(self.live_config.get('update_interval_seconds', 5))
                
            except Exception as e:
                logger.error(f"❌ Error en el bucle de procesamiento de datos: {str(e)}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                time.sleep(10)  # Esperar y reintentar
        
        logger.info("Hilo de procesamiento de datos finalizado")

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
    
    def _process_data_with_strategy(self, strategy_name: str, strategy, symbol: str, timeframe: str, data: pd.DataFrame):
        """
        Procesa los datos con una estrategia específica y genera señales de trading.
        
        Args:
            strategy_name: Nombre de la estrategia
            strategy: Instancia de la estrategia
            symbol: Símbolo a procesar
            timeframe: Timeframe a procesar
            data: DataFrame con datos OHLCV
        """
        try:
            logger.info(f"🎯 Ejecutando {strategy_name} para {symbol} {timeframe}")
            
            # Ejecutar estrategia
            result = strategy.run(data, symbol)
            
            if result and 'signals' in result and result['signals']:
                # Obtener solo la última señal (más reciente)
                latest_signal = result['signals'][-1]
                
                logger.info(f"[SIGNAL] ✅ {strategy_name} generó señal: {latest_signal.get('action', 'UNKNOWN')} para {symbol}")
                
                # Aplicar gestión de riesgo si está habilitada
                if self.live_config.get('apply_risk_management', True):
                    if not self._apply_risk_management_to_signal(latest_signal, symbol):
                        logger.info(f"[RISK] ❌ Señal rechazada por gestión de riesgo: {symbol}")
                        return
                
                # Verificar límites de posiciones
                if not self._check_position_limits(symbol):
                    logger.info(f"[LIMIT] ❌ Límite de posiciones alcanzado para {symbol}")
                    return
                
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
                logger.info(f"📤 Señal de {strategy_name} enviada a cola: {latest_signal['action']} {symbol}")
            else:
                logger.info(f"📭 {strategy_name} no generó señales para {symbol} {timeframe}")
                
        except Exception as e:
            logger.error(f"❌ Error procesando {strategy_name} para {symbol} ({timeframe}): {str(e)}")
    
    def _apply_risk_management_to_signal(self, signal: Dict[str, Any], symbol: str) -> bool:
        """
        Aplica gestión de riesgo a una señal de trading.
        
        Args:
            signal: Señal de trading
            symbol: Símbolo de la señal
            
        Returns:
            True si la señal pasa la gestión de riesgo
        """
        try:
            # Obtener balance de cuenta
            account_info = self.data_provider.get_account_info()
            account_balance = account_info.get('balance', 0.0)
            
            # Configuración de riesgo
            risk_config = {
                'risk_percent': self.live_config.get('risk_per_trade', 0.01) * 100,
                'max_drawdown_limit': 20.0
            }
            
            # Información del símbolo (básica por ahora)
            symbol_info = {
                'tick_size': 0.00001 if 'USD' in symbol else 0.01,  # Forex vs otros
                'min_lot': 0.01,
                'max_lot': 100.0
            }
            
            # Aplicar gestión de riesgo
            risk_result = apply_risk_management(signal, account_balance, symbol_info, risk_config)
            
            return not risk_result.get('rejected', False)
            
        except Exception as e:
            logger.error(f"Error aplicando gestión de riesgo: {str(e)}")
            return False
    
    def _check_position_limits(self, symbol: str) -> bool:
        """
        Verifica si se pueden abrir más posiciones para un símbolo.
        
        Args:
            symbol: Símbolo a verificar
            
        Returns:
            True si se puede abrir posición
        """
        # Contar posiciones abiertas totales
        total_positions = len(self.active_positions)
        max_positions = self.live_config.get('max_positions', 3)
        
        if total_positions >= max_positions:
            logger.info(f"Límite total de posiciones alcanzado: {total_positions}/{max_positions}")
            return False
        
        # Contar posiciones para este símbolo específico
        symbol_positions = sum(1 for pos in self.active_positions.values() if pos.get('symbol') == symbol)
        max_positions_per_symbol = self.live_config.get('max_positions_per_symbol', 1)
        
        if symbol_positions >= max_positions_per_symbol:
            logger.info(f"Límite de posiciones por símbolo alcanzado para {symbol}: {symbol_positions}/{max_positions_per_symbol}")
            return False
        
        return True
    
    def _execute_trading_signal(self, signal_data: Dict[str, Any]):
        """
        Ejecuta una señal de trading enviando órdenes a MT5.
        Sistema completamente modular con validaciones avanzadas.
        
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
        
        # Verificación final de límites antes de ejecutar
        if not self._check_position_limits(symbol):
            logger.warning(f"Verificación final fallida: límite de posiciones para {symbol}")
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
        from pathlib import Path
        
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = Path(__file__).parent.parent / "data" / "live_trading_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            filepath = results_dir / f"live_results_{timestamp}.json"
        
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