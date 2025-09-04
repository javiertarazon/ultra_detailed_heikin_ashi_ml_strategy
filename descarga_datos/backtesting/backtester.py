"""
Motor de backtesting avanzado para estrategias de trading.
Incluye métricas profesionales y gestión realista de costos.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..risk_management.risk_management import get_risk_manager

@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    position_type: str  # 'long' o 'short'
    exit_reason: str  # 'stop_loss', 'take_profit', 'psar_exit'
    commission: float = 0.0
    slippage: float = 0.0
    signal_strength: float = 0.0

class AdvancedBacktester:
    def __init__(self,
                 initial_capital: float = 10000,
                 commission: float = 0.1,
                 slippage: float = 0.05):
        self.initial_capital = initial_capital
        self.commission = commission / 100  # Convertir a decimal
        self.slippage = slippage / 100  # Convertir a decimal
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_position = 0  # 0: flat, 1: long, -1: short
        self.current_capital = initial_capital

        # Integrar sistema de gestión de riesgo
        self.risk_manager = get_risk_manager()
        self.risk_manager.portfolio_value = initial_capital
        self.risk_manager.daily_returns = []
        self.symbol = ""  # Se establecerá cuando se ejecute el backtest

    def run(self, strategy, df: pd.DataFrame, symbol: str = "") -> Dict:
        """
        Ejecuta el backtesting de una estrategia en los datos proporcionados.
        Compatible con estrategias tradicionales y optimizadas.
        """
        # Establecer símbolo para gestión de riesgo
        self.symbol = symbol or "BACKTEST"
        self.risk_manager.positions = {}  # Resetear posiciones para nuevo backtest

        # Detectar tipo de estrategia
        if hasattr(strategy, 'generate_signal'):
            # Estrategia optimizada (usa generate_signal)
            return self._run_optimized_strategy(strategy, df)
        else:
            # Estrategia tradicional (usa calculate_signals)
            return self._run_traditional_strategy(strategy, df)
        
        # Variables de seguimiento
        self.equity_curve = [self.initial_capital]
        current_trade = None
        position_size = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0

        # Iterar sobre cada vela
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Actualizar capital si hay una posición abierta
            if self.current_position != 0:
                # Verificar stop loss
                if (self.current_position == 1 and current_row['ha_low'] <= stop_loss) or \
                   (self.current_position == -1 and current_row['ha_high'] >= stop_loss):
                    self._close_position(stop_loss, current_row.name, 'stop_loss')
                
                # Verificar take profit
                elif (self.current_position == 1 and current_row['ha_high'] >= take_profit) or \
                     (self.current_position == -1 and current_row['ha_low'] <= take_profit):
                    self._close_position(take_profit, current_row.name, 'take_profit')
                
                # Verificar salida por PSAR
                elif ((self.current_position == 1 and current_row['psar_trend_change'] and current_row['psar_bearish']) or
                      (self.current_position == -1 and current_row['psar_trend_change'] and current_row['psar_bullish'])):
                    self._close_position(current_row['ha_close'], current_row.name, 'psar_exit')

            # Verificar señales de entrada si no hay posición abierta
            if self.current_position == 0:
                # Verificar si el risk manager permite abrir nuevas posiciones
                if self.risk_manager.should_halt_trading():
                    continue  # Saltar esta vela si el trading está detenido

                if current_row['buy_signal']:
                    entry_price = current_row['ha_close']
                    stop_loss = strategy.calculate_stop_loss(df.iloc[i:i+1], 1).iloc[0]
                    take_profit = strategy.calculate_take_profit(df.iloc[i:i+1], 1).iloc[0]

                    # Calcular tamaño base de posición
                    base_position_size = strategy.calculate_position_size(
                        self.current_capital, entry_price, stop_loss)

                    # Aplicar ajustes dinámicos del risk manager
                    drawdown_adjustment = self.risk_manager.calculate_drawdown_adjustment()
                    correlation_adjustment = self.risk_manager.calculate_correlation_adjustment(self.symbol)
                    performance_adjustment = self.risk_manager.calculate_performance_adjustment()

                    # Calcular tamaño final de posición con ajustes
                    position_size = base_position_size * drawdown_adjustment * correlation_adjustment * performance_adjustment

                    # Verificar si se debe reducir exposición
                    if self.risk_manager.should_reduce_exposure():
                        position_size *= 0.7  # Reducir 30% si hay señales de riesgo alto

                    self._open_position(1, position_size, entry_price, current_row.name, stop_loss, take_profit)

                elif current_row['sell_signal']:
                    entry_price = current_row['ha_close']
                    stop_loss = strategy.calculate_stop_loss(df.iloc[i:i+1], -1).iloc[0]
                    take_profit = strategy.calculate_take_profit(df.iloc[i:i+1], -1).iloc[0]

                    # Calcular tamaño base de posición
                    base_position_size = strategy.calculate_position_size(
                        self.current_capital, entry_price, stop_loss)

                    # Aplicar ajustes dinámicos del risk manager
                    drawdown_adjustment = self.risk_manager.calculate_drawdown_adjustment()
                    correlation_adjustment = self.risk_manager.calculate_correlation_adjustment(self.symbol)
                    performance_adjustment = self.risk_manager.calculate_performance_adjustment()

                    # Calcular tamaño final de posición con ajustes
                    position_size = base_position_size * drawdown_adjustment * correlation_adjustment * performance_adjustment

                    # Verificar si se debe reducir exposición
                    if self.risk_manager.should_reduce_exposure():
                        position_size *= 0.7  # Reducir 30% si hay señales de riesgo alto

                    self._open_position(-1, position_size, entry_price, current_row.name, stop_loss, take_profit)

            # Actualizar equity curve y calcular retornos diarios
            self.equity_curve.append(self.current_capital)

            # Calcular retorno diario para el risk manager
            if len(self.equity_curve) >= 2:
                daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
                self.risk_manager.daily_returns.append(daily_return)

                # Actualizar drawdown en el risk manager
                if self.current_capital > self.risk_manager.peak_equity:
                    self.risk_manager.peak_equity = self.current_capital

                current_drawdown = (self.risk_manager.peak_equity - self.current_capital) / self.risk_manager.peak_equity
                if current_drawdown > self.risk_manager.current_drawdown:
                    self.risk_manager.current_drawdown = current_drawdown
                    self.risk_manager.max_drawdown_reached = max(self.risk_manager.max_drawdown_reached, current_drawdown)

            # Actualizar portfolio value en risk manager
            self.risk_manager.portfolio_value = self.current_capital

        # Cerrar posición al final si está abierta
        if self.current_position != 0:
            self._close_position(df.iloc[-1]['ha_close'], df.index[-1], 'end_of_data')

        return self._calculate_advanced_statistics()

    def _open_position(self, direction: int, size: float, price: float, timestamp: datetime, stop_loss: float = None, take_profit: float = None):
        """Abre una nueva posición con slippage realista"""
        # Aplicar slippage al precio de entrada
        slippage_amount = price * self.slippage
        if direction == 1:  # Long
            actual_price = price + slippage_amount
        else:  # Short
            actual_price = price - slippage_amount

        self.current_position = direction
        self.position_size = size
        self.entry_price = actual_price
        self.entry_time = timestamp

        # Aplicar comisión
        commission_cost = abs(size * actual_price * self.commission)
        self.current_capital -= commission_cost

        # Usar valores por defecto si no se proporcionan
        if stop_loss is None:
            stop_loss = actual_price * 0.95 if direction == 1 else actual_price * 1.05
        if take_profit is None:
            take_profit = actual_price * 1.05 if direction == 1 else actual_price * 0.95

        # Actualizar risk manager con nueva posición
        from ..risk_management.risk_management import Position
        position = Position(
            symbol=self.symbol,
            quantity=size if direction == 1 else -size,
            entry_price=actual_price,
            current_price=actual_price,
            entry_time=timestamp,
            position_type='long' if direction == 1 else 'short',
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.risk_manager.positions[self.symbol] = position
        self.risk_manager.portfolio_value = self.current_capital

    def _close_position(self, price: float, timestamp: datetime, reason: str):
        """Cierra la posición actual con slippage realista"""
        if self.current_position == 0:
            return

        # Aplicar slippage al precio de salida
        slippage_amount = price * self.slippage
        if self.current_position == 1:  # Cerrando long
            actual_price = price - slippage_amount
        else:  # Cerrando short
            actual_price = price + slippage_amount

        # Calcular P&L
        position_type = 'long' if self.current_position == 1 else 'short'
        pnl = self.position_size * (actual_price - self.entry_price) if self.current_position == 1 else \
              self.position_size * (self.entry_price - actual_price)

        # Aplicar comisión de salida
        exit_commission = abs(self.position_size * actual_price * self.commission)
        total_commission = abs(self.position_size * self.entry_price * self.commission) + exit_commission
        pnl -= exit_commission

        # Actualizar capital
        self.current_capital += pnl

        # Actualizar risk manager
        if self.symbol in self.risk_manager.positions:
            # Actualizar precio actual de la posición antes de cerrarla
            self.risk_manager.positions[self.symbol].current_price = actual_price
            # Registrar el trade en el historial del risk manager
            trade_record = {
                'symbol': self.symbol,
                'entry_time': self.entry_time,
                'exit_time': timestamp,
                'entry_price': self.entry_price,
                'exit_price': actual_price,
                'quantity': self.position_size if self.current_position == 1 else -self.position_size,
                'pnl': pnl,
                'success': pnl > 0
            }
            self.risk_manager.trade_history.append(trade_record)
            # Remover posición del risk manager
            del self.risk_manager.positions[self.symbol]

        self.risk_manager.portfolio_value = self.current_capital

        # Registrar trade
        self.trades.append(Trade(
            entry_time=self.entry_time,
            exit_time=timestamp,
            entry_price=self.entry_price,
            exit_price=actual_price,
            position_size=self.position_size,
            pnl=pnl,
            position_type=position_type,
            exit_reason=reason,
            commission=total_commission,
            slippage=slippage_amount * 2  # Slippage de entrada + salida
        ))

        # Resetear posición
        self.current_position = 0
        self.position_size = 0
        self.entry_price = 0
        self.entry_time = None

    def _calculate_advanced_statistics(self) -> Dict:
        """Calcula métricas avanzadas de trading profesional"""
        if not self.trades:
            return self._get_empty_metrics()

        # Datos básicos
        total_trades = len(self.trades)
        profitable_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        # Métricas básicas
        win_rate = len(profitable_trades) / total_trades if total_trades > 0 else 0
        total_pnl = sum(t.pnl for t in self.trades)
        total_commission = sum(t.commission for t in self.trades)
        total_slippage = sum(t.slippage for t in self.trades)

        # Retorno total y CAGR
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        equity = np.array(self.equity_curve)
        if len(equity) > 1:
            # Asumiendo datos diarios para CAGR (252 días de trading)
            periods_per_year = 252
            total_periods = len(equity) - 1
            cagr = (equity[-1] / equity[0]) ** (periods_per_year / total_periods) - 1
        else:
            cagr = 0

        # Drawdown avanzado
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(np.min(drawdown)) * 100

        # Duración del drawdown máximo
        in_drawdown = drawdown < 0
        if np.any(in_drawdown):
            dd_durations = []
            current_dd = 0
            for is_dd in in_drawdown:
                if is_dd:
                    current_dd += 1
                else:
                    if current_dd > 0:
                        dd_durations.append(current_dd)
                    current_dd = 0
            if current_dd > 0:
                dd_durations.append(current_dd)
            max_dd_duration = max(dd_durations) if dd_durations else 0
        else:
            max_dd_duration = 0

        # Sharpe y Sortino Ratio
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) > 0 and returns.std() != 0:
            sharpe_ratio = np.sqrt(252) * (returns.mean() / returns.std())

            # Sortino Ratio (solo downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_deviation = downside_returns.std()
                sortino_ratio = np.sqrt(252) * (returns.mean() / downside_deviation)
            else:
                sortino_ratio = float('inf')
        else:
            sharpe_ratio = 0
            sortino_ratio = 0

        # Métricas de trades
        if profitable_trades:
            avg_win = np.mean([t.pnl for t in profitable_trades])
            largest_win = max([t.pnl for t in profitable_trades])
        else:
            avg_win = 0
            largest_win = 0

        if losing_trades:
            avg_loss = np.mean([abs(t.pnl) for t in losing_trades])
            largest_loss = max([abs(t.pnl) for t in losing_trades])
        else:
            avg_loss = 0
            largest_loss = 0

        # Profit Factor
        total_profit = sum([t.pnl for t in profitable_trades])
        total_loss = sum([abs(t.pnl) for t in losing_trades])
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Win/Loss Ratio
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

        # Calmar Ratio
        calmar_ratio = cagr / (max_drawdown / 100) if max_drawdown != 0 else float('inf')

        # Recovery Factor
        recovery_factor = total_pnl / (abs(max_drawdown) / 100 * self.initial_capital) if max_drawdown != 0 else float('inf')

        return {
            # Métricas básicas
            "total_trades": total_trades,
            "profitable_trades": len(profitable_trades),
            "loss_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_return": total_return,
            "total_return_pct": total_return * 100,

            # Costos de trading
            "total_commission": total_commission,
            "total_slippage": total_slippage,
            "total_costs": total_commission + total_slippage,

            # Métricas avanzadas
            "cagr": cagr,
            "cagr_pct": cagr * 100,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "recovery_factor": recovery_factor,

            # Drawdown
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_dd_duration,

            # Métricas de trades
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "win_loss_ratio": win_loss_ratio,

            # Datos adicionales
            "equity_curve": self.equity_curve,
            "trades": self.trades
        }

    def _get_empty_metrics(self) -> Dict:
        """Retorna métricas vacías cuando no hay trades"""
        return {
            "total_trades": 0,
            "profitable_trades": 0,
            "loss_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_return": 0,
            "total_return_pct": 0,
            "total_commission": 0,
            "total_slippage": 0,
            "total_costs": 0,
            "cagr": 0,
            "cagr_pct": 0,
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "calmar_ratio": 0,
            "recovery_factor": 0,
            "max_drawdown": 0,
            "max_drawdown_duration": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "win_loss_ratio": 0,
            "equity_curve": self.equity_curve,
            "trades": []
        }

    def _run_traditional_strategy(self, strategy, df: pd.DataFrame) -> Dict:
        """
        Ejecuta backtesting para estrategias tradicionales (UTBotPSARStrategy)
        """
        # Calcular señales
        df = strategy.calculate_signals(df)

        # Variables de seguimiento
        self.equity_curve = [self.initial_capital]
        current_trade = None
        position_size = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0

        # Iterar sobre cada vela
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]

            # Actualizar capital si hay una posición abierta
            if self.current_position != 0:
                # Verificar stop loss
                if (self.current_position == 1 and current_row['ha_low'] <= stop_loss) or \
                   (self.current_position == -1 and current_row['ha_high'] >= stop_loss):
                    self._close_position(stop_loss, current_row.name, 'stop_loss')

                # Verificar take profit
                elif (self.current_position == 1 and current_row['ha_high'] >= take_profit) or \
                     (self.current_position == -1 and current_row['ha_low'] <= take_profit):
                    self._close_position(take_profit, current_row.name, 'take_profit')

                # Verificar salida por PSAR
                elif ((self.current_position == 1 and current_row['psar_trend_change'] and current_row['psar_bearish']) or
                      (self.current_position == -1 and current_row['psar_trend_change'] and current_row['psar_bullish'])):
                    self._close_position(current_row['ha_close'], current_row.name, 'psar_exit')

            # Verificar señales de entrada si no hay posición abierta
            if self.current_position == 0:
                # Verificar si el risk manager permite abrir nuevas posiciones
                if self.risk_manager.should_halt_trading():
                    continue  # Saltar esta vela si el trading está detenido

                if current_row['buy_signal']:
                    entry_price = current_row['ha_close']
                    stop_loss = strategy.calculate_stop_loss(df.iloc[i:i+1], 1).iloc[0]
                    take_profit = strategy.calculate_take_profit(df.iloc[i:i+1], 1).iloc[0]

                    # Calcular tamaño base de posición
                    base_position_size = strategy.calculate_position_size(
                        self.current_capital, entry_price, stop_loss)

                    # Aplicar ajustes dinámicos del risk manager
                    drawdown_adjustment = self.risk_manager.calculate_drawdown_adjustment()
                    correlation_adjustment = self.risk_manager.calculate_correlation_adjustment(self.symbol)
                    performance_adjustment = self.risk_manager.calculate_performance_adjustment()

                    # Calcular tamaño final de posición con ajustes
                    position_size = base_position_size * drawdown_adjustment * correlation_adjustment * performance_adjustment

                    # Verificar si se debe reducir exposición
                    if self.risk_manager.should_reduce_exposure():
                        position_size *= 0.7  # Reducir 30% si hay señales de riesgo alto

                    self._open_position(1, position_size, entry_price, current_row.name, stop_loss, take_profit)

                elif current_row['sell_signal']:
                    entry_price = current_row['ha_close']
                    stop_loss = strategy.calculate_stop_loss(df.iloc[i:i+1], -1).iloc[0]
                    take_profit = strategy.calculate_take_profit(df.iloc[i:i+1], -1).iloc[0]

                    # Calcular tamaño base de posición
                    base_position_size = strategy.calculate_position_size(
                        self.current_capital, entry_price, stop_loss)

                    # Aplicar ajustes dinámicos del risk manager
                    drawdown_adjustment = self.risk_manager.calculate_drawdown_adjustment()
                    correlation_adjustment = self.risk_manager.calculate_correlation_adjustment(self.symbol)
                    performance_adjustment = self.risk_manager.calculate_performance_adjustment()

                    # Calcular tamaño final de posición con ajustes
                    position_size = base_position_size * drawdown_adjustment * correlation_adjustment * performance_adjustment

                    # Verificar si se debe reducir exposición
                    if self.risk_manager.should_reduce_exposure():
                        position_size *= 0.7  # Reducir 30% si hay señales de riesgo alto

                    self._open_position(-1, position_size, entry_price, current_row.name, stop_loss, take_profit)

            # Actualizar equity curve y calcular retornos diarios
            self.equity_curve.append(self.current_capital)

            # Calcular retorno diario para el risk manager
            if len(self.equity_curve) >= 2:
                daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
                self.risk_manager.daily_returns.append(daily_return)

                # Actualizar drawdown en el risk manager
                if self.current_capital > self.risk_manager.peak_equity:
                    self.risk_manager.peak_equity = self.current_capital

                current_drawdown = (self.risk_manager.peak_equity - self.current_capital) / self.risk_manager.peak_equity
                if current_drawdown > self.risk_manager.current_drawdown:
                    self.risk_manager.current_drawdown = current_drawdown
                    self.risk_manager.max_drawdown_reached = max(self.risk_manager.max_drawdown_reached, current_drawdown)

            # Actualizar portfolio value en risk manager
            self.risk_manager.portfolio_value = self.current_capital

        # Cerrar posición al final si está abierta
        if self.current_position != 0:
            self._close_position(df.iloc[-1]['ha_close'], df.index[-1], 'end_of_data')

        return self._calculate_advanced_statistics()

    def _run_optimized_strategy(self, strategy, df: pd.DataFrame) -> Dict:
        """
        Ejecuta backtesting para estrategias optimizadas (OptimizedUTBotStrategy)
        """
        # Variables de seguimiento
        self.equity_curve = [self.initial_capital]
        current_trade = None
        position_size = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0

        # Iterar sobre cada vela
        for i in range(max(strategy.atr_period, 20), len(df)):
            current_row = df.iloc[i]

            # Actualizar capital si hay una posición abierta
            if self.current_position != 0:
                # Verificar stop loss
                if (self.current_position == 1 and current_row['low'] <= stop_loss) or \
                   (self.current_position == -1 and current_row['high'] >= stop_loss):
                    self._close_position(stop_loss, current_row.name, 'stop_loss')

                # Verificar take profit
                elif (self.current_position == 1 and current_row['high'] >= take_profit) or \
                     (self.current_position == -1 and current_row['low'] <= take_profit):
                    self._close_position(take_profit, current_row.name, 'take_profit')

            # Generar señal con la estrategia optimizada
            if self.current_position == 0:
                # Verificar si el risk manager permite abrir nuevas posiciones
                if self.risk_manager.should_halt_trading():
                    self.equity_curve.append(self.current_capital)
                    continue  # Saltar esta vela si el trading está detenido

                # Usar datos históricos para generar señal
                historical_data = df.iloc[max(0, i-50):i+1]  # Últimas 50 velas + vela actual
                signal_result = strategy.generate_signal(historical_data)

                if signal_result and signal_result.signal != 'HOLD' and signal_result.confidence >= strategy.min_confidence:
                    entry_price = signal_result.entry_price
                    stop_loss = signal_result.stop_loss
                    take_profit = signal_result.take_profit

                    # Calcular tamaño base de posición usando ATR
                    current_atr = historical_data['atr'].iloc[-1] if 'atr' in historical_data.columns else historical_data['close'].iloc[-1] * 0.02
                    risk_amount = self.current_capital * 0.02  # 2% de capital por trade
                    position_size = risk_amount / (abs(entry_price - stop_loss) / entry_price)

                    # Aplicar ajustes dinámicos del risk manager
                    drawdown_adjustment = self.risk_manager.calculate_drawdown_adjustment()
                    correlation_adjustment = self.risk_manager.calculate_correlation_adjustment(self.symbol)
                    performance_adjustment = self.risk_manager.calculate_performance_adjustment()

                    # Calcular tamaño final de posición con ajustes
                    position_size = position_size * drawdown_adjustment * correlation_adjustment * performance_adjustment

                    # Verificar si se debe reducir exposición
                    if self.risk_manager.should_reduce_exposure():
                        position_size *= 0.7  # Reducir 30% si hay señales de riesgo alto

                    # Abrir posición
                    if signal_result.signal == 'BUY':
                        self._open_position(1, position_size, entry_price, current_row.name, stop_loss, take_profit)
                    elif signal_result.signal == 'SELL':
                        self._open_position(-1, position_size, entry_price, current_row.name, stop_loss, take_profit)

            # Actualizar equity curve y calcular retornos diarios
            self.equity_curve.append(self.current_capital)

            # Calcular retorno diario para el risk manager
            if len(self.equity_curve) >= 2:
                daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
                self.risk_manager.daily_returns.append(daily_return)

                # Actualizar drawdown en el risk manager
                if self.current_capital > self.risk_manager.peak_equity:
                    self.risk_manager.peak_equity = self.current_capital

                current_drawdown = (self.risk_manager.peak_equity - self.current_capital) / self.risk_manager.peak_equity
                if current_drawdown > self.risk_manager.current_drawdown:
                    self.risk_manager.current_drawdown = current_drawdown
                    self.risk_manager.max_drawdown_reached = max(self.risk_manager.max_drawdown_reached, current_drawdown)

            # Actualizar portfolio value en risk manager
            self.risk_manager.portfolio_value = self.current_capital

        # Cerrar posición al final si está abierta
        if self.current_position != 0:
            self._close_position(df.iloc[-1]['close'], df.index[-1], 'end_of_data')

        return self._calculate_advanced_statistics()
