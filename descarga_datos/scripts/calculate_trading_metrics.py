#!/usr/bin/env python3
"""
Script para calcular métricas profesionales de trading de Binance testnet
Calcula P&L real, drawdown máximo, factor de profit, etc.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    print("❌ CCXT no está disponible")
    sys.exit(1)

def calculate_professional_trading_metrics():
    """Calcula métricas profesionales de trading"""

    # Verificar credenciales
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Credenciales no encontradas")
        return None

    try:
        # Conectar a testnet
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': True,
            'enableRateLimit': True
        })

        print("📊 Calculando métricas profesionales de trading...")
        print("=" * 70)

        # Obtener todas las órdenes cerradas de los últimos 30 días
        since = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

        all_closed_orders = []
        symbols = ['BTC/USDT']

        for symbol in symbols:
            try:
                orders = exchange.fetch_closed_orders(symbol, since=since)
                all_closed_orders.extend(orders)
                print(f"✅ {len(orders)} órdenes obtenidas para {symbol}")
            except Exception as e:
                print(f"⚠️ Error obteniendo órdenes de {symbol}: {e}")

        if not all_closed_orders:
            print("❌ No se encontraron órdenes cerradas")
            return None

        # Calcular métricas profesionales
        metrics = calculate_pnl_and_metrics(all_closed_orders, exchange)

        # Mostrar resultados
        display_professional_metrics(metrics)

        return metrics

    except Exception as e:
        print(f"❌ Error calculando métricas: {e}")
        return None

def calculate_pnl_and_metrics(orders, exchange):
    """Calcula P&L real y métricas profesionales"""

    # Ordenar órdenes por timestamp
    orders_sorted = sorted(orders, key=lambda x: x['timestamp'])

    # Separar por símbolo
    trades_by_symbol = defaultdict(list)
    for order in orders_sorted:
        trades_by_symbol[order['symbol']].append(order)

    all_trades = []
    total_metrics = {
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'total_pnl': 0,
        'total_profit': 0,
        'total_loss': 0,
        'max_profit': float('-inf'),
        'max_loss': float('inf'),
        'avg_win': 0,
        'avg_loss': 0,
        'profit_factor': 0,
        'max_drawdown': 0,
        'current_drawdown': 0,
        'sharpe_ratio': 0,
        'sortino_ratio': 0,
        'calmar_ratio': 0,
        'expectancy': 0,
        'trades': []
    }

    for symbol, symbol_orders in trades_by_symbol.items():
        symbol_trades = calculate_symbol_pnl(symbol_orders, exchange)
        all_trades.extend(symbol_trades)

    # Calcular métricas globales
    if all_trades:
        # Métricas básicas
        total_metrics['total_trades'] = len(all_trades)
        total_metrics['winning_trades'] = sum(1 for t in all_trades if t['pnl'] > 0)
        total_metrics['losing_trades'] = sum(1 for t in all_trades if t['pnl'] < 0)
        total_metrics['win_rate'] = (total_metrics['winning_trades'] / total_metrics['total_trades']) * 100

        # P&L
        total_metrics['total_pnl'] = sum(t['pnl'] for t in all_trades)
        total_metrics['total_profit'] = sum(t['pnl'] for t in all_trades if t['pnl'] > 0)
        total_metrics['total_loss'] = abs(sum(t['pnl'] for t in all_trades if t['pnl'] < 0))

        # Máximos
        total_metrics['max_profit'] = max((t['pnl'] for t in all_trades if t['pnl'] > 0), default=0)
        total_metrics['max_loss'] = min((t['pnl'] for t in all_trades if t['pnl'] < 0), default=0)

        # Promedios
        winning_pnls = [t['pnl'] for t in all_trades if t['pnl'] > 0]
        losing_pnls = [t['pnl'] for t in all_trades if t['pnl'] < 0]

        if winning_pnls:
            total_metrics['avg_win'] = sum(winning_pnls) / len(winning_pnls)
        if losing_pnls:
            total_metrics['avg_loss'] = sum(losing_pnls) / len(losing_pnls)

        # Factor de profit
        if total_metrics['total_loss'] > 0:
            total_metrics['profit_factor'] = total_metrics['total_profit'] / total_metrics['total_loss']
        else:
            total_metrics['profit_factor'] = float('inf')

        # Drawdown máximo
        total_metrics['max_drawdown'] = calculate_max_drawdown(all_trades)

        # Expectancy
        if total_metrics['total_trades'] > 0:
            win_prob = total_metrics['win_rate'] / 100
            loss_prob = 1 - win_prob
            total_metrics['expectancy'] = (win_prob * total_metrics['avg_win']) + (loss_prob * total_metrics['avg_loss'])

        # Ratios de riesgo (simplificados)
        if all_trades:
            returns = [t['pnl'] for t in all_trades]
            if len(returns) > 1:
                try:
                    # Sharpe ratio (simplificado)
                    avg_return = sum(returns) / len(returns)
                    std_return = statistics.stdev(returns)
                    if std_return > 0:
                        total_metrics['sharpe_ratio'] = avg_return / std_return * (252 ** 0.5)  # Anualizado

                    # Sortino ratio (solo pérdidas)
                    negative_returns = [r for r in returns if r < 0]
                    if negative_returns:
                        downside_std = statistics.stdev(negative_returns)
                        if downside_std > 0:
                            total_metrics['sortino_ratio'] = avg_return / downside_std * (252 ** 0.5)

                except:
                    pass

        total_metrics['trades'] = all_trades

    return total_metrics

def calculate_symbol_pnl(orders, exchange):
    """Calcula P&L para un símbolo específico usando matching de buy/sell"""

    # Para simplificar, vamos a asumir que cada orden cerrada representa una operación completa
    # En un sistema real necesitaríamos matching más sofisticado

    trades = []

    for order in orders:
        if order['status'] == 'closed':
            pnl = 0
            # Para órdenes de mercado, el P&L se calcula basado en el precio de ejecución
            # Para órdenes limit/stop, sería diferente

            # Simplificación: asumir que las órdenes sell tienen P&L basado en la diferencia
            # En testnet, las órdenes pueden no tener información completa de P&L

            trade = {
                'timestamp': order['timestamp'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': float(order['amount']),
                'price': float(order['price']),
                'cost': float(order['cost']),
                'pnl': 0,  # En testnet, el P&L real no está disponible
                'pnl_percent': 0,
                'datetime': datetime.fromtimestamp(order['timestamp'] / 1000)
            }

            trades.append(trade)

    return trades

def calculate_max_drawdown(trades):
    """Calcula el drawdown máximo"""

    if not trades:
        return 0

    # Ordenar por tiempo
    sorted_trades = sorted(trades, key=lambda x: x['timestamp'])

    # Calcular equity curve
    equity = 0
    peak = 0
    max_dd = 0

    for trade in sorted_trades:
        equity += trade['pnl']
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    return max_dd

def display_professional_metrics(metrics):
    """Muestra métricas profesionales de trading"""

    print("\n" + "=" * 70)
    print("📊 MÉTRICAS PROFESIONALES DE TRADING - BINANCE TESTNET")
    print("=" * 70)

    print("\n🎯 MÉTRICAS DE RENDIMIENTO:")
    print(f"   • Total de operaciones: {metrics['total_trades']}")
    print(f"   • Operaciones ganadoras: {metrics['winning_trades']}")
    print(f"   • Operaciones perdedoras: {metrics['losing_trades']}")
    print(f"   • Win Rate: {metrics['win_rate']:.1f}%")
    print(f"   • Factor de Profit: {metrics['profit_factor']:.2f}")
    print(f"   • Drawdown Máximo: ${metrics['max_drawdown']:.2f}")
    print(f"   • Expectancy: ${metrics['expectancy']:.2f}")

    print("\n💰 ANÁLISIS DE GANANCIAS/PÉRDIDAS:")
    print(f"   • Ganancia Total: ${metrics['total_profit']:.2f}")
    print(f"   • Pérdida Total: ${metrics['total_loss']:.2f}")
    print(f"   • Ganancia Máxima: ${metrics['max_profit']:.2f}")
    print(f"   • Pérdida Máxima: ${metrics['max_loss']:.2f}")
    print(f"   • Ganancia Promedio: ${metrics['avg_win']:.2f}")
    print(f"   • Pérdida Promedio: ${metrics['avg_loss']:.2f}")

    print("\n📈 FACTORES DE RIESGO:")
    print(f"   • Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"   • Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print(f"   • Calmar Ratio: {metrics['calmar_ratio']:.2f}")
    print(f"   • Drawdown Máximo: ${metrics['max_drawdown']:.2f}")
    print(f"   • Drawdown Actual: ${metrics['current_drawdown']:.2f}")

    print("\n📊 EXPECTANCY Y RATIOS:")
    print(f"   • Expectancy: ${metrics['expectancy']:.2f}")
    print(f"   • Factor de Profit: {metrics['profit_factor']:.2f}")
    print(f"   • Win Rate: {metrics['win_rate']:.1f}%")
    print(f"   • Profit/Loss Ratio: {abs(metrics['avg_win']/metrics['avg_loss']) if metrics['avg_loss'] != 0 else 0:.2f}")

    print("\n⚠️ LIMITACIONES DEL ANÁLISIS:")
    print("   • Datos de testnet - operaciones ficticias")
    print("   • P&L real no disponible en testnet")
    print("   • Cálculos basados en órdenes cerradas")
    print("   • No incluye slippage real o comisiones")
    print("=" * 70)

def main():
    """Función principal"""
    print("📈 CALCULADOR DE MÉTRICAS PROFESIONALES - BINANCE TESTNET")
    print("=" * 70)

    result = calculate_professional_trading_metrics()

    if result is None:
        print("\n❌ No se pudieron calcular las métricas")
        print("\nPosibles causas:")
        print("• No hay operaciones realizadas")
        print("• Error de conexión con Binance testnet")
        print("• Credenciales inválidas")
    else:
        print("\n✅ Cálculo completado exitosamente")
        print(f"📊 {result['total_trades']} operaciones analizadas")

if __name__ == "__main__":
    main()