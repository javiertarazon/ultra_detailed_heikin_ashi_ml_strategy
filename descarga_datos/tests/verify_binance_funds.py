#!/usr/bin/env python3
"""
Script para verificar fondos en la cuenta de Binance Testnet
===========================================================

Este script verifica la conexión y fondos en Binance Testnet usando los API keys
configurados en el archivo .env
"""

import os
import sys
import ccxt
from pathlib import Path
import dotenv
import time
from datetime import datetime

# Cargar variables de entorno desde .env
dotenv_path = Path(__file__).parent / '.env'
dotenv.load_dotenv(dotenv_path)

def print_header(text):
    """Imprimir encabezado con formato"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

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
    """Imprimir advertencia"""
    print(f"⚠️ {text}")

def verify_api_keys():
    """Verificar que las API keys estén configuradas"""
    # Primero intentamos con las variables específicas de testnet
    api_key = os.getenv('BINANCE_TEST_API_KEY')
    api_secret = os.getenv('BINANCE_TEST_API_SECRET')
    
    # Si no existen, intentamos con las variables generales de Binance
    if not api_key:
        api_key = os.getenv('BINANCE_API_KEY')
        print_info("BINANCE_TEST_API_KEY no encontrada, usando BINANCE_API_KEY")
        
    if not api_secret:
        api_secret = os.getenv('BINANCE_API_SECRET')
        print_info("BINANCE_TEST_API_SECRET no encontrada, usando BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        print_error("No se encontraron credenciales de API en el archivo .env")
        print_info("Verifica que el archivo .env tenga las variables:")
        print("  BINANCE_API_KEY / BINANCE_TEST_API_KEY")
        print("  BINANCE_API_SECRET / BINANCE_TEST_API_SECRET")
        return None, None
    
    # Verificar si las keys parecen válidas (formato básico)
    if len(api_key) < 10 or len(api_secret) < 10:
        print_warning("Las API keys parecen ser demasiado cortas")
    
    print_success(f"API Key encontrada: {api_key[:5]}...{api_key[-5:]}")
    print_success(f"API Secret encontrada: {api_secret[:5]}...{api_secret[-5:]}")
    
    return api_key, api_secret

def connect_to_binance(api_key, api_secret):
    """Conectar a Binance Testnet"""
    try:
        # Verificar si sandbox está habilitado
        sandbox_mode = os.getenv('SANDBOX_MODE', 'true').lower() == 'true'
        
        if not sandbox_mode:
            print_warning("⚠️ SANDBOX_MODE no está habilitado en .env")
            print_warning("⚠️ Esto podría conectar a la API de producción")
            response = input("¿Deseas continuar de todos modos? (s/n): ")
            if response.lower() != 's':
                print_info("Operación cancelada")
                return None
        
        # Crear instancia de CCXT para Binance
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        
        # Configurar sandbox mode para testnet
        if sandbox_mode:
            exchange.set_sandbox_mode(True)
            print_info("Modo sandbox activado (usando Binance Testnet)")
        
        # Verificar conexión
        start_time = time.time()
        exchange.load_markets()
        end_time = time.time()
        
        print_success(f"Conexión establecida con Binance (latencia: {(end_time - start_time):.2f}s)")
        return exchange
    
    except Exception as e:
        print_error(f"Error al conectar con Binance: {str(e)}")
        return None

def check_funds(exchange):
    """Verificar fondos en la cuenta"""
    try:
        start_time = time.time()
        balance = exchange.fetch_balance()
        end_time = time.time()
        
        print_success(f"Balance obtenido correctamente (latencia: {(end_time - start_time):.2f}s)")
        
        # Mostrar timestamp de la información
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print_info(f"Fecha/Hora: {timestamp}")
        
        # Mostrar fondos disponibles
        print_header("FONDOS DISPONIBLES")
        
        # Primero mostrar USDT, BTC, ETH si existen
        priority_assets = ['USDT', 'BTC', 'ETH', 'BNB']
        for asset in priority_assets:
            if asset in balance['total'] and balance['total'][asset] > 0:
                print(f"{asset.ljust(8)} | Total: {balance['total'][asset]:12.8f} | Disponible: {balance['free'][asset]:12.8f} | En uso: {balance['used'][asset]:12.8f}")
        
        # Luego mostrar el resto de activos con balance
        print("\nOtros activos:")
        other_assets = [asset for asset in balance['total'] if asset not in priority_assets and balance['total'][asset] > 0]
        
        if other_assets:
            for asset in other_assets:
                print(f"{asset.ljust(8)} | Total: {balance['total'][asset]:12.8f} | Disponible: {balance['free'][asset]:12.8f} | En uso: {balance['used'][asset]:12.8f}")
        else:
            print("No hay otros activos con balance")
        
        # Verificar si hay suficientes USDT (al menos 1000)
        if 'USDT' in balance['free'] and balance['free']['USDT'] >= 1000:
            print_success("\n✅ Tienes suficientes USDT para operar (>= 1000)")
        elif 'USDT' in balance['free']:
            print_warning(f"\n⚠️ Saldo de USDT insuficiente: {balance['free']['USDT']:.2f} USDT")
            print_info("Se recomienda tener al menos 1000 USDT para operar")
        else:
            print_error("\n❌ No tienes USDT en tu cuenta")
        
        return balance
        
    except Exception as e:
        print_error(f"Error al verificar fondos: {str(e)}")
        return None

def verify_account_info(exchange):
    """Verificar información de la cuenta"""
    try:
        account_info = exchange.fetch_balance({'recvWindow': 10000})
        
        # Extraer información adicional si está disponible
        account_type = "Testnet (Sandbox)" if exchange.sandbox else "Producción"
        
        print_header("INFORMACIÓN DE LA CUENTA")
        print(f"Tipo de cuenta: {account_type}")
        
        # Mostrar información adicional si está disponible
        if hasattr(account_info, 'info'):
            info = account_info.info
            if 'updateTime' in info:
                update_time = datetime.fromtimestamp(info['updateTime'] / 1000).strftime("%Y-%m-%d %H:%M:%S")
                print(f"Última actualización: {update_time}")
                
            if 'permissions' in info:
                print(f"Permisos: {info['permissions']}")
        
        return True
    except Exception as e:
        print_error(f"Error al verificar información de cuenta: {str(e)}")
        return False

def main():
    """Función principal"""
    print_header("VERIFICACIÓN DE FONDOS EN BINANCE TESTNET")
    
    # Verificar API keys
    api_key, api_secret = verify_api_keys()
    if not api_key or not api_secret:
        sys.exit(1)
    
    # Conectar a Binance
    exchange = connect_to_binance(api_key, api_secret)
    if not exchange:
        sys.exit(1)
    
    # Verificar fondos
    balance = check_funds(exchange)
    if not balance:
        sys.exit(1)
    
    # Verificar información de cuenta
    verify_account_info(exchange)
    
    print_header("INSTRUCCIONES PARA SOLUCIONAR PROBLEMAS")
    print("1. Si no tienes suficiente balance en USDT:")
    print("   - Accede a https://testnet.binance.vision/")
    print("   - Inicia sesión con tu cuenta")
    print("   - Busca la opción 'Get Test Funds' o 'Faucet'")
    print("   - Solicita fondos de USDT (mínimo recomendado: 10,000 USDT)")
    print("")
    print("2. Si hay problemas de autenticación:")
    print("   - Verifica que las API keys sean correctas")
    print("   - Regenera las API keys en https://testnet.binance.vision/")
    print("   - Actualiza las keys en el archivo .env")
    print("")
    print("3. Para ejecutar el trading en vivo:")
    print("   python main.py --live-ccxt")

if __name__ == "__main__":
    main()