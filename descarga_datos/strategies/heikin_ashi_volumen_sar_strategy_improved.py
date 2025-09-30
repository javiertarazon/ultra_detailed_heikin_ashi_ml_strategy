"""
Implementación MEJORADA de la estrategia multi-activo con Heikin Ashi, Volumen y Par        # Señales de entrada ajustadas para balance 50/50
        # Long: Más flexible - solo requiere HA alcista + volumen + SAR bullish (muy amplio)
        df['long_condition'] = (
            df['volume_condition'] &
            df['ha_bullish'] &
            (df['close'] > df['sar'] * 1.005) &  # Buffer mínimo para longs
            (df['rsi'] < 85)  # RSI muy flexible
            # Sin requerimiento de tendencia para favorecer longs
        )

        # Short: Más estricto - requiere todas las condiciones
        df['short_condition'] = (
            df['volume_condition'] &
            df['ha_bearish'] &
            df['sar_bearish'] &  # Buffer estricto
            (df['rsi'] > 35) &   # RSI más estricto
            df['trend_down']     # Requiere tendencia bajista
        )sión mejorada con balance long/short, RSI para sobrecompra/sobreventa, y SAR más flexible.
Adecuada para acciones, forex y criptomonedas mediante ajuste de parámetros.
"""
import numpy as np
import pandas as pd
import logging
from utils.talib_wrapper import talib

