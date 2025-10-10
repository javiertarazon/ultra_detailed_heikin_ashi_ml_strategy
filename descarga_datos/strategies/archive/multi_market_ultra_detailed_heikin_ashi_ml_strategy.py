#!/usr/bin/env python3
"""
MULTI-MARKET ULTRA-DETAILED HEIKIN ASHI STRATEGY WITH REAL ML MODELS
======================================================================

Estrategia ultra-optimizada adaptable a múltiples mercados financieros:
- Forex (pares de divisas)
- Commodities (oro, petróleo, etc.)
- Acciones individuales
- Símbolos sintéticos con comportamiento similar a crypto

CARACTERÍSTICAS ADAPTATIVAS:
- Parámetros específicos por tipo de mercado
- Indicadores ajustados a características de cada mercado
- Gestión de riesgo adaptada a volatilidad y spreads
- Timeframes optimizados por mercado
- Modelos ML re-entrenados por mercado

REQUIERE: Datos históricos suficientes para entrenamiento ML (>100 muestras)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import talib
from datetime import datetime, timedelta
import os
import pickle
import joblib
import warnings
warnings.filterwarnings('ignore')

from models.model_manager import ModelManager

class MultiMarketMLModelManager:
    """
    Gestor de modelos ML adaptado para múltiples mercados
    """

    def __init__(self, model_dir: str = None, config: dict = None):
        self.model_manager = ModelManager(model_dir)
        self.model_dir = self.model_manager.model_dir
        self.models = {}
        self.scalers = {}
        self.config = config

        # Configuraciones específicas por mercado
        self.market_configs = {
            'forex': {
                'volatility_multiplier': 0.3,  # Forex menos volátil que crypto
                'spread_adjustment': 0.0001,   # Spreads muy bajos (0.01%)
                'timeframe_preference': '1h',  # Forex funciona mejor en 1h
                'volume_importance': 0.7,      # Menos importancia al volumen
                'trend_periods': [21, 50, 200] # Períodos más largos para tendencias
            },
            'commodities': {
                'volatility_multiplier': 0.8,  # Commodities volátiles pero predecibles
                'spread_adjustment': 0.0002,   # Spreads moderados
                'timeframe_preference': '4h',  # 4h funciona bien
                'volume_importance': 1.0,      # Volumen muy importante
                'trend_periods': [50, 100, 200] # Tendencias largas
            },
            'stocks': {
                'volatility_multiplier': 0.5,  # Acciones moderadamente volátiles
                'spread_adjustment': 0.0003,   # Spreads variables
                'timeframe_preference': '1d',  # Timeframe diario para acciones
                'volume_importance': 1.2,      # Volumen crítico
                'trend_periods': [50, 100, 200] # Análisis técnico clásico
            },
            'synthetic': {
                'volatility_multiplier': 1.0,  # Similar a crypto
                'spread_adjustment': 0.0005,   # Spreads moderados
                'timeframe_preference': '4h',  # Similar a crypto
                'volume_importance': 0.9,      # Importancia moderada
                'trend_periods': [21, 50, 100] # Mixto
            },
            'crypto': {  # Configuración original para crypto
                'volatility_multiplier': 1.0,
                'spread_adjustment': 0.001,
                'timeframe_preference': '4h',
                'volume_importance': 1.0,
                'trend_periods': [21, 50, 100]
            }
        }

    def detect_market_type(self, symbol: str) -> str:
        """
        Detectar automáticamente el tipo de mercado basado en el símbolo
        """
        symbol_upper = symbol.upper()

        # Forex: pares como EUR/USD, GBP/JPY, etc.
        if any(curr in symbol_upper for curr in ['EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']) and '/' in symbol:
            currencies = symbol_upper.split('/')
            if len(currencies) == 2 and all(len(curr) == 3 for curr in currencies):
                return 'forex'

        # Commodities: símbolos conocidos
        commodities = ['XAU/USD', 'XAG/USD', 'WTI', 'BRENT', 'COFFEE', 'SUGAR', 'COTTON']
        if any(comm in symbol_upper for comm in commodities):
            return 'commodities'

        # Stocks: símbolos sin '/', o con sufijos comunes de bolsa
        if '/' not in symbol and len(symbol) <= 5:
            return 'stocks'

        # Synthetic: índices sintéticos o CFDs
        synthetic_indicators = ['VOL', 'SYNTH', 'CFD', 'INDEX']
        if any(ind in symbol_upper for ind in synthetic_indicators):
            return 'synthetic'

        # Default: crypto
        return 'crypto'

    def get_market_config(self, symbol: str) -> dict:
        """
        Obtener configuración específica del mercado
        """
        market_type = self.detect_market_type(symbol)
        return self.market_configs.get(market_type, self.market_configs['crypto'])

    def prepare_features_adaptive(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Preparar features adaptados al tipo de mercado
        """
        from indicators.technical_indicators import TechnicalIndicators

        market_config = self.get_market_config(symbol)
        indicator = TechnicalIndicators(self.config)
        df = data.copy()

        # Calcular indicadores base
        df = indicator.calculate_all_indicators(df)

        # Features adaptativos al mercado
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # Volatilidad ajustada por mercado
        volatility_window = 20
        df['volatility'] = df['returns'].rolling(window=volatility_window).std() * market_config['volatility_multiplier']

        # Heikin Ashi (adaptado)
        df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        df['ha_open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
        df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
        df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)

        # Momentum adaptado
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)

        # Price position con períodos adaptados
        trend_period = market_config['trend_periods'][0]
        df['price_position'] = (df['close'] - df['close'].rolling(trend_period).min()) / \
                              (df['close'].rolling(trend_period).max() - df['close'].rolling(trend_period).min())

        # Volume ratio con importancia ajustada
        volume_window = 20
        df['volume_ratio'] = (df['volume'] / df['volume'].rolling(volume_window).mean()) * market_config['volume_importance']

        # Trend strength adaptado
        ema_short = df['close'].ewm(span=market_config['trend_periods'][0]).mean()
        ema_long = df['close'].ewm(span=market_config['trend_periods'][1]).mean()
        df['trend_strength'] = abs(ema_short - ema_long) / df['atr']

        # Spread adjustment para mercados con spreads
        if market_config['spread_adjustment'] > 0:
            df['spread_adjusted_returns'] = df['returns'] - market_config['spread_adjustment']

        return df.fillna(method='bfill').fillna(0)


