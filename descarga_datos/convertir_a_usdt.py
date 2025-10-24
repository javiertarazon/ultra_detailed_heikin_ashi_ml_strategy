#!/usr/bin/env python3
"""
Script para convertir automáticamente todas las criptomonedas a USDT
en Binance Testnet usando órdenes de mercado
"""

import ccxt
from pathlib import Path
from dotenv import load_dotenv
import os
import sys
import time

# Cargar .env
env_path = Path('descarga_datos/.env')
if env_path.exists():
    load_dotenv(env_path)

# Cargar credenciales
api_key = os.getenv('BINANCE_API_KEY', '')
api_secret = os.getenv('BINANCE_API_SECRET', '')

if not api_key or not api_secret:
    print("[ERROR] API Key o Secret no encontrados")
    sys.exit(1)

# Conectar a Binance Testnet
try:
    binance = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'sandbox': True,
        'enableRateLimit': True,
    })
    print("[OK] Conectado a Binance Testnet\n")
except Exception as e:
    print(f"[ERROR] No se pudo conectar: {e}")
    sys.exit(1)

# Monedas que NO se van a convertir (ya son stablecoins)
STABLECOINS = {'USDT', 'BUSD', 'USDC', 'DAI', 'TUSD', 'FDUSD', 'USDP', 'XUSD', 'USD1', 'BFUSD', 'USDE'}

# Monedas a IGNORAR (no tienen pares de trading o muy ilíquidas)
IGNORE_COINS = {
    'BRL', 'ZAR', 'UAH', 'PLN', 'RON', 'ARS', 'JPY', 'MXN', 'COP', 'CZK',  # Monedas fiat
    'EUR', 'EURI',  # Euros
}

print("=" * 80)
print("CONVERSION DE CRIPTOMONEDAS A USDT")
print("=" * 80)

# Obtener balance
balance = binance.fetch_balance()

# Obtener lista de pares disponibles
try:
    symbols = binance.symbols
    print(f"[OK] {len(symbols)} pares disponibles en el exchange")
except Exception as e:
    print(f"[ERROR] No se pudo obtener símbolos: {e}")
    sys.exit(1)

# Construir diccionario de símbolos para búsqueda rápida
symbol_dict = {s.replace('/', ''): s for s in symbols}

# Procesar conversiones
conversiones_exitosas = 0
conversiones_fallidas = 0
skipped = 0

print("\n" + "-" * 80)
print("INICIANDO CONVERSIONES A USDT")
print("-" * 80 + "\n")

for curr, info in sorted(balance.items()):
    if curr in ['free', 'used', 'total']:
        continue
    
    if not isinstance(info, dict):
        continue
    
    total = info.get('total', 0)
    if total <= 0:
        continue
    
    # Saltar stablecoins y monedas ignoradas
    if curr in STABLECOINS or curr in IGNORE_COINS:
        print(f"SKIP   {curr:<10} (moneda excluida)")
        skipped += 1
        continue
    
    # Buscar par de trading hacia USDT
    pair = f"{curr}/USDT"
    if pair not in symbols:
        print(f"FAIL   {curr:<10} (no hay par {pair})")
        conversiones_fallidas += 1
        continue
    
    try:
        # Obtener precio actual y mínimo de cantidad
        ticker = binance.fetch_ticker(pair)
        price = ticker['last']
        
        # Obtener el mínimo de cantidad del mercado
        try:
            market = binance.market(pair)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.00001)
            min_cost = market.get('limits', {}).get('cost', {}).get('min', 1)
            
            # Validar cantidad
            order_value = total * price
            if order_value < min_cost:
                print(f"SKIP   {curr:<10} (valor muy bajo: ${order_value:.2f} < ${min_cost})")
                skipped += 1
                continue
        except:
            min_amount = 0.00001
        
        # Crear orden de venta (solo si la cantidad es válida)
        if total >= min_amount:
            print(f"SELL   {curr:<10} cantidad={total:<15.8f} precio=${price:<12.4f}", end=" ")
            
            order = binance.create_market_sell_order(pair, total)
            
            print(f"-> EXITOSO (orden {order['id']})")
            conversiones_exitosas += 1
        else:
            print(f"SKIP   {curr:<10} (cantidad mínima no alcanzada)")
            skipped += 1
        
        # Esperar un poco para evitar rate limit
        time.sleep(0.5)
        
    except ccxt.InsufficientFunds as e:
        print(f"FAIL   (saldo insuficiente)")
        conversiones_fallidas += 1
    except ccxt.InvalidOrder as e:
        print(f"FAIL   (orden inválida: {str(e)[:30]})")
        conversiones_fallidas += 1
    except ccxt.RateLimitExceeded:
        print(f"FAIL   (límite de rate - esperando...)")
        time.sleep(5)
        conversiones_fallidas += 1
    except Exception as e:
        error_msg = str(e)
        if "NOTIONAL" in error_msg or "MIN_NOTIONAL" in error_msg:
            print(f"SKIP   (valor de orden muy bajo)")
            skipped += 1
        else:
            print(f"FAIL   ({error_msg[:40]})")
            conversiones_fallidas += 1

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"\nConversiones exitosas: {conversiones_exitosas}")
print(f"Conversiones fallidas: {conversiones_fallidas}")
print(f"Monedas saltadas: {skipped}")

# Verificar nuevo balance
print("\nVerificando nuevo balance...")
balance_final = binance.fetch_balance()

usdt_final = 0
other_remaining = 0

for curr, info in balance_final.items():
    if curr not in ['free', 'used', 'total'] and isinstance(info, dict):
        total = info.get('total', 0)
        if total > 0:
            if curr == 'USDT':
                usdt_final = total
            else:
                other_remaining += 1

print(f"\nBalance USDT final: {usdt_final:.8f}")
print(f"Otras monedas restantes: {other_remaining}")

if other_remaining == 0:
    print("\n✓ CONVERSIÓN COMPLETADA - TODA LA CUENTA EN USDT")
    print("  Ejecuta: .venv\\Scripts\\python.exe descarga_datos/main.py --live-ccxt")
else:
    print(f"\n⚠ {other_remaining} monedas aún no convertidas (ilíquidas o sin par)")
    print("  Puedes operarlas manualmente o ejecutar este script de nuevo")

print()
