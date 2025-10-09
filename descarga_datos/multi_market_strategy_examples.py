#!/usr/bin/env python3
"""
SCRIPT DE EJEMPLO: Multi-Market UltraDetailed Heikin Ashi ML Strategy
======================================================================

Este script demuestra cómo usar la estrategia adaptada para múltiples mercados:
- Forex (pares de divisas)
- Commodities (oro, petróleo, etc.)
- Stocks (acciones individuales)
- Synthetic (símbolos sintéticos similares a crypto)

INSTRUCCIONES:
1. Instalar dependencias: pip install -r requirements.txt
2. Configurar APIs según el mercado (OANDA para forex, Alpaca para stocks, etc.)
3. Ejecutar ejemplos según el mercado deseado

AUTORES: Sistema de Trading Multi-Mercado v2.8
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.multi_market_ultra_detailed_heikin_ashi_ml_strategy import MultiMarketUltraDetailedHeikinAshiMLStrategy
from config.config import load_config_from_yaml
import utils.logger as logger

def run_forex_example():
    """
    Ejemplo: Ejecutar estrategia en mercado FOREX
    """
    print("🌍 EJEMPLO FOREX: EUR/USD en timeframe 1h")
    print("=" * 50)

    # Configurar para forex
    config = load_config_from_yaml()
    config.symbol = 'EUR/USD'
    config.timeframe = '1h'
    config.backtesting.timeframe = '1h'

    # Crear estrategia multi-mercado
    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

    # NOTA: En producción, cargarías datos reales de tu broker forex
    # Aquí usamos datos simulados para demostración
    print("⚠️  NOTA: Este es un ejemplo con datos simulados")
    print("   Para producción: integrar con API de OANDA, Interactive Brokers, etc.")

    # Simular datos forex (en producción vendrían de la API)
    dates = pd.date_range('2023-01-01', periods=1000, freq='1H')
    np.random.seed(42)

    # Generar datos simulados realistas para EUR/USD
    base_price = 1.0850
    prices = []
    current_price = base_price

    for i in range(len(dates)):
        # Movimiento browniano con drift y volatilidad forex realista
        drift = 0.00001  # Drift muy pequeño en forex
        volatility = 0.0008  # Volatilidad realista para EUR/USD
        shock = np.random.normal(drift, volatility)
        current_price *= (1 + shock)

        # Generar OHLC
        high = current_price * (1 + abs(np.random.normal(0, 0.0003)))
        low = current_price * (1 - abs(np.random.normal(0, 0.0003)))
        open_price = prices[-1][3] if prices else current_price
        close = current_price
        volume = np.random.randint(1000, 10000)  # Volumen forex típico

        prices.append([open_price, high, low, close, volume])

    data = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)

    print(f"📊 Datos simulados preparados: {len(data)} velas de 1h")
    print(f"   Precio promedio: {data['close'].mean():.4f}")
    print(f"   Rango: {data['low'].min():.4f} - {data['high'].max():.4f}")

    # Ejecutar estrategia
    try:
        results = strategy.run(data, 'EUR/USD', '1h')

        print("\n📈 RESULTADOS FOREX:")
        print(f"   Trades Totales: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1%}")
        print(f"   P&L Total: ${results['total_pnl']:.2f}")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"   Capital Final: ${results['final_capital']:.2f}")

    except Exception as e:
        print(f"❌ Error en estrategia forex: {e}")
        return False

    return True

def run_commodities_example():
    """
    Ejemplo: Ejecutar estrategia en mercado COMMODITIES
    """
    print("\n🛢️ EJEMPLO COMMODITIES: XAU/USD (Oro) en timeframe 4h")
    print("=" * 50)

    config = load_config_from_yaml()
    config.symbol = 'XAU/USD'
    config.timeframe = '4h'
    config.backtesting.timeframe = '4h'

    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

    print("⚠️  NOTA: Ejemplo con datos simulados de oro")
    print("   Para producción: integrar con API de Binance, CME Group, etc.")

    # Simular datos de oro (XAU/USD)
    dates = pd.date_range('2023-01-01', periods=500, freq='4H')
    np.random.seed(123)

    base_price = 1950.00
    prices = []
    current_price = base_price

    for i in range(len(dates)):
        # Oro tiene volatilidad y tendencias más pronunciadas
        drift = 0.00005  # Drift positivo (oro como refugio)
        volatility = 0.008  # Volatilidad más alta que forex
        shock = np.random.normal(drift, volatility)
        current_price *= (1 + shock)

        high = current_price * (1 + abs(np.random.normal(0, 0.005)))
        low = current_price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[-1][3] if prices else current_price
        close = current_price
        volume = np.random.randint(5000, 50000)  # Volumen commodities

        prices.append([open_price, high, low, close, volume])

    data = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)

    print(f"📊 Datos simulados de oro preparados: {len(data)} velas de 4h")
    print(f"   Precio promedio: ${data['close'].mean():.2f}")
    print(f"   Rango: ${data['low'].min():.2f} - ${data['high'].max():.2f}")

    try:
        results = strategy.run(data, 'XAU/USD', '4h')

        print("\n📈 RESULTADOS COMMODITIES:")
        print(f"   Trades Totales: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1%}")
        print(f"   P&L Total: ${results['total_pnl']:.2f}")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"   Capital Final: ${results['final_capital']:.2f}")

    except Exception as e:
        print(f"❌ Error en estrategia commodities: {e}")
        return False

    return True

def run_stocks_example():
    """
    Ejemplo: Ejecutar estrategia en mercado STOCKS
    """
    print("\n📈 EJEMPLO STOCKS: AAPL (Apple) en timeframe diario")
    print("=" * 50)

    config = load_config_from_yaml()
    config.symbol = 'AAPL'
    config.timeframe = '1d'
    config.backtesting.timeframe = '1d'

    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

    print("⚠️  NOTA: Ejemplo con datos simulados de acciones")
    print("   Para producción: integrar con API de Alpaca, Interactive Brokers, etc.")

    # Simular datos de acciones (AAPL)
    dates = pd.date_range('2023-01-01', periods=250, freq='1D')  # ~1 año de datos diarios
    np.random.seed(456)

    base_price = 150.00
    prices = []
    current_price = base_price

    for i in range(len(dates)):
        # Acciones tienen tendencias más suaves pero con gaps
        drift = 0.0002  # Drift moderado positivo
        volatility = 0.015  # Volatilidad acciones típica
        shock = np.random.normal(drift, volatility)
        current_price *= (1 + shock)

        # Simular gaps de fin de semana (aumentar volatilidad los lunes)
        if dates[i].weekday() == 0:  # Lunes
            gap_volatility = 0.025
            gap_shock = np.random.normal(0, gap_volatility)
            current_price *= (1 + gap_shock)

        high = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low = current_price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[-1][3] if prices else current_price
        close = current_price
        volume = np.random.randint(50000000, 200000000)  # Volumen acciones típico

        prices.append([open_price, high, low, close, volume])

    data = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)

    print(f"📊 Datos simulados de AAPL preparados: {len(data)} velas diarias")
    print(f"   Precio promedio: ${data['close'].mean():.2f}")
    print(f"   Rango: ${data['low'].min():.2f} - ${data['high'].max():.2f}")

    try:
        results = strategy.run(data, 'AAPL', '1d')

        print("\n📈 RESULTADOS STOCKS:")
        print(f"   Trades Totales: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1%}")
        print(f"   P&L Total: ${results['total_pnl']:.2f}")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"   Capital Final: ${results['final_capital']:.2f}")

    except Exception as e:
        print(f"❌ Error en estrategia stocks: {e}")
        return False

    return True

def run_synthetic_example():
    """
    Ejemplo: Ejecutar estrategia en mercado SYNTHETIC
    """
    print("\n🎯 EJEMPLO SYNTHETIC: Volatility Index Sintético en timeframe 4h")
    print("=" * 50)

    config = load_config_from_yaml()
    config.symbol = 'VOLATILITY_INDEX'
    config.timeframe = '4h'
    config.backtesting.timeframe = '4h'

    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

    print("⚠️  NOTA: Ejemplo con índice sintético de volatilidad")
    print("   Similar a VIX pero con comportamiento crypto-like")

    # Simular índice sintético de volatilidad
    dates = pd.date_range('2023-01-01', periods=500, freq='4H')
    np.random.seed(789)

    base_price = 25.00  # Nivel base de volatilidad
    prices = []
    current_price = base_price

    for i in range(len(dates)):
        # Volatilidad tiene mean-reversion pero con spikes
        mean_reversion = (base_price - current_price) * 0.01  # Revertir a la media
        volatility = 0.05  # Alta volatilidad propia de índices VIX-like
        shock = np.random.normal(mean_reversion, volatility)

        # Spikes aleatorios (eventos de mercado)
        if np.random.random() < 0.02:  # 2% de probabilidad de spike
            spike_direction = np.random.choice([-1, 1])
            spike_magnitude = np.random.uniform(0.1, 0.3)
            shock += spike_direction * spike_magnitude

        current_price += shock
        current_price = max(5, min(100, current_price))  # Límites realistas

        high = current_price * (1 + abs(np.random.normal(0, 0.03)))
        low = current_price * (1 - abs(np.random.normal(0, 0.03)))
        open_price = prices[-1][3] if prices else current_price
        close = current_price
        volume = np.random.randint(10000, 100000)  # Volumen sintético

        prices.append([open_price, high, low, close, volume])

    data = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)

    print(f"📊 Datos sintéticos preparados: {len(data)} velas de 4h")
    print(f"   Nivel promedio: {data['close'].mean():.2f}")
    print(f"   Rango: {data['low'].min():.2f} - {data['high'].max():.2f}")

    try:
        results = strategy.run(data, 'VOLATILITY_INDEX', '4h')

        print("\n📈 RESULTADOS SYNTHETIC:")
        print(f"   Trades Totales: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1%}")
        print(f"   P&L Total: ${results['total_pnl']:.2f}")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"   Capital Final: ${results['final_capital']:.2f}")

    except Exception as e:
        print(f"❌ Error en estrategia synthetic: {e}")
        return False

    return True

def main():
    """
    Función principal: Ejecutar todos los ejemplos
    """
    print("🚀 MULTI-MARKET ULTRA DETAILED HEIKIN ASHI ML STRATEGY")
    print("=" * 60)
    print("Ejecutando ejemplos para todos los mercados...")
    print()

    results = []

    # Ejecutar ejemplos
    results.append(("Forex (EUR/USD)", run_forex_example()))
    results.append(("Commodities (XAU/USD)", run_commodities_example()))
    results.append(("Stocks (AAPL)", run_stocks_example()))
    results.append(("Synthetic (VOLATILITY_INDEX)", run_synthetic_example()))

    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE EJEMPLOS EJECUTADOS:")
    print("=" * 60)

    successful = 0
    for market, success in results:
        status = "✅ ÉXITO" if success else "❌ ERROR"
        print(f"   {market}: {status}")
        if success:
            successful += 1

    print(f"\n🎯 Resultado: {successful}/{len(results)} mercados ejecutados exitosamente")

    if successful == len(results):
        print("\n🎉 ¡Todos los ejemplos se ejecutaron correctamente!")
        print("💡 RECOMENDACIONES PARA PRODUCCIÓN:")
        print("   1. Integrar APIs reales para datos de mercado")
        print("   2. Ajustar parámetros según backtesting real")
        print("   3. Implementar validación cruzada de mercados")
        print("   4. Configurar límites de riesgo apropiados")
        print("   5. Monitorear rendimiento en tiempo real")
    else:
        print(f"\n⚠️  {len(results) - successful} ejemplos fallaron. Revisar configuración y dependencias.")

if __name__ == "__main__":
    main()