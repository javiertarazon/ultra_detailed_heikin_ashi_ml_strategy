"""
Implementación de la estrategia Solana 4H con Trailing Stop.
Versión mejorada con trailing stop para asegurar ganancias.
"""
import numpy as np
import pandas as pd
from utils.talib_wrapper import talib

class Solana4HTrailingStrategy:
    def __init__(self,
                 volume_threshold=1000,
                 take_profit_percent=5.0,
                 stop_loss_percent=3.0,
                 trailing_stop_percent=2.0,
                 volume_sma_period=20):
        self.volume_threshold = volume_threshold
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent
        self.trailing_stop_percent = trailing_stop_percent
        self.volume_sma_period = volume_sma_period

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

    def calculate_signals(self, df):
        """
        Calcula las señales usando Heiken Ashi y volumen.
        """
        # Calcular Heiken Ashi
        ha_df = self.calculate_heikin_ashi(df)
        df = df.copy()
        df['ha_open'] = ha_df['ha_open']
        df['ha_close'] = ha_df['ha_close']

        # Media móvil de volumen
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=self.volume_sma_period)

        # Condición de volumen
        df['volume_condition'] = (df['volume'] > self.volume_threshold) & (df['volume'] > df['volume_sma'])

        # Señales de entrada
        df['long_condition'] = df['volume_condition'] & (df['ha_close'] > df['ha_open'])
        df['short_condition'] = df['volume_condition'] & (df['ha_close'] < df['ha_open'])

        return df

    def calculate_position_size(self, capital, entry_price, stop_loss):
        """Calcula el tamaño de posición basado en riesgo"""
        risk_amount = capital * 0.02  # 2% de riesgo por trade
        return risk_amount / abs(entry_price - stop_loss)

    def update_trailing_stop(self, position, current_price, entry_price, trailing_stop, highest_price, lowest_price):
        """
        Actualiza el trailing stop basado en el movimiento del precio
        """
        if position == 1:  # Long position
            # Update highest price
            highest_price = max(highest_price, current_price)

            # Calculate new trailing stop
            new_trailing_stop = highest_price * (1 - self.trailing_stop_percent / 100)

            # Only move trailing stop up, never down
            trailing_stop = max(trailing_stop, new_trailing_stop)

        elif position == -1:  # Short position
            # Update lowest price
            lowest_price = min(lowest_price, current_price)

            # Calculate new trailing stop
            new_trailing_stop = lowest_price * (1 + self.trailing_stop_percent / 100)

            # Only move trailing stop down, never up
            trailing_stop = min(trailing_stop, new_trailing_stop)

        return trailing_stop, highest_price, lowest_price

    def run(self, data, symbol):
        """
        Ejecuta la estrategia con trailing stop y devuelve los resultados del backtesting
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

            # Simular trading
            for i in range(len(df)):
                current_price = df['close'].iloc[i]

                # Verificar señales de entrada
                if position == 0:
                    if df['long_condition'].iloc[i]:
                        # Entrar en posición long
                        position = 1
                        entry_price = current_price
                        stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 + self.take_profit_percent / 100)
                        trailing_stop = stop_loss  # Initial trailing stop is the stop loss
                        highest_price = current_price

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)

                    elif df['short_condition'].iloc[i]:
                        # Entrar en posición short
                        position = -1
                        entry_price = current_price
                        stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 - self.take_profit_percent / 100)
                        trailing_stop = stop_loss  # Initial trailing stop is the stop loss
                        lowest_price = current_price

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)

                # Gestionar posiciones abiertas con trailing stop
                elif position == 1:  # Posición long
                    # Update trailing stop
                    trailing_stop, highest_price, _ = self.update_trailing_stop(
                        position, current_price, entry_price, trailing_stop, highest_price, lowest_price
                    )

                    # Check exit conditions
                    if current_price >= take_profit or current_price <= trailing_stop:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long',
                            'exit_reason': 'take_profit' if current_price >= take_profit else 'trailing_stop'
                        })

                        position = 0
                        trailing_stop = 0.0
                        highest_price = 0.0

                elif position == -1:  # Posición short
                    # Update trailing stop
                    trailing_stop, _, lowest_price = self.update_trailing_stop(
                        position, current_price, entry_price, trailing_stop, highest_price, lowest_price
                    )

                    # Check exit conditions
                    if current_price <= take_profit or current_price >= trailing_stop:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (entry_price - exit_price) * position_size
                        capital += pnl

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'short',
                            'exit_reason': 'take_profit' if current_price <= take_profit else 'trailing_stop'
                        })

                        position = 0
                        trailing_stop = 0.0
                        lowest_price = float('inf')

            # Calcular métricas
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

            # Profit factor
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

            # Calcular métricas adicionales del trailing stop
            trailing_stop_exits = len([t for t in trades if t.get('exit_reason') == 'trailing_stop'])
            take_profit_exits = len([t for t in trades if t.get('exit_reason') == 'take_profit'])

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': 0.0,  # Placeholder
                'profit_factor': profit_factor,
                'symbol': symbol,
                'trades': trades,
                'equity_curve': equity_curve,
                'trailing_stop_exits': trailing_stop_exits,
                'take_profit_exits': take_profit_exits,
                'trailing_stop_ratio': (trailing_stop_exits / total_trades * 100) if total_trades > 0 else 0
            }

        except Exception as e:
            print(f"Error ejecutando estrategia Solana4HTrailingStrategy: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'symbol': symbol,
                'trades': [],
                'trailing_stop_exits': 0,
                'take_profit_exits': 0,
                'trailing_stop_ratio': 0.0
            }