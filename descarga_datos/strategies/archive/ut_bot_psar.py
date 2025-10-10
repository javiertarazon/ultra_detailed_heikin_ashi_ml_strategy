"""
Implementación de la estrategia UT Bot + PSAR.
"""
import numpy as np
import pandas as pd
from utils.talib_wrapper import talib
from base_strategy import BaseStrategy

class UTBotPSARStrategy(BaseStrategy):
    def __init__(self, 
                 sensitivity=1,
                 atr_period=10,
                 use_heikin_ashi=False,
                 risk_percent=2.0,
                 tp_atr_multiplier=3.0,  # AJUSTADO: Mejor ratio riesgo/recompensa
                 sl_atr_multiplier=1.0,  # AJUSTADO: Mejor ratio riesgo/recompensa
                 psar_start=0.02,
                 psar_increment=0.02,
                 psar_max=0.2,
                 max_drawdown_limit=25.0,  # NUEVO: Límite de drawdown global al 25%
                 config=None):
        super().__init__(config)
        self.sensitivity = sensitivity
        self.atr_period = atr_period
        self.use_heikin_ashi = use_heikin_ashi
        self.risk_percent = risk_percent
        self.tp_atr_multiplier = tp_atr_multiplier
        self.sl_atr_multiplier = sl_atr_multiplier
        self.psar_start = psar_start
        self.psar_increment = psar_increment
        self.psar_max = psar_max
        self.max_drawdown_limit = max_drawdown_limit  # Límite de drawdown global

    def calculate_signals(self, df):
        """
        Calcula las señales usando los indicadores ya existentes en los datos.
        Los datos deben contener: atr, sar, ema_10, ema_20, ema_200
        """
        if self.use_heikin_ashi:
            heikin_ashi_df = self.indicators.calculate_heikin_ashi(df)
            df = pd.concat([df, heikin_ashi_df], axis=1)
            price_col = 'ha_close'
        else:
            # Agregar columnas como alias para compatibilidad
            df['ha_close'] = df['close']
            df['ha_high'] = df['high']
            df['ha_low'] = df['low']
            price_col = 'close'

        # Usar ATR existente
        df['n_loss'] = self.sensitivity * df['atr']

        # Usar SAR existente
        df['psar'] = df['sar']  # Renombrar para mantener consistencia con el código
        df['psar_bullish'] = df[price_col] > df['sar']
        df['psar_bearish'] = df[price_col] < df['sar']
        df['psar_trend_change'] = df['psar_bullish'] != df['psar_bullish'].shift(1)

        # Calcular RSI para filtro adicional
        df['rsi'] = talib.RSI(df[price_col], timeperiod=14)

        # Calcular trailing stop de manera más robusta
        trailing_stop_values = []
        current_stop = df['ha_close'].iloc[0]

        for i in range(len(df)):
            price = df[price_col].iloc[i]
            n_loss = df['n_loss'].iloc[i]

            if i == 0:
                trailing_stop_values.append(price - n_loss if price > current_stop else price + n_loss)
                continue

            prev_stop = trailing_stop_values[-1]

            if price > prev_stop and df[price_col].iloc[i-1] > prev_stop:
                current_stop = max(prev_stop, price - n_loss)
            elif price < prev_stop and df[price_col].iloc[i-1] < prev_stop:
                current_stop = min(prev_stop, price + n_loss)
            else:
                current_stop = price - n_loss if price > prev_stop else price + n_loss

            trailing_stop_values.append(current_stop)

        # Crear la serie con los valores calculados
        df = df.copy()
        df['trailing_stop'] = trailing_stop_values        # Calcular señales de entrada usando EMA existente (usaremos ema_10 como señal rápida)
        df['above'] = (df['ema_10'] > df['trailing_stop']) & (df['ema_10'].shift(1) <= df['trailing_stop'].shift(1))
        df['below'] = (df['ema_10'] < df['trailing_stop']) & (df['ema_10'].shift(1) >= df['trailing_stop'].shift(1))

        # Confirmar señales con tendencia (usando ema_200 como referencia de tendencia)
        long_trend = df[price_col] > df['ema_200']
        short_trend = df[price_col] < df['ema_200']

        # Filtros adicionales con RSI
        long_rsi_filter = df['rsi'] > 30  # Evitar oversold extremos
        short_rsi_filter = df['rsi'] < 70  # Evitar overbought extremos
        
        df['buy_signal'] = (df[price_col] > df['trailing_stop']) & df['above'] & long_trend & long_rsi_filter
        df['sell_signal'] = (df[price_col] < df['trailing_stop']) & df['below'] & short_trend & short_rsi_filter

        return df

    def calculate_position_size(self, capital, entry_price, stop_loss):
        risk_amount = capital * (self.risk_percent / 100)
        return risk_amount / max(abs(entry_price - stop_loss), 0.0001)

    def calculate_stop_loss(self, df, position):
        """
        Calcula el stop loss basado en ATR
        position: 1 para long, -1 para short
        """
        if position == 1:
            return df['ha_close'] - (df['atr'] * self.sl_atr_multiplier)
        else:
            return df['ha_close'] + (df['atr'] * self.sl_atr_multiplier)

    def calculate_take_profit(self, df, position):
        """
        Calcula el take profit basado en ATR
        position: 1 para long, -1 para short
        """
        if position == 1:
            return df['ha_close'] + (df['atr'] * self.tp_atr_multiplier)
        else:
            return df['ha_close'] - (df['atr'] * self.tp_atr_multiplier)

    def run(self, data, symbol, timeframe=None):
        """
        Ejecuta la estrategia y devuelve los resultados del backtesting
        """
        try:
            # Calcular señales
            df = self.calculate_signals(data.copy())
            
            # Inicializar variables de trading
            capital = 10000.0  # Capital inicial
            position = 0  # 0: sin posición, 1: long, -1: short
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            trades = []
            peak_capital = capital  # Nuevo: Para calcular drawdown
            current_balance = capital  # Nuevo: Balance actual
            
            # Simular trading
            for i in range(len(df)):
                current_price = df['close'].iloc[i]
                
                # Calcular drawdown actual
                current_balance = capital
                peak_capital = max(peak_capital, current_balance)
                current_drawdown_pct = ((peak_capital - current_balance) / peak_capital) * 100 if peak_capital > 0 else 0
                
                # Verificar stop-loss global si hay posición abierta
                if position != 0 and current_drawdown_pct >= self.max_drawdown_limit:
                    # Cerrar posición por stop-loss global
                    exit_price = current_price
                    pnl = (exit_price - entry_price) * position_size if position == 1 else (entry_price - exit_price) * position_size
                    capital += pnl
                    
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'type': 'long' if position == 1 else 'short',
                        'emergency_stop': True,
                        'drawdown_at_stop': current_drawdown_pct
                    })
                    
                    position = 0
                    print(f"[GLOBAL STOP] Posición cerrada por drawdown global - Drawdown: {current_drawdown_pct:.2f}% (límite: {self.max_drawdown_limit:.1f}%)")
                    continue

                # Verificar señales de entrada
                if position == 0:
                    if df['buy_signal'].iloc[i]:
                        # Entrar en posición long
                        position = 1
                        entry_price = current_price
                        stop_loss = self.calculate_stop_loss(df.iloc[i:i+1], position).iloc[0]
                        take_profit = self.calculate_take_profit(df.iloc[i:i+1], position).iloc[0]
                        
                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)
                        
                    elif df['sell_signal'].iloc[i]:
                        # Entrar en posición short
                        position = -1
                        entry_price = current_price
                        stop_loss = self.calculate_stop_loss(df.iloc[i:i+1], position).iloc[0]
                        take_profit = self.calculate_take_profit(df.iloc[i:i+1], position).iloc[0]
                        
                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)
                
                # Verificar condiciones de salida
                elif position == 1:  # Posición long
                    if current_price >= take_profit or current_price <= stop_loss:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl
                        peak_capital = max(peak_capital, capital)  # Actualizar peak
                        
                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long'
                        })
                        
                        position = 0
                        
                elif position == -1:  # Posición short
                    if current_price <= take_profit or current_price >= stop_loss:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (entry_price - exit_price) * position_size
                        capital += pnl
                        peak_capital = max(peak_capital, capital)  # Actualizar peak
                        
                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'short'
                        })
                        
                        position = 0
            
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
                'equity_curve': equity_curve
            }
            
        except Exception as e:
            print(f"Error ejecutando estrategia UTBotPSARStrategy: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'symbol': symbol,
                'trades': []
            }
