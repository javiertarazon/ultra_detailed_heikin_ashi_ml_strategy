#!/usr/bin/env python3
"""
Script para calcular métricas aproximadas de trading en testnet
Explica limitaciones y proporciona métricas disponibles
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

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

def calculate_available_metrics():
    """Calcula métricas disponibles en testnet"""

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

        print("📊 Calculando métricas disponibles en testnet...")
        print("=" * 70)

        # Obtener órdenes cerradas
        since = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        orders = exchange.fetch_closed_orders('BTC/USDT', since=since)

        print(f"✅ {len(orders)} órdenes obtenidas")

        # Calcular métricas disponibles
        metrics = calculate_basic_metrics(orders)

        # Mostrar resultados
        display_available_metrics(metrics)

        return metrics

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def calculate_basic_metrics(orders):
    """Calcula métricas básicas disponibles en testnet"""

    metrics = {
        'total_orders': len(orders),
        'buy_orders': len([o for o in orders if o['side'] == 'buy']),
        'sell_orders': len([o for o in orders if o['side'] == 'sell']),
        'total_volume_usdt': sum(float(o['cost']) for o in orders),
        'avg_order_size': 0,
        'symbols': set(o['symbol'] for o in orders),
        'date_range': {'start': None, 'end': None},
        'hourly_distribution': defaultdict(int),
        'daily_volume': defaultdict(float),
        'price_ranges': {'min': float('inf'), 'max': float('-inf'), 'avg': 0}
    }

    if orders:
        # Tamaño promedio
        metrics['avg_order_size'] = metrics['total_volume_usdt'] / len(orders)

        # Rango de fechas
        timestamps = [o['timestamp'] for o in orders]
        metrics['date_range']['start'] = datetime.fromtimestamp(min(timestamps) / 1000)
        metrics['date_range']['end'] = datetime.fromtimestamp(max(timestamps) / 1000)

        # Distribución por hora
        for order in orders:
            dt = datetime.fromtimestamp(order['timestamp'] / 1000)
            metrics['hourly_distribution'][dt.hour] += 1

        # Volumen por día
        for order in orders:
            dt = datetime.fromtimestamp(order['timestamp'] / 1000)
            date = dt.date()
            metrics['daily_volume'][date] += float(order['cost'])

        # Rangos de precio
        prices = [float(o['price']) for o in orders]
        metrics['price_ranges']['min'] = min(prices)
        metrics['price_ranges']['max'] = max(prices)
        metrics['price_ranges']['avg'] = sum(prices) / len(prices)

    return metrics

def display_available_metrics(metrics):
    """Muestra métricas disponibles"""

    print("\n" + "=" * 70)
    print("📊 MÉTRICAS DISPONIBLES EN TESTNET - BINANCE")
    print("=" * 70)

    print("\n📈 ESTADÍSTICAS DE OPERACIONES:")
    print(f"   • Total de órdenes: {metrics['total_orders']}")
    print(f"   • Órdenes de compra: {metrics['buy_orders']}")
    print(f"   • Órdenes de venta: {metrics['sell_orders']}")
    print(f"   • Volumen total: ${metrics['total_volume_usdt']:.2f}")
    print(f"   • Tamaño promedio: ${metrics['avg_order_size']:.2f}")
    print(f"   • Símbolos operados: {len(metrics['symbols'])}")

    if metrics['date_range']['start']:
        print("\n📅 PERÍODO DE OPERACIONES:")
        print(f"   • Desde: {metrics['date_range']['start']}")
        print(f"   • Hasta: {metrics['date_range']['end']}")
        days = (metrics['date_range']['end'] - metrics['date_range']['start']).days
        print(f"   • Duración: {days} días")

    print("\n💰 RANGOS DE PRECIO (BTC/USDT):")
    print(f"   • Precio mínimo: ${metrics['price_ranges']['min']:.2f}")
    print(f"   • Precio máximo: ${metrics['price_ranges']['max']:.2f}")
    print(f"   • Precio promedio: ${metrics['price_ranges']['avg']:.2f}")

    print("\n🕐 DISTRIBUCIÓN HORARIA (órdenes/día):")
    for hour in sorted(metrics['hourly_distribution'].keys()):
        orders_per_day = metrics['hourly_distribution'][hour] / max(1, (metrics['date_range']['end'] - metrics['date_range']['start']).days)
        print(f"   • {hour:02d}:00: {orders_per_day:.1f} órdenes/día")

    print("\n📊 VOLUMEN DIARIO PROMEDIO:")
    if metrics['daily_volume']:
        avg_daily_volume = sum(metrics['daily_volume'].values()) / len(metrics['daily_volume'])
        print(f"   • Volumen promedio diario: ${avg_daily_volume:.2f}")
        max_daily_volume = max(metrics['daily_volume'].values())
        print(f"   • Volumen máximo diario: ${max_daily_volume:.2f}")

    print("\n⚠️ LIMITACIONES CRÍTICAS EN TESTNET:")
    print("   ❌ P&L REAL: No disponible en testnet")
    print("   ❌ DRAW DOWN: No se puede calcular sin P&L")
    print("   ❌ WIN RATE: No se puede determinar sin P&L")
    print("   ❌ FACTOR DE PROFIT: No disponible sin P&L")
    print("   ❌ EXPECTANCY: No calculable sin P&L")
    print("   ❌ SHARPE/SORTINO RATIO: No disponibles sin P&L")

    print("\n💡 PARA MÉTRICAS PROFESIONALES REALES:")
    print("   • Usar cuenta REAL de Binance (NO testnet)")
    print("   • Implementar tracking de P&L en el código del bot")
    print("   • Usar base de datos para almacenar resultados")
    print("   • Calcular métricas basadas en operaciones reales")
    print("=" * 70)

def main():
    """Función principal"""
    print("📊 MÉTRICAS DISPONIBLES EN TESTNET")
    print("=" * 70)

    result = calculate_available_metrics()

    if result:
        print("\n✅ Análisis completado")
        print(f"📊 {result['total_orders']} órdenes analizadas")
    else:
        print("\n❌ Error en el análisis")

if __name__ == "__main__":
    main()