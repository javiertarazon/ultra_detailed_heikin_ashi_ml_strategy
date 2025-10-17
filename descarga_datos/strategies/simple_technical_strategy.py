"""
Estrategia Simple de Trading Técnico - Sin ML
Usa indicadores básicos: RSI, EMA, MACD
"""

from typing import Dict, List, Any
import pandas as pd
import numpy as np
from indicators.technical_indicators import TechnicalIndicators

class SimpleTechnicalStrategy:
    """
    Estrategia simple basada en indicadores técnicos tradicionales
    Sin dependencia de Machine Learning
    """

    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.name = "SimpleTechnicalStrategy"

        # Parámetros de la estrategia
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.ema_fast = 9
        self.ema_slow = 21
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 3.0

    def run(self, data: pd.DataFrame, symbol: str, timeframe: str = "1h") -> Dict[str, Any]:
        """
        Ejecuta la estrategia de trading técnico simple

        Args:
            data: DataFrame con datos OHLCV
            symbol: Símbolo del activo

        Returns:
            Dict con resultados del backtesting
        """
        try:
            print(f"🔄 Ejecutando estrategia SimpleTechnical para {symbol}")

            # Calcular indicadores
            data = self._calculate_indicators(data)

            # Generar señales
            signals = self._generate_signals(data)

            # Ejecutar backtesting
            results = self._run_backtest(data, signals, symbol)

            print(f"✅ Estrategia completada: {results['total_trades']} trades")

            return results

        except Exception as e:
            print(f"❌ Error en estrategia SimpleTechnical: {e}")
            return self._get_empty_results(symbol)

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores técnicos necesarios"""
        df = data.copy()

        # Usar el método centralizado para calcular todos los indicadores
        df = self.indicators.calculate_all_indicators_unified(df)
        
        # Los indicadores ya están calculados:
        # - rsi: RSI 14
        # - ema_9, ema_21: EMAs rápidas y lentas  
        # - macd, macd_signal, macd_hist: MACD
        # - atr: Average True Range

        return df

    def _generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Genera señales de compra/venta basadas en indicadores"""
        signals = pd.Series(0, index=data.index, name='signal')

        # Condiciones de compra
        buy_condition = (
            (data['rsi'] < self.rsi_oversold) &  # RSI oversold
            (data['ema_9'] > data['ema_21']) &  # Trend up
            (data['macd'] > data['macd_signal'])  # MACD positive
        )

        # Condiciones de venta
        sell_condition = (
            (data['rsi'] > self.rsi_overbought) |  # RSI overbought
            (data['ema_9'] < data['ema_21']) |  # Trend down
            (data['macd'] < data['macd_signal'])  # MACD negative
        )

        signals[buy_condition] = 1  # Buy signal
        signals[sell_condition] = -1  # Sell signal

        return signals

    def _run_backtest(self, data: pd.DataFrame, signals: pd.Series, symbol: str) -> Dict[str, Any]:
        """Ejecuta el backtesting con las señales generadas"""
        trades = []
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0
        entry_time = None
        capital = 1000.0  # Capital inicial
        position_size = 0

        for i in range(len(data)):
            current_price = data.iloc[i]['close']
            current_time = data.index[i]
            atr = data.iloc[i]['atr'] if not pd.isna(data.iloc[i]['atr']) else 0.01

            signal = signals.iloc[i]

            # Abrir posición larga
            if position == 0 and signal == 1:
                position = 1
                entry_price = current_price
                entry_time = current_time
                position_size = capital * 0.1  # 10% del capital
                stop_loss = entry_price - (atr * self.stop_loss_atr)
                take_profit = entry_price + (atr * self.take_profit_atr)

                print(f"🟢 LONG en {current_time}: ${entry_price:.4f}")

            # Abrir posición corta
            elif position == 0 and signal == -1:
                position = -1
                entry_price = current_price
                entry_time = current_time
                position_size = capital * 0.1  # 10% del capital
                stop_loss = entry_price + (atr * self.stop_loss_atr)
                take_profit = entry_price - (atr * self.take_profit_atr)

                print(f"🔴 SHORT en {current_time}: ${entry_price:.4f}")

            # Cerrar posición larga
            elif position == 1:
                # Check stop loss
                if current_price <= stop_loss:
                    pnl = (current_price - entry_price) / entry_price * position_size
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'direction': 'long',
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    position = 0
                    print(f"🔴 STOP LOSS LONG: ${current_price:.4f}, PnL: ${pnl:.2f}")

                # Check take profit
                elif current_price >= take_profit:
                    pnl = (current_price - entry_price) / entry_price * position_size
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'direction': 'long',
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    position = 0
                    print(f"🟢 TAKE PROFIT LONG: ${current_price:.4f}, PnL: ${pnl:.2f}")

            # Cerrar posición corta
            elif position == -1:
                # Check stop loss
                if current_price >= stop_loss:
                    pnl = (entry_price - current_price) / entry_price * position_size
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'direction': 'short',
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    position = 0
                    print(f"🔴 STOP LOSS SHORT: ${current_price:.4f}, PnL: ${pnl:.2f}")

                # Check take profit
                elif current_price <= take_profit:
                    pnl = (entry_price - current_price) / entry_price * position_size
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'direction': 'short',
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    position = 0
                    print(f"🟢 TAKE PROFIT SHORT: ${current_price:.4f}, PnL: ${pnl:.2f}")

        # Calcular métricas
        return self._calculate_metrics(trades, capital, symbol)

    def _calculate_metrics(self, trades: List[Dict], final_capital: float, symbol: str) -> Dict[str, Any]:
        """Calcula métricas de rendimiento"""
        if not trades:
            return self._get_empty_results(symbol)

        # Métricas básicas
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Drawdown máximo (simplificado)
        capital_history = [1000.0]
        current_capital = 1000.0
        max_capital = 1000.0
        max_drawdown = 0

        for trade in trades:
            current_capital += trade['pnl']
            capital_history.append(current_capital)
            max_capital = max(max_capital, current_capital)
            drawdown = (max_capital - current_capital) / max_capital
            max_drawdown = max(max_drawdown, drawdown)

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_capital': final_capital,
            'return_pct': (final_capital - 1000.0) / 1000.0 * 100,
            'symbol': symbol,
            'strategy_name': self.name,
            'trades': trades
        }

    def _get_empty_results(self, symbol: str) -> Dict[str, Any]:
        """Retorna resultados vacíos cuando no hay trades"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'final_capital': 1000.0,
            'return_pct': 0.0,
            'symbol': symbol,
            'strategy_name': self.name,
            'trades': []
        }