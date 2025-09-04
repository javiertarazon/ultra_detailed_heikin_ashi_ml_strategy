"""
Tests para la estrategia UT Bot + PSAR.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ..strategies.ut_bot_psar import UTBotPSARStrategy
from ..backtesting.backtester import Backtester

def create_test_data():
    """Crea datos sintéticos para testing"""
    dates = pd.date_range(start='2025-01-01', end='2025-01-10', freq='1H')
    n = len(dates)
    
    # Crear tendencia alcista seguida de bajista
    price = np.linspace(100, 150, n//2)
    price = np.concatenate([price, np.linspace(150, 100, n - n//2)])
    
    # Añadir algo de ruido
    noise = np.random.normal(0, 1, n)
    price += noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price,
        'high': price + np.random.uniform(0, 2, n),
        'low': price - np.random.uniform(0, 2, n),
        'close': price,
        'volume': np.random.uniform(1000, 5000, n)
    })
    
    return df.set_index('timestamp')

@pytest.mark.asyncio
async def test_strategy():
    """Test de la estrategia completa"""
    # Crear datos de prueba
    df = create_test_data()
    
    # Configurar estrategia
    strategy = UTBotPSARStrategy()
    
    # Configurar backtester
    backtester = Backtester(initial_capital=10000, commission=0.1)
    
    # Ejecutar backtesting
    results = backtester.run(strategy, df)
    
    # Verificaciones básicas
    assert results['total_trades'] > 0, "La estrategia debería generar trades"
    assert results['win_rate'] >= 0 and results['win_rate'] <= 1, "Win rate debe estar entre 0 y 1"
    assert len(results['equity_curve']) == len(df) + 1, "Equity curve debe tener la longitud correcta"
    
    # Verificar que no hay pérdidas excesivas
    assert results['max_drawdown'] < 50, "El drawdown máximo no debe ser excesivo"
    
    # Verificar la gestión de riesgo
    trades = results['trades']
    if trades:
        for trade in trades:
            # Verificar que el tamaño de la posición es razonable
            assert trade.position_size > 0, "El tamaño de la posición debe ser positivo"
            assert trade.position_size * trade.entry_price < results['equity_curve'][0], \
                "El tamaño de la posición no debe exceder el capital inicial"

@pytest.mark.asyncio
async def test_position_sizing():
    """Test específico para el cálculo del tamaño de la posición"""
    strategy = UTBotPSARStrategy(risk_percent=2.0)
    
    # Caso de prueba
    capital = 10000
    entry_price = 100
    stop_loss = 95
    
    # El riesgo es 2% de 10000 = 200
    # La diferencia entry-stop es 5
    # Por lo tanto, el tamaño debería ser aproximadamente 40 unidades
    position_size = strategy.calculate_position_size(capital, entry_price, stop_loss)
    
    expected_size = (capital * 0.02) / 5  # 200 / 5 = 40
    assert abs(position_size - expected_size) < 0.01, "El cálculo del tamaño de la posición es incorrecto"
