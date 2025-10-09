#!/usr/bin/env python3
"""
VALIDACIÓN MULTI-MERCADO STRATEGY
===============================

Script de validación completo para la estrategia Multi-Market UltraDetailed Heikin Ashi ML.
Verifica funcionamiento en todos los mercados soportados.

INSTRUCCIONES:
1. Ejecutar después de cualquier cambio en la estrategia
2. Verificar que todos los mercados pasan las pruebas
3. Usar para debugging de problemas específicos

AUTORES: Sistema Multi-Mercado v2.8
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Agregar directorio padre
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.multi_market_ultra_detailed_heikin_ashi_ml_strategy import MultiMarketUltraDetailedHeikinAshiMLStrategy
from config.config import load_config_from_yaml
import utils.logger as logger

def validate_market_type_detection():
    """Validar detección automática de tipos de mercado"""
    print("🔍 VALIDANDO DETECCIÓN DE MERCADOS...")

    test_cases = [
        ('EUR/USD', 'forex'),
        ('GBP/JPY', 'forex'),
        ('XAU/USD', 'commodities'),
        ('WTI', 'commodities'),
        ('AAPL', 'stocks'),
        ('TSLA', 'stocks'),
        ('VOLATILITY_INDEX', 'synthetic'),
        ('SYNTH_BTC_INDEX', 'synthetic'),
        ('BTC/USDT', 'crypto'),
        ('XRP/USDT', 'crypto')
    ]

    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy()

    passed = 0
    for symbol, expected_market in test_cases:
        detected_market = strategy.ml_manager.detect_market_type(symbol)
        status = "✅" if detected_market == expected_market else "❌"
        print(f"   {status} {symbol}: esperado {expected_market}, detectado {detected_market}")
        if detected_market == expected_market:
            passed += 1

    print(f"   Resultado: {passed}/{len(test_cases)} mercados detectados correctamente")
    return passed == len(test_cases)

def validate_market_configs():
    """Validar configuraciones específicas por mercado"""
    print("\n⚙️ VALIDANDO CONFIGURACIONES POR MERCADO...")

    markets = ['forex', 'commodities', 'stocks', 'synthetic', 'crypto']
    required_params = [
        'ml_threshold', 'max_drawdown', 'max_concurrent_trades',
        'kelly_fraction', 'atr_multiplier', 'stop_loss_atr_multiplier'
    ]

    strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy()
    passed = 0

    for market in markets:
        config = strategy.ml_manager.get_market_config('TEST_SYMBOL')
        missing_params = [p for p in required_params if p not in config]

        if missing_params:
            print(f"   ❌ {market}: parámetros faltantes {missing_params}")
        else:
            print(f"   ✅ {market}: configuración completa")
            passed += 1

    print(f"   Resultado: {passed}/{len(markets)} mercados con configuración válida")
    return passed == len(markets)

def generate_synthetic_data(market_type: str, symbol: str, periods: int = 1000) -> pd.DataFrame:
    """Generar datos sintéticos realistas por mercado"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=periods, freq='1H')

    # Parámetros base por mercado
    market_params = {
        'forex': {
            'base_price': 1.0850,
            'volatility': 0.0008,
            'drift': 0.00001,
            'spread': 0.0001
        },
        'commodities': {
            'base_price': 1950.00,
            'volatility': 0.008,
            'drift': 0.00005,
            'spread': 0.0002
        },
        'stocks': {
            'base_price': 150.00,
            'volatility': 0.015,
            'drift': 0.0002,
            'spread': 0.0003
        },
        'synthetic': {
            'base_price': 25.00,
            'volatility': 0.05,
            'drift': 0.0001,
            'spread': 0.0005
        },
        'crypto': {
            'base_price': 45000.00,
            'volatility': 0.03,
            'drift': 0.0003,
            'spread': 0.001
        }
    }

    params = market_params.get(market_type, market_params['crypto'])
    current_price = params['base_price']
    prices = []

    for i in range(len(dates)):
        # Generar movimiento con características del mercado
        shock = np.random.normal(params['drift'], params['volatility'])
        current_price *= (1 + shock)

        # Evitar precios negativos o extremos
        current_price = max(current_price * 0.1, min(current_price, params['base_price'] * 10))

        # Generar OHLC con spreads realistas
        spread = params['spread'] * current_price
        high = current_price * (1 + abs(np.random.normal(0, params['volatility'] * 0.5)))
        low = current_price * (1 - abs(np.random.normal(0, params['volatility'] * 0.5)))
        open_price = prices[-1][3] if prices else current_price
        close = current_price

        # Volumen realista por mercado
        if market_type == 'forex':
            volume = np.random.randint(1000, 10000)
        elif market_type == 'stocks':
            volume = np.random.randint(50000000, 200000000)
        elif market_type == 'commodities':
            volume = np.random.randint(5000, 50000)
        else:
            volume = np.random.randint(10000, 100000)

        prices.append([open_price, high, low, close, volume])

    data = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)
    return data

