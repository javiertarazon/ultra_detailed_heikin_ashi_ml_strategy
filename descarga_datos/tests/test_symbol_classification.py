#!/usr/bin/env python3
"""
Test para verificar la clasificación de símbolos
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.downloader import AdvancedDataDownloader
from config.config_loader import load_config_from_yaml

def test_symbol_classification():
    """Test para verificar cómo se clasifican los símbolos"""

    # Cargar configuración
    config = load_config_from_yaml()

    # Crear downloader
    downloader = AdvancedDataDownloader(config)

    # Símbolos a testear
    symbols = [
        'SOL/USDT', 'ETH/USDT',  # CCXT crypto
        'BTC/USD', 'ADA/USD', 'DOT/USD', 'MATIC/USD', 'XRP/USD', 'LTC/USD', 'DOGE/USD',  # MT5 crypto
        'TSLA/US', 'NVDA/US', 'AAPL/US', 'MSFT/US', 'GOOGL/US', 'AMZN/US',  # MT5 stocks
        'EUR/USD', 'USD/JPY', 'GBP/USD'  # MT5 forex
    ]

    print("🔍 Clasificación de símbolos:")
    print("=" * 50)

    for symbol in symbols:
        is_crypto = downloader._is_crypto_symbol(symbol)
        source = "CCXT" if is_crypto else "MT5"
        print(f"{symbol:<12} → {source}")

if __name__ == "__main__":
    test_symbol_classification()