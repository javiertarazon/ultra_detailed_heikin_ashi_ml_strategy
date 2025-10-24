#!/usr/bin/env python3
"""
Script para verificar balance en Binance Testnet
y preparar conversión a USDT para trading en derivados
"""

import ccxt
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Cargar .env
env_path = Path('descarga_datos/.env')
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] .env cargado desde: {env_path}")
else:
    print("[ERROR] .env no encontrado")
    sys.exit(1)

# Cargar credenciales
api_key = os.getenv('BINANCE_API_KEY', '')
api_secret = os.getenv('BINANCE_API_SECRET', '')

if not api_key or not api_secret:
    print("[ERROR] API Key o Secret no encontrados")
    sys.exit(1)

print("[OK] Credenciales cargadas")

# Conectar a Binance Testnet
try:
    binance = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'sandbox': True,
        'enableRateLimit': True,
    })
    print("[OK] Conectado a Binance Testnet")
except Exception as e:
    print(f"[ERROR] No se pudo conectar: {e}")
    sys.exit(1)

# Obtener balance
try:
    balance = binance.fetch_balance()
    print("[OK] Balance obtenido\n")
except Exception as e:
    print(f"[ERROR] No se pudo obtener balance: {e}")
    sys.exit(1)

# Procesar activos
assets = []
for curr, info in balance.items():
    # Saltar las claves especiales
    if curr in ['free', 'used', 'total']:
        continue
    
    # Procesar como dict si es dict, sino skipear
    if not isinstance(info, dict):
        continue
    
    total = info.get('total', 0)
    if total > 0:
        assets.append({
            'currency': curr,
            'free': info.get('free', 0),
            'used': info.get('used', 0),
            'total': total
        })

# Ordenar por cantidad
assets.sort(key=lambda x: x['total'], reverse=True)

# Mostrar balance
print("=" * 90)
print("BALANCE ACTUAL - BINANCE TESTNET")
print("=" * 90)
print()
print(f"{'Moneda':<12} {'Libre':<20} {'En uso':<20} {'Total':<20}")
print("-" * 90)

for a in assets:
    print(f"{a['currency']:<12} {a['free']:<20.8f} {a['used']:<20.8f} {a['total']:<20.8f}")

print()
print("=" * 90)
print("ANALISIS Y RECOMENDACIONES")
print("=" * 90)
print()

# Categorizar activos
stablecoins = ['USDT', 'BUSD', 'USDC', 'USDC', 'DAI']
principales = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL']

sc_assets = [a for a in assets if a['currency'] in stablecoins]
main_assets = [a for a in assets if a['currency'] in principales]
other_assets = [a for a in assets if a['currency'] not in (stablecoins + principales)]

if sc_assets:
    print("STABLECOINS (USDT/BUSD) - Ya lista para derivados:")
    sc_total = 0
    for a in sc_assets:
        print(f"  {a['currency']:<12} Total: {a['total']:>15.8f}  Libre: {a['free']:>15.8f}")
        sc_total += a['total']
    print(f"  {'TOTAL':<12} {sc_total:>15.8f}")

if main_assets:
    print("\nCRIPTOS PRINCIPALES - Recomendado convertir a USDT:")
    for a in main_assets:
        print(f"  {a['currency']:<12} Total: {a['total']:>15.8f}  Libre: {a['free']:>15.8f}")

if other_assets:
    print("\nOTROS ACTIVOS - Recomendado convertir a USDT:")
    for a in other_assets:
        print(f"  {a['currency']:<12} Total: {a['total']:>15.8f}  Libre: {a['free']:>15.8f}")

# Resumen
print()
print("=" * 90)
print("RESUMEN")
print("=" * 90)

sc_total = sum(a['total'] for a in sc_assets)
others_total = sum(a['total'] for a in main_assets + other_assets)

print(f"\nStablecoins totales: {sc_total:.8f} USDT")
print(f"Otros activos totales: {others_total:.8f}")

if others_total > 0:
    print(f"\nPASO 1: Necesitas convertir los siguientes activos a USDT:")
    conversions_needed = []
    for a in main_assets + other_assets:
        conversions_needed.append(f"{a['currency']}/{a['total']:.8f}")
        print(f"  - {a['currency']}: {a['total']:.8f}")
    
    print(f"\nPASO 2: Usa el siguiente script para convertir a USDT:")
    print(f"  python descarga_datos/convertir_a_usdt.py")
    
    print(f"\nPASO 3: Después de convertir, ejecuta:")
    print(f"  .venv\\Scripts\\python.exe descarga_datos/main.py --live-ccxt")
else:
    print(f"\nTODA LA CUENTA ESTA EN STABLECOINS - LISTA PARA DERIVADOS")
    print(f"Puedes ejecutar directamente: .venv\\Scripts\\python.exe descarga_datos/main.py --live-ccxt")

print()