class MultiMarketUltraDetailedHeikinAshiMLStrategy:
    """
    Estrategia ultra-detallada adaptable a múltiples mercados financieros
    """

    def __init__(self, config=None):
        if config is None:
            from config.config import load_config_from_yaml
            config = load_config_from_yaml()
        elif hasattr(config, 'backtesting'):
            pass
        else:
            self.config = config

        # Extraer parámetros con valores por defecto
        self.symbol = self.config.get('symbol', 'EUR/USD')
        self.timeframe = self.config.get('timeframe', '1h')

        # Detectar tipo de mercado automáticamente
        self.market_type = self._detect_market_type(self.symbol)
        print(f"🧠 Mercado detectado: {self.market_type.upper()} para {self.symbol}")

        # Parámetros ML adaptados por mercado
        self.ml_threshold = self._get_market_ml_threshold()
        self.stoch_overbought = self._get_market_stoch_levels()[0]
        self.stoch_oversold = self._get_market_stoch_levels()[1]

        # Cargar parámetros específicos del símbolo y mercado
        self._load_market_specific_params(config)

        # Gestión de riesgo adaptada al mercado
        self.max_drawdown = self._get_market_risk_limits()[0]
        self.max_portfolio_heat = self._get_market_risk_limits()[1]
        self.max_concurrent_trades = self._get_market_concurrent_trades()
        self.kelly_fraction = self._get_market_kelly_fraction()

        # Estado interno
        self.active_trades = []
        self.portfolio_value = 10000.0
        self.current_drawdown = 0.0

        # Inicializar gestor de modelos ML multi-mercado
        self.ml_manager = MultiMarketMLModelManager(config=self.config)

    def _detect_market_type(self, symbol: str) -> str:
        """Detectar tipo de mercado"""
        return self.ml_manager.detect_market_type(symbol)

    def _get_market_ml_threshold(self) -> float:
        """Threshold ML adaptado por mercado"""
        thresholds = {
            'forex': 0.55,      # Forex más conservador
            'commodities': 0.60, # Commodities moderado
            'stocks': 0.65,     # Acciones necesitan más confianza
            'synthetic': 0.50,  # Similar a crypto
            'crypto': 0.50      # Original
        }
        return thresholds.get(self.market_type, 0.50)

    def _get_market_stoch_levels(self) -> Tuple[int, int]:
        """Niveles Stochastic adaptados por mercado"""
        levels = {
            'forex': (80, 20),        # Forex más conservador
            'commodities': (75, 25),  # Commodities moderado
            'stocks': (70, 30),       # Acciones clásico
            'synthetic': (85, 15),    # Similar a crypto
            'crypto': (85, 15)        # Original
        }
        return levels.get(self.market_type, (85, 15))

    def _get_market_risk_limits(self) -> Tuple[float, float]:
        """Límites de riesgo por mercado"""
        limits = {
            'forex': (0.03, 0.04),      # Forex más conservador
            'commodities': (0.05, 0.06), # Commodities moderado
            'stocks': (0.04, 0.05),     # Acciones balanceado
            'synthetic': (0.08, 0.10),  # Similar a crypto
            'crypto': (0.08, 0.10)      # Original
        }
        return limits.get(self.market_type, (0.08, 0.10))

    def _get_market_concurrent_trades(self) -> int:
        """Trades concurrentes por mercado"""
        limits = {
            'forex': 5,        # Forex permite más trades
            'commodities': 3,  # Commodities moderado
            'stocks': 2,       # Acciones más conservador
            'synthetic': 4,    # Similar a crypto
            'crypto': 4        # Original
        }
        return limits.get(self.market_type, 4)

    def _get_market_kelly_fraction(self) -> float:
        """Kelly fraction por mercado"""
        fractions = {
            'forex': 0.2,      # Forex más conservador
            'commodities': 0.3, # Commodities moderado
            'stocks': 0.25,    # Acciones balanceado
            'synthetic': 0.35, # Similar a crypto
            'crypto': 0.35     # Original
        }
        return fractions.get(self.market_type, 0.35)

    def _load_market_specific_params(self, config):
        """
        Cargar parámetros específicos del mercado y símbolo
        """
        # Parámetros base adaptados por mercado
        base_params = {
            'forex': {
                'volume_threshold': 0.8,    # Menos énfasis en volumen
                'atr_multiplier': 2.0,      # ATR más conservador
                'stop_loss_pct': 0.005,     # Stop loss más ajustado (0.5%)
                'take_profit_pct': 0.015,   # Take profit más realista (1.5%)
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'atr_period': 14,
                'atr_volatility_threshold': 1.5,
                'ema_trend_period': 50,
                'max_consecutive_losses': 5,  # Más tolerancia
                'min_trend_strength': 0.3,
                'sar_acceleration': 0.02,
                'sar_maximum': 0.2,
                'stop_loss_atr_multiplier': 2.5,
                'take_profit_atr_multiplier': 4.0,
                'trailing_stop_atr_multiplier': 1.2,
                'volatility_filter_threshold': 0.005,
                'volume_sma_period': 20,
                'volume_threshold': 100
            },
            'commodities': {
                'volume_threshold': 1.5,
                'atr_multiplier': 3.0,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.06,
                'rsi_overbought': 75,
                'rsi_oversold': 25,
                'atr_period': 20,
                'atr_volatility_threshold': 2.5,
                'ema_trend_period': 100,
                'max_consecutive_losses': 3,
                'min_trend_strength': 0.7,
                'sar_acceleration': 0.05,
                'sar_maximum': 0.15,
                'stop_loss_atr_multiplier': 3.0,
                'take_profit_atr_multiplier': 6.0,
                'trailing_stop_atr_multiplier': 1.8,
                'volatility_filter_threshold': 0.02,
                'volume_sma_period': 30,
                'volume_threshold': 5000
            },
            'stocks': {
                'volume_threshold': 1.2,
                'atr_multiplier': 2.5,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.08,
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'atr_period': 20,
                'atr_volatility_threshold': 2.0,
                'ema_trend_period': 100,
                'max_consecutive_losses': 2,
                'min_trend_strength': 0.6,
                'sar_acceleration': 0.03,
                'sar_maximum': 0.18,
                'stop_loss_atr_multiplier': 2.8,
                'take_profit_atr_multiplier': 5.0,
                'trailing_stop_atr_multiplier': 1.5,
                'volatility_filter_threshold': 0.015,
                'volume_sma_period': 50,
                'volume_threshold': 10000
            },
            'synthetic': {
                'volume_threshold': 1.1,
                'atr_multiplier': 3.2,
                'stop_loss_pct': 0.08,
                'take_profit_pct': 0.18,
                'rsi_overbought': 72,
                'rsi_oversold': 28,
                'atr_period': 16,
                'atr_volatility_threshold': 2.2,
                'ema_trend_period': 60,
                'max_consecutive_losses': 4,
                'min_trend_strength': 0.5,
                'sar_acceleration': 0.04,
                'sar_maximum': 0.12,
                'stop_loss_atr_multiplier': 3.0,
                'take_profit_atr_multiplier': 5.2,
                'trailing_stop_atr_multiplier': 1.4,
                'volatility_filter_threshold': 0.025,
                'volume_sma_period': 25,
                'volume_threshold': 2000
            },
            'crypto': {  # Parámetros originales
                'volume_threshold': 1.3,
                'atr_multiplier': 3.4,
                'stop_loss_pct': 0.09,
                'take_profit_pct': 0.19,
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'stoch_overbought': 85,
                'stoch_oversold': 35,
                'atr_period': 14,
                'atr_volatility_threshold': 2.0,
                'ema_trend_period': 50,
                'max_consecutive_losses': 3,
                'min_trend_strength': 0.5,
                'sar_acceleration': 0.06,
                'sar_maximum': 0.11,
                'stop_loss_atr_multiplier': 3.25,
                'take_profit_atr_multiplier': 5.5,
                'trailing_stop_atr_multiplier': 1.5,
                'volatility_filter_threshold': 0.03,
                'volume_sma_period': 20,
                'volume_threshold': 1000
            }
        }

        # Obtener parámetros base del mercado
        default_params = base_params.get(self.market_type, base_params['crypto'])

        # Intentar cargar parámetros específicos del símbolo desde configuración
        symbol_params = {}
        if config and hasattr(config, 'backtesting'):
            backtesting_config = config.backtesting
            if hasattr(backtesting_config, 'optimized_parameters'):
                opt_params = backtesting_config.optimized_parameters
                symbol_key = self.symbol.replace('/', '_').replace('.', '_')
                if hasattr(opt_params, symbol_key):
                    symbol_section = getattr(opt_params, symbol_key)
                    if hasattr(symbol_section, self.timeframe):
                        timeframe_section = getattr(symbol_section, self.timeframe)
                        if hasattr(timeframe_section, '__dict__'):
                            symbol_params = timeframe_section.__dict__
                        elif hasattr(timeframe_section, 'items'):
                            symbol_params = dict(timeframe_section)

        # Aplicar parámetros: config directa > símbolo específico > mercado default
        for param_name, default_value in default_params.items():
            value = self.config.get(param_name,
                                   symbol_params.get(param_name, default_value))
            setattr(self, param_name, value)

        print(f"📊 Parámetros {self.market_type.upper()} cargados para {self.symbol}:")
        print(f"   ML Threshold: {self.ml_threshold}, ATR Stop Loss: {self.stop_loss_atr_multiplier}")
        print(f"   Max Drawdown: {self.max_drawdown}, Concurrent Trades: {self.max_concurrent_trades}")

    def run(self, data: pd.DataFrame, symbol: str, timeframe: str = None) -> Dict:
        """
        Ejecutar estrategia multi-mercado con ML real
        """
        try:
            print(f"[START] Multi-Market Strategy {self.market_type.upper()} para {symbol}")

            if timeframe:
                self.timeframe = timeframe

            # Validar datos mínimos
            if len(data) < 100:
                raise ValueError(f"Datos insuficientes: {len(data)} filas. Necesario mínimo 100.")

            # Preparar datos con indicadores adaptados al mercado
            data_processed = self._prepare_data_adaptive(data)
            print(f"Datos preparados: {len(data_processed)} filas con indicadores {self.market_type}")

            # Verificar modelos ML
            optimization_mode = getattr(self, '_optimization_mode', False)

            if optimization_mode:
                print(f"🎯 MODO OPTIMIZACIÓN: Usando modelos ML pre-entrenados para {symbol}")
                model_exists = self.ml_manager.load_model(symbol, 'random_forest')[0] is not None
                if not model_exists:
                    raise ValueError(f"Modelos ML no encontrados para {symbol} en modo optimización")
            else:
                model_exists = self.ml_manager.load_model(symbol, 'random_forest')[0] is not None
                if not model_exists:
                    print(f"⚠️  Entrenando modelos ML para mercado {self.market_type}...")
                    self.ml_manager.train_models(data_processed, symbol)
                    print("✅ Modelos ML entrenados y guardados")

            # Generar predicciones ML adaptadas al mercado
            print(f"Generando predicciones ML para mercado {self.market_type}...")
            ml_confidence_cached = self.ml_manager.predict_signal(data_processed, symbol, 'random_forest')
            print(f"Predicciones ML: confianza {ml_confidence_cached.min():.3f} - {ml_confidence_cached.max():.3f}")

            # Generar señales con filtros adaptados al mercado
            signals = self._generate_signals_adaptive(data_processed, symbol, ml_confidence_cached)

            # Ejecutar backtesting con gestión de riesgo adaptada
            results = self._run_backtest_adaptive(data_processed, signals, symbol, ml_confidence_cached)
            print(f"[RESULT] Backtesting completado: {results['total_trades']} trades, P&L: ${results['total_pnl']:.2f}")

            return results

        except Exception as e:
            print(f"[ERROR] Error en Multi-Market Strategy: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_results(symbol)

    def _prepare_data_adaptive(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preparar datos con indicadores adaptados al mercado"""

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Columnas requeridas faltantes: {missing_cols}")

        print(f"[CALC] Calculando indicadores para mercado {self.market_type.upper()}...")

        # Usar el método adaptativo del ML manager
        data = self.ml_manager.prepare_features_adaptive(data, self.symbol)

        # Calcular indicadores específicos del mercado
        if self.market_type == 'forex':
            # Forex: énfasis en tendencias y correlaciones
            data['ema_21'] = talib.EMA(data['close'], timeperiod=21)
            data['ema_50'] = talib.EMA(data['close'], timeperiod=50)
            data['trend_strength'] = abs(data['ema_21'] - data['ema_50']) / data['atr']

        elif self.market_type == 'commodities':
            # Commodities: énfasis en momentum y volumen
            data['roc'] = talib.ROC(data['close'], timeperiod=14)
            data['momentum'] = talib.MOM(data['close'], timeperiod=10)
            data['volume_oscillator'] = (data['volume'] - data['volume'].rolling(20).mean()) / data['volume'].rolling(20).std()

        elif self.market_type == 'stocks':
            # Stocks: análisis técnico clásico
            data['sma_50'] = talib.SMA(data['close'], timeperiod=50)
            data['sma_200'] = talib.SMA(data['close'], timeperiod=200)
            data['golden_cross'] = (data['sma_50'] > data['sma_200']).astype(int)

        # Validar y limpiar datos
        critical_indicators = ['ha_close', 'atr', 'rsi']
        nan_counts = data[critical_indicators].isna().sum()
        total_critical_nans = nan_counts.sum()
        max_allowed_nans = len(data) * 0.05

        if total_critical_nans > max_allowed_nans:
            print(f"⚠️ NaN detectados: {nan_counts.to_dict()}")
            data = data.dropna(subset=critical_indicators)

        if len(data) < 50:
            raise ValueError(f"Datos insuficientes después de limpieza: {len(data)} filas")

        data = data.fillna(method='bfill').fillna(method='ffill').fillna(0)
        print(f"Datos preparados: {len(data)} filas válidas para {self.market_type}")

        return data

    def _generate_signals_adaptive(self, data: pd.DataFrame, symbol: str, ml_confidence: pd.Series) -> pd.Series:
        """
        Generar señales adaptadas al tipo de mercado
        """
        signals = pd.Series(0, index=data.index, name='signal')

        if ml_confidence is None:
            raise ValueError("ML confidence requerido")

        long_signals = 0
        short_signals = 0

        for i in range(1, len(data)):
            ml_conf = ml_confidence.iloc[i]
            if ml_conf < self.ml_threshold:
                continue

            # Filtros base de Heikin Ashi
            ha_change_long = data['ha_color_change'].iloc[i] == 1
            ha_change_short = data['ha_color_change'].iloc[i] == -1

            # Filtros adaptados por mercado
            if self.market_type == 'forex':
                # Forex: más conservador, énfasis en tendencias
                rsi_ok = 25 < data['rsi'].iloc[i] < 75
                stoch_ok = 20 < data['stoch_k'].iloc[i] < 80
                volume_ok = data['volume_ratio'].iloc[i] > 0.5  # Menos estricto
                trend_ok = data['trend_strength'].iloc[i] > 0.2
                conditions_met = sum([rsi_ok, stoch_ok, volume_ok, trend_ok])

            elif self.market_type == 'commodities':
                # Commodities: momentum y volumen importantes
                rsi_ok = 30 < data['rsi'].iloc[i] < 70
                stoch_ok = 25 < data['stoch_k'].iloc[i] < 75
                volume_ok = data['volume_ratio'].iloc[i] > 1.0
                momentum_ok = data['roc'].iloc[i] > 0.5
                conditions_met = sum([rsi_ok, stoch_ok, volume_ok, momentum_ok])

            elif self.market_type == 'stocks':
                # Stocks: análisis técnico clásico
                rsi_ok = 30 < data['rsi'].iloc[i] < 70
                stoch_ok = 20 < data['stoch_k'].iloc[i] < 80
                volume_ok = data['volume_ratio'].iloc[i] > 0.8
                trend_ok = data['golden_cross'].iloc[i] == 1
                conditions_met = sum([rsi_ok, stoch_ok, volume_ok, trend_ok])

            else:  # crypto, synthetic
                # Lógica original
                rsi_ok = 20 < data['rsi'].iloc[i] < 80
                stoch_ok = 10 < data['stoch_k'].iloc[i] < 90
                volume_ok = data['volume_ratio'].iloc[i] > 0.8
                volatility_ok = data['atr'].iloc[i] / data['close'].iloc[i] > 0.001
                conditions_met = sum([rsi_ok, stoch_ok, volume_ok, volatility_ok])

            # Generar señales
            min_conditions = 3 if self.market_type in ['forex', 'stocks'] else 2

            if ha_change_long and conditions_met >= min_conditions:
                signals.iloc[i] = 1
                long_signals += 1
            elif ha_change_short and conditions_met >= min_conditions:
                signals.iloc[i] = -1
                short_signals += 1

        print(f"Señales {self.market_type.upper()}: {long_signals} LONG, {short_signals} SHORT")
        return signals

    def _run_backtest_adaptive(self, data: pd.DataFrame, signals: pd.Series, symbol: str, ml_confidence_all: pd.Series) -> Dict:
        """Backtesting con gestión de riesgo adaptada al mercado"""

        capital = self.portfolio_value
        trades = []
        peak_value = capital
        max_drawdown = 0
        position = 0
        entry_price = 0

        # Parámetros de riesgo adaptados por mercado
        risk_configs = {
            'forex': {'risk_per_trade': 0.015, 'min_rr_ratio': 2.0, 'max_holding_period': 48},  # 2 días en 1h
            'commodities': {'risk_per_trade': 0.02, 'min_rr_ratio': 2.5, 'max_holding_period': 80},  # ~1 semana en 4h
            'stocks': {'risk_per_trade': 0.025, 'min_rr_ratio': 3.0, 'max_holding_period': 200},  # ~1 mes en diario
            'synthetic': {'risk_per_trade': 0.025, 'min_rr_ratio': 2.8, 'max_holding_period': 80},
            'crypto': {'risk_per_trade': 0.02, 'min_rr_ratio': 2.5, 'max_holding_period': 80}
        }

        risk_config = risk_configs.get(self.market_type, risk_configs['crypto'])
        risk_per_trade = risk_config['risk_per_trade']
        min_rr_ratio = risk_config['min_rr_ratio']
        max_holding_period = risk_config['max_holding_period']

        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            atr = data['atr'].iloc[i]

            if pd.isna(atr) or atr == 0:
                continue

            # Entrada de posiciones
            if position == 0 and signals.iloc[i] != 0:
                ml_conf = ml_confidence_all.iloc[i]
                if ml_conf < self.ml_threshold:
                    continue

                entry_price = current_price

                # Stop loss y take profit adaptados al mercado
                if self.market_type == 'forex':
                    # Forex: stops más ajustados
                    stop_distance = atr * 2.0  # ATR más conservador
                    take_profit_distance = stop_distance * 2.0
                elif self.market_type == 'stocks':
                    # Stocks: stops más amplios
                    stop_distance = atr * 3.0
                    take_profit_distance = stop_distance * 3.0
                else:
                    # Crypto, commodities, synthetic: configuración original
                    stop_distance = atr * self.stop_loss_atr_multiplier
                    take_profit_distance = stop_distance * min_rr_ratio

                risk_amount = capital * risk_per_trade
                position_size = risk_amount / stop_distance
                position_size *= self.kelly_fraction * ml_conf

                # Límites de posición
                active_trades_count = len([t for t in self.active_trades if t['status'] == 'open'])
                if active_trades_count >= self.max_concurrent_trades:
                    continue

                # Validar liquidez
                if not self._check_liquidity_score_adaptive(data.iloc[i]):
                    continue

                position = signals.iloc[i] * position_size
                direction = 'long' if signals.iloc[i] > 0 else 'short'

                take_profit_price = entry_price + (signals.iloc[i] * take_profit_distance)
                stop_loss_price = entry_price - (signals.iloc[i] * stop_distance)

                trade = {
                    'entry_time': data.index[i],
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'direction': direction,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'status': 'open',
                    'symbol': symbol,
                    'ml_confidence': ml_conf,
                    'atr_at_entry': atr,
                    'market_type': self.market_type
                }

                self.active_trades.append(trade)

            # Gestionar posiciones abiertas
            elif position != 0:
                unrealized_pnl = (current_price - entry_price) * position

                # Trailing stop adaptado
                if unrealized_pnl > 0:
                    profit_amount = abs(current_price - entry_price)
                    trailing_multiplier = 0.4 if self.market_type == 'forex' else 0.5  # Forex más conservador
                    new_stop_distance = profit_amount * trailing_multiplier

                    if position > 0:
                        new_stop = entry_price + new_stop_distance
                        if new_stop > stop_loss_price:
                            stop_loss_price = new_stop
                    else:
                        new_stop = entry_price - new_stop_distance
                        if new_stop < stop_loss_price:
                            stop_loss_price = new_stop

                # Condiciones de salida
                exit_reason = None

                if signals.iloc[i] == -position:
                    exit_price = current_price
                    exit_reason = 'signal_reversal'
                elif (position > 0 and current_price >= take_profit_price) or (position < 0 and current_price <= take_profit_price):
                    exit_price = take_profit_price
                    exit_reason = 'take_profit'
                elif (position > 0 and current_price <= stop_loss_price) or (position < 0 and current_price >= stop_loss_price):
                    exit_price = stop_loss_price
                    exit_reason = 'stop_loss'
                elif len(trades) > 0 and (i - trades[-1].get('entry_index', 0)) > max_holding_period:
                    exit_price = current_price
                    exit_reason = 'time_exit'

                if exit_reason:
                    pnl = (exit_price - entry_price) * position
                    capital += pnl
                    position = 0

                    # Actualizar trade
                    for trade in self.active_trades:
                        if trade['status'] == 'open':
                            trade.update({
                                'exit_time': data.index[i],
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'status': 'closed',
                                'exit_reason': exit_reason
                            })
                            trades.append(trade.copy())
                            break

                    # Actualizar drawdown
                    peak_value = max(peak_value, capital)
                    current_drawdown = (peak_value - capital) / peak_value
                    max_drawdown = max(max_drawdown, current_drawdown)

                    if current_drawdown > self.max_drawdown:
                        break

        # Calcular métricas finales
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        total_pnl = sum([t.get('pnl', 0) for t in trades])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        gross_profit = sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0])
        gross_loss = abs(sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_capital': capital,
            'return_pct': (capital - self.portfolio_value) / self.portfolio_value,
            'symbol': symbol,
            'market_type': self.market_type,
            'strategy_name': f'MultiMarketUltraDetailedHeikinAshiMLStrategy-{self.market_type}',
            'trades': trades
        }

    def _check_liquidity_score_adaptive(self, row: pd.Series) -> bool:
        """
        Verificar score de liquidez adaptado al mercado
        """
        if self.market_type == 'forex':
            # Forex: menos énfasis en volumen
            volume_score = min(row['volume_ratio'] * 5, 100)  # Factor más bajo
            volatility_pct = (row['atr'] / row['close']) * 100
            volatility_score = min(volatility_pct * 8, 100)
        elif self.market_type == 'stocks':
            # Stocks: volumen muy importante
            volume_score = min(row['volume_ratio'] * 15, 100)  # Factor más alto
            volatility_pct = (row['atr'] / row['close']) * 100
            volatility_score = min(volatility_pct * 6, 100)
        else:
            # Crypto, commodities, synthetic: configuración original
            volume_score = min(row['volume_ratio'] * 10, 100)
            volatility_pct = (row['atr'] / row['close']) * 100
            volatility_score = min(volatility_pct * 10, 100)

        liquidity_score = (volume_score + volatility_score) / 2
        min_score = 40 if self.market_type == 'forex' else 50  # Forex más permisivo

        return liquidity_score > min_score

    def _get_empty_results(self, symbol: str) -> Dict:
        """Retornar resultados vacíos en caso de error"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'final_capital': self.portfolio_value,
            'return_pct': 0,
            'symbol': symbol,
            'market_type': self.market_type,
            'strategy_name': f'MultiMarketUltraDetailedHeikinAshiMLStrategy-{self.market_type}',
            'trades': []
        }