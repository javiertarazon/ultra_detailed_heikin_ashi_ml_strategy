#!/usr/bin/env python
"""Test para verificar que el fallback a SPOT endpoint funciona en Binance testnet."""

import sys
sys.path.insert(0, 'descarga_datos')

import logging
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv('descarga_datos/.env')

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("=== Test de Balance via SPOT Endpoint ===")

try:
    # Usar CCXT directamente
    import ccxt
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    logger.info(f"API Key disponible: {'Sí' if api_key else 'No'}")
    logger.info(f"API Secret disponible: {'Sí' if api_secret else 'No'}")
    
    # Crear exchange en modo MARGIN (que causará el error SAPI)
    logger.info("\n1. Intentando obtener balance con defaultType='margin'...")
    exchange_margin = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'sandbox': True,
        'timeout': 30000,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'margin',
            'leverage': 10,
        },
    })
    
    try:
        balance_margin = exchange_margin.fetch_balance()
        logger.info("✓ Balance obtenido con margin")
        logger.info(f"  Free USDT: ${balance_margin.get('free', {}).get('USDT', 0):.2f}")
    except Exception as margin_error:
        logger.warning(f"✗ Error con margin: {margin_error}")
        
        if 'sapi' in str(margin_error).lower():
            logger.info("\n2. Error SAPI detectado, intentando fallback a SPOT...")
            
            # Cambiar a spot
            exchange_margin.options['defaultType'] = 'spot'
            
            try:
                balance_spot = exchange_margin.fetch_balance()
                logger.info("✓ Balance obtenido con SPOT endpoint!")
                logger.info(f"  Free USDT: ${balance_spot.get('free', {}).get('USDT', 0):.2f}")
                
                # Restaurar a margin
                exchange_margin.options['defaultType'] = 'margin'
                logger.info("\n✓ Test exitoso - Fallback a SPOT funciona!")
                
            except Exception as spot_error:
                logger.error(f"✗ Error también con SPOT: {spot_error}")
                raise
    
except Exception as e:
    logger.error(f"✗ Error durante el test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
