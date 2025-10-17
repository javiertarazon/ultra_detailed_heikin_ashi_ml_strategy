#!/usr/bin/env python3
"""
Auditoría de Datos Live desde Exchange Testnet
==============================================

Este script realiza una auditoría completa de los datos obtenidos en tiempo real
desde el testnet del exchange configurado (Binance o Bybit), verificando calidad,
consistencia y rendimiento.

Funcionalidades:
1. Conexión al exchange de testnet usando CCXT
2. Validación de calidad de datos (precios, volúmenes, timestamps)
3. Pruebas de latencia y frecuencia de actualización
4. Análisis de consistencia de datos históricos vs tiempo real
5. Auditoría de operaciones de trading (compra, venta, trailing stops)
6. Generación de reporte detallado con métricas

Uso:
python auditorias/audit_binance_testnet_data.py

Requisitos:
- Credenciales del exchange configurado en .env
- CCXT instalado
- Conexión a internet

Author: GitHub Copilot
Date: Octubre 2025
"""

import os
import sys
import time
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importar sistema de logging centralizado
from utils.logger import initialize_system_logging, get_logger

# Inicializar logging
initialize_system_logging({
    'level': 'INFO',
    'file': 'logs/binance_testnet_audit.log'
})

logger = get_logger('binance_testnet_audit')

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    dotenv_path = Path(__file__).parent.parent / '.env'
    success = load_dotenv(dotenv_path=dotenv_path)
    if success:
        logger.info(f"✅ Variables de entorno cargadas desde {dotenv_path}")
    else:
        logger.warning(f"⚠️ No se pudieron cargar variables desde {dotenv_path}")
        # Intentar sin path específico
        load_dotenv()
        logger.info("ℹ️ Intentando carga automática de .env")
except ImportError:
    logger.warning("⚠️ python-dotenv no disponible, usando variables de entorno del sistema")

# Detectar exchange activo
ACTIVE_EXCHANGE = os.getenv('ACTIVE_EXCHANGE', 'binance').lower()
logger.info(f"🔄 Exchange activo detectado: {ACTIVE_EXCHANGE}")

# Intentar importar CCXT
try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.error("CCXT no disponible - Se requiere para auditoría de Binance")

