#!/usr/bin/env python3
"""
Script para configurar la cuenta de sandbox de Binance y añadir fondos de prueba
=============================================================================

Este script configura automáticamente la cuenta de sandbox de Binance para trading.
Verifica la conexión, balance y añade fondos si es necesario.

Requisitos:
1. API Keys de Binance Testnet configuradas como variables de entorno
2. Módulo CCXT instalado

Uso:
python setup_binance_sandbox.py
"""

import os
import sys
import time
import ccxt
import json
from pathlib import Path

def print_header(text):
    """Imprimir encabezado con formato"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_success(text):
    """Imprimir mensaje de éxito"""
    print(f"✅ {text}")

def print_error(text):
    """Imprimir mensaje de error"""
    print(f"❌ {text}")

def print_info(text):
    """Imprimir mensaje informativo"""
    print(f"ℹ️ {text}")

def print_warning(text):
    """Imprimir mensaje de advertencia"""
    print(f"⚠️ {text}")

def load_credentials():
    """Cargar credenciales desde variables de entorno"""
    api_key = os.getenv('BINANCE_TEST_API_KEY')
    api_secret = os.getenv('BINANCE_TEST_API_SECRET')
    
    if not api_key or not api_secret:
        print_error("No se encontraron las credenciales de API de Binance Testnet")
        print_info("Asegúrate de configurar las variables de entorno:")
        print("  BINANCE_TEST_API_KEY=tu_api_key")
        print("  BINANCE_TEST_API_SECRET=tu_api_secret")
        print("\nPuedes obtener credenciales en: https://testnet.binance.vision/")
        return None, None
        
    return api_key, api_secret

def connect_to_exchange(api_key, api_secret):
    """Conectar al exchange y verificar conexión"""
    try:
        # Crear instancia de CCXT para Binance Testnet
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            },
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision/api/v3',
                    'private': 'https://testnet.binance.vision/api/v3',
                },
                'www': 'https://testnet.binance.vision',
                'doc': 'https://binance-docs.github.io/apidocs/spot/en',
            },
        })
        
        # Habilitar modo sandbox
        exchange.set_sandbox_mode(True)
        
        # Verificar conexión
        markets = exchange.load_markets()
        print_success(f"Conectado a Binance Testnet - {len(markets)} mercados disponibles")
        
        return exchange
    except Exception as e:
        print_error(f"Error conectando a Binance Testnet: {str(e)}")
        return None

def check_balance(exchange):
    """Verificar balance en la cuenta"""
    try:
        balance = exchange.fetch_balance()
        print_info("Balance actual en la cuenta:")
        
        # Mostrar balances relevantes
        for currency in ['USDT', 'BTC', 'ETH', 'BNB']:
            if currency in balance['total']:
                print(f"  {currency}: {balance['total'][currency]:.6f}")
                
        return balance
    except Exception as e:
        print_error(f"Error obteniendo balance: {str(e)}")
        return None

def main():
    """Función principal"""
    print_header("Configuración de Binance Sandbox para Trading")
    
    # Cargar credenciales
    api_key, api_secret = load_credentials()
    if not api_key or not api_secret:
        sys.exit(1)
        
    # Conectar al exchange
    exchange = connect_to_exchange(api_key, api_secret)
    if not exchange:
        sys.exit(1)
        
    # Verificar balance actual
    balance = check_balance(exchange)
    if not balance:
        sys.exit(1)
    
    # Verificar si hay suficiente USDT
    has_enough_usdt = balance.get('total', {}).get('USDT', 0) >= 1000
    
    if has_enough_usdt:
        print_success("Tu cuenta tiene suficiente balance USDT para operar")
    else:
        print_warning("No tienes suficiente balance USDT para operar")
        print_info("Para añadir fondos a tu cuenta de Binance Testnet:")
        print("1. Ve a https://testnet.binance.vision/")
        print("2. Inicia sesión con tu cuenta")
        print("3. Busca la opción 'Get Funds' o similar")
        print("4. Solicita fondos de prueba (BTC, USDT, ETH)")
        print("5. Ejecuta este script nuevamente para verificar")
        
    print("\n" + "=" * 60)
    print(" Información adicional para trading en sandbox")
    print("=" * 60)
    print("• Los fondos en Binance Testnet se resetean periódicamente")
    print("• Las operaciones funcionan igual que en producción")
    print("• Puedes ejecutar el test completo con:")
    print("  python run_binance_sandbox_test.py")
    print("=" * 60)

if __name__ == '__main__':
    main()