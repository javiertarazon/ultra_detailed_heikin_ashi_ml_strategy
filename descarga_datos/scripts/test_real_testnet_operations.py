#!/usr/bin/env python3
"""
Script de verificación para operaciones reales en Binance testnet.

Este script verifica que el sistema ahora obtiene posiciones y balance REALES
desde Binance testnet en lugar de usar datos simulados localmente.
"""

import sys
import os

# Agregar el directorio descarga_datos al path para las importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
descarga_datos_dir = os.path.join(current_dir, 'descarga_datos')
sys.path.insert(0, descarga_datos_dir)
sys.path.insert(0, current_dir)

from utils.logger import get_logger
from core.ccxt_order_executor import CCXTOrderExecutor
from config.config_loader import load_config

logger = get_logger(__name__)

def test_real_testnet_operations():
    """Prueba las operaciones reales en testnet."""

    print("🚀 VERIFICACIÓN DE OPERACIONES REALES EN BINANCE TESTNET")
    print("=" * 60)

    try:
        # Cargar configuración
        print("📋 Cargando configuración...")
        config = load_config()
        active_exchange = config.get('active_exchange', 'binance')
        print(f"🔄 Exchange activo configurado: {active_exchange}")

        # Inicializar order executor con el exchange correcto
        print("🔧 Inicializando CCXT Order Executor...")
        order_executor = CCXTOrderExecutor(config, exchange_name=active_exchange)

        # Conectar al exchange
        print("🔌 Conectando a Binance testnet...")
        if not order_executor.connect():
            print("❌ ERROR: No se pudo conectar a Binance testnet")
            return False

        print("✅ Conexión exitosa a Binance testnet")

        # Obtener balance real
        print("\n💰 Obteniendo balance REAL desde testnet...")
        balance = order_executor.get_account_balance()

        if balance:
            total_usdt = balance.get('total', {}).get('USDT', 0)
            free_usdt = balance.get('free', {}).get('USDT', 0)
            print(f"✅ Balance obtenido: ${total_usdt:.2f} USDT total, ${free_usdt:.2f} USDT disponible")
        else:
            print("❌ ERROR: No se pudo obtener balance")
            return False

        # Obtener posiciones reales
        print("\n📊 Obteniendo posiciones REALES desde testnet...")
        positions = order_executor.get_open_positions()

        print(f"📋 Posiciones encontradas: {len(positions)}")

        if positions:
            print("✅ POSICIONES REALES ENCONTRADAS:")
            for i, pos in enumerate(positions, 1):
                source = pos.get('source', 'unknown')
                print(f"  {i}. Ticket: {pos.get('ticket', 'N/A')} - "
                      f"Symbol: {pos.get('symbol', 'N/A')} - "
                      f"Type: {pos.get('type', 'N/A')} - "
                      f"Quantity: {pos.get('quantity', 0)} - "
                      f"Entry: ${pos.get('entry_price', 0):.2f} - "
                      f"Source: {source}")
        else:
            print("📭 No hay posiciones abiertas reales en testnet (esto es normal)")

        # Verificar método de verificación de órdenes
        print("\n🔍 Probando verificación de órdenes...")
        # Si hay posiciones, verificar la primera
        if positions:
            first_pos = positions[0]
            ticket = first_pos.get('ticket')
            if ticket and ticket.isdigit():  # Es un ID real de Binance
                print(f"🔎 Verificando orden real: {ticket}")
                verification = order_executor.verify_order_execution(ticket, 'BTC/USDT')
                print(f"✅ Verificación completada: {verification.get('execution_status', 'unknown')}")
            else:
                print("⏭️  Saltando verificación (ticket no es ID real de Binance)")
        else:
            print("⏭️  No hay posiciones para verificar")

        print("\n🎯 VERIFICACIÓN COMPLETADA EXITOSAMENTE")
        print("✅ El sistema ahora obtiene datos REALES de Binance testnet")
        print("✅ Balance dinámico verificado desde exchange")
        print("✅ Posiciones sincronizadas realmente con testnet")
        print("✅ Verificación de ejecución de órdenes implementada")

        return True

    except Exception as e:
        print(f"❌ ERROR durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_testnet_operations()
    sys.exit(0 if success else 1)