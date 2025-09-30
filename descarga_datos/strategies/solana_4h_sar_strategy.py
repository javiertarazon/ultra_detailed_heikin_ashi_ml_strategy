"""
Implementación de la estrategia Solana 4H con confirmación SAR.
Basada en Solana4HStrategy pero agrega Parabolic SAR como confirmación de señales.

PARÁMETROS OPTIMIZADOS MEDIANTE MONTE CARLO (29/09/2025):
- Optimización: 500 iteraciones en XRP/USDT
- Mejor Score: 153.10
- Rendimiento: $151,788.72 PNL (1,518% retorno)
- Win Rate: 51.9%
- Max Drawdown: 38.8%
- Profit Factor: 1.52
- Sharpe Ratio: 2.65

PARÁMETROS OPTIMIZADOS XRP/USDT 1H (29/09/2025):
- Optimización: 300 iteraciones Monte Carlo
- Mejor Score: 61980.23
- P&L Validación: $342.70
- Win Rate: 65.9%
- Max Drawdown: 0.0%
- Trades: 44
- Parámetros: volume_threshold=482, take_profit=1.056%, stop_loss=2.173%, volume_sma=17, sar_acc=0.074, sar_max=0.199
"""
import numpy as np
import pandas as pd
import numpy as np
from utils.talib_wrapper import talib

