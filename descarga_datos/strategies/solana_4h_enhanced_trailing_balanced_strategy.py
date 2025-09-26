"""
Implementación de la estrategia Solana 4H Enhanced Trailing Stop Balanceada.
Versión optimizada para mayor número de trades manteniendo buena rentabilidad.
Ajustes: filtros más permisivos + stops optimizados + gestión de riesgo mejorada.
"""
import numpy as np
import pandas as pd
from utils.talib_wrapper import talib

class Solana4HEnhancedTrailingBalancedStrategy:
    def __init__(self,
                 take_profit_percent=3.5,      # Optimizado: 3.5% (balance entre agresividad y rentabilidad)
                 stop_loss_percent=2.5,        # Optimizado: 2.5% (más amplio que 2.0% para más trades)
                 base_trailing_stop=2.5,       # Optimizado: 2.5% (balance entre trailing y stops)
                 atr_trailing_multiplier=0.7,  # Optimizado: 0.7x (menos conservador que 0.5x)
                 volume_sma_period=15,         # Optimizado: 15 (más señales que 10)
                 trend_ema_period=40,          # Optimizado: 40 (más señales que 60, menos ruido que 20)
                 adx_threshold=18,             # Optimizado: 18 (más permisivo que 10, requiere tendencia moderada)
                 max_consecutive_losses=4):    # Optimizado: 4 (balance entre protección y flexibilidad)

        # Parámetros optimizados para mayor número de trades
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent
        self.base_trailing_stop = base_trailing_stop
        self.atr_trailing_multiplier = atr_trailing_multiplier
        self.volume_sma_period = volume_sma_period
        self.trend_ema_period = trend_ema_period
        self.adx_threshold = adx_threshold
        self.max_consecutive_losses = max_consecutive_losses

        # Parámetros de volumen más permisivos
        self.volume_threshold = 800  # Más bajo que 1000
        self.min_volume_multiplier = 1.1  # Más bajo que 1.2 para más señales

        # Contador de pérdidas consecutivas
        self.consecutive_losses = 0

    def calculate_heikin_ashi(self, df):
        """Calcula velas Heiken Ashi"""
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = pd.Series(0.0, index=df.index)
        ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        ha_high = pd.Series([max(h, o, c) for h, o, c in zip(df['high'], ha_open, ha_close)], index=df.index)
        ha_low = pd.Series([min(l, o, c) for l, o, c in zip(df['low'], ha_open, ha_close)], index=df.index)
        return pd.DataFrame({
            'ha_open': ha_open,
            'ha_high': ha_high,
            'ha_low': ha_low,
            'ha_close': ha_close
        }, index=df.index)

    def calculate_adaptive_trailing_stop(self, position, current_price, entry_price, atr_value, highest_price, lowest_price):
        """
        Calcula trailing stop adaptativo basado en ATR y precio máximo/mínimo
        """
        if position == 1:  # Long position
            # Update highest price
            highest_price = max(highest_price, current_price)

            # ATR-based trailing stop
            atr_trailing = highest_price - (atr_value * self.atr_trailing_multiplier)

            # Base trailing stop
            base_trailing = highest_price * (1 - self.base_trailing_stop / 100)

            # Use the higher of the two (more conservative)
            new_trailing_stop = max(atr_trailing, base_trailing)

            return new_trailing_stop, highest_price, lowest_price

        elif position == -1:  # Short position
            # Update lowest price
            lowest_price = min(lowest_price, current_price)

            # ATR-based trailing stop
            atr_trailing = lowest_price + (atr_value * self.atr_trailing_multiplier)

            # Base trailing stop
            base_trailing = lowest_price * (1 + self.base_trailing_stop / 100)

            # Use the lower of the two (more conservative)
            new_trailing_stop = min(atr_trailing, base_trailing)

            return new_trailing_stop, highest_price, lowest_price

        return 0.0, highest_price, lowest_price

    def calculate_signals(self, df):
        """
        Calcula las señales con filtros más permisivos para mayor número de trades.
        """
        # Calcular Heiken Ashi
        ha_df = self.calculate_heikin_ashi(df)
        df = df.copy()
        df['ha_open'] = ha_df['ha_open']
        df['ha_close'] = ha_df['ha_close']

        # Indicadores técnicos
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=self.volume_sma_period)
        df['trend_ema'] = talib.EMA(df['close'], timeperiod=self.trend_ema_period)
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)

        # RSI para filtro adicional (nuevo)
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)

        # Condiciones de filtro más permisivas
        df['volume_condition'] = (
            (df['volume'] > self.volume_threshold) &
            (df['volume'] > df['volume_sma'] * self.min_volume_multiplier)
        )

        # Tendencia más flexible
        df['trend_condition'] = df['close'] > df['trend_ema']  # Tendencia alcista

        # ADX más permisivo
        df['adx_condition'] = df['adx'] > self.adx_threshold   # Tendencia moderada-fuerte

        # RSI para evitar sobrecompra/sobreventa (nuevo filtro)
        df['rsi_condition'] = (
            (df['rsi'] < 70) & (df['rsi'] > 30)  # Evita extremos
        )

        # Señales de entrada con filtros balanceados
        df['long_condition'] = (
            df['volume_condition'] &
            df['trend_condition'] &
            df['adx_condition'] &
            df['rsi_condition'] &
            (df['ha_close'] > df['ha_open'])
        )

        df['short_condition'] = (
            df['volume_condition'] &
            (~df['trend_condition']) &  # Tendencia bajista
            df['adx_condition'] &
            df['rsi_condition'] &
            (df['ha_close'] < df['ha_open'])
        )

        return df

    def calculate_position_size(self, capital, entry_price, stop_loss, atr_value):
        """Calcula el tamaño de posición basado en riesgo y ATR"""
        risk_amount = capital * 0.015  # 1.5% de riesgo por trade (más agresivo que 1%)

        # Usar ATR para ajustar el stop loss si es más conservador
        atr_stop = entry_price - (atr_value * 1.2)  # 1.2 ATR stop (menos conservador)
        effective_stop = max(stop_loss, atr_stop) if stop_loss < entry_price else min(stop_loss, atr_stop)

        risk_per_unit = abs(entry_price - effective_stop)
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
            # Limitar tamaño máximo de posición
            max_position = capital * 0.05  # Máximo 5% del capital por trade
            return min(position_size, max_position)
        return 0.01  # Tamaño mínimo

    def run(self, data, symbol):
        """
        Ejecuta la estrategia balanceada con mayor número de trades
        """
        try:
            # Calcular señales
            df = self.calculate_signals(data.copy())

            # Inicializar variables de trading
            capital = 10000.0
            position = 0  # 0: sin posición, 1: long, -1: short
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            trailing_stop = 0.0
            highest_price = 0.0
            lowest_price = float('inf')
            trades = []
            self.consecutive_losses = 0

            # Simular trading
            for i in range(len(df)):
                current_price = df['close'].iloc[i]
                atr_value = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else 0.01

                # Verificar límite de pérdidas consecutivas
                if self.consecutive_losses >= self.max_consecutive_losses:
                    continue  # Saltar señales hasta que se resetee el contador

                # Verificar señales de entrada
                if position == 0:
                    if df['long_condition'].iloc[i]:
                        # Entrar en posición long
                        position = 1
                        entry_price = current_price
                        stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 + self.take_profit_percent / 100)
                        trailing_stop = stop_loss
                        highest_price = current_price

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss, atr_value)

                    elif df['short_condition'].iloc[i]:
                        # Entrar en posición short
                        position = -1
                        entry_price = current_price
                        stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 - self.take_profit_percent / 100)
                        trailing_stop = stop_loss
                        lowest_price = current_price

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss, atr_value)

                # Gestionar posiciones abiertas con trailing stop adaptativo
                elif position == 1:  # Posición long
                    # Update trailing stop adaptativo
                    trailing_stop, highest_price, _ = self.calculate_adaptive_trailing_stop(
                        position, current_price, entry_price, atr_value, highest_price, lowest_price
                    )

                    # Check exit conditions
                    if current_price >= take_profit or current_price <= trailing_stop:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl

                        # Actualizar contador de pérdidas consecutivas
                        if pnl < 0:
                            self.consecutive_losses += 1
                        else:
                            self.consecutive_losses = 0

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long',
                            'exit_reason': 'take_profit' if current_price >= take_profit else 'trailing_stop',
                            'atr_at_exit': atr_value,
                            'consecutive_losses': self.consecutive_losses,
                            'rsi_at_entry': df['rsi'].iloc[i] if not pd.isna(df['rsi'].iloc[i]) else 50
                        })

                        position = 0
                        trailing_stop = 0.0
                        highest_price = 0.0

                elif position == -1:  # Posición short
                    # Update trailing stop adaptativo
                    trailing_stop, _, lowest_price = self.calculate_adaptive_trailing_stop(
                        position, current_price, entry_price, atr_value, highest_price, lowest_price
                    )

                    # Check exit conditions
                    if current_price <= take_profit or current_price >= trailing_stop:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (entry_price - exit_price) * position_size
                        capital += pnl

                        # Actualizar contador de pérdidas consecutivas
                        if pnl < 0:
                            self.consecutive_losses += 1
                        else:
                            self.consecutive_losses = 0

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'short',
                            'exit_reason': 'take_profit' if current_price <= take_profit else 'trailing_stop',
                            'atr_at_exit': atr_value,
                            'consecutive_losses': self.consecutive_losses,
                            'rsi_at_entry': df['rsi'].iloc[i] if not pd.isna(df['rsi'].iloc[i]) else 50
                        })

                        position = 0
                        trailing_stop = 0.0
                        lowest_price = float('inf')

            # Calcular métricas avanzadas
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
            total_pnl = sum(t['pnl'] for t in trades)

            # Calcular equity curve y max drawdown
            if trades:
                equity_curve = [10000.0]
                for tr in trades:
                    equity_curve.append(equity_curve[-1] + tr['pnl'])

                peak = equity_curve[0]
                max_dd = 0.0
                for eq in equity_curve:
                    if eq > peak:
                        peak = eq
                    dd = peak - eq
                    if dd > max_dd:
                        max_dd = dd
                max_drawdown = -max_dd
            else:
                max_drawdown = 0.0
                equity_curve = [10000.0]

            # Calcular Sharpe Ratio (simplificado)
            if total_trades > 1:
                returns = [t['pnl'] / 10000.0 for t in trades]
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365) if np.std(returns) > 0 else 0.0
            else:
                sharpe_ratio = 0.0

            # Profit factor
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

            # Calmar Ratio
            if max_drawdown != 0:
                calmar_ratio = (total_pnl / 10000.0) / abs(max_drawdown / 10000.0) if max_drawdown < 0 else 0.0
            else:
                calmar_ratio = 0.0

            # Métricas adicionales del trailing stop balanceado
            trailing_stop_exits = len([t for t in trades if t.get('exit_reason') == 'trailing_stop'])
            take_profit_exits = len([t for t in trades if t.get('exit_reason') == 'take_profit'])
            avg_atr_at_exit = np.mean([t.get('atr_at_exit', 0) for t in trades]) if trades else 0.0
            avg_rsi_at_entry = np.mean([t.get('rsi_at_entry', 50) for t in trades]) if trades else 50.0

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'calmar_ratio': calmar_ratio,
                'profit_factor': profit_factor,
                'symbol': symbol,
                'trades': trades,
                'equity_curve': equity_curve,
                'trailing_stop_exits': trailing_stop_exits,
                'take_profit_exits': take_profit_exits,
                'trailing_stop_ratio': (trailing_stop_exits / total_trades * 100) if total_trades > 0 else 0,
                'avg_atr_at_exit': avg_atr_at_exit,
                'avg_rsi_at_entry': avg_rsi_at_entry,
                'max_consecutive_losses_hit': self.max_consecutive_losses,
                'final_consecutive_losses': self.consecutive_losses,
                # Parámetros optimizados balanceados
                'optimized_params': {
                    'take_profit_percent': self.take_profit_percent,
                    'stop_loss_percent': self.stop_loss_percent,
                    'base_trailing_stop': self.base_trailing_stop,
                    'atr_trailing_multiplier': self.atr_trailing_multiplier,
                    'volume_sma_period': self.volume_sma_period,
                    'trend_ema_period': self.trend_ema_period,
                    'adx_threshold': self.adx_threshold,
                    'max_consecutive_losses': self.max_consecutive_losses,
                    'volume_threshold': self.volume_threshold,
                    'min_volume_multiplier': self.min_volume_multiplier
                }
            }

        except Exception as e:
            print(f"Error ejecutando estrategia Solana4HEnhancedTrailingBalancedStrategy: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'calmar_ratio': 0.0,
                'profit_factor': 0.0,
                'symbol': symbol,
                'trades': [],
                'trailing_stop_exits': 0,
                'take_profit_exits': 0,
                'trailing_stop_ratio': 0.0,
                'avg_atr_at_exit': 0.0,
                'avg_rsi_at_entry': 50.0,
                'max_consecutive_losses_hit': 0,
                'final_consecutive_losses': 0
            }