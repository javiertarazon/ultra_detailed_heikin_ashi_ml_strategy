#!/usr/bin/env python3
"""
Script para obtener balances en Binance Testnet y proveer opciones para recargar fondos

Este script ayuda a:
1. Obtener balances actuales en Binance Testnet
2. Proporcionar instrucciones para recargar fondos
3. Crear órdenes de prueba con cantidades muy pequeñas para verificar conectividad

Author: GitHub Copilot
Date: Octubre 2025
"""

import os
import sys
import json
import time
import ccxt
from pathlib import Path
import dotenv

# Cargar variables de entorno
dotenv_path = Path(__file__).parent / '.env'
dotenv.load_dotenv(dotenv_path)

# Funciones de utilidad para imprimir mensajes
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

def get_exchange_connection(exchange_id='binance', sandbox=True):
    """Conectar al exchange"""
    try:
        # Intentar primero con las variables TEST
        api_key = os.getenv(f'{exchange_id.upper()}_TEST_API_KEY')
        api_secret = os.getenv(f'{exchange_id.upper()}_TEST_API_SECRET')
        
        # Si no existen, intentar con las variables normales
        if not api_key:
            api_key = os.getenv(f'{exchange_id.upper()}_API_KEY')
            print_info(f"{exchange_id.upper()}_TEST_API_KEY no encontrada, usando {exchange_id.upper()}_API_KEY")
            
        if not api_secret:
            api_secret = os.getenv(f'{exchange_id.upper()}_API_SECRET')
            print_info(f"{exchange_id.upper()}_TEST_API_SECRET no encontrada, usando {exchange_id.upper()}_API_SECRET")
        
        if not api_key or not api_secret:
            print_error(f"No se encontraron credenciales de API para {exchange_id}")
            return None

        # Crear instancia del exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # Activar modo sandbox si es necesario
        if sandbox:
            exchange.set_sandbox_mode(True)
        
        # Verificar conectividad
        exchange.load_markets()
        print_success(f"Conectado a {exchange_id}" + (" (SANDBOX)" if sandbox else ""))
        return exchange
        
    except Exception as e:
        print_error(f"Error conectando a {exchange_id}: {str(e)}")
        return None

def get_balances(exchange):
    """Obtener y mostrar balances"""
    try:
        balance = exchange.fetch_balance()
        
        print_header("BALANCES DISPONIBLES")
        
        # Mostrar balances totales
        print("Balance total:")
        has_funds = False
        for currency, amount in balance['total'].items():
            if float(amount) > 0:
                has_funds = True
                print(f"  {currency}: {amount}")
        
        if not has_funds:
            print_warning("No hay fondos disponibles en la cuenta")
        
        # Mostrar balances disponibles (free)
        print("\nBalance disponible:")
        has_free_funds = False
        for currency, amount in balance['free'].items():
            if float(amount) > 0:
                has_free_funds = True
                print(f"  {currency}: {amount}")
        
        if not has_free_funds:
            print_warning("No hay fondos disponibles para operar")
        
        # Mostrar fondos en órdenes
        if balance.get('used'):
            in_orders = False
            for currency, amount in balance['used'].items():
                if float(amount) > 0:
                    if not in_orders:
                        print("\nFondos en órdenes:")
                        in_orders = True
                    print(f"  {currency}: {amount}")
        
        return balance
    except Exception as e:
        print_error(f"Error obteniendo balances: {str(e)}")
        return None

def show_reload_instructions():
    """Mostrar instrucciones para recargar fondos en Binance Testnet"""
    print_header("INSTRUCCIONES PARA RECARGAR FONDOS EN BINANCE TESTNET")
    print("1. Ve a https://testnet.binance.vision/")
    print("2. Inicia sesión con tu cuenta (o crea una si no tienes)")
    print("3. Haz clic en 'Get Assets' para recargar fondos de prueba")
    print("4. Asegúrate de solicitar tanto BTC como USDT")
    print("5. Espera unos minutos a que los fondos se acrediten")
    
    input("Presiona Enter cuando hayas completado estos pasos...")

def create_test_order(exchange, symbol="BTC/USDT"):
    """Crear una orden de prueba muy pequeña"""
    try:
        # Obtener ticker
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        print_info(f"Precio actual de {symbol}: {price}")
        
        # Obtener información de mercado
        market = exchange.market(symbol)
        min_amount = market['limits']['amount']['min']
        min_cost = market.get('limits', {}).get('cost', {}).get('min', 0)
        
        print_info(f"Cantidad mínima: {min_amount} {symbol.split('/')[0]}")
        print_info(f"Costo mínimo: {min_cost} {symbol.split('/')[1]}")
        
        # Calcular cantidad que cumpla los mínimos pero sea muy pequeña
        amount = max(min_amount, 0.001)  # Al menos 0.001 BTC o el mínimo
        
        # Verificar que el costo cumpla el mínimo
        cost = amount * price
        if min_cost > 0 and cost < min_cost:
            amount = min_cost / price
            print_warning(f"Ajustando cantidad a {amount} para cumplir con el costo mínimo")
        
        # Preguntar confirmación
        print_info(f"Se creará una orden de compra de {amount} {symbol.split('/')[0]} a precio de mercado")
        print_info(f"Costo aproximado: {amount * price} {symbol.split('/')[1]}")
        
        confirm = input("¿Confirmar la creación de esta orden de prueba? (s/n): ")
        if confirm.lower() != 's':
            print_info("Operación cancelada por el usuario")
            return False
        
        # Crear orden
        order = exchange.create_market_buy_order(symbol, amount)
        
        print_success("Orden creada correctamente")
        print(json.dumps(order, indent=2))
        
        # Mostrar saldo actualizado
        print_info("Esperando 3 segundos para obtener balance actualizado...")
        time.sleep(3)
        get_balances(exchange)
        
        return True
    
    except Exception as e:
        print_error(f"Error creando orden de prueba: {str(e)}")
        return False

def main():
    print_header("VERIFICACIÓN DE BALANCE EN BINANCE TESTNET")
    
    # Conectar al exchange
    exchange = get_exchange_connection('binance', True)
    if not exchange:
        print_error("No se pudo conectar al exchange")
        return
    
    # Obtener balances
    balance = get_balances(exchange)
    if not balance:
        print_error("No se pudieron obtener los balances")
        return
    
    # Verificar si hay suficiente USDT
    usdt_balance = balance['free'].get('USDT', 0)
    if float(usdt_balance) < 10:  # Menos de 10 USDT
        print_warning("¡Saldo USDT muy bajo para operar!")
        
        # Preguntar si desea recargar fondos
        reload = input("¿Deseas ver instrucciones para recargar fondos? (s/n): ")
        if reload.lower() == 's':
            show_reload_instructions()
            
            # Verificar nuevamente los balances después de recargar
            print_info("Verificando balances actualizados...")
            time.sleep(3)  # Esperar un poco
            balance = get_balances(exchange)
    
    # Preguntar si desea crear una orden de prueba
    test_order = input("¿Deseas crear una orden de prueba pequeña para verificar la conectividad? (s/n): ")
    if test_order.lower() == 's':
        create_test_order(exchange)
    
    # Mostrar próximos pasos
    print_header("PRÓXIMOS PASOS")
    print("1. Ejecuta 'python descarga_datos/adjust_position_size.py' para ajustar el tamaño de posición")
    print("2. Ejecuta 'python descarga_datos/main.py --live-ccxt' para iniciar el trading en vivo")
    
if __name__ == "__main__":
    main()