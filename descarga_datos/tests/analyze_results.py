#!/usr/bin/env python3
"""
Análisis de resultados del backtest para verificar uniformidad en P&L
"""
import json
import os
from pathlib import Path
import pandas as pd

def analyze_backtest_results():
    """Analiza los resultados del backtest para detectar patrones sospechosos"""

    results_dir = Path("data/dashboard_results")

    if not results_dir.exists():
        print("❌ No se encontraron resultados del backtest")
        return

    # Leer todos los archivos de resultados
    results = {}
    for file_path in results_dir.glob("*_results.json"):
        if file_path.name == "global_summary.json":
            continue

        symbol = file_path.stem.replace("_results", "").replace("_", "/")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results[symbol] = data
        except Exception as e:
            print(f"❌ Error leyendo {file_path}: {e}")

    if not results:
        print("❌ No se pudieron cargar resultados")
        return

    print("🔍 ANÁLISIS DE RESULTADOS DEL BACKTEST")
    print("=" * 60)

    # Extraer métricas clave
    metrics = []
    for symbol, data in results.items():
        try:
            # Las métricas están dentro de strategies.UltraDetailedHeikinAshiML
            strategy_data = data.get('strategies', {}).get('UltraDetailedHeikinAshiML', {})

            # Extraer métricas principales
            total_pnl = strategy_data.get('total_pnl', 0)
            total_trades = strategy_data.get('total_trades', 0)
            win_rate = strategy_data.get('win_rate', 0) * 100  # Convertir a porcentaje
            max_drawdown = strategy_data.get('max_drawdown', 0)
            profit_factor = strategy_data.get('profit_factor', 0)

            metrics.append({
                'symbol': symbol,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor
            })
        except Exception as e:
            print(f"⚠️ Error procesando {symbol}: {e}")

    if not metrics:
        print("❌ No se pudieron extraer métricas")
        return

    # Crear DataFrame para análisis
    df = pd.DataFrame(metrics)

    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   Total símbolos analizados: {len(df)}")
    print(f"   P&L total acumulado: ${df['total_pnl'].sum():.2f}")
    print(f"   Rango P&L: ${df['total_pnl'].min():.2f} - ${df['total_pnl'].max():.2f}")
    print(f"   P&L promedio por símbolo: ${df['total_pnl'].mean():.2f}")
    # Análisis de uniformidad
    print(f"\n🔍 ANÁLISIS DE UNIFORMIDAD:")

    # Estadísticas de P&L
    pnl_std = df['total_pnl'].std()
    pnl_mean = df['total_pnl'].mean()
    pnl_cv = pnl_std / pnl_mean if pnl_mean != 0 else 0  # Coeficiente de variación

    print(f"   Desviación estándar P&L: ${pnl_std:.2f}")
    print(f"   Coeficiente de variación: {pnl_cv:.2f}")

    if pnl_cv < 0.3:
        print("   ⚠️ ALERTA: P&L muy uniforme entre símbolos (coeficiente de variación < 30%)")
    elif pnl_cv < 0.5:
        print("   ⚠️ ATENCIÓN: P&L moderadamente uniforme entre símbolos")
    else:
        print("   ✅ P&L variado entre símbolos (parece normal)")

    # Análisis por tipo de activo
    print(f"\n📈 ANÁLISIS POR TIPO DE ACTIVO:")

    # Clasificar símbolos
    crypto_ccxt = ['SOL/USDT', 'ETH/USDT']
    crypto_mt5 = ['BTC/USD', 'ADA/USD', 'DOT/USD', 'MATIC/USD', 'XRP/USD', 'LTC/USD', 'DOGE/USD']
    stocks_mt5 = ['TSLA/US', 'NVDA/US', 'AAPL/US', 'MSFT/US', 'GOOGL/US', 'AMZN/US']
    forex_mt5 = ['EUR/USD', 'USD/JPY', 'GBP/USD']

    categories = {
        'Crypto CCXT': crypto_ccxt,
        'Crypto MT5': crypto_mt5,
        'Stocks MT5': stocks_mt5,
        'Forex MT5': forex_mt5
    }

    for category, symbols in categories.items():
        cat_data = df[df['symbol'].isin(symbols)]
        if not cat_data.empty:
            avg_pnl = cat_data['total_pnl'].mean()
            std_pnl = cat_data['total_pnl'].std()
            print(f"   {category}: P&L promedio ${avg_pnl:.2f} (±${std_pnl:.2f})")
    # Mostrar top/bottom performers
    print(f"\n🏆 TOP 5 MEJORES PERFORMERS:")
    top_5 = df.nlargest(5, 'total_pnl')[['symbol', 'total_pnl', 'win_rate', 'total_trades']]
    for _, row in top_5.iterrows():
        print(f"   {row['symbol']}: ${row['total_pnl']:.2f} ({row['win_rate']:.1f}% win, {int(row['total_trades'])} trades)")

    print(f"\n👎 BOTTOM 5 PEores PERFORMERS:")
    bottom_5 = df.nsmallest(5, 'total_pnl')[['symbol', 'total_pnl', 'win_rate', 'total_trades']]
    for _, row in bottom_5.iterrows():
        print(f"   {row['symbol']}: ${row['total_pnl']:.2f} ({row['win_rate']:.1f}% win, {int(row['total_trades'])} trades)")
    # Análisis de correlación entre métricas
    print(f"\n🔗 ANÁLISIS DE CORRELACIONES:")
    correlation_matrix = df[['total_pnl', 'win_rate', 'total_trades', 'max_drawdown', 'profit_factor']].corr()
    pnl_correlations = correlation_matrix['total_pnl'].drop('total_pnl')

    print("   Correlación de P&L con otras métricas:")
    for metric, corr in pnl_correlations.items():
        status = "🔴 Alta" if abs(corr) > 0.7 else "🟡 Media" if abs(corr) > 0.3 else "🟢 Baja"
        print(f"   {metric}: {status} ({corr:.3f})")
    # Verificar si hay modelos entrenados por símbolo
    print(f"\n🤖 VERIFICACIÓN DE MODELOS ML:")
    # Usar la ruta centralizada en descarga_datos/models
    models_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("**/*.pkl"))
        print(f"   Modelos encontrados: {len(model_files)}")
        for model_file in model_files[:10]:  # Mostrar primeros 10
            print(f"   - {model_file.name}")
        if len(model_files) > 10:
            print(f"   ... y {len(model_files) - 10} más")
    else:
        print("   ❌ No se encontró directorio de modelos")

    # Verificar archivos de optimización
    opt_dir = Path("data/optimization_results")
    if opt_dir.exists():
        opt_files = list(opt_dir.glob("*.json"))
        print(f"   Archivos de optimización: {len(opt_files)}")
    else:
        print("   ❌ No se encontró directorio de optimización")

if __name__ == "__main__":
    analyze_backtest_results()