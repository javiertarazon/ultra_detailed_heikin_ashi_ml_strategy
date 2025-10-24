#!/usr/bin/env python3
"""
Script para extraer estadísticas desde los logs de trading.
Busca las operaciones ejecutadas en tiempo real.
"""
import re
import json
from pathlib import Path
from datetime import datetime

log_file = Path("c:\\Users\\javie\\copilot\\botcopilot-sar\\logs\\bot_trader.log")

print("\n" + "="*70)
print("📊 ANÁLISIS DE OPERACIONES DE TRADING EN VIVO")
print("="*70 + "\n")

# Patrones de búsqueda
operaciones = []
tickets = set()
winning = 0
losing = 0
total_pnl = 0

if log_file.exists():
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Buscar operaciones de HOY (24 de octubre)
    print("🔍 Buscando operaciones de hoy (2025-10-24)...\n")
    
    for i, line in enumerate(lines):
        # Buscar líneas con información de operaciones
        
        # 1. APERTURA DE OPERACIONES
        if "APERTURA DE OPERACI" in line and "2025-10-24" in line:
            match = re.search(r"(BUY|SELL)", line)
            if match:
                direction = match.group(1)
                # Buscar ticket en líneas siguientes
                for j in range(i, min(i+5, len(lines))):
                    if "Ticket:" in lines[j]:
                        ticket_match = re.search(r"Ticket:\s*(\d+)", lines[j])
                        if ticket_match:
                            ticket = ticket_match.group(1)
                            print(f"✓ Operación {direction}: Ticket #{ticket}")
                            tickets.add(ticket)
                        break
        
        # 2. POSICIONES ACTIVAS CON P&L
        if "POSICIÓN ACTIVA" in line and "P&L:" in line:
            match = re.search(r"POSICIÓN ACTIVA\s*(\d+).*?P&L:\s*(\$[^\|]+)", line)
            if match:
                ticket = match.group(1)
                pnl_str = match.group(2).strip()
                print(f"  └─ P&L registrado: {pnl_str}")
        
        # 3. POSICIONES CERRADAS
        if "Posición cerrada:" in line and "PnL:" in line:
            match = re.search(r"Posición cerrada:\s*(\d+).*?PnL:\s*([-\d.]+)", line)
            if match:
                ticket = match.group(1)
                pnl = float(match.group(2))
                total_pnl += pnl
                
                if pnl > 0:
                    winning += 1
                    print(f"✓ Posición CERRADA GANADORA #{ticket}: +${abs(pnl):,.2f}")
                else:
                    losing += 1
                    print(f"✗ Posición CERRADA PERDEDORA #{ticket}: -${abs(pnl):,.2f}")
        
        # 4. TRAILING STOP ACTIVADO
        if "trailing stop" in line.lower() and "activado" in line.lower():
            match = re.search(r"#(\d+)", line)
            if match:
                ticket = match.group(1)
                print(f"🎯 Trailing Stop Activado - Ticket #{ticket}")
    
    print("\n" + "="*70)
    print("📈 RESUMEN OPERACIONES")
    print("="*70)
    
    total_ops = winning + losing
    print(f"\n✅ Operaciones Ganadoras: {winning}")
    print(f"❌ Operaciones Perdedoras: {losing}")
    print(f"📊 Total Operaciones Cerradas: {total_ops}")
    print(f"💵 P&L Total: ${total_pnl:,.2f}")
    
    if total_ops > 0:
        win_rate = (winning / total_ops) * 100
        print(f"📊 Tasa de Ganancia: {win_rate:.1f}%")
    
    print(f"\n📍 Posiciones Únicas Detectadas: {len(tickets)}")
    print(f"    Tickets: {', '.join(sorted(tickets))}")
    
    print("\n" + "="*70)
    
else:
    print(f"❌ No se encontró archivo de log: {log_file}")

print("\n💡 NOTA: Este análisis se basa en los registros disponibles en el log.\n")
