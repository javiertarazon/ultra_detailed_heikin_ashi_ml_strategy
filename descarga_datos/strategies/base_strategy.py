from indicators.technical_indicators import TechnicalIndicators
from risk_management.risk_management import get_risk_manager
from typing import Dict, Any, Optional


class BaseStrategy:
    def __init__(self, config):
        self.config = config
        self.indicators = TechnicalIndicators()
        self.risk_manager = get_risk_manager()

        # Configuración de riesgo específica de la estrategia
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.01)
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.20)
        self.min_win_rate = config.get('min_win_rate', 0.55)

    def calculate_indicators(self, data):
        """Centraliza el cálculo de indicadores técnicos."""
        return self.indicators.calculate_all_indicators_unified(data)

    def calculate_position_size(self, entry_price: float, stop_loss: float,
                              account_balance: float, direction: str) -> float:
        """
        Calcula el tamaño de posición basado en la lógica específica de la estrategia.

        Args:
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            account_balance: Balance disponible
            direction: 'buy' o 'sell'

        Returns:
            Tamaño óptimo de la posición
        """
        # Lógica específica de cada estrategia para calcular position size
        risk_amount = account_balance * self.max_risk_per_trade

        if direction.lower() == 'buy':
            stop_distance = abs(entry_price - stop_loss)
        else:
            stop_distance = abs(stop_loss - entry_price)

        if stop_distance <= 0:
            return 0.0

        # Aplicar factores específicos de la estrategia (volatilidad, confianza, etc.)
        position_size = risk_amount / stop_distance

        # Estrategia puede aplicar sus propios límites
        max_size = self._get_strategy_max_position_size(account_balance)
        position_size = min(position_size, max_size)

        return position_size

    def validate_risk_conditions(self, account_balance: float, current_drawdown: float) -> bool:
        """
        Valida condiciones de riesgo específicas de la estrategia.

        Args:
            account_balance: Balance actual
            current_drawdown: Drawdown actual

        Returns:
            True si las condiciones se cumplen
        """
        # Verificar drawdown máximo de la estrategia
        if current_drawdown > self.max_drawdown_limit:
            return False

        # Verificar balance mínimo
        min_balance = self.config.get('min_account_balance', 1000)
        if account_balance < min_balance:
            return False

        # Condiciones específicas de la estrategia
        return self._validate_strategy_specific_conditions()

    def _get_strategy_max_position_size(self, account_balance: float) -> float:
        """Método que las estrategias pueden sobrescribir para límites específicos."""
        return account_balance * 0.1  # Default 10%

    def _validate_strategy_specific_conditions(self) -> bool:
        """Método que las estrategias pueden sobrescribir para validaciones específicas."""
        return True

    def run(self, data, symbol):
        """Método base para ejecutar estrategias. Debe ser sobrescrito."""
        raise NotImplementedError(
            "El método 'run' debe ser implementado en la estrategia específica."
        )
