#!/usr/bin/env python3
"""
EJEMPLO DE ESTRATEGIA CON GESTIÓN DE RIESGO INTEGRADA
======================================================

Esta estrategia demuestra cómo la gestión de riesgo debería manejarse
directamente desde la estrategia, no desde una función externa.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from strategies.base_strategy import BaseStrategy


class ExampleStrategyWithIntegratedRisk(BaseStrategy):
    """
    Estrategia de ejemplo que maneja su propia gestión de riesgo.
    """

    def __init__(self, config):
        super().__init__(config)

        # Configuración específica de la estrategia
        self.fast_ma_period = config.get('fast_ma_period', 9)
        self.slow_ma_period = config.get('slow_ma_period', 21)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)

        # Gestión de riesgo específica
        self.atr_multiplier_sl = config.get('atr_multiplier_sl', 1.5)
        self.atr_multiplier_tp = config.get('atr_multiplier_tp', 3.0)
        self.min_atr_value = config.get('min_atr_value', 0.0001)

    def _get_strategy_max_position_size(self, account_balance: float) -> float:
        """
        Esta estrategia limita posiciones al 5% del capital
        cuando la volatilidad (ATR) es alta.
        """
        # Lógica específica: reducir posición si ATR > cierto umbral
        # (simplificado para el ejemplo)
        return account_balance * 0.05

    def _validate_strategy_specific_conditions(self) -> bool:
        """
        Validaciones específicas de la estrategia.
        """
        # Verificar que tenemos suficientes datos históricos
        # Verificar que los indicadores están calculados correctamente
        # Verificar correlaciones específicas de la estrategia
        return True

    def calculate_position_size(self, entry_price: float, stop_loss: float,
                              account_balance: float, direction: str) -> float:
        """
        Cálculo de position size específico de la estrategia.

        Esta estrategia usa ATR para ajustar el riesgo dinámicamente.
        """
        # Calcular riesgo base
        risk_amount = account_balance * self.max_risk_per_trade

        # Calcular distancia del stop loss
        if direction.lower() == 'buy':
            stop_distance = abs(entry_price - stop_loss)
        else:
            stop_distance = abs(stop_loss - entry_price)

        if stop_distance <= 0:
            return 0.0

        # Position size base
        position_size = risk_amount / stop_distance

        # Ajuste específico de la estrategia: reducir si volatilidad es muy alta
        # (En una implementación real, calcularíamos ATR aquí)
        volatility_adjustment = 1.0  # Placeholder

        position_size *= volatility_adjustment

        # Aplicar límites de la estrategia
        max_size = self._get_strategy_max_position_size(account_balance)
        position_size = min(position_size, max_size)

        return position_size

    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[Dict[str, any]]:
        """
        Genera señales de trading con gestión de riesgo integrada.
        """
        if len(data) < max(self.slow_ma_period, self.rsi_period):
            return None

        # Calcular indicadores
        indicators = self.calculate_indicators(data)

        # Lógica de señal simplificada
        fast_ma = indicators[f'ma_{self.fast_ma_period}']
        slow_ma = indicators[f'ma_{self.slow_ma_period}']
        rsi = indicators[f'rsi_{self.rsi_period}']

        # Señal de compra
        if (fast_ma.iloc[-1] > slow_ma.iloc[-1] and
            rsi.iloc[-1] < self.rsi_oversold):

            # Calcular precios de entrada y stop loss
            entry_price = data['close'].iloc[-1]

            # Stop loss basado en ATR (simplificado)
            atr_value = indicators.get('atr_14', pd.Series([0.001])).iloc[-1]
            stop_loss = entry_price - (atr_value * self.atr_multiplier_sl)

            # Take profit basado en riesgo/recompensa
            take_profit = entry_price + (atr_value * self.atr_multiplier_tp)

            # Calcular tamaño de posición usando método de la estrategia
            # NOTA: En implementación real, necesitaríamos account_balance
            position_size = 0.01  # Placeholder

            return {
                'symbol': symbol,
                'direction': 'buy',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'confidence': 0.75,
                'indicators': {
                    'fast_ma': fast_ma.iloc[-1],
                    'slow_ma': slow_ma.iloc[-1],
                    'rsi': rsi.iloc[-1]
                }
            }

        return None

    def run(self, data: pd.DataFrame, symbol: str) -> Optional[Dict[str, any]]:
        """
        Ejecuta la estrategia completa con gestión de riesgo integrada.
        """
        # Generar señal
        signal = self.generate_signal(data, symbol)

        if signal:
            # Aquí la estrategia podría validar condiciones de riesgo
            # usando los métodos heredados de BaseStrategy
            # if not self.validate_risk_conditions(account_balance, current_drawdown):
            #     return None

            return signal

        return None