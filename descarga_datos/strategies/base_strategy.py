from indicators.technical_indicators import TechnicalIndicators


class BaseStrategy:
    def __init__(self, config):
        self.config = config
        self.indicators = TechnicalIndicators()

    def calculate_indicators(self, data):
        """Centraliza el cálculo de indicadores técnicos."""
        return self.indicators.calculate_all_indicators_unified(data)

    def run(self, data, symbol):
        """Método base para ejecutar estrategias. Debe ser sobrescrito."""
        raise NotImplementedError(
            "El método 'run' debe ser implementado en la estrategia específica."
        )
