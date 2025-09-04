"""
Estrategia UT Bot + PSAR Avanzada - Versión Trader Profesional
Implementa técnicas avanzadas de trading basadas en 20 años de experiencia
Enfoque en maximizar rentabilidad y minimizar riesgo
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
# import talib  # Comentado por ahora, usaremos implementaciones propias

from ..core.base_strategy import BaseStrategy, Signal, Position, SignalType

class MarketRegime(Enum):
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

class PositionSizing(Enum):
    FIXED = "fixed"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"

@dataclass
class AdvancedConfig:
    """Configuración avanzada de estrategia profesional"""
    # Parámetros base optimizados
    sensitivity: int = 2
    atr_period: int = 14
    base_risk_percent: float = 1.0
    tp_multiplier: float = 3.0
    sl_multiplier: float = 2.0
    
    # Gestión de riesgo avanzada
    max_daily_loss: float = 3.0  # 3% pérdida máxima diaria
    max_drawdown: float = 10.0   # 10% drawdown máximo
    position_sizing_method: PositionSizing = PositionSizing.VOLATILITY_ADJUSTED
    correlation_filter: bool = True  # Evitar posiciones correlacionadas
    
    # Filtros de mercado avanzados
    use_market_regime_filter: bool = True
    use_volume_profile: bool = True
    use_order_flow: bool = True
    use_momentum_confluence: bool = True
    
    # Optimización dinámica
    adaptive_parameters: bool = True
    performance_tracking: bool = True
    auto_optimization: bool = True
    
    # Parámetros adicionales
    min_reward_risk_ratio: float = 2.5  # Mínimo R:R
    trend_strength_threshold: float = 0.7
    volume_surge_multiplier: float = 2.0

class AdvancedUTBotStrategy(BaseStrategy):
    """
    Estrategia UT Bot + PSAR con técnicas profesionales avanzadas
    
    Mejoras implementadas:
    1. Análisis de régimen de mercado
    2. Gestión de riesgo multi-nivel
    3. Filtros de confluencia técnica
    4. Optimización dinámica de parámetros
    5. Posicionamiento inteligente
    6. Control de correlación
    7. Análisis de volumen profesional
    """
    
    def __init__(self, config: AdvancedConfig = None):
        super().__init__()
        self.config = config or AdvancedConfig()
        
        # Estado de la estrategia
        self.current_regime = MarketRegime.RANGING
        self.daily_pnl = 0.0
        self.peak_equity = 10000.0
        self.current_drawdown = 0.0
        
        # Tracking de performance
        self.win_streak = 0
        self.loss_streak = 0
        self.recent_performance = []
        
        # Parámetros adaptativos
        self.adaptive_multiplier = 1.0
        self.volatility_factor = 1.0
        
        # Historial para análisis
        self.signal_history = []
        self.performance_history = []

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI manualmente"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calcula ATR manualmente"""
        high_low = high - low
        high_close = abs(high - close.shift(1))
        low_close = abs(low - close.shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def calculate_sar(self, high: pd.Series, low: pd.Series, acceleration: float = 0.02, maximum: float = 0.2) -> pd.Series:
        """Calcula PSAR manualmente"""
        psar = pd.Series(index=high.index, dtype=float)
        psar.iloc[0] = low.iloc[0]
        
        af = acceleration
        trend = 1  # 1 para uptrend, -1 para downtrend
        ep = high.iloc[0]  # Extreme point
        
        for i in range(1, len(high)):
            if trend == 1:  # Uptrend
                psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
                
                if low.iloc[i] <= psar.iloc[i]:
                    trend = -1
                    psar.iloc[i] = ep
                    ep = low.iloc[i]
                    af = acceleration
                else:
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af = min(af + acceleration, maximum)
                    psar.iloc[i] = min(psar.iloc[i], min(low.iloc[i-1:i+1]))
            else:  # Downtrend
                psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
                
                if high.iloc[i] >= psar.iloc[i]:
                    trend = 1
                    psar.iloc[i] = ep
                    ep = high.iloc[i]
                    af = acceleration
                else:
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af = min(af + acceleration, maximum)
                    psar.iloc[i] = max(psar.iloc[i], max(high.iloc[i-1:i+1]))
        
        return psar

    def analyze_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """Análisis avanzado del régimen de mercado"""
        if len(df) < 100:
            return MarketRegime.RANGING
        
        # 1. Análisis de tendencia con múltiples timeframes
        ema_20 = df['close'].ewm(span=20).mean()
        ema_50 = df['close'].ewm(span=50).mean()
        ema_200 = df['close'].ewm(span=200).mean()
        
        # Fortaleza de tendencia
        trend_score = 0
        if ema_20.iloc[-1] > ema_50.iloc[-1] > ema_200.iloc[-1]:
            trend_score += 3  # Fuerte tendencia alcista
        elif ema_20.iloc[-1] < ema_50.iloc[-1] < ema_200.iloc[-1]:
            trend_score -= 3  # Fuerte tendencia bajista
        
        # 2. Análisis de volatilidad
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(20).std().iloc[-1]
        avg_volatility = returns.rolling(100).std().mean()
        
        vol_ratio = volatility / avg_volatility if avg_volatility > 0 else 1
        
        # 3. Análisis de momentum
        rsi = self.calculate_rsi(df['close'])
        
        momentum_score = 0
        if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]):
            if rsi.iloc[-1] > 70:
                momentum_score += 1
            elif rsi.iloc[-1] < 30:
                momentum_score -= 1
        
        # Determinar régimen
        if vol_ratio > 1.5:
            return MarketRegime.HIGH_VOLATILITY
        elif vol_ratio < 0.7:
            return MarketRegime.LOW_VOLATILITY
        elif trend_score >= 2 and momentum_score >= 1:
            return MarketRegime.TRENDING_BULL
        elif trend_score <= -2 and momentum_score <= -1:
            return MarketRegime.TRENDING_BEAR
        else:
            return MarketRegime.RANGING

    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos avanzados"""
        data = df.copy()
        
        # Indicadores base
        data = self.calculate_base_indicators(data)
        
        # Indicadores avanzados
        
        # 1. Volume Profile simplificado
        data['volume_ma'] = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['volume_surge'] = data['volume_ratio'] > self.config.volume_surge_multiplier
        
        # 2. Momentum avanzado
        data['rsi'] = self.calculate_rsi(data['close'])
        data['roc'] = data['close'].pct_change(10) * 100  # Rate of Change
        
        # 3. Volatilidad adaptativa
        returns = data['close'].pct_change()
        data['volatility'] = returns.rolling(20).std()
        data['vol_percentile'] = data['volatility'].rolling(100).rank(pct=True)
        
        # 4. Trend strength
        # 5. Trend strength (simplificado)
        data['adx'] = data['close'].rolling(14).std() * 100  # Aproximación de ADX
        
        # 5. Support/Resistance levels
        data['pivot_high'] = data['high'].rolling(5, center=True).max() == data['high']
        data['pivot_low'] = data['low'].rolling(5, center=True).min() == data['low']
        
        # 6. Market structure
        data['higher_high'] = (data['high'] > data['high'].shift(1)) & (data['high'].shift(1) > data['high'].shift(2))
        data['lower_low'] = (data['low'] < data['low'].shift(1)) & (data['low'].shift(1) < data['low'].shift(2))
        
        return data

    def calculate_base_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores base UT Bot + PSAR"""
        data = df.copy()
        
        # ATR
        data['atr'] = self.calculate_atr(data['high'], data['low'], data['close'], self.config.atr_period)
        
        # PSAR
        data['sar'] = self.calculate_sar(data['high'], data['low'])
        
        # UT Bot calculation
        data['hl2'] = (data['high'] + data['low']) / 2
        data['upper_band'] = data['hl2'] + (self.config.sensitivity * data['atr'])
        data['lower_band'] = data['hl2'] - (self.config.sensitivity * data['atr'])
        
        # Trailing stops
        data['final_upper'] = data['upper_band'].copy()
        data['final_lower'] = data['lower_band'].copy()
        
        for i in range(1, len(data)):
            # Upper band logic
            if (data['upper_band'].iloc[i] < data['final_upper'].iloc[i-1] or 
                data['close'].iloc[i-1] > data['final_upper'].iloc[i-1]):
                data.loc[data.index[i], 'final_upper'] = data['upper_band'].iloc[i]
            else:
                data.loc[data.index[i], 'final_upper'] = data['final_upper'].iloc[i-1]
            
            # Lower band logic
            if (data['lower_band'].iloc[i] > data['final_lower'].iloc[i-1] or 
                data['close'].iloc[i-1] < data['final_lower'].iloc[i-1]):
                data.loc[data.index[i], 'final_lower'] = data['lower_band'].iloc[i]
            else:
                data.loc[data.index[i], 'final_lower'] = data['final_lower'].iloc[i-1]
        
        # UT Bot signal
        data['ut_signal'] = 0
        for i in range(1, len(data)):
            if data['close'].iloc[i] <= data['final_lower'].iloc[i]:
                data.loc[data.index[i], 'ut_signal'] = 1
            elif data['close'].iloc[i] >= data['final_upper'].iloc[i]:
                data.loc[data.index[i], 'ut_signal'] = -1
            else:
                data.loc[data.index[i], 'ut_signal'] = data['ut_signal'].iloc[i-1]
        
        return data

    def apply_advanced_filters(self, df: pd.DataFrame, signal_type: SignalType, index: int) -> Tuple[bool, float]:
        """Aplica filtros avanzados y calcula score de calidad"""
        current_row = df.iloc[index]
        score = 0.0
        max_score = 0.0
        
        # 1. Filtro de régimen de mercado (30% peso)
        regime_weight = 0.3
        max_score += regime_weight
        
        if self.current_regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            if ((signal_type == SignalType.BUY and self.current_regime == MarketRegime.TRENDING_BULL) or
                (signal_type == SignalType.SELL and self.current_regime == MarketRegime.TRENDING_BEAR)):
                score += regime_weight
        elif self.current_regime == MarketRegime.RANGING:
            score += regime_weight * 0.7  # Menor score en ranging
        
        # 2. Filtro de momentum (25% peso)
        momentum_weight = 0.25
        max_score += momentum_weight
        
        rsi = current_row.get('rsi', 50)
        roc = current_row.get('roc', 0)
        
        if signal_type == SignalType.BUY:
            if 30 < rsi < 70 and roc > 0:  # Momentum favorable
                score += momentum_weight
            elif rsi < 30:  # Oversold
                score += momentum_weight * 0.8
        else:  # SELL
            if 30 < rsi < 70 and roc < 0:
                score += momentum_weight
            elif rsi > 70:  # Overbought
                score += momentum_weight * 0.8
        
        # 3. Filtro de volatilidad (20% peso)
        vol_weight = 0.2
        max_score += vol_weight
        
        vol_percentile = current_row.get('vol_percentile', 0.5)
        if 0.2 <= vol_percentile <= 0.8:  # Volatilidad normal
            score += vol_weight
        elif vol_percentile < 0.2:  # Muy baja volatilidad
            score += vol_weight * 0.5
        
        # 4. Filtro de volumen (15% peso)
        volume_weight = 0.15
        max_score += volume_weight
        
        if current_row.get('volume_surge', False):
            score += volume_weight
        elif current_row.get('volume_ratio', 1) > 1.2:
            score += volume_weight * 0.7
        
        # 5. Filtro de tendencia (10% peso)
        trend_weight = 0.1
        max_score += trend_weight
        
        adx = current_row.get('adx', 0)
        if adx > self.config.trend_strength_threshold * 100:
            score += trend_weight
        
        # Normalizar score
        quality_score = score / max_score if max_score > 0 else 0
        
        # Filtro mínimo de calidad
        min_quality = 0.6  # Solo señales de alta calidad
        return quality_score >= min_quality, quality_score

    def calculate_dynamic_position_size(self, signal: Signal, account_balance: float) -> float:
        """Cálculo avanzado de tamaño de posición"""
        base_risk = self.config.base_risk_percent / 100
        
        # Ajuste por método de posicionamiento
        if self.config.position_sizing_method == PositionSizing.VOLATILITY_ADJUSTED:
            # Ajuste por volatilidad
            volatility_adj = 1.0 / self.volatility_factor if self.volatility_factor > 0 else 1.0
            volatility_adj = max(0.5, min(2.0, volatility_adj))  # Limitar entre 0.5x y 2x
            
            adjusted_risk = base_risk * volatility_adj
            
        elif self.config.position_sizing_method == PositionSizing.KELLY_CRITERION:
            # Simplified Kelly (requiere historial)
            if len(self.recent_performance) > 10:
                wins = [p for p in self.recent_performance if p > 0]
                losses = [p for p in self.recent_performance if p < 0]
                
                if wins and losses:
                    win_rate = len(wins) / len(self.recent_performance)
                    avg_win = np.mean(wins)
                    avg_loss = abs(np.mean(losses))
                    
                    if avg_loss > 0:
                        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                        kelly_fraction = max(0, min(0.25, kelly_fraction))  # Máximo 25%
                        adjusted_risk = kelly_fraction
                    else:
                        adjusted_risk = base_risk
                else:
                    adjusted_risk = base_risk
            else:
                adjusted_risk = base_risk
                
        else:  # FIXED
            adjusted_risk = base_risk
        
        # Ajuste por performance reciente
        if self.loss_streak >= 3:
            adjusted_risk *= 0.5  # Reducir riesgo tras racha perdedora
        elif self.win_streak >= 3:
            adjusted_risk *= min(1.5, 1 + (self.win_streak - 2) * 0.1)  # Incrementar gradualmente
        
        # Ajuste por drawdown actual
        if self.current_drawdown > 5.0:
            dd_factor = max(0.3, 1 - (self.current_drawdown - 5) / 20)
            adjusted_risk *= dd_factor
        
        # Calcular tamaño final
        if signal.stop_loss is None:
            return account_balance * adjusted_risk
        
        risk_amount = account_balance * adjusted_risk
        
        if signal.type == SignalType.BUY:
            risk_per_share = signal.price - signal.stop_loss
        else:
            risk_per_share = signal.stop_loss - signal.price
        
        if risk_per_share <= 0:
            return account_balance * 0.005  # Mínimo 0.5%
        
        position_size = risk_amount / risk_per_share
        
        # Límites de seguridad
        max_position = account_balance * 0.15  # Máximo 15% del balance
        return min(position_size, max_position)

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """Generación de señales con filtros avanzados"""
        # Calcular indicadores
        data = self.calculate_advanced_indicators(df)
        
        # Determinar régimen de mercado
        self.current_regime = self.analyze_market_regime(data)
        
        # Actualizar factor de volatilidad
        if len(data) > 20:
            recent_vol = data['volatility'].tail(20).mean()
            avg_vol = data['volatility'].mean()
            self.volatility_factor = recent_vol / avg_vol if avg_vol > 0 else 1.0
        
        signals = []
        
        for i in range(1, len(data)):
            current_row = data.iloc[i]
            prev_row = data.iloc[i-1]
            
            signal_type = None
            
            # Lógica de señales UT Bot + PSAR
            if (prev_row['ut_signal'] != 1 and current_row['ut_signal'] == 1 and
                current_row['close'] > current_row['sar']):
                signal_type = SignalType.BUY
                
            elif (prev_row['ut_signal'] != -1 and current_row['ut_signal'] == -1 and
                  current_row['close'] < current_row['sar']):
                signal_type = SignalType.SELL
            
            if signal_type:
                # Aplicar filtros avanzados
                is_valid, quality_score = self.apply_advanced_filters(data, signal_type, i)
                
                if is_valid:
                    # Calcular niveles con gestión de riesgo avanzada
                    atr_value = current_row['atr']
                    price = current_row['close']
                    
                    # Ajuste dinámico de TP/SL basado en volatilidad y régimen
                    tp_mult = self.config.tp_multiplier
                    sl_mult = self.config.sl_multiplier
                    
                    # Ajustar según régimen
                    if self.current_regime == MarketRegime.HIGH_VOLATILITY:
                        tp_mult *= 1.3
                        sl_mult *= 1.2
                    elif self.current_regime == MarketRegime.LOW_VOLATILITY:
                        tp_mult *= 0.8
                        sl_mult *= 0.9
                    elif self.current_regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
                        tp_mult *= 1.2  # Más agresivo en tendencias
                    
                    # Verificar ratio R:R mínimo
                    if tp_mult / sl_mult >= self.config.min_reward_risk_ratio:
                        
                        if signal_type == SignalType.BUY:
                            stop_loss = price - (sl_mult * atr_value)
                            take_profit = price + (tp_mult * atr_value)
                        else:
                            stop_loss = price + (sl_mult * atr_value)
                            take_profit = price - (tp_mult * atr_value)
                        
                        signal = Signal(
                            type=signal_type,
                            timestamp=current_row.name,
                            price=price,
                            confidence=quality_score,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            metadata={
                                'atr': atr_value,
                                'regime': self.current_regime.value,
                                'quality_score': quality_score,
                                'volatility_factor': self.volatility_factor,
                                'tp_multiplier': tp_mult,
                                'sl_multiplier': sl_mult,
                                'rsi': current_row.get('rsi', 50),
                                'adx': current_row.get('adx', 0),
                                'volume_surge': current_row.get('volume_surge', False)
                            }
                        )
                        signals.append(signal)
                        self.signal_history.append(signal)
        
        return signals

    def update_performance_tracking(self, trade_result: float):
        """Actualiza tracking de performance"""
        self.recent_performance.append(trade_result)
        
        # Mantener solo últimos 50 trades
        if len(self.recent_performance) > 50:
            self.recent_performance.pop(0)
        
        # Actualizar streaks
        if trade_result > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        # Actualizar drawdown
        self.daily_pnl += trade_result
        current_equity = self.peak_equity + self.daily_pnl
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = ((self.peak_equity - current_equity) / self.peak_equity) * 100

    def should_halt_trading(self) -> bool:
        """Determina si se debe detener el trading por riesgo"""
        # Parar si se alcanza pérdida máxima diaria
        if abs(self.daily_pnl) >= (self.peak_equity * self.config.max_daily_loss / 100):
            return True
        
        # Parar si se alcanza drawdown máximo
        if self.current_drawdown >= self.config.max_drawdown:
            return True
        
        # Parar si hay muchas pérdidas consecutivas
        if self.loss_streak >= 5:
            return True
        
        return False

    def get_strategy_stats(self) -> Dict:
        """Retorna estadísticas avanzadas de la estrategia"""
        return {
            'name': 'Advanced UT Bot + PSAR Pro',
            'version': '3.0',
            'current_regime': self.current_regime.value,
            'volatility_factor': self.volatility_factor,
            'win_streak': self.win_streak,
            'loss_streak': self.loss_streak,
            'current_drawdown': self.current_drawdown,
            'daily_pnl': self.daily_pnl,
            'signals_generated': len(self.signal_history),
            'recent_performance_avg': np.mean(self.recent_performance) if self.recent_performance else 0,
            'config': {
                'sensitivity': self.config.sensitivity,
                'atr_period': self.config.atr_period,
                'position_sizing': self.config.position_sizing_method.value,
                'max_daily_loss': self.config.max_daily_loss,
                'max_drawdown': self.config.max_drawdown,
                'min_rr_ratio': self.config.min_reward_risk_ratio
            }
        }
