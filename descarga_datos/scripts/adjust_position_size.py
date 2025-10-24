#!/usr/bin/env python3
"""
Script para ajustar el tamaño de posición en config.yaml para evitar errores de balance insuficiente
"""

import os
import sys
import yaml
from pathlib import Path
import dotenv
import ccxt

# Cargar variables de entorno
dotenv_path = Path(__file__).parent / '.env'
dotenv.load_dotenv(dotenv_path)

CONFIG_FILE = Path(__file__).parent / 'config' / 'config.yaml'

def print_header(text):
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️ {text}")

def print_warning(text):
    print(f"⚠️ {text}")

def load_config():
    """Cargar configuración desde archivo YAML"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print_error(f"Error cargando configuración: {str(e)}")
        return None

def save_config(config):
    """Guardar configuración en archivo YAML"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print_error(f"Error guardando configuración: {str(e)}")
        return False

def get_binance_balance():
    """Obtener balance de Binance Testnet"""
    try:
        # Intentar primero con las variables TEST
        api_key = os.getenv('BINANCE_TEST_API_KEY')
        api_secret = os.getenv('BINANCE_TEST_API_SECRET')
        
        # Si no existen, intentar con las variables normales
        if not api_key:
            api_key = os.getenv('BINANCE_API_KEY')
            print_info("BINANCE_TEST_API_KEY no encontrada, usando BINANCE_API_KEY")
            
        if not api_secret:
            api_secret = os.getenv('BINANCE_API_SECRET')
            print_info("BINANCE_TEST_API_SECRET no encontrada, usando BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            print_error("No se encontraron credenciales de API")
            return None

        # Crear instancia de Binance
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # Activar modo sandbox
        exchange.set_sandbox_mode(True)
        
        # Obtener balance
        balance = exchange.fetch_balance()
        
        # Mostrar detalles de balance disponible
        print_header("BALANCE DISPONIBLE EN BINANCE TESTNET")
        
        for currency, data in balance['free'].items():
            if float(data) > 0:
                print(f"{currency}: {data}")
                
        return balance
    
    except Exception as e:
        print_error(f"Error obteniendo balance: {str(e)}")
        return None

def adjust_position_size(config, balance):
    """Ajustar tamaño de posición en base al balance disponible"""
    if not config or not balance:
        return False
    
    try:
        # Verificar si hay USDT disponible
        usdt_balance = balance.get('free', {}).get('USDT', 0)
        print_info(f"Balance USDT disponible: {usdt_balance:.2f}")
        
        if usdt_balance <= 0:
            print_error("No hay USDT disponible para operar")
            print_info("Verificando si hay BTC u otras monedas disponibles...")
            
            other_currencies = []
            for currency, amount in balance.get('free', {}).items():
                if currency != 'USDT' and float(amount) > 0:
                    other_currencies.append(f"{currency}: {amount}")
            
            if other_currencies:
                print_info(f"Se encontraron otras monedas disponibles: {', '.join(other_currencies)}")
                print_warning("Considera vender estas monedas por USDT en la interfaz de Binance Testnet")
            else:
                print_error("No se encontraron otras monedas disponibles")
                print_warning("Necesitas recargar tu cuenta de Binance Testnet: https://testnet.binance.vision/")
            
            # Continuar ajustando la configuración aunque no haya USDT
        
        # Verificar la configuración actual de risk_management
        if 'risk_management' not in config:
            config['risk_management'] = {}
            
        # Valores actuales
        current_max_position = config['risk_management'].get('max_position_size_pct', 0.1)
        current_risk = config['risk_management'].get('risk_per_trade', 0.02)
        
        print_info(f"Configuración actual:")
        print(f"- Tamaño máximo de posición: {current_max_position * 100:.1f}%")
        print(f"- Riesgo por operación: {current_risk * 100:.1f}%")
        
        # Ajustar valores a configuraciones muy conservadoras para evitar errores de saldo insuficiente
        if current_max_position > 0.01:  # Reducir a 1% como máximo
            config['risk_management']['max_position_size_pct'] = 0.01
            print_warning(f"Ajustando tamaño máximo de posición a 1% (era {current_max_position * 100:.1f}%)")
        
        # Reducir riesgo por operación a un valor muy bajo
        if current_risk > 0.002:  # Reducir a 0.2%
            config['risk_management']['risk_per_trade'] = 0.002
            print_warning(f"Ajustando riesgo por operación a 0.2% (era {current_risk * 100:.1f}%)")
        
        # Asegurarse de que live_trading tenga la misma configuración
        if 'live_trading' in config:
            config['live_trading']['risk_per_trade'] = config['risk_management']['risk_per_trade']
            print_info("Sincronizando configuración de riesgo con live_trading")
            
        # Si hay una configuración específica para ccxt_order_executor
        if 'ccxt_order_executor' in config:
            leverage = config['ccxt_order_executor'].get('leverage', 1)
            if leverage > 1:
                print_warning(f"Reduciendo apalancamiento de {leverage}x a 1x para modo sandbox")
                config['ccxt_order_executor']['leverage'] = 1
                
        # Guardar cambios
        if save_config(config):
            print_success("Configuración ajustada y guardada correctamente")
            return True
        else:
            print_error("Error al guardar la configuración")
            return False
            
    except Exception as e:
        print_error(f"Error ajustando tamaño de posición: {str(e)}")
        return False

def reload_testnet_funds():
    """Mostrar instrucciones para recargar fondos en Binance Testnet"""
    print_header("RECARGA DE FONDOS EN BINANCE TESTNET")
    print_info("Sigue estos pasos para recargar fondos:")
    print("1. Ve a https://testnet.binance.vision/")
    print("2. Inicia sesión con tu cuenta")
    print("3. Haz clic en 'Get Assets' para recargar fondos de prueba")
    print("4. Asegúrate de recargar USDT y BTC")
    print("5. Espera unos minutos a que los fondos se acrediten")
    
    response = input("¿Has recargado los fondos? (s/n): ")
    if response.lower() == 's':
        print_info("Verificando balance actualizado...")
        return get_binance_balance()
    return None

def check_order_size(exchange, symbol='BTC/USDT', amount=0.001):
    """Verificar si el tamaño de orden es válido"""
    try:
        # Obtener información del mercado
        market = exchange.market(symbol)
        
        # Obtener límites de cantidad
        min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
        precision = market.get('precision', {}).get('amount', 8)
        
        print_info(f"Límites para {symbol}:")
        print(f"- Cantidad mínima: {min_amount}")
        print(f"- Precisión: {precision} decimales")
        
        if amount < min_amount:
            print_warning(f"La cantidad {amount} es menor que el mínimo {min_amount}")
            suggested = max(min_amount, 0.001)  # Al menos 0.001 BTC
            print_info(f"Cantidad sugerida: {suggested}")
            return False, suggested
        return True, amount
    
    except Exception as e:
        print_error(f"Error verificando tamaño de orden: {str(e)}")
        return False, 0.001

def main():
    print_header("AJUSTE DE TAMAÑO DE POSICIÓN PARA BINANCE TESTNET")
    
    # Cargar configuración
    print_info("Cargando configuración...")
    config = load_config()
    if not config:
        sys.exit(1)
        
    # Obtener balance
    print_info("Obteniendo balance de Binance Testnet...")
    balance = get_binance_balance()
    if not balance:
        sys.exit(1)
    
    # Verificar si hay suficiente saldo
    usdt_balance = balance.get('free', {}).get('USDT', 0)
    if float(usdt_balance) < 10:  # Menos de 10 USDT
        print_warning("¡Saldo USDT muy bajo para operar! Considera recargar fondos.")
        reload = input("¿Deseas ver instrucciones para recargar fondos? (s/n): ")
        if reload.lower() == 's':
            new_balance = reload_testnet_funds()
            if new_balance:
                balance = new_balance
        
    # Ajustar tamaño de posición
    if adjust_position_size(config, balance):
        print_success("Tamaño de posición ajustado correctamente")
        
        # Verificar conexión y tamaños de orden
        try:
            # Obtener credenciales
            api_key = os.getenv('BINANCE_TEST_API_KEY') or os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_TEST_API_SECRET') or os.getenv('BINANCE_API_SECRET')
            
            # Crear instancia de Binance
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            # Activar modo sandbox
            exchange.set_sandbox_mode(True)
            
            # Verificar tamaño mínimo de orden
            print_info("Verificando tamaños mínimos de orden...")
            is_valid, suggested_amount = check_order_size(exchange)
            
            if is_valid:
                print_success("Los tamaños de orden son válidos")
            else:
                print_warning("Considera ajustar manualmente el tamaño mínimo de orden")
        except Exception as e:
            print_error(f"Error verificando tamaños de orden: {str(e)}")
        
        print_info("Ahora puedes ejecutar:")
        print("python descarga_datos/main.py --live-ccxt")
    else:
        print_error("No se pudo ajustar el tamaño de posición")
        
if __name__ == "__main__":
    main()