class Solana4HSARStrategy:
    def __init__(self,
                 volume_threshold=None,        # Parámetros específicos por símbolo
                 take_profit_percent=None,
                 stop_loss_percent=None,
                 volume_sma_period=None,
                 sar_acceleration=None,
                 sar_maximum=None,
                 symbol=None,
                 timeframe=None,
                 config=None):  # Nueva: objeto de configuración
        # Parámetros optimizados por defecto (1 día)
        self.default_params = {
            'volume_threshold': 930,
            'take_profit_percent': 2.349,
            'stop_loss_percent': 1.287,
            'volume_sma_period': 25,
            'sar_acceleration': 0.064,
            'sar_maximum': 0.207
        }

        # Cargar parámetros optimizados desde configuración si está disponible
        self.optimized_params = {}
        if config and hasattr(config, 'backtesting') and hasattr(config.backtesting, 'optimized_parameters'):
            # Convertir estructura YAML a formato de tupla
            for symbol_key, timeframes in config.backtesting.optimized_parameters.items():
                if isinstance(timeframes, dict):
                    for tf, params in timeframes.items():
                        if params:  # Solo si hay parámetros definidos
                            self.optimized_params[(symbol_key, tf)] = params

        # Si no hay config, usar parámetros hardcodeados como fallback
        if not self.optimized_params:
            self.optimized_params = {
                ('XRP/USDT', '1h'): {
                    'volume_threshold': 482,
                    'take_profit_percent': 1.056,
                    'stop_loss_percent': 2.173,
                    'volume_sma_period': 17,
                    'sar_acceleration': 0.074,
                    'sar_maximum': 0.199
                }
            }

        # Determinar parámetros a usar
        if symbol and timeframe and (symbol, timeframe) in self.optimized_params:
            params = self.optimized_params[(symbol, timeframe)]
            print(f"🎯 Usando parámetros optimizados para {symbol} {timeframe}")
        else:
            params = self.default_params
            if symbol and timeframe:
                print(f"⚠️  Usando parámetros por defecto para {symbol} {timeframe}")

        # Asignar parámetros
        self.volume_threshold = volume_threshold if volume_threshold is not None else params['volume_threshold']
        self.take_profit_percent = take_profit_percent if take_profit_percent is not None else params['take_profit_percent']
        self.stop_loss_percent = stop_loss_percent if stop_loss_percent is not None else params['stop_loss_percent']
        self.volume_sma_period = volume_sma_period if volume_sma_period is not None else params['volume_sma_period']
        self.sar_acceleration = sar_acceleration if sar_acceleration is not None else params['sar_acceleration']
        self.sar_maximum = sar_maximum if sar_maximum is not None else params['sar_maximum']

        # Guardar símbolo y timeframe para logging
        self.symbol = symbol
        self.timeframe = timeframe

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
        Calcula las señales usando Heiken Ashi, volumen y confirmación SAR.
        """
        # Calcular Heiken Ashi
        ha_df = self.calculate_heikin_ashi(df)
        df = df.copy()
        df['ha_open'] = ha_df['HA_Open']
        df['ha_close'] = ha_df['HA_Close']

        # Calcular Parabolic SAR
        try:
            df['sar'] = talib.SAR(df['high'], df['low'], acceleration=self.sar_acceleration, maximum=self.sar_maximum)
            # Limpiar valores problemáticos
            df['sar'] = df['sar'].bfill().fillna(df['close'])
            # Asegurar que SAR no tenga valores extremos
            df['sar'] = np.clip(df['sar'], df['low'] * 0.9, df['high'] * 1.1)
        except Exception as e:
            # Si el cálculo del SAR falla completamente, usar precio de cierre como fallback
            df['sar'] = df['close']
            print(f"Warning: SAR calculation failed, using close price as fallback: {e}")

        # Media móvil de volumen
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=self.volume_sma_period)

        # Condición de volumen
        df['volume_condition'] = (df['volume'] > self.volume_threshold) & (df['volume'] > df['volume_sma'])

        # Señales base de Heiken Ashi
        df['ha_long_signal'] = df['ha_close'] > df['ha_open']
        df['ha_short_signal'] = df['ha_close'] < df['ha_open']

        # Confirmación SAR
        df['sar_long_confirm'] = df['close'] > df['sar']  # Precio por encima del SAR = bullish
        df['sar_short_confirm'] = df['close'] < df['sar']  # Precio por debajo del SAR = bearish

        # Señales finales con confirmación SAR
        df['long_condition'] = df['volume_condition'] & df['ha_long_signal'] & df['sar_long_confirm']
        df['short_condition'] = df['volume_condition'] & df['ha_short_signal'] & df['sar_short_confirm']

        return df

    def calculate_position_size(self, capital, entry_price, stop_loss):
        """Calcula el tamaño de posición basado en riesgo"""
        risk_amount = capital * 0.02  # 2% de riesgo por trade
        risk_percent = abs(entry_price - stop_loss) / entry_price
        if risk_percent <= 0:
            return 0
        position_value = risk_amount / risk_percent  # Valor de la posición para que el riesgo sea exactamente 2%
        position_size = position_value / entry_price  # Convertir a cantidad de monedas

        # LIMITAR POSITION SIZE PARA EVITAR NÚMEROS IRREALES
        max_position_value = capital * 10  # Máximo 10x el capital actual
        if position_value > max_position_value:
            position_value = max_position_value
            position_size = position_value / entry_price

        return position_size

    def run(self, data, symbol, timeframe='1d'):
        """
        Ejecuta la estrategia y devuelve los resultados del backtesting
        """
        try:
            # Actualizar parámetros si se proporciona timeframe
            if timeframe and symbol and (symbol, timeframe) in self.optimized_params:
                params = self.optimized_params[(symbol, timeframe)]
                self.volume_threshold = params['volume_threshold']
                self.take_profit_percent = params['take_profit_percent']
                self.stop_loss_percent = params['stop_loss_percent']
                self.volume_sma_period = params['volume_sma_period']
                self.sar_acceleration = params['sar_acceleration']
                self.sar_maximum = params['sar_maximum']
                print(f"🎯 Aplicando parámetros optimizados para {symbol} {timeframe}")

            # Calcular señales
            df = self.calculate_signals(data.copy())

            # Validar que el DataFrame tenga las columnas necesarias
            required_columns = ['close', 'long_condition', 'short_condition']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Columna requerida '{col}' no encontrada en el DataFrame")

            # Reemplazar NaN e infinitos
            df = df.fillna(0)
            df = df.replace([np.inf, -np.inf], 0)

            # Inicializar variables de trading
            capital = 10000.0
            position = 0  # 0: sin posición, 1: long, -1: short
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            trades = []
            equity_curve = []  # Inicializar equity curve

            # Simular trading
            for i in range(len(df)):
                # Validar índice antes de acceder
                if i >= len(df) or 'close' not in df.columns:
                    continue

                current_price = df['close'].iloc[i]

                # Validar que el precio sea válido
                if not isinstance(current_price, (int, float)) or np.isnan(current_price) or np.isinf(current_price):
                    continue

                # Verificar señales de entrada
                if position == 0:
                    if df['long_condition'].iloc[i]:
                        # Entrar en posición long
                        position = 1
                        entry_price = current_price
                        stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 + self.take_profit_percent / 100)

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)

                    elif df['short_condition'].iloc[i]:
                        # Entrar en posición short
                        position = -1
                        entry_price = current_price
                        stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
                        take_profit = entry_price * (1 - self.take_profit_percent / 100)

                        position_size = self.calculate_position_size(capital, entry_price, stop_loss)

                # Verificar condiciones de salida
                elif position == 1:  # Posición long
                    if current_price >= take_profit or current_price <= stop_loss:
                        # Cerrar posición
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl

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

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'short'
                        })

                        position = 0

                # Registrar capital en equity curve al final de cada vela
                equity_curve.append(capital)

            # Calcular métricas
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
            total_pnl = sum(t['pnl'] for t in trades)

            # Profit factor
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
            
            # Calcular drawdown correctamente
            equity_array = np.array(equity_curve)
            peak_values = np.maximum.accumulate(equity_array)
            drawdowns = (peak_values - equity_array) / peak_values * 100
            max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,  # Drawdown calculado correctamente
                'sharpe_ratio': 0.0,  # Placeholder
                'profit_factor': profit_factor,
                'symbol': symbol,
                'trades': trades,
                'equity_curve': equity_curve
            }

        except Exception as e:
            print(f"Error ejecutando estrategia Solana4HSARStrategy: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'profit_factor': 0.0,
                'symbol': symbol,
                'trades': [],
                'equity_curve': [10000.0]
            }