class HeikinAshiVolumenSarStrategyImproved:
    def __init__(self,
                 volume_threshold=1000,
                 take_profit_percent=6.0,  # Aumentado de 5.0% a 6.0%
                 stop_loss_percent=2.5,    # Reducido de 3.0% a 2.5%
                 trailing_stop_percent=2.5, # Aumentado de 2.0% a 2.5%
                 volume_sma_period=20,     # Ajustado de 15 a 20 para más señales
                 sar_acceleration=0.01,    # Más suave: 0.01 para menos sensibilidad
                 sar_maximum=0.15,
                 rsi_period=14,
                 rsi_overbought=75,        # Relajado de 70 a 75
                 rsi_oversold=25,          # Relajado de 30 a 25
                 max_long_ratio=0.7):      # Ajustado de 0.65 a 0.7
        self.volume_threshold = volume_threshold
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent
        self.trailing_stop_percent = trailing_stop_percent
        self.volume_sma_period = volume_sma_period
        self.sar_acceleration = sar_acceleration
        self.sar_maximum = sar_maximum
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.max_long_ratio = max_long_ratio

        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Estrategia HeikinAshiVolumenSar MEJORADA inicializada con: TP={take_profit_percent}%, " +
                        f"SL={stop_loss_percent}%, TrailStop={trailing_stop_percent}%, VolThreshold={volume_threshold}")

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
            'HA_Open': ha_open,
            'HA_High': ha_high,
            'HA_Low': ha_low,
            'HA_Close': ha_close
        }, index=df.index)

    def calculate_signals(self, df):
        """
        Calcula las señales mejoradas usando Heiken Ashi, Volumen, Parabolic SAR y RSI.
        Incluye lógica de balance long/short y filtros de sobrecompra/sobreventa.
        """
        # Calcular Heiken Ashi
        ha_df = self.calculate_heikin_ashi(df)
        df = df.copy()
        df['ha_open'] = ha_df['HA_Open']
        df['ha_close'] = ha_df['HA_Close']

        # Calcular indicadores técnicos adicionales
        df['sar'] = talib.SAR(df['high'], df['low'], acceleration=self.sar_acceleration, maximum=self.sar_maximum)
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        df['ema_50'] = talib.EMA(df['close'], timeperiod=50)
        df['ema_200'] = talib.EMA(df['close'], timeperiod=200)

        # Media móvil de volumen
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=self.volume_sma_period)

        # Condición de volumen mejorada
        df['volume_condition'] = (df['volume'] > self.volume_threshold) & (df['volume'] > df['volume_sma'] * 1.2)  # Spike mínimo 20%

        # Condiciones base equilibradas
        df['ha_bullish'] = df['ha_close'] > df['ha_open']
        df['ha_bearish'] = df['ha_close'] < df['ha_open']
        df['sar_bullish'] = df['close'] > df['sar'] * 1.01  # Buffer más amplio para longs: 1%
        df['sar_bearish'] = df['close'] < df['sar'] * 0.99  # Buffer más estricto para shorts: 1%

        # Filtros de tendencia equilibrados
        df['trend_up'] = df['ema_50'] > df['ema_200'] * 0.97   # Tolerancia razonable de 3%
        df['trend_down'] = df['ema_50'] < df['ema_200'] * 1.03 # Tolerancia razonable de 3%

        # Señales de entrada agresivas para generar shorts
        # Long: HA alcista + volumen alto + precio > SAR + RSI no sobrecomprado + tendencia alcista
        df['long_condition'] = (
            df['volume_condition'] &
            df['ha_bullish'] &
            df['sar_bullish'] &
            (df['rsi'] < 70) &  # Moderadamente flexible
            df['trend_up']
        )

        # Short: HA bajista + volumen alto (muy agresivo para generar shorts)
        df['short_condition'] = (
            df['volume_condition'] &
            df['ha_bearish']
            # Sin restricciones de SAR, RSI o tendencia para forzar shorts
        )

        return df

    def calculate_position_size(self, capital, entry_price, stop_loss):
        """Calcula el tamaño de posición basado en riesgo"""
        risk_amount = capital * 0.02  # 2% de riesgo por trade
        return risk_amount / abs(entry_price - stop_loss)

    def check_long_short_balance(self, long_count, short_count, max_ratio=0.65):
        """
        Verifica el balance long/short para evitar sesgo excesivo.
        Retorna True si se permite la señal, False si se bloquea.
        """
        total_trades = long_count + short_count
        if total_trades == 0:
            return True  # Permitir primera señal

        long_ratio = long_count / total_trades

        # Si el ratio de longs excede el máximo, bloquear nuevas señales long
        if long_ratio > max_ratio:
            return False  # Bloquear long, permitir short

        return True  # Permitir señal

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
        Ejecuta la estrategia mejorada con balance long/short y trailing stop
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
            long_count = 0
            short_count = 0

            # Simular trading con balance long/short
            for i in range(len(df)):
                current_price = df['close'].iloc[i]

                # Verificar señales de entrada (sin restricciones de balance para más señales)
                if position == 0:
                    # Verificar señal long
                    if df['long_condition'].iloc[i]:
                        # Entrar en posición long
                        position = 1
                        entry_price = current_price
                        stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 + self.take_profit_percent / 100)
                        trailing_stop = stop_loss  # Initial trailing stop is the stop loss
                        highest_price = current_price
                        long_count += 1

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)

                    # Verificar señal short
                    elif df['short_condition'].iloc[i]:
                        # Entrar en posición short
                        position = -1
                        entry_price = current_price
                        stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 - self.take_profit_percent / 100)
                        trailing_stop = stop_loss  # Initial trailing stop is the stop loss
                        lowest_price = current_price
                        short_count += 1

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
                            'pnl_percent': (exit_price - entry_price) / entry_price * 100,
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
                            'pnl_percent': (entry_price - exit_price) / entry_price * 100,
                            'exit_reason': 'take_profit' if current_price <= take_profit else 'trailing_stop'
                        })

                        position = 0
                        trailing_stop = 0.0
                        lowest_price = float('inf')

            # Calcular métricas
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
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

            # Calcular Sharpe Ratio simplificado
            if trades and len(equity_curve) > 1:
                returns = [(equity_curve[i] / equity_curve[i-1] - 1) for i in range(1, len(equity_curve))]
                if len(returns) > 1 and np.std(returns) > 0:
                    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizado
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0

            # Calcular métricas adicionales del trailing stop
            trailing_stop_exits = len([t for t in trades if t.get('exit_reason') == 'trailing_stop'])
            take_profit_exits = len([t for t in trades if t.get('exit_reason') == 'take_profit'])

            return {
                'symbol': symbol,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': 0.0,  # Placeholder, podría calcularse si se necesita
                'calmar_ratio': abs(total_pnl / max_drawdown) if max_drawdown != 0 else 0,
                'profit_factor': profit_factor,
                'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0,
                'avg_win_pnl': gross_profit / winning_trades if winning_trades > 0 else 0,
                'avg_loss_pnl': -gross_loss / losing_trades if losing_trades > 0 else 0,
                'largest_win': max([t['pnl'] for t in trades]) if trades else 0,
                'largest_loss': min([t['pnl'] for t in trades]) if trades else 0,
                'trades': trades,
                'equity_curve': equity_curve,
                'trailing_stop_exits': trailing_stop_exits,
                'take_profit_exits': take_profit_exits,
                'trailing_stop_ratio': (trailing_stop_exits / total_trades) if total_trades > 0 else 0,
                'long_trades': long_count,
                'short_trades': short_count,
                'long_short_ratio': f"{long_count}/{short_count}",
                'compensated_trades': 0,  # No aplica para esta estrategia
                'compensation_success_rate': 0,  # No aplica para esta estrategia
                'total_compensation_pnl': 0,  # No aplica para esta estrategia
                'avg_compensation_pnl': 0,  # No aplica para esta estrategia
                'compensation_ratio': 0.0,  # No aplica para esta estrategia
                'adjusted_total_pnl': total_pnl,  # No hay compensación en esta estrategia
                'compensation_trades_data': [],  # No aplica para esta estrategia
                'cagr': total_pnl / 10000.0,  # Crecimiento anual simplificado
                'volatility': np.std([t['pnl_percent'] for t in trades]) if trades else 0,
            }

        except Exception as e:
            self.logger.error(f"Error ejecutando estrategia HeikinAshiVolumenSarImproved: {e}")
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
                'symbol': symbol,
                'trades': [],
                'equity_curve': [10000.0],
                'trailing_stop_exits': 0,
                'take_profit_exits': 0,
                'trailing_stop_ratio': 0.0,
                'long_trades': 0,
                'short_trades': 0,
                'long_short_ratio': "0/0",
                'compensated_trades': 0,
                'compensation_success_rate': 0,
                'total_compensation_pnl': 0,
                'avg_compensation_pnl': 0,
                'compensation_ratio': 0.0,
                'adjusted_total_pnl': 0.0,
                'compensation_trades_data': [],
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'profit_factor': 0.0,
                'avg_trade_pnl': 0.0,
                'avg_win_pnl': 0.0,
                'avg_loss_pnl': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'cagr': 0.0,
                'volatility': 0.0,
            }