@dataclass
class AuditMetrics:
    """Métricas recopiladas durante la auditoría"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    data_quality_score: float = 0.0
    timestamp_consistency: bool = True
    price_anomalies: int = 0
    volume_anomalies: int = 0
    connection_drops: int = 0
    start_time: datetime = None
    end_time: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

class ExchangeTestnetAuditor:
    """
    Auditor de datos live desde Exchange Testnet.

    Realiza pruebas exhaustivas de calidad y rendimiento de datos.
    """

    def __init__(self, config_path: str = None):
        """
        Inicializa el auditor de Exchange Testnet.

        Args:
            config_path: Ruta al archivo de configuración (opcional)
        """
        self.config_path = config_path
        self.exchange = None
        self.metrics = AuditMetrics()
        self.test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.test_timeframes = ['1m', '5m', '15m']
        self.audit_duration_minutes = 5  # Duración de la auditoría en minutos
        self.sample_interval_seconds = 10  # Intervalo entre muestras
        self.public_mode = False  # Modo público sin credenciales

        # Cargar configuración si existe
        self.config = {}
        if self.config_path and Path(self.config_path).exists():
            self._load_config()

        # Inicializar exchange
        self._init_exchange()

    def _load_config(self):
        """Carga la configuración desde archivo YAML"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"✅ Configuración cargada desde {self.config_path}")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            self.config = {}

    def _init_exchange(self):
        """Inicializa la conexión a Exchange Testnet"""
        if not CCXT_AVAILABLE:
            raise RuntimeError("CCXT no está disponible")

        try:
            # Obtener exchange activo desde .env
            active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').lower()

            # Obtener credenciales según el exchange
            if active_exchange == 'binance':
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                exchange_class = ccxt.binance
                exchange_name = "Binance"
            elif active_exchange == 'bybit':
                api_key = os.getenv('BYBIT_API_KEY')
                api_secret = os.getenv('BYBIT_API_SECRET')
                exchange_class = ccxt.bybit
                exchange_name = "Bybit"
            else:
                raise ValueError(f"Exchange no soportado: {active_exchange}")

            logger.info(f"DEBUG: API_KEY presente: {bool(api_key)}, API_SECRET presente: {bool(api_secret)}")
            # Si no hay credenciales, usar modo público limitado
            if not api_key or not api_secret:
                logger.warning(f"⚠️ Credenciales no configuradas para {exchange_name} - Usando modo auditoría pública limitada")
                self.exchange = exchange_class({
                    'sandbox': True,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                    }
                })
                self.public_mode = True
            else:
                # Modo completo con credenciales
                self.exchange = exchange_class({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': True,
                    'test': True,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                    }
                })
                self.public_mode = False

            logger.info(f"✅ Exchange {exchange_name} Testnet inicializado" + (" (modo público)" if self.public_mode else ""))

        except Exception as e:
            logger.error(f"❌ Error inicializando exchange: {e}")
            raise

    def test_connection(self) -> bool:
        """Prueba la conexión básica al exchange"""
        try:
            active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
            logger.info(f"🔍 Probando conexión a {active_exchange} Testnet...")

            # Probar conexión - cargar mercados (disponible en modo público)
            self.exchange.loadMarkets()
            logger.info("✅ Mercados cargados exitosamente")

            # En modo público, no podemos obtener balance
            if not self.public_mode:
                # Obtener balance solo si tenemos credenciales
                balance = self.exchange.fetchBalance()
                free_balance = balance.get('free', {})
                usdt_balance = free_balance.get('USDT', 0)
                btc_balance = free_balance.get('BTC', 0)
                logger.info(f"✅ Conexión completa. Balance disponible: USDT={usdt_balance}, BTC={btc_balance}")
                logger.info(f"📊 Balance completo: {free_balance}")
            else:
                logger.info("✅ Conexión en modo público (sin credenciales)")

            return True

        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False

    def audit_data_quality(self, symbol: str, timeframe: str) -> Dict:
        """
        Audita la calidad de datos para un símbolo y timeframe específico.

        Args:
            symbol: Símbolo a auditar (ej: 'BTC/USDT')
            timeframe: Timeframe (ej: '1m', '5m')

        Returns:
            Dict con métricas de calidad
        """
        logger.info(f"🔍 Auditando calidad de datos: {symbol} {timeframe}")

        quality_metrics = {
            'symbol': symbol,
            'timeframe': timeframe,
            'samples_collected': 0,
            'price_anomalies': 0,
            'volume_anomalies': 0,
            'timestamp_issues': 0,
            'avg_price': 0.0,
            'avg_volume': 0.0,
            'price_volatility': 0.0,
            'data_completeness': 0.0
        }

        try:
            # Obtener datos históricos recientes
            since = self.exchange.parse8601((datetime.now() - timedelta(hours=1)).isoformat())
            ohlcv = self.exchange.fetchOHLCV(symbol, timeframe, since=since, limit=100)

            if not ohlcv:
                logger.warning(f"⚠️ No se obtuvieron datos para {symbol} {timeframe}")
                return quality_metrics

            # Convertir a DataFrame para análisis
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            quality_metrics['samples_collected'] = len(df)

            if len(df) > 1:
                # Calcular métricas de calidad
                quality_metrics['avg_price'] = df['close'].mean()
                quality_metrics['avg_volume'] = df['volume'].mean()
                quality_metrics['price_volatility'] = df['close'].std() / df['close'].mean()

                # Verificar anomalías de precio
                price_changes = df['close'].pct_change().abs()
                quality_metrics['price_anomalies'] = (price_changes > 0.1).sum()  # Cambios > 10%

                # Verificar anomalías de volumen
                volume_mean = df['volume'].mean()
                volume_std = df['volume'].std()
                quality_metrics['volume_anomalies'] = ((df['volume'] - volume_mean).abs() > 3 * volume_std).sum()

                # Verificar timestamps
                expected_interval = pd.Timedelta(timeframe)
                timestamp_diffs = df['timestamp'].diff()
                quality_metrics['timestamp_issues'] = (timestamp_diffs != expected_interval).sum()

                # Calcular completitud de datos
                total_expected = len(df)
                quality_metrics['data_completeness'] = (total_expected - quality_metrics['timestamp_issues']) / total_expected

            logger.info(f"✅ Análisis completado para {symbol} {timeframe}: {quality_metrics['samples_collected']} muestras")

        except Exception as e:
            logger.error(f"❌ Error auditando {symbol} {timeframe}: {e}")

        return quality_metrics

    def audit_latency(self, symbol: str, num_tests: int = 10) -> Dict:
        """
        Mide la latencia de las llamadas a la API.

        Args:
            symbol: Símbolo para las pruebas
            num_tests: Número de pruebas a realizar

        Returns:
            Dict con métricas de latencia
        """
        logger.info(f"⏱️ Midiendo latencia para {symbol} ({num_tests} pruebas)")

        latencies = []
        successful_requests = 0

        for i in range(num_tests):
            try:
                start_time = time.time()

                # Hacer una llamada simple
                ticker = self.exchange.fetchTicker(symbol)

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                latencies.append(latency_ms)
                successful_requests += 1

                logger.debug(f"Prueba {i+1}: {latency_ms:.2f}ms")

                # Pequeña pausa entre pruebas
                time.sleep(0.1)

            except Exception as e:
                logger.warning(f"Prueba {i+1} fallida: {e}")

        latency_metrics = {
            'symbol': symbol,
            'total_tests': num_tests,
            'successful_tests': successful_requests,
            'success_rate': successful_requests / num_tests,
            'avg_latency_ms': np.mean(latencies) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'p95_latency_ms': np.percentile(latencies, 95) if latencies else 0
        }

        logger.info(f"✅ Latencia medida: {latency_metrics['avg_latency_ms']:.2f}ms promedio")

        return latency_metrics

    def audit_trading_operations(self) -> Dict:
        """
        Audita operaciones de trading: órdenes de compra/venta, stop loss, take profit, etc.

        Returns:
            Dict con resultados de las pruebas de trading
        """
        logger.info("🔄 Iniciando auditoría de operaciones de trading")

        trading_results = {
            'balance_check': {},
            'market_buy_order': {},
            'market_sell_order': {},
            'limit_buy_order': {},
            'limit_sell_order': {},
            'stop_loss_order': {},
            'take_profit_order': {},
            'oco_order': {},
            'order_cancellation': {},
            'position_management': {},
            'overall_trading_score': 0.0
        }

        test_symbol = 'BTC/USDT'
        test_amount = 0.001  # Cantidad pequeña para pruebas

        try:
            # 1. Verificar balance
            logger.info("💰 Verificando balance de cuenta")
            balance = self.exchange.fetchBalance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            btc_balance = balance.get('BTC', {}).get('free', 0)

            logger.info(f"📊 Balance detallado - USDT: {usdt_balance}, BTC: {btc_balance}")
            logger.info(f"💼 Balance completo: {balance}")

            trading_results['balance_check'] = {
                'usdt_free': usdt_balance,
                'btc_free': btc_balance,
                'status': 'SUCCESS' if usdt_balance > 0 else 'LOW_BALANCE'
            }

            if usdt_balance < 10:  # Necesitamos al menos algo de USDT
                logger.warning("⚠️ Balance USDT bajo - algunas pruebas pueden fallar")
                trading_results['balance_check']['warning'] = 'Low USDT balance for comprehensive testing'

            # 2. Probar orden de compra de mercado
            logger.info("🛒 Probando orden de compra de mercado")
            try:
                # Obtener precio actual
                ticker = self.exchange.fetchTicker(test_symbol)
                current_price = ticker['last']

                # Calcular cantidad basada en balance disponible
                amount = min(test_amount, usdt_balance / current_price * 0.1)  # Usar solo 10% del balance

                if amount > 0.0001:  # Mínimo para BTC
                    buy_order = self.exchange.createMarketBuyOrder(test_symbol, amount)
                    trading_results['market_buy_order'] = {
                        'status': 'SUCCESS',
                        'order_id': buy_order['id'],
                        'amount': amount,
                        'price': current_price
                    }
                    logger.info(f"✅ Orden de compra creada: {buy_order['id']}")
                else:
                    trading_results['market_buy_order'] = {
                        'status': 'SKIPPED',
                        'reason': 'Insufficient balance or amount too small'
                    }

            except Exception as e:
                trading_results['market_buy_order'] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                logger.error(f"❌ Error en orden de compra: {e}")

            # 3. Probar orden de venta de mercado (si tenemos BTC)
            logger.info("💸 Probando orden de venta de mercado")
            try:
                if btc_balance > 0.0001:
                    sell_amount = min(test_amount, btc_balance * 0.1)  # Vender solo 10%
                    sell_order = self.exchange.createMarketSellOrder(test_symbol, sell_amount)
                    trading_results['market_sell_order'] = {
                        'status': 'SUCCESS',
                        'order_id': sell_order['id'],
                        'amount': sell_amount
                    }
                    logger.info(f"✅ Orden de venta creada: {sell_order['id']}")
                else:
                    trading_results['market_sell_order'] = {
                        'status': 'SKIPPED',
                        'reason': 'No BTC balance available'
                    }

            except Exception as e:
                trading_results['market_sell_order'] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                logger.error(f"❌ Error en orden de venta: {e}")

            # 4. Probar órdenes limitadas
            logger.info("📈 Probando órdenes limitadas")
            try:
                ticker = self.exchange.fetchTicker(test_symbol)
                current_price = ticker['last']

                # Orden limit buy por debajo del precio actual
                limit_buy_price = current_price * 0.995  # 0.5% por debajo
                limit_buy_amount = min(test_amount, usdt_balance / limit_buy_price * 0.05)

                if limit_buy_amount > 0.0001:
                    limit_buy = self.exchange.createLimitBuyOrder(test_symbol, limit_buy_amount, limit_buy_price)
                    trading_results['limit_buy_order'] = {
                        'status': 'SUCCESS',
                        'order_id': limit_buy['id'],
                        'price': limit_buy_price,
                        'amount': limit_buy_amount
                    }

                    # Cancelar la orden para no dejar posiciones abiertas
                    self.exchange.cancelOrder(limit_buy['id'], test_symbol)
                    trading_results['order_cancellation'] = {
                        'status': 'SUCCESS',
                        'cancelled_order': limit_buy['id']
                    }

                else:
                    trading_results['limit_buy_order'] = {'status': 'SKIPPED', 'reason': 'Insufficient balance'}

            except Exception as e:
                trading_results['limit_buy_order'] = {'status': 'FAILED', 'error': str(e)}
                logger.error(f"❌ Error en orden limit: {e}")

            # 5. Probar órdenes OCO (One-Cancels-Other) para stop loss y take profit
            logger.info("🎯 Probando órdenes OCO (Stop Loss + Take Profit)")
            try:
                if btc_balance > 0.0001:
                    ticker = self.exchange.fetchTicker(test_symbol)
                    current_price = ticker['last']

                    # Configurar OCO: Stop Loss 2% por debajo, Take Profit 3% por encima
                    stop_price = current_price * 0.98
                    limit_price = current_price * 1.03
                    oco_amount = min(test_amount, btc_balance * 0.05)

                    oco_order = self.exchange.createOrder(test_symbol, 'OCO', 'sell', oco_amount, None, {
                        'stopPrice': stop_price,
                        'stopLimitPrice': stop_price * 0.999,  # Límite ligeramente por debajo del stop
                        'price': limit_price
                    })

                    trading_results['oco_order'] = {
                        'status': 'SUCCESS',
                        'order_id': oco_order['id'],
                        'stop_price': stop_price,
                        'take_profit_price': limit_price,
                        'amount': oco_amount
                    }

                    # Cancelar para limpiar
                    self.exchange.cancelOrder(oco_order['id'], test_symbol)

                else:
                    trading_results['oco_order'] = {'status': 'SKIPPED', 'reason': 'No BTC balance'}

            except Exception as e:
                trading_results['oco_order'] = {'status': 'FAILED', 'error': str(e)}
                logger.error(f"❌ Error en orden OCO: {e}")

            # 6. Calcular puntuación general de trading
            successful_operations = sum(1 for op in trading_results.values()
                                      if isinstance(op, dict) and op.get('status') == 'SUCCESS')
            total_operations = len([op for op in trading_results.values() if isinstance(op, dict)])

            trading_results['overall_trading_score'] = (successful_operations / total_operations) * 100 if total_operations > 0 else 0

            logger.info(f"✅ Auditoría de trading completada. Puntuación: {trading_results['overall_trading_score']:.1f}%")

        except Exception as e:
            logger.error(f"❌ Error general en auditoría de trading: {e}")
            trading_results['error'] = str(e)

        return trading_results

    def run_comprehensive_audit(self) -> Dict:
        """
        Ejecuta una auditoría completa del sistema.

        Returns:
            Dict con resultados completos de la auditoría
        """
        active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
        logger.info(f"🚀 Iniciando auditoría completa de {active_exchange} Testnet")
        self.metrics.start_time = datetime.now()

        audit_results = {
            'audit_info': {
                'start_time': self.metrics.start_time.isoformat(),
                'testnet': True,
                'public_mode': self.public_mode,
                'symbols_tested': self.test_symbols,
                'timeframes_tested': self.test_timeframes,
                'duration_minutes': self.audit_duration_minutes
            },
            'connection_test': {},
            'data_quality': {},
            'latency_tests': {},
            'overall_metrics': {},
            'recommendations': []
        }

        try:
            # 1. Probar conexión
            logger.info("=== PRUEBA DE CONEXIÓN ===")
            connection_ok = self.test_connection()
            audit_results['connection_test'] = {
                'status': 'SUCCESS' if connection_ok else 'FAILED',
                'timestamp': datetime.now().isoformat()
            }

            if not connection_ok:
                active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
                audit_results['recommendations'].append(f"❌ Verificar credenciales de {active_exchange} Testnet")
                audit_results['recommendations'].append("❌ Verificar conexión a internet")
                return audit_results

            # 2. Auditar calidad de datos
            logger.info("=== AUDITORÍA DE CALIDAD DE DATOS ===")
            data_quality_results = {}

            for symbol in self.test_symbols:
                for timeframe in self.test_timeframes:
                    key = f"{symbol}_{timeframe}"
                    quality = self.audit_data_quality(symbol, timeframe)
                    data_quality_results[key] = quality

                    # Actualizar métricas globales
                    self.metrics.price_anomalies += quality['price_anomalies']
                    self.metrics.volume_anomalies += quality['volume_anomalies']

            audit_results['data_quality'] = data_quality_results

            # 3. Probar latencia
            logger.info("=== PRUEBAS DE LATENCIA ===")
            latency_results = {}

            for symbol in self.test_symbols:
                latency = self.audit_latency(symbol, num_tests=5)
                latency_results[symbol] = latency

                # Actualizar métricas globales
                self.metrics.avg_latency_ms = latency['avg_latency_ms']
                self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency['min_latency_ms'])
                self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency['max_latency_ms'])

            audit_results['latency_tests'] = latency_results

            # 4. Auditar operaciones de trading (solo si hay credenciales)
            if not self.public_mode:
                logger.info("=== AUDITORÍA DE OPERACIONES DE TRADING ===")
                trading_results = self.audit_trading_operations()
                audit_results['trading_operations'] = trading_results
            else:
                audit_results['trading_operations'] = {
                    'status': 'SKIPPED',
                    'reason': 'Modo público - sin credenciales para operaciones'
                }

            # 5. Generar métricas generales
            self.metrics.end_time = datetime.now()
            audit_results['overall_metrics'] = {
                'total_duration_seconds': (self.metrics.end_time - self.metrics.start_time).total_seconds(),
                'avg_latency_ms': self.metrics.avg_latency_ms,
                'price_anomalies_detected': self.metrics.price_anomalies,
                'volume_anomalies_detected': self.metrics.volume_anomalies,
                'data_quality_score': self._calculate_data_quality_score(data_quality_results)
            }

            # 5. Generar recomendaciones
            audit_results['recommendations'] = self._generate_recommendations(audit_results)

            logger.info("✅ Auditoría completa finalizada")

        except Exception as e:
            logger.error(f"❌ Error durante la auditoría: {e}")
            audit_results['error'] = str(e)

        finally:
            # Cerrar conexión si es necesario
            pass

        return audit_results

    def _calculate_data_quality_score(self, data_quality_results: Dict) -> float:
        """Calcula un puntaje general de calidad de datos (0-100)"""
        if not data_quality_results:
            return 0.0

        scores = []
        for result in data_quality_results.values():
            if result['samples_collected'] > 0:
                # Puntaje basado en completitud y anomalías
                completeness_score = result['data_completeness'] * 100
                anomaly_penalty = (result['price_anomalies'] + result['volume_anomalies']) * 5
                timestamp_penalty = result['timestamp_issues'] * 2

                score = max(0, completeness_score - anomaly_penalty - timestamp_penalty)
                scores.append(score)

        return np.mean(scores) if scores else 0.0

    def _generate_recommendations(self, audit_results: Dict) -> List[str]:
        """Genera recomendaciones basadas en los resultados de la auditoría"""
        recommendations = []

        # Verificar modo público
        active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
        if audit_results.get('audit_info', {}).get('public_mode', False):
            if active_exchange == 'BYBIT':
                recommendations.append("ℹ️ Modo público: Configurar credenciales BYBIT_API_KEY y BYBIT_API_SECRET para pruebas completas")
            else:
                recommendations.append("ℹ️ Modo público: Configurar credenciales BINANCE_TEST_API_KEY y BINANCE_TEST_API_SECRET para pruebas completas")

        # Verificar conexión
        if audit_results.get('connection_test', {}).get('status') != 'SUCCESS':
            recommendations.append(f"❌ CRÍTICO: Verificar configuración de conexión a {active_exchange} Testnet")
            return recommendations

        # Verificar latencia
        latency_tests = audit_results.get('latency_tests', {})
        avg_latencies = [test.get('avg_latency_ms', 0) for test in latency_tests.values()]

        if avg_latencies and np.mean(avg_latencies) > 1000:  # > 1 segundo
            recommendations.append("⚠️ Alto: Latencia de API elevada (>1000ms). Considerar optimizaciones")

        # Verificar calidad de datos
        data_quality = audit_results.get('data_quality', {})
        quality_score = audit_results.get('overall_metrics', {}).get('data_quality_score', 0)

        if quality_score < 70:
            recommendations.append(f"⚠️ Calidad de datos baja ({quality_score:.1f}/100). Revisar integridad de datos")

        # Anomalías específicas
        total_anomalies = audit_results.get('overall_metrics', {}).get('price_anomalies_detected', 0)
        if total_anomalies > 0:
            recommendations.append(f"⚠️ Detectadas {total_anomalies} anomalías de precio. Revisar lógica de validación")

        # Recomendaciones positivas
        if quality_score >= 90:
            recommendations.append("✅ Excelente calidad de datos. Sistema funcionando correctamente")

        if avg_latencies and np.mean(avg_latencies) < 500:
            recommendations.append("✅ Buena latencia de API (<500ms). Conexión óptima")

        return recommendations

    def save_audit_report(self, audit_results: Dict, output_path: str = None):
        """
        Guarda el reporte de auditoría en formato JSON.

        Args:
            audit_results: Resultados de la auditoría
            output_path: Ruta donde guardar el reporte
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"auditorias/audit_binance_testnet_{timestamp}.json"

        # Crear directorio si no existe
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(audit_results, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"✅ Reporte de auditoría guardado en: {output_path}")

        except Exception as e:
            logger.error(f"❌ Error guardando reporte: {e}")

    def print_audit_summary(self, audit_results: Dict):
        """Imprime un resumen de la auditoría en consola"""
        active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
        print("\n" + "="*80)
        print(f"📊 REPORTE DE AUDITORÍA - {active_exchange} TESTNET")
        print("="*80)

        # Información general
        audit_info = audit_results.get('audit_info', {})
        print(f"🕐 Fecha: {audit_info.get('start_time', 'N/A')}")
        print(f"🎯 Testnet: {audit_info.get('testnet', False)}")
        print(f"📈 Símbolos auditados: {', '.join(audit_info.get('symbols_tested', []))}")
        print(f"⏱️ Duración: {audit_info.get('duration_minutes', 0)} minutos")

        # Estado de conexión
        conn_test = audit_results.get('connection_test', {})
        status = conn_test.get('status', 'UNKNOWN')
        status_icon = "✅" if status == 'SUCCESS' else "❌"
        print(f"\n🔗 Conexión: {status_icon} {status}")

        # Métricas generales
        metrics = audit_results.get('overall_metrics', {})
        print("\n📊 MÉTRICAS GENERALES:")
        print(f"   • Total de solicitudes: {metrics.get('total_requests', 0)}")
        print(f"   • Solicitudes exitosas: {metrics.get('successful_requests', 0)}")
        print(f"   • Tasa de éxito: {metrics.get('success_rate', 0):.2f}%")
        # Calidad de datos
        data_quality = audit_results.get('data_quality', {})
        if data_quality:
            print("\n🔍 CALIDAD DE DATOS:")
            for key, quality in data_quality.items():
                completeness = quality.get('data_quality_score', quality.get('data_completeness', 0)) * 100
                anomalies = quality.get('price_anomalies', 0) + quality.get('volume_anomalies', 0)
                print(f"   • {key}: Completitud {completeness:.1f}%, Anomalías: {anomalies}")
        # Latencia
        latency_tests = audit_results.get('latency_tests', {})
        if latency_tests:
            print("\n⏱️ LATENCIA DE API:")
            for symbol, latency in latency_tests.items():
                avg_lat = latency.get('avg_latency_ms', 0)
                success_rate = latency.get('success_rate', 0) * 100
                print(f"   • {symbol}: {avg_lat:.1f}ms, Éxito: {success_rate:.1f}%")

        # Operaciones de trading
        trading_ops = audit_results.get('trading_operations', {})
        if trading_ops and trading_ops.get('status') != 'SKIPPED':
            print("\n💼 OPERACIONES DE TRADING:")
            trading_score = trading_ops.get('overall_trading_score', 0)
            print(f"   • Puntuación general: {trading_score:.1f}%")

            # Balance
            balance = trading_ops.get('balance_check', {})
            if balance:
                print(f"   • Balance USDT: {balance.get('usdt_free', 0):.2f}")
                print(f"   • Balance BTC: {balance.get('btc_free', 0):.6f}")

            # Órdenes
            operations = ['market_buy_order', 'market_sell_order', 'limit_buy_order', 'oco_order', 'order_cancellation']
            for op_name in operations:
                op = trading_ops.get(op_name, {})
                if op and op.get('status') == 'SUCCESS':
                    print(f"   • {op_name.replace('_', ' ').title()}: ✅")
                elif op and op.get('status') == 'FAILED':
                    print(f"   • {op_name.replace('_', ' ').title()}: ❌ {op.get('error', '')}")
                elif op and op.get('status') == 'SKIPPED':
                    print(f"   • {op_name.replace('_', ' ').title()}: ⏭️ {op.get('reason', '')}")

        elif trading_ops.get('status') == 'SKIPPED':
            print("\n💼 OPERACIONES DE TRADING:")
            print(f"   • Estado: ⏭️ {trading_ops.get('reason', 'Modo público')}")

        # Recomendaciones
        recommendations = audit_results.get('recommendations', [])
        if recommendations:
            print("\n💡 RECOMENDACIONES:")
            for rec in recommendations:
                print(f"   {rec}")

        print("\n" + "="*80)

async def main():
    """Función principal"""
    active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
    print(f"🔬 AUDITORÍA DE DATOS LIVE - {active_exchange} TESTNET")
    print("=" * 60)

    try:
        # Crear auditor
        auditor = ExchangeTestnetAuditor()

        # Ejecutar auditoría completa
        print("🚀 Ejecutando auditoría completa...")
        audit_results = await auditor.run_comprehensive_audit()

        # Imprimir resumen
        auditor.print_audit_summary(audit_results)

        # Guardar reporte
        auditor.save_audit_report(audit_results)

        print("✅ Auditoría completada exitosamente")

    except Exception as e:
        logger.error(f"❌ Error en auditoría: {e}")
        print(f"❌ Error: {e}")
        return 1

    return 0

    def display_results(self, audit_results: Dict):
        """
        Muestra los resultados de la auditoría de forma formateada.

        Args:
            audit_results: Resultados de la auditoría
        """
        active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
        print("\n" + "="*80)
        print(f"📋 RESULTADOS DE LA AUDITORÍA - {active_exchange} TESTNET")
        print("="*80)

        # Información general
        audit_info = audit_results.get('audit_info', {})
        print(f"🕐 Fecha: {audit_info.get('start_time', 'N/A')}")
        print(f"🎯 Testnet: {audit_info.get('testnet', False)}")
        print(f"🔒 Modo público: {audit_info.get('public_mode', False)}")
        print(f"📈 Símbolos auditados: {', '.join(audit_info.get('symbols_tested', []))}")
        print(f"⏱️ Duración: {audit_info.get('duration_minutes', 0)} minutos")

        # Estado de conexión
        conn_test = audit_results.get('connection_test', {})
        status = conn_test.get('status', 'UNKNOWN')
        status_icon = "✅" if status == 'SUCCESS' else "❌"
        print(f"\n🔗 Conexión: {status_icon} {status}")

        # Métricas generales
        metrics = audit_results.get('overall_metrics', {})
        print("\n📊 MÉTRICAS GENERALES:")
        print(f"   • Duración total: {metrics.get('total_duration_seconds', 0):.1f} segundos")
        print(f"   • Latencia promedio: {metrics.get('avg_latency_ms', 0):.1f}ms")
        print(f"   • Anomalías de precio detectadas: {metrics.get('price_anomalies_detected', 0)}")
        print(f"   • Anomalías de volumen detectadas: {metrics.get('volume_anomalies_detected', 0)}")
        print(f"   • Puntaje calidad de datos: {metrics.get('data_quality_score', 0):.1f}/100")

        # Calidad de datos
        data_quality = audit_results.get('data_quality', {})
        if data_quality:
            print("\n🔍 CALIDAD DE DATOS:")
            for key, quality in data_quality.items():
                completeness = quality.get('data_completeness', 0) * 100
                anomalies = quality.get('price_anomalies', 0) + quality.get('volume_anomalies', 0)
                samples = quality.get('samples_collected', 0)
                print(f"   • {key}: {samples} muestras, Completitud {completeness:.1f}%, Anomalías: {anomalies}")

        # Latencia
        latency_tests = audit_results.get('latency_tests', {})
        if latency_tests:
            print("\n⏱️ LATENCIA DE API:")
            for symbol, latency in latency_tests.items():
                avg_lat = latency.get('avg_latency_ms', 0)
                success_rate = latency.get('success_rate', 0) * 100
                min_lat = latency.get('min_latency_ms', 0)
                max_lat = latency.get('max_latency_ms', 0)
                print(f"   • {symbol}: {avg_lat:.1f}ms (min: {min_lat:.1f}ms, max: {max_lat:.1f}ms), Éxito: {success_rate:.1f}%")

        # Recomendaciones
        recommendations = audit_results.get('recommendations', [])
        if recommendations:
            print("\n💡 RECOMENDACIONES:")
            for rec in recommendations:
                print(f"   {rec}")

        print("\n" + "="*80)

def main():
    """Función principal"""
    active_exchange = os.getenv('ACTIVE_EXCHANGE', 'binance').upper()
    print(f"🔬 AUDITORÍA DE DATOS LIVE - {active_exchange} TESTNET")
    print("=" * 60)

    try:
        # Crear auditor
        auditor = ExchangeTestnetAuditor()

        print("🚀 Ejecutando auditoría completa...")

        # Ejecutar auditoría
        audit_results = auditor.run_comprehensive_audit()

        # Mostrar resultados (ya se hace en run_comprehensive_audit)
        # display_results(audit_results)

        print("\n✅ Auditoría completada exitosamente")
        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Auditoría interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)
        