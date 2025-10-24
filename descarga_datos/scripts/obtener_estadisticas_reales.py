#!/usr/bin/env python3
"""
Script para obtener estadísticas REALES de trading del exchange en vivo.
Lee directamente desde la sesión activa de CCXT.
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Importar desde módulos locales
from core.ccxt_live_data import CCXTLiveDataProvider
from core.ccxt_live_trading_orchestrator import CCXTLiveTradingOrchestrator
from config.config_loader import load_config


async def get_live_trading_stats():
    """Obtiene estadísticas REALES de la sesión de trading en vivo."""
    try:
        # Cargar configuración
        config = load_config()
        
        print("\n" + "="*80)
        print("📊 ESTADÍSTICAS REALES DE TRADING EN VIVO")
        print("="*80)
        
        # Inicializar el orquestador
        orchestrator = CCXTLiveTradingOrchestrator(config)
        await orchestrator.connect()
        
        # Obtener posiciones activas
        positions = await orchestrator.get_active_positions()
        print(f"\n📍 Posiciones Activas: {len(positions)}")
        
        for i, pos in enumerate(positions, 1):
            print(f"\n  Posición {i}:")
            print(f"    - Símbolo: {pos.get('symbol', 'N/A')}")
            print(f"    - Tipo: {pos.get('side', 'N/A').upper()}")
            print(f"    - Cantidad: {pos.get('contracts', 0):.8f}")
            print(f"    - Precio Entrada: ${pos.get('entry_price', 0):.2f}")
            print(f"    - P&L Actual: ${pos.get('unrealized_pnl', 0):.2f}")
            print(f"    - Stop Loss: ${pos.get('stop_loss', 0):.2f}")
            print(f"    - Take Profit: ${pos.get('take_profit', 0):.2f}")
        
        # Obtener historial de operaciones cerradas
        closed_trades = await orchestrator.get_closed_trades()
        if closed_trades:
            print(f"\n\n✅ Operaciones Cerradas: {len(closed_trades)}")
            
            total_pnl = 0
            winning_trades = 0
            losing_trades = 0
            
            for i, trade in enumerate(closed_trades[-10:], 1):  # Últimas 10
                pnl = trade.get('pnl', 0)
                total_pnl += pnl
                
                if pnl > 0:
                    winning_trades += 1
                    icon = "✅"
                elif pnl < 0:
                    losing_trades += 1
                    icon = "❌"
                else:
                    icon = "➖"
                
                print(f"\n  {icon} Operación {i}:")
                print(f"     - Símbolo: {trade.get('symbol', 'N/A')}")
                print(f"     - Tipo: {trade.get('side', 'N/A').upper()}")
                print(f"     - Entrada: ${trade.get('entry_price', 0):.2f}")
                print(f"     - Salida: ${trade.get('exit_price', 0):.2f}")
                print(f"     - Cantidad: {trade.get('quantity', 0):.8f}")
                print(f"     - P&L: ${pnl:.2f}")
                print(f"     - Cierre: {trade.get('close_time', 'N/A')}")
            
            # Resumen estadísticas
            print(f"\n\n📈 RESUMEN ESTADÍSTICO:")
            print(f"   - Operaciones Ganadoras: {winning_trades}")
            print(f"   - Operaciones Perdedoras: {losing_trades}")
            print(f"   - Total P&L (últimas 10): ${total_pnl:.2f}")
            
            win_rate = (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0
            print(f"   - Tasa de Acierto: {win_rate:.1f}%")
        
        # Obtener métricas del tracker
        metrics = orchestrator.live_metrics if hasattr(orchestrator, 'live_metrics') else None
        if metrics:
            print(f"\n\n📊 MÉTRICAS AVANZADAS:")
            print(f"   - Balance Total: ${metrics.get('total_balance', 0):.2f}")
            print(f"   - Patrimonio: ${metrics.get('equity', 0):.2f}")
            print(f"   - Ganancias Realizadas: ${metrics.get('realized_pnl', 0):.2f}")
            print(f"   - Ganancias No Realizadas: ${metrics.get('unrealized_pnl', 0):.2f}")
            print(f"   - Factor de Ganancia: {metrics.get('profit_factor', 0):.2f}")
            print(f"   - Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"   - Máximo Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
        
        # Cerrar conexión
        await orchestrator.shutdown()
        
        print("\n" + "="*80)
        print("✅ Estadísticas obtenidas exitosamente")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error al obtener estadísticas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_live_trading_stats())
