#!/usr/bin/env python3
"""
Script para consultar historial de operaciones y métricas de Binance testnet
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

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

def get_binance_trade_history():
    """Obtiene historial de trades de Binance testnet"""

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

        print("🔍 Consultando historial de operaciones...")
        print("=" * 60)

        # Obtener trades de los últimos 30 días
        since = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

        # Obtener todas las órdenes
        all_orders = []
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Principales símbolos

        for symbol in symbols:
            try:
                orders = exchange.fetch_closed_orders(symbol, since=since)
                all_orders.extend(orders)
                print(f"✅ {len(orders)} órdenes obtenidas para {symbol}")
            except Exception as e:
                print(f"⚠️ Error obteniendo órdenes de {symbol}: {e}")

        # Filtrar solo órdenes ejecutadas (filled)
        filled_orders = [order for order in all_orders if order['status'] == 'closed']

        print(f"\n📊 Total de órdenes cerradas: {len(filled_orders)}")

        if not filled_orders:
            print("❌ No se encontraron órdenes ejecutadas en los últimos 30 días")
            return None

        # Calcular métricas
        metrics = calculate_trade_metrics(filled_orders, exchange)

        # Mostrar resultados
        display_trade_summary(metrics, filled_orders)

        return metrics

    except Exception as e:
        print(f"❌ Error consultando historial: {e}")
        return None

def calculate_trade_metrics(orders, exchange):
    """Calcula métricas de trading"""

    metrics = {
        'total_orders': len(orders),
        'buy_orders': 0,
        'sell_orders': 0,
        'total_volume_usdt': 0,
        'total_fees_usdt': 0,
        'symbols_traded': set(),
        'winning_trades': 0,
        'losing_trades': 0,
        'total_pnl_usdt': 0,
        'best_trade_usdt': float('-inf'),
        'worst_trade_usdt': float('inf'),
        'avg_trade_size_usdt': 0,
        'trades_by_symbol': {},
        'daily_trades': {},
        'hourly_distribution': {}
    }

    for order in orders:
        symbol = order['symbol']
        side = order['side']
        amount = float(order['amount'])
        price = float(order['price'])
        cost = float(order['cost'])
        fee = order.get('fee', {})

        # Contar tipos de órdenes
        if side == 'buy':
            metrics['buy_orders'] += 1
        elif side == 'sell':
            metrics['sell_orders'] += 1

        # Símbolos operados
        metrics['symbols_traded'].add(symbol)

        # Volumen total
        metrics['total_volume_usdt'] += cost

        # Fees
        if fee and 'cost' in fee:
            fee_cost = float(fee['cost'])
            if fee.get('currency') == 'USDT':
                metrics['total_fees_usdt'] += fee_cost
            elif fee.get('currency') == 'BNB':
                # Convertir BNB a USDT si es posible
                try:
                    bnb_price = exchange.fetch_ticker('BNB/USDT')['last']
                    metrics['total_fees_usdt'] += fee_cost * bnb_price
                except:
                    pass

        # Estadísticas por símbolo
        if symbol not in metrics['trades_by_symbol']:
            metrics['trades_by_symbol'][symbol] = 0
        metrics['trades_by_symbol'][symbol] += 1

        # Distribución por hora del día
        timestamp = datetime.fromtimestamp(order['timestamp'] / 1000)
        hour = timestamp.hour
        if hour not in metrics['hourly_distribution']:
            metrics['hourly_distribution'][hour] = 0
        metrics['hourly_distribution'][hour] += 1

        # Distribución por día
        date = timestamp.date()
        if date not in metrics['daily_trades']:
            metrics['daily_trades'][date] = 0
        metrics['daily_trades'][date] += 1

    # Calcular PnL aproximado (simplificado)
    # En una implementación real necesitaríamos emparejar buys/sells
    # Por ahora solo contamos el número de operaciones

    metrics['avg_trade_size_usdt'] = metrics['total_volume_usdt'] / metrics['total_orders'] if metrics['total_orders'] > 0 else 0

    return metrics

def display_trade_summary(metrics, orders):
    """Muestra resumen de operaciones"""

    print("\n" + "=" * 60)
    print("📈 RESUMEN DE OPERACIONES - BINANCE TESTNET")
    print("=" * 60)

    print("\n📊 ESTADÍSTICAS GENERALES:")
    print(f"   • Total de órdenes: {metrics['total_orders']}")
    print(f"   • Órdenes de compra: {metrics['buy_orders']}")
    print(f"   • Órdenes de venta: {metrics['sell_orders']}")
    print(f"   • Volumen total: ${metrics['total_volume_usdt']:.2f} USDT")
    print(f"   • Fees totales: ${metrics['total_fees_usdt']:.2f} USDT")
    print(f"   • Símbolos operados: {len(metrics['symbols_traded'])}")

    print("\n🪙 SÍMBOLOS OPERADOS:")
    for symbol, count in sorted(metrics['trades_by_symbol'].items(), key=lambda x: x[1], reverse=True):
        print(f"   • {symbol}: {count} operaciones")

    print("\n📅 DISTRIBUCIÓN POR DÍA:")
    for date, count in sorted(metrics['daily_trades'].items()):
        print(f"   • {date}: {count} operaciones")

    print("\n🕐 DISTRIBUCIÓN POR HORA:")
    for hour in sorted(metrics['hourly_distribution'].keys()):
        count = metrics['hourly_distribution'][hour]
        hour_str = f"{hour:02d}:00"
        print(f"   • {hour_str}: {count} operaciones")

    # Mostrar últimas 5 operaciones
    print("\n📋 ÚLTIMAS 5 OPERACIONES:")
    print("-" * 60)

    recent_orders = sorted(orders, key=lambda x: x['timestamp'], reverse=True)[:5]

    for order in recent_orders:
        timestamp = datetime.fromtimestamp(order['timestamp'] / 1000)
        symbol = order['symbol']
        side = order['side'].upper()
        amount = float(order['amount'])
        price = float(order['price'])
        cost = float(order['cost'])

        print("<12")

    print("-" * 60)
    print("\n💡 NOTAS:")
    print("   • Estas son operaciones en TESTNET (fondos ficticios)")
    print("   • Las métricas son aproximadas y para fines de análisis")
    print("   • Para análisis detallado de PnL real se necesitaría matching de buy/sell")
    print("=" * 60)

def main():
    """Función principal"""
    print("📊 CONSULTOR DE OPERACIONES - BINANCE TESTNET")
    print("=" * 60)

    result = get_binance_trade_history()

    if result is None:
        print("\n❌ No se pudo obtener el historial de operaciones")
        print("\nPosibles causas:")
        print("• No hay operaciones realizadas")
        print("• Error de conexión con Binance testnet")
        print("• Credenciales inválidas")
    else:
        print("\n✅ Consulta completada exitosamente")
        print(f"📊 Total de operaciones analizadas: {result['total_orders']}")

if __name__ == "__main__":
    main()