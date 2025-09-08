#!/usr/bin/env python3
"""
Bot Trader Copilot - Configuración de Backtesting
===================================================

Archivo de configuración centralizada para el sistema de backtesting.
Modifica los parámetros aquí para cambiar el comportamiento del sistema.
"""

# ===============================
# CONFIGURACIÓN DE SÍMBOLOS
# ===============================

# Lista de símbolos a procesar
# - Acciones: terminan en .US (requieren MT5)
# - Criptos: formato BASE/QUOTE (usarán CCXT)
BACKTEST_SYMBOLS = [
    # Acciones de alta volatilidad
    "TSLA.US", "LYFT.US", "AMD.US", "NVDA.US", "UBER.US", "NFLX.US",

    # Criptomonedas de alta volatilidad
    "SOL/USDT", "ADA/USDT", "COMP/USDT", "YFI/USDT",

    # Puedes agregar más símbolos aquí:
    # "BTC/USDT", "ETH/USDT", "AVAX/USDT", "DOT/USDT",
    # "AAPL.US", "GOOGL.US", "META.US", "AMZN.US"
]

# ===============================
# CONFIGURACIÓN DE TIEMPO
# ===============================

# Temporalidad para el análisis
# Opciones: '1m', '5m', '15m', '30m', '1h', '4h', '1d'
TIMEFRAME = '1h'

# Período de análisis
START_DATE = '2024-01-01'  # Formato: YYYY-MM-DD
END_DATE = '2024-06-01'    # Formato: YYYY-MM-DD

# ===============================
# CONFIGURACIÓN DE BACKTESTING
# ===============================

# Número máximo de símbolos a procesar (0 = todos)
MAX_SYMBOLS = 0  # 0 significa procesar todos los símbolos de BACKTEST_SYMBOLS

# Configuración de capital y comisiones
INITIAL_CAPITAL = 10000  # Capital inicial en USD
COMMISSION = 0.1         # Comisión por trade en porcentaje (0.1 = 0.1%)
SLIPPAGE = 0.05          # Slippage estimado en porcentaje

# ===============================
# CONFIGURACIÓN DE ESTRATEGIAS
# ===============================

# Estrategias a probar (True = activar, False = desactivar)
ENABLED_STRATEGIES = {
    "UTBot_Conservadora": True,
    "UTBot_Intermedia": True,
    "UTBot_Agresiva": True,
    "Optimizada_Ganadora": True  # Activada para testing
}

# ===============================
# CONFIGURACIÓN AVANZADA
# ===============================

# Configuración de indicadores técnicos
TECHNICAL_CONFIG = {
    'atr_period': 10,
    'ema_periods': [10, 20, 200],
    'psar_start': 0.02,
    'psar_increment': 0.02,
    'psar_max': 0.2
}

# Configuración de riesgo
RISK_CONFIG = {
    'risk_percent': 2.0,        # Riesgo por operación (% del capital)
    'tp_atr_multiplier': 2.0,   # Take profit (multiplicador de ATR)
    'sl_atr_multiplier': 1.5,   # Stop loss (multiplicador de ATR)
}

# ===============================
# CONFIGURACIÓN DE DATOS
# ===============================

# Configuración de descarga de datos
DATA_CONFIG = {
    'use_mt5_for_stocks': True,   # Usar MT5 para acciones
    'use_ccxt_for_crypto': True,  # Usar CCXT para criptos
    'max_retries': 3,             # Máximo número de reintentos
    'retry_delay': 5,             # Delay entre reintentos (segundos)
    'limit_per_request': 1000     # Límite de velas por solicitud
}

# ===============================
# CONFIGURACIÓN DE REPORTES
# ===============================

# Configuración de reportes
REPORT_CONFIG = {
    'save_individual_results': True,  # Guardar resultados por símbolo
    'save_equity_curves': True,       # Guardar curvas de equity
    'save_trade_details': True,       # Guardar detalles de trades
    'generate_comparison': True,      # Generar comparación entre estrategias
    'output_directory': 'backtest_results'  # Directorio de salida
}

# ===============================
# FUNCIONES DE CONFIGURACIÓN
# ===============================

def get_backtest_config():
    """Retorna la configuración completa para backtesting"""
    return {
        'symbols': BACKTEST_SYMBOLS,
        'timeframe': TIMEFRAME,
        'start_date': START_DATE,
        'end_date': END_DATE,
        'max_symbols': MAX_SYMBOLS,
        'initial_capital': INITIAL_CAPITAL,
        'commission': COMMISSION,
        'slippage': SLIPPAGE,
        'enabled_strategies': ENABLED_STRATEGIES,
        'technical_config': TECHNICAL_CONFIG,
        'risk_config': RISK_CONFIG,
        'data_config': DATA_CONFIG,
        'report_config': REPORT_CONFIG
    }

def get_active_symbols():
    """Retorna la lista de símbolos activos según MAX_SYMBOLS"""
    if MAX_SYMBOLS == 0 or MAX_SYMBOLS >= len(BACKTEST_SYMBOLS):
        return BACKTEST_SYMBOLS
    else:
        return BACKTEST_SYMBOLS[:MAX_SYMBOLS]

def get_enabled_strategies():
    """Retorna las estrategias activadas"""
    return [name for name, enabled in ENABLED_STRATEGIES.items() if enabled]

def print_current_config():
    """Imprime la configuración actual"""
    config = get_backtest_config()

    print("🤖 CONFIGURACIÓN ACTUAL DE BACKTESTING")
    print("=" * 50)
    print(f"Símbolos: {len(config['symbols'])} activos")
    print(f"Temporalidad: {config['timeframe']}")
    print(f"Período: {config['start_date']} a {config['end_date']}")
    print(f"Capital inicial: ${config['initial_capital']}")
    print(f"Estrategias activas: {len(get_enabled_strategies())}")
    print("=" * 50)

    print("\n📊 SÍMBOLOS CONFIGURADOS:")
    for i, symbol in enumerate(config['symbols'], 1):
        print(f"  {i:2d}. {symbol}")

    print("\n🎯 ESTRATEGIAS ACTIVAS:")
    for strategy in get_enabled_strategies():
        print(f"  • {strategy}")

    print(f"\n💰 CONFIGURACIÓN DE RIESGO:")
    print(f"  • Riesgo por operación: {config['risk_config']['risk_percent']}%")
    print(f"  • Take Profit: {config['risk_config']['tp_atr_multiplier']}x ATR")
    print(f"  • Stop Loss: {config['risk_config']['sl_atr_multiplier']}x ATR")

if __name__ == "__main__":
    print_current_config()
