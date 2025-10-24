#!/usr/bin/env python3
"""
Script para analizar operaciones abiertas en modo live CCXT
Cuenta tickets únicos y detecta si posiciones se cierran correctamente
"""

import sys
import os
import re
from collections import OrderedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_live_log(log_text):
    """Analiza el log de trading live y cuenta operaciones."""
    
    # Extraer todos los tickets de operaciones abiertas
    opened_positions = OrderedDict()
    closed_positions = set()
    
    # Buscar operaciones abiertas - patrón: "ticket': '6000094'"
    ticket_pattern = r"'ticket':\s*'(\d+)'"
    
    # Buscar líneas de apertura de operación
    open_lines = re.findall(r"\[START\] APERTURA DE OPERACIÓN:.*?ticket': '(\d+)'", log_text, re.DOTALL)
    for ticket in open_lines:
        if ticket not in opened_positions:
            opened_positions[ticket] = {'status': 'open', 'count': 0}
        opened_positions[ticket]['count'] += 1
    
    # Buscar líneas de cierre de operación
    close_lines = re.findall(r"\[SYNC\] Removiendo posición (\d+) del seguimiento", log_text)
    for ticket in close_lines:
        closed_positions.add(ticket)
    
    # Buscar tickets únicos en posiciones
    all_tickets = re.findall(ticket_pattern, log_text)
    unique_tickets = set(all_tickets)
    
    # Contar intentos de apertura
    buy_attempts = len(re.findall(r"Abrir nueva posición BUY", log_text))
    sell_attempts = len(re.findall(r"Abrir nueva posición SELL", log_text))
    limit_reached = len(re.findall(r"Límite de posiciones alcanzado", log_text))
    
    # Contar órdenes verificadas como filled
    filled_orders = len(re.findall(r"\[OK\] Posición REAL abierta en testnet", log_text))
    
    # Contar NO_SIGNAL
    no_signals = len(re.findall(r"NO_SIGNAL", log_text))
    
    print("=" * 80)
    print("📊 ANÁLISIS DE OPERACIONES EN MODO LIVE CCXT")
    print("=" * 80)
    print()
    
    print("🔍 RESUMEN DE OPERACIONES:")
    print(f"  • Intentos de apertura BUY: {buy_attempts}")
    print(f"  • Intentos de apertura SELL: {sell_attempts}")
    print(f"  • Total intentos: {buy_attempts + sell_attempts}")
    print(f"  • Veces bloqueado por límite: {limit_reached}")
    print(f"  • Órdenes realmente ejecutadas (filled): {filled_orders}")
    print(f"  • Señales sin activación (NO_SIGNAL): {no_signals}")
    print()
    
    print("📈 TICKETS ÚNICOS DETECTADOS:")
    print(f"  • Total tickets únicos: {len(unique_tickets)}")
    for ticket in sorted(unique_tickets, key=lambda x: int(x)):
        status = "✅ CERRADA" if ticket in closed_positions else "🟢 ABIERTA"
        count = opened_positions.get(ticket, {}).get('count', 1)
        print(f"    {ticket}: {status} (aparece {count}x en logs)")
    print()
    
    print("📊 OPERACIONES ABIERTAS vs CERRADAS:")
    print(f"  • Posiciones abiertas: {len(opened_positions)}")
    print(f"  • Posiciones cerradas: {len(closed_positions)}")
    print(f"  • Posiciones aún abiertas: {len(opened_positions) - len(closed_positions)}")
    print()
    
    # Calcular tasas
    if buy_attempts + sell_attempts > 0:
        execution_rate = (filled_orders / (buy_attempts + sell_attempts)) * 100
        print(f"📊 TASAS DE EJECUCIÓN:")
        print(f"  • Tasa de ejecución: {execution_rate:.1f}%")
        print(f"  • Bloqueadas por límite: {(limit_reached / (buy_attempts + sell_attempts)) * 100:.1f}%")
        if limit_reached > 0:
            print(f"  ⚠️  El límite de posiciones bloqueó {limit_reached} operaciones")
    print()
    
    # Análisis de confianza ML
    ml_confidence = re.findall(r"ML confidence: ([\d.]+)", log_text)
    if ml_confidence:
        confidences = [float(c) for c in ml_confidence]
        print(f"📈 ANÁLISIS DE CONFIANZA ML:")
        print(f"  • Confianza mínima: {min(confidences):.4f}")
        print(f"  • Confianza máxima: {max(confidences):.4f}")
        print(f"  • Confianza promedio: {sum(confidences) / len(confidences):.4f}")
        print(f"  • Señales >50%: {sum(1 for c in confidences if c > 0.5)}")
        print()
    
    # Recomendación
    print("💡 RECOMENDACIONES:")
    if limit_reached > 0:
        percentage_blocked = (limit_reached / max(buy_attempts + sell_attempts, 1)) * 100
        if percentage_blocked > 30:
            print(f"  ⚠️  {percentage_blocked:.0f}% de operaciones fueron bloqueadas por límite")
            print("  ✅ SOLUCIÓN: Reducir max_positions o DESACTIVAR el límite")
    else:
        print("  ✅ Sin bloqueos por límite de posiciones")
    
    if no_signals > 0:
        print(f"  ℹ️  {no_signals} señales fueron filtradas (liquidity check)")
    
    print()
    print("=" * 80)
    
    return {
        'buy_attempts': buy_attempts,
        'sell_attempts': sell_attempts,
        'filled_orders': filled_orders,
        'limit_reached': limit_reached,
        'unique_tickets': list(unique_tickets),
        'closed_tickets': list(closed_positions),
        'open_tickets': [t for t in opened_positions.keys() if t not in closed_positions],
    }


if __name__ == "__main__":
    # Ejemplo de uso con un fragmento de log
    sample_log = """
2025-10-23 22:14:41 - CCXTLiveTradingOrchestrator - INFO - Abrir nueva posición BUY para BTC/USDT - Estrategia: UltraDetailedHeikinAshiML
2025-10-23 22:14:43 - CCXTOrderExecutor - INFO - [OK] Posición REAL abierta en testnet - Ticket: 5999749
2025-10-23 22:15:49 - CCXTOrderExecutor - INFO - [OK] Posición REAL abierta en testnet - Ticket: 6000094
2025-10-23 22:16:51 - CCXTLiveTradingOrchestrator - INFO - [SYNC] Removiendo posición 6000094 del seguimiento - ya cerrada en exchange
2025-10-23 22:16:52 - CCXTOrderExecutor - WARNING - Límite de posiciones alcanzado (2)
2025-10-23 22:16:49 - CCXTLiveTradingOrchestrator - INFO - Abrir nueva posición BUY para BTC/USDT - Estrategia: UltraDetailedHeikinAshiML
2025-10-23 22:17:53 - CCXTOrderExecutor - WARNING - Límite de posiciones alcanzado (2)
[LIVE SIGNAL] ML confidence: 0.497
[LIVE SIGNAL] ML confidence: 0.501
[LIVE SIGNAL] ML confidence: 0.513
2025-10-23 22:25:16 - CCXTLiveTradingOrchestrator - INFO - NO_SIGNAL - reason=low_liquidity
    """
    
    analyze_live_log(sample_log)
