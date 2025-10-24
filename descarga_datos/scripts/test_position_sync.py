#!/usr/bin/env python3
"""
Script de prueba para verificar la sincronización de posiciones.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_loader import load_config
from core.ccxt_order_executor import CCXTOrderExecutor
from utils.logger import setup_logger

logger = setup_logger('test_position_sync')

def test_position_sync():
    """Prueba la sincronización de posiciones con el exchange."""
    try:
        # Cargar configuración
        config = load_config()
        logger.info("Configuración cargada correctamente")

        # Crear order executor
        order_executor = CCXTOrderExecutor(
            config=config,
            exchange_name='binance',
            risk_per_trade=0.01,
            max_positions=2
        )

        # Intentar conectar
        if not order_executor.connect():
            logger.error("No se pudo conectar al exchange")
            return False

        logger.info("Conectado al exchange exitosamente")

        # Verificar estado inicial de posiciones
        initial_positions = len(order_executor.open_positions)
        logger.info(f"Posiciones iniciales en order_executor: {initial_positions}")

        # Sincronizar posiciones
        sync_success = order_executor.sync_positions_with_exchange()
        if not sync_success:
            logger.error("Error en sincronización de posiciones")
            return False

        # Verificar estado después de sincronización
        synced_positions = len(order_executor.open_positions)
        logger.info(f"Posiciones después de sincronización: {synced_positions}")

        # Obtener posiciones reales para comparación
        real_positions = order_executor.get_open_positions()
        real_count = len([p for p in real_positions if p.get('source') == 'exchange'])
        logger.info(f"Posiciones reales en exchange: {real_count}")

        # Verificar que la sincronización fue correcta
        if synced_positions == real_count:
            logger.info("✅ SINCRONIZACIÓN EXITOSA: Las posiciones internas coinciden con las del exchange")
            return True
        else:
            logger.error(f"❌ ERROR DE SINCRONIZACIÓN: Internas={synced_positions}, Reales={real_count}")
            return False

    except Exception as e:
        logger.error(f"Error en prueba de sincronización: {e}")
        return False
    finally:
        # Desconectar
        try:
            order_executor.disconnect()
        except:
            pass

if __name__ == "__main__":
    logger.info("🚀 Iniciando prueba de sincronización de posiciones")

    success = test_position_sync()

    if success:
        logger.info("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        sys.exit(0)
    else:
        logger.error("❌ PRUEBA FALLIDA")
        sys.exit(1)