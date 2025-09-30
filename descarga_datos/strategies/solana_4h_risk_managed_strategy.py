"""
Implementación de la estrategia Solana 4H con Gestión de Riesgo Avanzada.
Versión mejorada que utiliza el módulo de gestión de riesgo del sistema.
"""
import numpy as np
import pandas as pd
from utils.talib_wrapper import talib
from risk_management.risk_management import AdvancedRiskManager

class Solana4HRiskManagedStrategy:
    def __init__(self,
                 volume_threshold=1000,
                 volume_sma_period=20):
        """
        Inicializa la estrategia con gestión de riesgo avanzada

        Args:
            volume_threshold: Umbral mínimo de volumen
            volume_sma_period: Período para la media móvil de volumen
        """
        self.volume_threshold = volume_threshold
        self.volume_sma_period = volume_sma_period

        # Parámetros para indicadores de calidad
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.momentum_period = 10

        # Parámetros para control de calidad
        self.min_signal_strength = 0.6
        self.max_trades_per_day = 3
        self.daily_trade_count = 0
        self.current_date = None

        # Inicializar el gestor de riesgo
        self.risk_manager = AdvancedRiskManager()
        
        # Configurar valores por defecto si no hay config manager
        if self.risk_manager.config_manager is None:
            # Usar configuración básica por defecto
            self.risk_manager.portfolio_value = 10000.0
            self.risk_manager.risk_config = self.risk_manager.risk_config

        # Parámetros para ATR
        self.atr_period = 14

    def calculate_rsi(self, data):
        """Calcular RSI para momentum"""
        if len(data) < self.rsi_period + 1:
            return 50.0  # Valor neutral si no hay suficientes datos
        
        prices = data['close'].values
        deltas = np.diff(prices)
        seed = deltas[:self.rsi_period+1]
        up = seed[seed >= 0].sum()/self.rsi_period
        down = -seed[seed < 0].sum()/self.rsi_period
        rs = up/down
        rsi = np.zeros_like(prices)
        rsi[:self.rsi_period] = 100. - 100./(1.+rs)

        for i in range(self.rsi_period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up*(self.rsi_period-1) + upval)/self.rsi_period
            down = (down*(self.rsi_period-1) + downval)/self.rsi_period

            rs = up/down
            rsi[i] = 100. - 100./(1.+rs)

        return rsi[-1]

    def calculate_momentum(self, data):
        """Calcular momentum basado en precio"""
        if len(data) < self.momentum_period + 1:
            return 0.0
        
        current_price = data['close'].iloc[-1]
        past_price = data['close'].iloc[-self.momentum_period-1]
        return (current_price - past_price) / past_price * 100

    def calculate_signal_quality(self, data, heiken_ashi_signal):
        """Calcular calidad de la señal combinando múltiples factores"""
        if heiken_ashi_signal == 0:
            return 0.0
        
        quality_score = 0.0
        
        # 1. RSI momentum (30% peso)
        rsi = self.calculate_rsi(data)
        if heiken_ashi_signal > 0:  # Señal de compra
            rsi_score = min(rsi / self.rsi_overbought, 1.0)  # Mejor cuando RSI no está sobrecomprado
        else:  # Señal de venta
            rsi_score = min((100 - rsi) / (100 - self.rsi_oversold), 1.0)  # Mejor cuando no está sobrevendido
        quality_score += rsi_score * 0.3
        
        # 2. Momentum (25% peso)
        momentum = self.calculate_momentum(data)
        if heiken_ashi_signal > 0:
            momentum_score = max(min(momentum / 5.0, 1.0), 0.0)  # Momentum positivo favorece compras
        else:
            momentum_score = max(min(-momentum / 5.0, 1.0), 0.0)  # Momentum negativo favorece ventas
        quality_score += momentum_score * 0.25
        
        # 3. Volumen (25% peso)
        volume_ratio = self.calculate_volume_ratio(data)
        volume_score = min(volume_ratio / 2.0, 1.0)  # Volumen alto mejora calidad
        quality_score += volume_score * 0.25
        
        # 4. ATR volatilidad (20% peso)
        atr = self.calculate_atr(data)
        volatility_score = min(atr / data['close'].iloc[-1] * 100 / 2.0, 1.0)  # Volatilidad moderada es buena
        quality_score += volatility_score * 0.2
        
        return quality_score

    def check_daily_trade_limit(self, current_date):
        """Verificar límite diario de trades"""
        if self.current_date != current_date:
            self.daily_trade_count = 0
            self.current_date = current_date
        
        return self.daily_trade_count < self.max_trades_per_day

    def calculate_volume_ratio(self, data):
        """Calcular ratio de volumen vs promedio"""
        if len(data) < self.volume_sma_period:
            return 1.0
        
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].rolling(self.volume_sma_period).mean().iloc[-1]
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0

    def calculate_atr(self, data):
        """Calcular ATR para volatilidad"""
        if len(data) < self.atr_period + 1:
            return data['high'].iloc[-1] - data['low'].iloc[-1]  # Rango simple
        
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift(1))
        low_close = np.abs(data['low'] - data['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean().iloc[-1]
        
        return atr

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
        Calcula las señales usando Heiken Ashi y volumen.
        """
        # Calcular Heiken Ashi
        ha_df = self.calculate_heikin_ashi(df)
        df = df.copy()
        df['ha_open'] = ha_df['HA_Open']
        df['ha_close'] = ha_df['HA_Close']

        # Media móvil de volumen
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=self.volume_sma_period)

        # Condición de volumen
        df['volume_condition'] = (df['volume'] > self.volume_threshold) & (df['volume'] > df['volume_sma'])

        # Señales de entrada
        df['long_condition'] = df['volume_condition'] & (df['ha_close'] > df['ha_open'])
        df['short_condition'] = df['volume_condition'] & (df['ha_close'] < df['ha_open'])

        return df

    def run(self, data, symbol):
        """
        Ejecuta la estrategia usando el gestor de riesgo avanzado
        """
        try:
            # Calcular señales
            df = self.calculate_signals(data.copy())

            trades = []
            position_open = False
            entry_price = 0.0
            position_type = None

            # Simular trading vela por vela
            for i in range(len(df)):
                current_price = df['close'].iloc[i]

                # Actualizar posiciones abiertas en el risk manager
                if position_open:
                    # Actualizar precio actual en el risk manager
                    self.risk_manager.update_position(symbol, current_price, update_trailing_stop=True)

                    # Activar trailing stop optimizado más temprano (0.5% de ganancia)
                    if position_type == 'long' and current_price > entry_price * 1.005:  # 0.5% de ganancia
                        # Activar trailing stop si no está activo
                        if self.risk_manager.positions[symbol].trailing_stop is None:
                            trail_distance = abs(entry_price - self.risk_manager.positions[symbol].stop_loss)
                            self.risk_manager.positions[symbol].trailing_stop = current_price - trail_distance
                    elif position_type == 'short' and current_price < entry_price * 0.995:  # 0.5% de ganancia
                        # Activar trailing stop si no está activo
                        if self.risk_manager.positions[symbol].trailing_stop is None:
                            trail_distance = abs(entry_price - self.risk_manager.positions[symbol].stop_loss)
                            self.risk_manager.positions[symbol].trailing_stop = current_price + trail_distance

                    # Verificar si alguna posición debe cerrarse
                    closed_positions = self.risk_manager.check_stop_loss_take_profit()

                    if symbol in closed_positions:
                        # La posición fue cerrada por stop loss, take profit o trailing stop
                        position_open = False
                        position_type = None

                        # Obtener el último trade del historial
                        if self.risk_manager.trade_history:
                            last_trade = self.risk_manager.trade_history[-1]
                            trades.append({
                                'entry_price': last_trade['entry_price'],
                                'exit_price': last_trade['exit_price'],
                                'pnl': last_trade['realized_pnl'],
                                'type': last_trade['position_type'],
                                'exit_reason': last_trade['exit_reason']
                            })

                # Verificar señales de entrada (solo si no hay posición abierta)
                if not position_open:
                    # Obtener fecha actual para control diario
                    current_date = df.index[i].date() if hasattr(df.index[i], 'date') else str(df.index[i])[:10]
                    
                    if df['long_condition'].iloc[i]:
                        # Calcular calidad de la señal
                        signal_quality = self.calculate_signal_quality(df.iloc[max(0, i-20):i+1], 1)  # Señal de compra
                        
                        # Verificar calidad mínima y límite diario
                        if signal_quality >= self.min_signal_strength and self.check_daily_trade_limit(current_date):
                            # Calcular ATR para el risk manager
                            if len(df) >= self.atr_period:
                                atr_value = talib.ATR(df['high'].iloc[max(0, i-self.atr_period):i+1],
                                                     df['low'].iloc[max(0, i-self.atr_period):i+1],
                                                     df['close'].iloc[max(0, i-self.atr_period):i+1],
                                                     timeperiod=self.atr_period).iloc[-1]
                            else:
                                atr_value = 0.0

                            # Calcular stop loss inicial optimizado (1.3 ATR - más conservador)
                            if atr_value > 0:
                                stop_loss_distance = atr_value * 1.3  # Optimizado: 1.3 ATR
                            else:
                                stop_loss_distance = current_price * 0.025  # Optimizado: 2.5% por defecto

                            stop_loss_price = current_price - stop_loss_distance

                            # Usar el risk manager para calcular el tamaño de posición
                            position_result = self.calculate_position_size_safe(
                                symbol=symbol,
                                entry_price=current_price,
                                stop_loss_price=stop_loss_price,
                                atr_value=atr_value
                            )

                            if position_result.recommended_size > 0:
                                # Abrir posición usando el risk manager
                                success = self.risk_manager.open_position(
                                    symbol=symbol,
                                    entry_price=current_price,
                                    quantity=position_result.recommended_size,
                                    position_type='long',
                                    stop_loss=position_result.stop_loss_price,
                                    take_profit=position_result.take_profit_price,
                                    risk_amount=position_result.risk_amount
                                )

                                if success:
                                    position_open = True
                                    position_type = 'long'
                                    entry_price = current_price
                                    self.daily_trade_count += 1  # Incrementar contador diario

                    elif df['short_condition'].iloc[i]:
                        # Calcular calidad de la señal
                        signal_quality = self.calculate_signal_quality(df.iloc[max(0, i-20):i+1], -1)  # Señal de venta
                        
                        # Verificar calidad mínima y límite diario
                        if signal_quality >= self.min_signal_strength and self.check_daily_trade_limit(current_date):
                            # Calcular ATR para el risk manager
                            if len(df) >= self.atr_period:
                                atr_value = talib.ATR(df['high'].iloc[max(0, i-self.atr_period):i+1],
                                                     df['low'].iloc[max(0, i-self.atr_period):i+1],
                                                     df['close'].iloc[max(0, i-self.atr_period):i+1],
                                                     timeperiod=self.atr_period).iloc[-1]
                            else:
                                atr_value = 0.0

                            # Calcular stop loss inicial optimizado
                            if atr_value > 0:
                                stop_loss_distance = atr_value * 1.3  # Optimizado: 1.3 ATR
                            else:
                                stop_loss_distance = current_price * 0.025  # Optimizado: 2.5%

                            stop_loss_price = current_price + stop_loss_distance

                            # Usar el risk manager para calcular el tamaño de posición
                            position_result = self.calculate_position_size_safe(
                                symbol=symbol,
                                entry_price=current_price,
                                stop_loss_price=stop_loss_price,
                                atr_value=atr_value
                            )

                            if position_result.recommended_size > 0:
                                # Abrir posición usando el risk manager
                                success = self.risk_manager.open_position(
                                    symbol=symbol,
                                    entry_price=current_price,
                                    quantity=position_result.recommended_size,
                                    position_type='short',
                                    stop_loss=position_result.stop_loss_price,
                                    take_profit=position_result.take_profit_price,
                                    risk_amount=position_result.risk_amount
                                )

                                if success:
                                    position_open = True
                                    position_type = 'short'
                                    entry_price = current_price
                                    self.daily_trade_count += 1  # Incrementar contador diario

            # Cerrar cualquier posición abierta al final del período
            if position_open:
                # Cerrar posición al precio final
                final_price = df['close'].iloc[-1]
                trade_record = self.risk_manager.close_position(symbol, final_price, "End of Period")

                if trade_record:
                    trades.append({
                        'entry_price': trade_record['entry_price'],
                        'exit_price': trade_record['exit_price'],
                        'pnl': trade_record['realized_pnl'],
                        'type': trade_record['position_type'],
                        'exit_reason': trade_record['exit_reason']
                    })

            # Calcular métricas finales
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
            total_pnl = sum(t['pnl'] for t in trades)

            # Calcular equity curve usando el historial del risk manager
            equity_curve = [10000.0]  # Capital inicial
            for trade in self.risk_manager.trade_history:
                equity_curve.append(equity_curve[-1] + trade['realized_pnl'])

            # Calcular drawdown máximo
            if equity_curve:
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

            # Calcular profit factor
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

            # Calcular Sharpe ratio básico
            if len(equity_curve) > 1:
                returns = np.diff(equity_curve) / equity_curve[:-1]
                if len(returns) > 0 and np.std(returns) > 0:
                    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365)  # Anualizado para 4h
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'profit_factor': profit_factor,
                'symbol': symbol,
                'trades': trades,
                'equity_curve': equity_curve
            }

        except Exception as e:
            print(f"Error ejecutando estrategia Solana4HRiskManagedStrategy: {e}")
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
                'trades': []
            }

    def calculate_position_size_safe(self, symbol: str, entry_price: float,
                                   stop_loss_price: float, atr_value: float = None):
        """
        Método seguro para calcular tamaño de posición optimizado para Solana4HRiskManaged
        """
        try:
            # Validaciones básicas
            if entry_price <= 0 or stop_loss_price <= 0:
                return self._create_zero_position_result("Precios inválidos")

            # Usar parámetros optimizados para Solana4HRiskManaged
            risk_per_trade = self.risk_manager.portfolio_value * 0.015  # 1.5% optimizado
            price_risk = abs(entry_price - stop_loss_price)

            if price_risk <= 0:
                return self._create_zero_position_result("Stop loss muy cercano")

            # Calcular tamaño base con parámetros optimizados
            base_position_size = risk_per_trade / price_risk

            # Limitar tamaño máximo optimizado (5% del portfolio)
            max_position_value = self.risk_manager.portfolio_value * 0.05
            max_size_by_value = max_position_value / entry_price
            final_size = min(base_position_size, max_size_by_value)

            # Limitar tamaño mínimo optimizado
            min_position_value = 50  # $50 mínimo optimizado
            if final_size * entry_price < min_position_value:
                return self._create_zero_position_result("Posición muy pequeña")

            # Calcular take profit optimizado (2.5:1 risk:reward usando ATR)
            risk_amount = final_size * price_risk

            if atr_value and atr_value > 0:
                # Usar ATR para calcular take profit más inteligente
                atr_distance = atr_value * 2.5  # 2.5 ATR optimizado
                if entry_price > stop_loss_price:  # Long position
                    take_profit_price = entry_price + atr_distance
                else:  # Short position
                    take_profit_price = entry_price - atr_distance
            else:
                # Fallback al método anterior
                reward_amount = risk_amount * 2.5  # 2.5:1 optimizado
                if entry_price > stop_loss_price:  # Long position
                    take_profit_price = entry_price + (reward_amount / final_size)
                else:  # Short position
                    take_profit_price = entry_price - (reward_amount / final_size)

            # Crear resultado con parámetros optimizados
            from risk_management.risk_management import PositionSizeResult
            return PositionSizeResult(
                recommended_size=final_size,
                max_position_value=final_size * entry_price,
                risk_amount=risk_amount,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                position_risk_percent=(risk_amount / self.risk_manager.portfolio_value) * 100,
                confidence_score=0.8,  # Score optimizado
                warnings=[]
            )

        except Exception as e:
            print(f"Error en calculate_position_size_safe optimizado: {e}")
            return self._create_zero_position_result(f"Error: {str(e)}")

    def _create_zero_position_result(self, reason: str):
        """Crea resultado con posición cero"""
        from risk_management.risk_management import PositionSizeResult
        return PositionSizeResult(
            recommended_size=0.0,
            max_position_value=0.0,
            risk_amount=0.0,
            stop_loss_price=0.0,
            take_profit_price=0.0,
            position_risk_percent=0.0,
            confidence_score=0.0,
            warnings=[reason]
        )