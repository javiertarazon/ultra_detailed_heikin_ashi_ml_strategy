"""
Implementación de la estrategia UT Bot + PSAR con Sistema de Compensación.
Versión con compensación automática de operaciones perdedoras.
"""
import numpy as np
import pandas as pd
import talib

class UTBotPSARCompensationStrategy:
    def __init__(self,
                 sensitivity=1,
                 atr_period=10,
                 use_heikin_ashi=False,
                 risk_percent=2.0,
                 tp_atr_multiplier=2.0,
                 sl_atr_multiplier=1.5,
                 psar_start=0.02,
                 psar_increment=0.02,
                 psar_max=0.2,
                 # Parámetros de compensación OPTIMIZADOS para mejor control de riesgo
                 compensation_loss_threshold=0.2,  # REDUCIDO: 0.2% del balance para activar compensación
                 compensation_size_multiplier=1.5,  # REDUCIDO: 1.5x el tamaño de compensación
                 compensation_tp_percent=0.25,     # REDUCIDO: 0.25% del balance como TP de compensación
                 max_account_drawdown=1.5,         # REDUCIDO: 1.5% máximo de drawdown del balance total
                 compensation_max_loss_percent=0.3, # NUEVO: 0.3% límite máximo de pérdida por compensación
                 # NUEVAS MEJORAS PARA CONTROL DE RIESGO AVANZADO
                 anticipatory_stop_threshold=0.8,   # NUEVO: 80% del límite para activar stops anticipatorios
                 progressive_risk_levels=None):     # NUEVO: Niveles progresivos de reducción de riesgo
        self.sensitivity = sensitivity
        self.atr_period = atr_period
        self.use_heikin_ashi = use_heikin_ashi
        self.risk_percent = risk_percent
        self.tp_atr_multiplier = tp_atr_multiplier
        self.sl_atr_multiplier = sl_atr_multiplier
        self.psar_start = psar_start
        self.psar_increment = psar_increment
        self.psar_max = psar_max

        # Parámetros de compensación OPTIMIZADOS
        self.compensation_loss_threshold = compensation_loss_threshold
        self.compensation_size_multiplier = compensation_size_multiplier
        self.compensation_tp_percent = compensation_tp_percent
        self.max_account_drawdown = max_account_drawdown
        self.compensation_max_loss_percent = compensation_max_loss_percent

        # NUEVAS MEJORAS PARA CONTROL DE RIESGO AVANZADO
        self.anticipatory_stop_threshold = anticipatory_stop_threshold

        # Configurar niveles progresivos de reducción de riesgo por defecto
        if progressive_risk_levels is None:
            self.progressive_risk_levels = {
                0.7: 0.8,   # Si drawdown > 70% del límite, reducir riesgo al 80%
                0.5: 0.6,   # Si drawdown > 50% del límite, reducir riesgo al 60%
                0.3: 0.4    # Si drawdown > 30% del límite, reducir riesgo al 40%
            }
        else:
            self.progressive_risk_levels = progressive_risk_levels

    def calculate_progressive_risk_multiplier(self, current_drawdown_pct):
        """
        Calcula el multiplicador de riesgo basado en reducción progresiva según drawdown.
        Retorna un valor entre 0.0 y 1.0 donde 1.0 es riesgo normal.
        """
        if current_drawdown_pct <= 0:
            return 1.0

        # Calcular porcentaje relativo al límite de drawdown
        drawdown_ratio = current_drawdown_pct / self.max_account_drawdown

        # Aplicar reducción progresiva según niveles configurados
        risk_multiplier = 1.0
        for threshold_ratio, reduction_factor in sorted(self.progressive_risk_levels.items(), reverse=True):
            if drawdown_ratio >= threshold_ratio:
                risk_multiplier = reduction_factor
                break

        return risk_multiplier

    def _activate_compensation_with_risk_control(self, current_price, position, position_size,
                                                current_pnl, loss_percentage, current_drawdown_pct,
                                                progressive_risk_mult, activation_type, capital, symbol):
        """
        Método centralizado para activar compensación con control de riesgo avanzado.
        """
        global compensation_active, compensation_position, compensation_entry_price
        global compensation_size, compensation_max_loss, compensation_target_pnl
        global main_position_pnl_at_compensation

        # Activar compensación
        compensation_active = True
        compensation_position = -position  # Posición opuesta
        compensation_entry_price = current_price

        # Aplicar multiplicador de riesgo progresivo
        base_multiplier = self.compensation_size_multiplier
        final_risk_multiplier = base_multiplier * progressive_risk_mult

        # Ajustar multiplicador según tipo de activación
        if activation_type == "anticipatory_stop":
            final_risk_multiplier *= 0.8  # Reducir 20% adicional para stops anticipatorios

        compensation_size = position_size * final_risk_multiplier

        # Calcular límite de pérdida para compensación (más estricto con riesgo alto)
        max_loss_base = self.compensation_max_loss_percent / 100
        if progressive_risk_mult < 1.0:
            max_loss_base *= progressive_risk_mult  # Reducir límite si riesgo ya está reducido

        compensation_max_loss = -(capital * max_loss_base)

        # Calcular objetivo de compensación (más conservador con riesgo alto)
        main_position_loss = abs(current_pnl)
        tp_base = self.compensation_tp_percent / 100
        if progressive_risk_mult < 1.0:
            tp_base *= progressive_risk_mult  # Reducir objetivo si riesgo está reducido

        compensation_tp_amount = capital * tp_base
        compensation_target_pnl = main_position_loss + compensation_tp_amount

        main_position_pnl_at_compensation = current_pnl

        print(f"[{activation_type.upper()}] Activada para {symbol}")
        print(f"  Pérdida principal: ${current_pnl:.2f} ({loss_percentage:.2f}%)")
        print(f"  Drawdown actual: {current_drawdown_pct:.2f}%")
        print(f"  Multiplicador base: {base_multiplier:.1f}x")
        print(f"  Multiplicador riesgo progresivo: {progressive_risk_mult:.2f}")
        print(f"  Multiplicador final: {final_risk_multiplier:.2f}x")
        print(f"  Tamaño compensación: ${compensation_size:.2f}")
        print(f"  Límite pérdida: ${compensation_max_loss:.2f}")
        print(f"  Objetivo total: ${compensation_target_pnl:.2f}")

    def should_activate_anticipatory_stop(self, current_drawdown_pct):
        """
        Determina si se debe activar un stop anticipatorio basado en el umbral configurado.
        """
        drawdown_ratio = current_drawdown_pct / self.max_account_drawdown
        return drawdown_ratio >= self.anticipatory_stop_threshold

    def calculate_heikin_ashi(self, df):
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = pd.Series(0.0, index=df.index)
        ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        ha_high = pd.Series([max(h, o, c) for h, o, c in zip(df['high'], ha_open, ha_close)], index=df.index)
        ha_low = pd.Series([min(l, o, c) for l, o, c in zip(df['low'], ha_open, ha_close)], index=df.index)
        return pd.DataFrame({
            'open': ha_open,
            'high': ha_high,
            'low': ha_low,
            'close': ha_close
        }, index=df.index)

    def calculate_signals(self, df):
        """
        Calcula las señales usando los indicadores ya existentes en los datos.
        Los datos deben contener: atr, sar, ema_10, ema_20, ema_200
        """
        if self.use_heikin_ashi:
            df = self.calculate_heikin_ashi(df)
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
        df['trailing_stop'] = trailing_stop_values

        # Calcular señales de entrada usando EMA existente (usaremos ema_10 como señal rápida)
        df['above'] = (df['ema_10'] > df['trailing_stop']) & (df['ema_10'].shift(1) <= df['trailing_stop'].shift(1))
        df['below'] = (df['ema_10'] < df['trailing_stop']) & (df['ema_10'].shift(1) >= df['trailing_stop'].shift(1))

        # Confirmar señales con tendencia (usando ema_200 como referencia de tendencia)
        long_trend = df[price_col] > df['ema_200']
        short_trend = df[price_col] < df['ema_200']

        df['buy_signal'] = (df[price_col] > df['trailing_stop']) & df['above'] & long_trend
        df['sell_signal'] = (df[price_col] < df['trailing_stop']) & df['below'] & short_trend

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

    def run(self, data, symbol):
        """
        Ejecuta la estrategia con sistema de compensación y devuelve los resultados del backtesting
        """
        try:
            # Calcular señales
            df = self.calculate_signals(data.copy())

            # Inicializar variables de trading
            capital = 10000.0  # Capital inicial
            initial_capital = capital  # Guardar capital inicial para cálculos de drawdown
            position = 0  # 0: sin posición, 1: long, -1: short
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            position_size = 0.0

            # Variables de compensación
            compensation_active = False
            compensation_position = 0  # 0: sin compensación, 1: long, -1: short
            compensation_entry_price = 0.0
            compensation_size = 0.0
            compensation_target_pnl = 0.0
            compensation_max_loss = 0.0  # Límite de pérdida para compensación
            main_position_pnl_at_compensation = 0.0

            trades = []
            compensation_trades = []

            # Simular trading
            for i in range(len(df)):
                current_price = df['close'].iloc[i]

                # Verificar señales de entrada (solo si no hay compensación activa)
                if position == 0 and not compensation_active:
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

                # Gestionar posiciones abiertas
                elif position != 0:
                    # Calcular PnL actual de la posición principal
                    if position == 1:  # Long
                        current_pnl = (current_price - entry_price) * position_size
                    else:  # Short
                        current_pnl = (entry_price - current_price) * position_size

                    # Calcular drawdown actual del balance
                    current_balance = capital + current_pnl
                    current_drawdown_pct = ((initial_capital - current_balance) / initial_capital) * 100

                    # VERIFICAR STOP-LOSS GLOBAL MEJORADO - Más conservador
                    emergency_stop_threshold = self.max_account_drawdown * 0.8  # 80% del límite máximo
                    if current_drawdown_pct >= emergency_stop_threshold:
                        # Cerrar todas las posiciones por stop-loss global anticipado
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size if position == 1 else (entry_price - exit_price) * position_size
                        capital += pnl

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long' if position == 1 else 'short',
                            'had_compensation': compensation_active,
                            'emergency_stop': True,
                            'drawdown_at_stop': current_drawdown_pct,
                            'stop_reason': 'anticipado'
                        })

                        if compensation_active:
                            compensation_pnl = (current_price - compensation_entry_price) * compensation_size if compensation_position == 1 else (compensation_entry_price - current_price) * compensation_size
                            compensation_trades.append({
                                'entry_price': compensation_entry_price,
                                'exit_price': exit_price,
                                'pnl': compensation_pnl,
                                'type': 'emergency_stop_anticipado',
                                'main_position_pnl': pnl
                            })

                        position = 0
                        compensation_active = False
                        print(f"[EMERGENCY STOP ANTICIPADO] Stop-loss global anticipado - Drawdown: {current_drawdown_pct:.2f}% (threshold: {emergency_stop_threshold:.2f}%)")
                        continue

                    # STOP-LOSS GLOBAL FINAL - Solo si llega al límite absoluto
                    elif current_drawdown_pct >= self.max_account_drawdown:
                        # Cerrar todas las posiciones por stop-loss global final
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * position_size if position == 1 else (entry_price - exit_price) * position_size
                        capital += pnl

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long' if position == 1 else 'short',
                            'had_compensation': compensation_active,
                            'emergency_stop': True,
                            'drawdown_at_stop': current_drawdown_pct,
                            'stop_reason': 'final'
                        })

                        if compensation_active:
                            compensation_pnl = (current_price - compensation_entry_price) * compensation_size if compensation_position == 1 else (compensation_entry_price - current_price) * compensation_size
                            compensation_trades.append({
                                'entry_price': compensation_entry_price,
                                'exit_price': exit_price,
                                'pnl': compensation_pnl,
                                'type': 'emergency_stop_final',
                                'main_position_pnl': pnl
                            })

                        position = 0
                        compensation_active = False
                        print(f"[EMERGENCY STOP FINAL] Stop-loss global final - Drawdown: {current_drawdown_pct:.2f}% (límite: {self.max_account_drawdown:.1f}%)")
                        continue

                    # Verificar si necesitamos activar compensación con validaciones avanzadas de riesgo
                    if not compensation_active and current_pnl < 0:
                        loss_percentage = abs(current_pnl) / capital * 100

                        # NUEVO: Verificar anticipatory stop threshold
                        anticipatory_triggered = self.should_activate_anticipatory_stop(current_drawdown_pct)
                        progressive_risk_mult = self.calculate_progressive_risk_multiplier(current_drawdown_pct)

                        # Validar que no estemos demasiado cerca del límite de drawdown global
                        drawdown_buffer = 0.5  # Mantener 0.5% de buffer antes del límite
                        if current_drawdown_pct >= (self.max_account_drawdown - drawdown_buffer):
                            print(f"[RISK CONTROL] Compensación NO activada - Drawdown cercano al límite: {current_drawdown_pct:.2f}% (límite: {self.max_account_drawdown:.1f}%)")
                        elif anticipatory_triggered and loss_percentage >= (self.compensation_loss_threshold * 0.8):
                            # ACTIVAR COMPENSACIÓN CON ANTICIPATORY STOP (más temprano)
                            print(f"[ANTICIPATORY STOP] Activando compensación preventiva - Drawdown: {current_drawdown_pct:.2f}% (threshold: {self.anticipatory_stop_threshold * self.max_account_drawdown:.2f}%)")
                            self._activate_compensation_with_risk_control(
                                current_price, position, position_size, current_pnl,
                                loss_percentage, current_drawdown_pct, progressive_risk_mult,
                                "anticipatory_stop", capital, symbol
                            )
                        elif loss_percentage >= self.compensation_loss_threshold:
                            # Activar compensación normal con validaciones de riesgo mejoradas
                            print(f"[COMPENSATION] Evaluando activación - Drawdown: {current_drawdown_pct:.2f}%, Risk Mult: {progressive_risk_mult:.2f}")
                            self._activate_compensation_with_risk_control(
                                current_price, position, position_size, current_pnl,
                                loss_percentage, current_drawdown_pct, progressive_risk_mult,
                                "standard_compensation", capital, symbol
                            )
                        else:
                            # Logging de estado de riesgo
                            if anticipatory_triggered:
                                print(f"[ANTICIPATORY WARNING] Drawdown alto ({current_drawdown_pct:.2f}%) pero pérdida insuficiente ({loss_percentage:.2f}% < {self.compensation_loss_threshold:.2f}%)")

                    # Gestionar compensación activa
                    if compensation_active:
                        # Calcular PnL de compensación
                        if compensation_position == 1:  # Compensación long
                            compensation_pnl = (current_price - compensation_entry_price) * compensation_size
                        else:  # Compensación short
                            compensation_pnl = (compensation_entry_price - current_price) * compensation_size

                        total_pnl = current_pnl + compensation_pnl

                        # Verificar límite de pérdida de compensación
                        if compensation_pnl <= compensation_max_loss:
                            # Cerrar compensación por límite de pérdida
                            compensation_trades.append({
                                'entry_price': compensation_entry_price,
                                'exit_price': current_price,
                                'pnl': compensation_pnl,
                                'type': 'compensation_max_loss',
                                'main_position_pnl': current_pnl
                            })
                            compensation_active = False
                            print(f"[COMPENSATION] Cerrada por límite de pérdida - PnL compensación: ${compensation_pnl:.2f}")

                        # Verificar si la posición principal se recuperó antes de compensar
                        elif current_pnl > main_position_pnl_at_compensation:
                            # Cerrar compensación en breakeven y continuar con principal
                            compensation_trades.append({
                                'entry_price': compensation_entry_price,
                                'exit_price': current_price,
                                'pnl': compensation_pnl,
                                'type': 'compensation_recovery',
                                'main_position_pnl': current_pnl
                            })
                            compensation_active = False
                            print(f"[COMPENSATION] Cerrada en recuperación - PnL compensación: ${compensation_pnl:.2f}")

                        # Verificar si se alcanzó el objetivo de compensación
                        elif total_pnl >= compensation_target_pnl:
                            # Cerrar ambas posiciones
                            exit_price = current_price
                            pnl = (exit_price - entry_price) * position_size if position == 1 else (entry_price - exit_price) * position_size
                            capital += pnl

                            compensation_trades.append({
                                'entry_price': compensation_entry_price,
                                'exit_price': exit_price,
                                'pnl': compensation_pnl,
                                'type': 'compensation_success',
                                'main_position_pnl': pnl,
                                'total_pnl': total_pnl
                            })

                            trades.append({
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': 'long' if position == 1 else 'short',
                                'had_compensation': True,
                                'compensation_pnl': compensation_pnl,
                                'total_pnl': total_pnl
                            })

                            position = 0
                            compensation_active = False
                            print(f"[COMPENSATION] Objetivo alcanzado - Total PnL: ${total_pnl:.2f}")

                    # Verificar condiciones normales de salida (solo si no hay compensación)
                    if not compensation_active:
                        if position == 1:  # Posición long
                            if current_price >= take_profit or current_price <= stop_loss:
                                # Cerrar posición
                                exit_price = current_price
                                pnl = (exit_price - entry_price) * position_size
                                capital += pnl

                                trades.append({
                                    'entry_price': entry_price,
                                    'exit_price': exit_price,
                                    'pnl': pnl,
                                    'type': 'long',
                                    'had_compensation': False
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
                                    'type': 'short',
                                    'had_compensation': False
                                })

                                position = 0

            # Calcular métricas principales
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            total_pnl = sum(t['pnl'] for t in trades)

            # Calcular métricas de compensación
            total_compensation_trades = len(compensation_trades)
            successful_compensations = len([t for t in compensation_trades if t.get('type') == 'compensation_success'])
            compensation_win_rate = successful_compensations / total_compensation_trades if total_compensation_trades > 0 else 0.0
            total_compensation_pnl = sum(t['pnl'] for t in compensation_trades)

            # Calcular drawdown máximo mejorado
            if trades:
                # Calcular equity curve completa
                equity_curve = [initial_capital]
                for trade in trades:
                    new_equity = equity_curve[-1] + trade['pnl']
                    equity_curve.append(new_equity)

                # Calcular drawdown máximo
                peak = initial_capital
                max_drawdown = 0.0

                for equity in equity_curve:
                    if equity > peak:
                        peak = equity
                    drawdown = peak - equity
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                # Convertir a negativo para mantener consistencia
                max_drawdown = -max_drawdown
            else:
                max_drawdown = 0.0

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': 0.0,  # Placeholder
                'symbol': symbol,
                'trades': trades,
                # Métricas de compensación
                'compensation_trades': total_compensation_trades,
                'successful_compensations': successful_compensations,
                'compensation_win_rate': compensation_win_rate,
                'total_compensation_pnl': total_compensation_pnl,
                'compensation_details': compensation_trades,
                # Parámetros de compensación
                'compensation_loss_threshold': self.compensation_loss_threshold,
                'compensation_size_multiplier': self.compensation_size_multiplier,
                'compensation_tp_percent': self.compensation_tp_percent,
                'max_account_drawdown': self.max_account_drawdown
            }

        except Exception as e:
            print(f"Error ejecutando estrategia UTBotPSARCompensationStrategy: {e}")
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
                'compensation_trades': 0,
                'successful_compensations': 0,
                'compensation_win_rate': 0.0,
                'total_compensation_pnl': 0.0,
                'compensation_details': []
            }