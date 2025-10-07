# BACKUP DE PARÁMETROS ORIGINALES - UltraDetailedHeikinAshiStrategy
# Fecha: 4 de octubre de 2025
# Versión antes de aplicar parámetros optimizados

ORIGINAL_PARAMETERS = {
    'ml_threshold': 0.4,
    'stoch_overbought': 75,
    'stoch_oversold': 25,
    'cci_threshold': 80,
    'volume_ratio_min': 0.6,
    'liquidity_score_min': 50,
    'max_drawdown': 0.05,
    'max_portfolio_heat': 0.06,
    'max_concurrent_trades': 3,
    'kelly_fraction': 0.3,
    # Parámetros que no existían originalmente:
    # 'volume_threshold': None,
    # 'atr_multiplier': None,
    # 'stop_loss_pct': None,
    # 'take_profit_pct': None,
    # 'rsi_overbought': None,
    # 'rsi_oversold': None
}

# Parámetros optimizados encontrados:
OPTIMIZED_PARAMETERS_BTC = {
    'volume_threshold': 1.3,
    'atr_multiplier': 3.4,
    'stop_loss_pct': 0.09,
    'take_profit_pct': 0.19,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'stoch_overbought': 85,
    'stoch_oversold': 25
}

OPTIMIZED_PARAMETERS_TSLA = {
    'volume_threshold': 1.7,
    'atr_multiplier': 2.0,
    'stop_loss_pct': 0.09,
    'take_profit_pct': 0.15,
    'rsi_overbought': 65,
    'rsi_oversold': 30,
    'stoch_overbought': 75,
    'stoch_oversold': 15
}