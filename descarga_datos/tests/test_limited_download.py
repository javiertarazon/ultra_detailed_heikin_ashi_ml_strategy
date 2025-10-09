import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from config.config_loader import load_config_from_yaml
from core.downloader import AdvancedDataDownloader

async def test_limited_download():
    """Probar descarga limitada solo para acciones y forex"""
    print("🔄 PRUEBA DE DESCARGA LIMITADA - ACCIONES Y FOREX")
    print("=" * 60)

    # Cargar configuración
    config = load_config_from_yaml()

    downloader = AdvancedDataDownloader(config)

    # Solo símbolos problemáticos
    symbols = ['TSLA/US', 'NVDA/US', 'AAPL/US', 'EUR/USD', 'USD/JPY', 'GBP/USD']
    timeframe = '4h'
    start_date = '2023-01-01'
    end_date = '2025-10-06'

    print(f"🎯 Símbolos a descargar: {symbols}")
    print(f"📅 Período: {start_date} → {end_date}")
    print()

    try:
        results = await downloader.download_multiple_symbols(symbols, timeframe, start_date, end_date)
        print("✅ Descarga completada exitosamente")
        print()

        for symbol, data in results.items():
            if data is not None and not data.empty:
                count = len(data)
                date_range = f"{data['timestamp'].min()} → {data['timestamp'].max()}" if 'timestamp' in data.columns else "N/A"
                print(f"✅ {symbol}: {count:,} registros | {date_range}")
            else:
                print(f"❌ {symbol}: Sin datos")

    except Exception as e:
        print(f"❌ Error durante la descarga: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_limited_download())