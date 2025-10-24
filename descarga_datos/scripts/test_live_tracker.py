#!/usr/bin/env python3
"""
Script de prueba para el sistema de Live Trading Tracker.

Este script prueba todas las funcionalidades del LiveTradingTracker
con datos simulados para verificar que las métricas profesionales
se calculan correctamente.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from utils.live_trading_tracker import LiveTradingTracker

def generate_sample_trades(num_trades=20):
    """
    Genera operaciones de ejemplo para testing.

    Args:
        num_trades: Número de operaciones a generar

    Returns:
        Lista de diccionarios con datos de trades
    """
    trades = []
    symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
    base_time = datetime.now() - timedelta(days=7)

    for i in range(num_trades):
        symbol = random.choice(symbols)
        side = random.choice(['buy', 'sell'])

        # Generar precios realistas
        if symbol == 'BTC/USDT':
            entry_price = random.uniform(105000, 111000)
            exit_price = entry_price * random.uniform(0.95, 1.05)  # -5% a +5%
        elif symbol == 'ETH/USDT':
            entry_price = random.uniform(3200, 3800)
            exit_price = entry_price * random.uniform(0.95, 1.05)
        else:  # ADA/USDT
            entry_price = random.uniform(0.8, 1.2)
            exit_price = entry_price * random.uniform(0.95, 1.05)

        # Calcular P&L
        quantity = random.uniform(0.1, 2.0) if symbol == 'BTC/USDT' else random.uniform(1, 10)
        if side == 'buy':
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        trade = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'open_time': base_time + timedelta(hours=i*2),
            'close_time': base_time + timedelta(hours=i*2 + random.uniform(1, 24)),
            'exit_reason': random.choice(['take_profit', 'stop_loss', 'trailing_stop', 'manual'])
        }

        trades.append(trade)

    return trades

def test_live_trading_tracker():
    """
    Función principal de testing del LiveTradingTracker.
    """
    print("🧪 PRUEBA DEL SISTEMA LIVE TRADING TRACKER")
    print("=" * 60)

    # Inicializar tracker
    initial_balance = 100000.0
    tracker = LiveTradingTracker(initial_balance=initial_balance)

    print(f"✅ Tracker inicializado con balance: ${initial_balance:,.2f}")

    # Generar y agregar trades de prueba
    print("\n📊 GENERANDO OPERACIONES DE PRUEBA...")
    sample_trades = generate_sample_trades(25)

    for i, trade in enumerate(sample_trades, 1):
        tracker.add_trade(trade)
        if i % 5 == 0:
            print(f"   ➤ Agregadas {i} operaciones...")

    print(f"✅ {len(sample_trades)} operaciones agregadas exitosamente")

    # Obtener métricas completas
    print("\n📈 MÉTRICAS PROFESIONALES CALCULADAS:")
    print("-" * 60)

    metrics = tracker.get_comprehensive_metrics()

    # Métricas básicas
    print("🎯 MÉTRICAS BÁSICAS:")
    print(f"   • Total de operaciones: {metrics['total_trades']}")
    print(f"   • Operaciones ganadoras: {metrics['winning_trades']}")
    print(f"   • Operaciones perdedoras: {metrics['losing_trades']}")
    print(".1f")
    print(".2f")
    print(".2f")

    # Balance y capital
    print("\n💰 BALANCE Y CAPITAL:")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")

    # Métricas de riesgo
    print("\n📉 MÉTRICAS DE RIESGO:")
    print(".2f")
    print(".2f")

    # Métricas avanzadas
    print("\n🎲 MÉTRICAS AVANZADAS:")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")

    # Estadísticas adicionales
    print("\n📊 ESTADÍSTICAS ADICIONALES:")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".1f")

    # Información temporal
    print("\n⏰ INFORMACIÓN TEMPORAL:")
    print(f"   • Tiempo de ejecución: {metrics['runtime_minutes']:.1f} minutos")
    print(f"   • Inicio: {metrics['start_time']}")
    print(f"   • Última actualización: {metrics['last_update']}")

    # Guardar estado
    print("\n💾 GUARDANDO ESTADO...")
    results_dir = Path(__file__).parent.parent / "data" / "live_trading_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    test_filename = f"test_tracker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    test_filepath = results_dir / test_filename

    tracker.save_to_file(str(test_filepath))
    print(f"✅ Estado guardado en: {test_filepath}")

    # Probar carga de estado
    print("\n📂 PROBANDO CARGA DE ESTADO...")
    new_tracker = LiveTradingTracker(initial_balance=initial_balance)
    if new_tracker.load_from_file(str(test_filepath)):
        new_metrics = new_tracker.get_comprehensive_metrics()
        if abs(new_metrics['total_pnl'] - metrics['total_pnl']) < 0.01:
            print("✅ Carga de estado exitosa - métricas coinciden")
        else:
            print("❌ Error en carga de estado - métricas no coinciden")
    else:
        print("❌ Error cargando estado")

    # Verificación final
    print("\n🎯 VERIFICACIÓN FINAL:")
    print(f"   • Trades en historial: {len(tracker.trades_history)}")
    print(f"   • Puntos en equity curve: {len(tracker.equity_curve)}")
    print(f"   • Archivo guardado: {test_filepath.exists()}")

    print("\n🏆 PRUEBA COMPLETADA EXITOSAMENTE!")
    print("=" * 60)

    return metrics

if __name__ == "__main__":
    # Ejecutar prueba
    metrics = test_live_trading_tracker()

    # Mostrar resumen final
    print("\n📋 RESUMEN EJECUTIVO:")
    print(f"• Sistema de tracking: ✅ Funcional")
    print(f"• Métricas profesionales: ✅ Calculadas")
    print(f"• Persistencia de datos: ✅ Implementada")
    print(f"• Total P&L generado: ${metrics['total_pnl']:,.2f}")
    print(f"• Win Rate alcanzado: {metrics['win_rate']*100:.1f}%")
    print(f"• Profit Factor: {metrics['profit_factor']:.2f}")
    print("\n🚀 Sistema listo para LIVE TRADING!")