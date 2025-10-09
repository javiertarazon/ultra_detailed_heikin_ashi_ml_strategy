#!/usr/bin/env python3
"""
Script de prueba para verificar descargas CCXT
"""
import asyncio
import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from config.config_loader import load_config_from_yaml
from core.downloader import AdvancedDataDownloader

async def test_ccxt_only():
    print('🧪 PRUEBA DE DESCARGA CCXT SOLAMENTE')
    print('=' * 50)

    try:
        config = load_config_from_yaml()
        downloader = AdvancedDataDownloader(config)

        # Solo símbolos CCXT (criptomonedas)
        ccxt_symbols = ['SOL/USDT', 'ETH/USDT']

        print(f'📊 Probando descarga de: {ccxt_symbols}')

        timeframe = '1h'
        start_date = '2024-01-01'
        end_date = '2024-01-15'  # Período corto para prueba

        for symbol in ccxt_symbols:
            try:
                print(f'\n🔄 Descargando {symbol}...')
                data = await downloader.download_symbol(symbol, timeframe, start_date, end_date)

                if data is not None and not data.empty:
                    print(f'✅ {symbol}: {len(data)} filas descargadas')
                    print(f'   Rango: {data.index[0]} → {data.index[-1]}')
                else:
                    print(f'❌ {symbol}: Sin datos')

            except Exception as e:
                print(f'❌ {symbol}: Error - {str(e)}')

    except Exception as e:
        print(f'❌ Error general: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_ccxt_only())