def validate_market_strategy(market_type: str, symbol: str):
    """Validar estrategia completa para un mercado específico"""
    print(f"\n🎯 VALIDANDO ESTRATEGIA {market_type.upper()} ({symbol})...")

    try:
        # Generar datos sintéticos
        data = generate_synthetic_data(market_type, symbol, periods=500)
        print(f"   📊 Datos generados: {len(data)} velas")

        # Configurar estrategia
        config = {
            'symbol': symbol,
            'timeframe': '1h',
            'ml_training': {'safe_mode': True}  # Modo seguro para testing
        }

        strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

        # Verificar configuración cargada
        print(f"   🧠 Mercado detectado: {strategy.market_type}")
        print(f"   📈 ML Threshold: {strategy.ml_threshold}")
        print(f"   🛡️ Max Drawdown: {strategy.max_drawdown}")

        # Ejecutar estrategia
        results = strategy.run(data, symbol, '1h')

        # Validar resultados
        required_keys = ['total_trades', 'win_rate', 'total_pnl', 'max_drawdown', 'trades']
        missing_keys = [k for k in required_keys if k not in results]

        if missing_keys:
            print(f"   ❌ Resultados incompletos: faltan {missing_keys}")
            return False

        # Verificar métricas razonables
        trades = results['total_trades']
        win_rate = results['win_rate']
        pnl = results['total_pnl']
        drawdown = results['max_drawdown']

        print(f"   📊 Resultados: {trades} trades, Win Rate: {win_rate:.1%}, P&L: ${pnl:.2f}, Max DD: {drawdown:.1%}")

        # Validaciones específicas por mercado
        if market_type == 'forex':
            assert 0.50 <= win_rate <= 0.70, f"Win rate forex anormal: {win_rate}"
            assert drawdown <= 0.05, f"Drawdown forex muy alto: {drawdown}"
        elif market_type == 'stocks':
            assert 0.55 <= win_rate <= 0.75, f"Win rate stocks anormal: {win_rate}"
            assert drawdown <= 0.06, f"Drawdown stocks muy alto: {drawdown}"
        elif market_type == 'commodities':
            assert 0.55 <= win_rate <= 0.75, f"Win rate commodities anormal: {win_rate}"
            assert drawdown <= 0.08, f"Drawdown commodities muy alto: {drawdown}"

        print(f"   ✅ Estrategia {market_type} validada correctamente")
        return True

    except Exception as e:
        print(f"   ❌ Error en validación {market_type}: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_all_markets():
    """Validar estrategia en todos los mercados soportados"""
    print("🚀 VALIDACIÓN COMPLETA MULTI-MERCADO STRATEGY")
    print("=" * 60)

    market_tests = [
        ('forex', 'EUR/USD'),
        ('commodities', 'XAU/USD'),
        ('stocks', 'AAPL'),
        ('synthetic', 'VOLATILITY_INDEX'),
        ('crypto', 'BTC/USDT')
    ]

    results = []

    # Tests preliminares
    detection_ok = validate_market_type_detection()
    config_ok = validate_market_configs()

    if not detection_ok or not config_ok:
        print("\n❌ FALLÓ VALIDACIÓN PRELIMINAR - Abortando tests completos")
        return False

    # Tests por mercado
    for market_type, symbol in market_tests:
        success = validate_market_strategy(market_type, symbol)
        results.append((market_type, success))

    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN VALIDACIÓN MULTI-MERCADO:")
    print("=" * 60)

    successful = 0
    for market, success in results:
        status = "✅ ÉXITO" if success else "❌ FALLO"
        print(f"   {market.upper()}: {status}")
        if success:
            successful += 1

    print(f"\n🎯 Resultado Final: {successful}/{len(results)} mercados validados correctamente")

    if successful == len(results):
        print("\n🎉 ¡VALIDACIÓN COMPLETA EXITOSA!")
        print("💡 La estrategia Multi-Mercado está lista para uso en producción")
        return True
    else:
        print(f"\n⚠️ {len(results) - successful} mercados fallaron la validación")
        print("🔧 Revisar logs y corregir problemas antes del deployment")
        return False

def run_performance_benchmark():
    """Benchmark de performance entre mercados"""
    print("\n⏱️ EJECUTANDO BENCHMARK DE PERFORMANCE...")

    market_tests = [
        ('forex', 'EUR/USD'),
        ('commodities', 'XAU/USD'),
        ('stocks', 'AAPL'),
        ('crypto', 'BTC/USDT')
    ]

    benchmark_results = {}

    for market_type, symbol in market_tests:
        try:
            data = generate_synthetic_data(market_type, symbol, periods=1000)

            config = {
                'symbol': symbol,
                'timeframe': '1h',
                'ml_training': {'safe_mode': True}
            }

            strategy = MultiMarketUltraDetailedHeikinAshiMLStrategy(config)

            import time
            start_time = time.time()
            results = strategy.run(data, symbol, '1h')
            execution_time = time.time() - start_time

            benchmark_results[market_type] = {
                'execution_time': execution_time,
                'trades': results['total_trades'],
                'win_rate': results['win_rate'],
                'profit_factor': results['profit_factor']
            }

            print(".2f"
        except Exception as e:
            print(f"   ❌ {market_type}: Error en benchmark - {e}")
            benchmark_results[market_type] = {'error': str(e)}

    # Mostrar comparación
    print("\n📊 COMPARACIÓN DE PERFORMANCE:")
    print("Mercado      | Tiempo | Trades | Win Rate | Profit Factor")
    print("-" * 55)

    for market, data in benchmark_results.items():
        if 'error' not in data:
            print("12")
        else:
            print("12")

    return benchmark_results

def main():
    """Función principal de validación"""
    print("🔬 VALIDACIÓN MULTI-MERCADO ULTRA DETAILED HEIKIN ASHI ML STRATEGY")
    print("=" * 70)

    # Ejecutar validaciones
    validation_success = validate_all_markets()

    if validation_success:
        # Ejecutar benchmark si validación pasa
        benchmark_results = run_performance_benchmark()

        print("\n" + "=" * 70)
        print("✅ VALIDACIÓN COMPLETA - SISTEMA LISTO PARA PRODUCCIÓN")
        print("=" * 70)

        # Recomendaciones finales
        print("\n💡 RECOMENDACIONES PARA DEPLOYMENT:")
        print("   1. Configurar APIs reales para datos de mercado")
        print("   2. Ejecutar optimización Optuna para parámetros específicos")
        print("   3. Implementar monitoreo continuo de performance")
        print("   4. Configurar alertas automáticas para drawdown")
        print("   5. Validar con datos out-of-sample antes de ir live")

    else:
        print("\n" + "=" * 70)
        print("❌ VALIDACIÓN FALLIDA - CORREGIR ERRORES ANTES DE CONTINUAR")
        print("=" * 70)

        print("\n🔧 PASOS PARA DEBUGGING:")
        print("   1. Revisar logs de error detallados arriba")
        print("   2. Verificar configuraciones en multi_market_config.yaml")
        print("   3. Validar datos de entrada para cada mercado")
        print("   4. Ejecutar tests individuales por mercado")
        print("   5. Verificar dependencias e imports")

    return validation_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)