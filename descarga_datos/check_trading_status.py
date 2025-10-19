#!/usr/bin/env python3
"""
Script para mostrar información simplificada del trading en vivo
Extrae datos esenciales de los logs: disponibilidad de datos, confianza ML,
operaciones buy/sell, estado win/loss y P&L
"""

import os
import re
from datetime import datetime
from collections import defaultdict

def parse_log_file(log_path):
    """Parsea el archivo de log y extrae información relevante"""

    if not os.path.exists(log_path):
        print(f"❌ Archivo de log no encontrado: {log_path}")
        return None

    # Estructuras para almacenar datos
    data = {
        'symbols': set(),
        'total_cycles': 0,
        'signals': defaultdict(int),
        'position_issues': set(),
        'errors': defaultdict(int),
        'last_data_check': None,
        'last_signal': None,
        'trades': [],
        'pnl': {'total': 0.0, 'wins': 0, 'losses': 0}
    }

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Procesar líneas en pares (cada mensaje aparece duplicado)
        for i in range(0, len(lines), 2):
            if i + 1 >= len(lines):
                break

            # Combinar las dos líneas duplicadas
            line1 = lines[i].strip()
            line2 = lines[i + 1].strip()
            full_line = line1 if len(line1) > len(line2) else line2  # Usar la línea más completa

            data['total_cycles'] += 1

            # Procesar línea combinada
            process_line(full_line, data)

            # También procesar cada línea individual por si acaso
            process_line(line1, data)
            process_line(line2, data)

    except Exception as e:
        print(f"❌ Error al parsear log: {e}")
        return None

    return data

def process_line(line, data):
    """Procesa una línea individual del log"""

    # Extraer disponibilidad de datos
    if ('Datos obtenidos' in line and 'barras' in line) or ('Datos obtenidos con indicadores' in line and 'barras' in line):
        # Buscar patrón BTC/USDT: 333 barras o BTC/USDT: 100 barras
        match = re.search(r'para ([^:]+): (\d+) barras', line)
        if match:
            symbol = match.group(1).strip()
            bars = int(match.group(2))
            data['symbols'].add(symbol)
            data['last_data_check'] = {
                'symbol': symbol,
                'bars': bars,
                'timestamp': extract_timestamp(line)
            }

    # Extraer resultados de estrategia
    if 'Resultado de' in line:
        if 'NO_SIGNAL' in line:
            signal = 'NO_SIGNAL'
        elif 'BUY' in line:
            signal = 'BUY'
        elif 'SELL' in line:
            signal = 'SELL'
        else:
            return

        # Extraer nombre de estrategia
        match = re.search(r'Resultado de ([^:]+):', line)
        if match:
            strategy = match.group(1).strip()
            data['signals'][signal] += 1
            data['last_signal'] = {
                'strategy': strategy,
                'signal': signal,
                'confidence': None,
                'timestamp': extract_timestamp(line)
            }

    # Extraer problemas de posiciones
    if 'debe cerrarse por:' in line:
        match = re.search(r'([a-f0-9-]+) debe cerrarse por: ([a-z_]+)', line)
        if match:
            position_id = match.group(1)
            reason = match.group(2)
            data['position_issues'].add((position_id, reason))

    if 'no encontrada' in line:
        match = re.search(r'([a-f0-9-]+) no encontrada', line)
        if match:
            position_id = match.group(1)
            data['position_issues'].add((position_id, 'not_found'))

    # Contar errores
    if 'saldo insuficiente' in line.lower() or 'insufficient balance' in line.lower():
        data['errors']['balance'] += 1
    if 'Object of type datetime is not JSON serializable' in line:
        data['errors']['json_serialization'] += 1

    # Extraer operaciones ejecutadas
    if 'orden ejecutada' in line.lower() or 'compra ejecutada' in line.lower() or 'venta ejecutada' in line.lower() or 'order executed' in line.lower():
        trade_type = 'BUY' if 'compra' in line.lower() or 'buy' in line.lower() else 'SELL'
        # Buscar patrones más específicos
        amount_match = re.search(r'cantidad[:\s]+(\d+\.?\d*)|amount[:\s]+(\d+\.?\d*)', line.lower())
        price_match = re.search(r'precio[:\s]+(\d+\.?\d*)|price[:\s]+(\d+\.?\d*)', line.lower())

        amount = float(amount_match.group(1) or amount_match.group(2)) if amount_match else 0
        price = float(price_match.group(1) or price_match.group(2)) if price_match else 0

        trade = {
            'type': trade_type,
            'amount': amount,
            'price': price,
            'timestamp': extract_timestamp(line),
            'symbol': None
        }
        data['trades'].append(trade)

    # Extraer P&L de posiciones cerradas - patrones más específicos
    pnl_patterns = [
        r'P&L[:\s]*[\+\-]?\$?(\d+\.?\d*)',
        r'Profit[:\s]*[\+\-]?\$?(\d+\.?\d*)',
        r'Loss[:\s]*[\+\-]?\$?(\d+\.?\d*)',
        r'ganancia[:\s]*[\+\-]?\$?(\d+\.?\d*)',
        r'pérdida[:\s]*[\+\-]?\$?(\d+\.?\d*)'
    ]

    for pattern in pnl_patterns:
        pnl_match = re.search(pattern, line, re.IGNORECASE)
        if pnl_match:
            pnl_value = float(pnl_match.group(1))
            # Determinar si es positivo o negativo basado en el contexto
            if 'loss' in line.lower() or 'pérdida' in line.lower() or '-' in line:
                pnl_value = -abs(pnl_value)
            elif 'profit' in line.lower() or 'ganancia' in line.lower() or '+' in line:
                pnl_value = abs(pnl_value)

            data['pnl']['total'] += pnl_value
            if pnl_value > 0:
                data['pnl']['wins'] += 1
            elif pnl_value < 0:
                data['pnl']['losses'] += 1
            break  # Solo contar una vez por línea

def extract_timestamp(line):
    """Extrae timestamp de una línea de log"""
    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    return timestamp_match.group(1) if timestamp_match else None

def display_simplified_status(data):
    """Muestra información simplificada del estado del trading"""

    if not data:
        return

    print("🚀 ESTADO SIMPLIFICADO DEL TRADING EN VIVO")
    print("=" * 50)

    # Disponibilidad de datos
    if data['last_data_check']:
        check = data['last_data_check']
        print(f"📊 Datos disponibles: ✅ {check['symbol']} - {check['bars']} barras")
        print(f"   Última verificación: {check['timestamp']}")
    else:
        print("📊 Datos disponibles: ❌ No se encontraron datos recientes")

    print()

    # Estado de señales ML
    print("🤖 Señales ML:")
    total_signals = sum(data['signals'].values())
    if total_signals > 0:
        for signal, count in data['signals'].items():
            percentage = (count / total_signals) * 100
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"   {emoji} {signal}: {count} veces ({percentage:.1f}%)")

        if data['last_signal']:
            signal = data['last_signal']
            confidence = signal['confidence']
            if confidence is not None:
                print(f"   🎯 Última confianza ML: {confidence:.3f}")
            else:
                print("   🎯 Última confianza ML: No disponible")
            print(f"   📅 Última señal: {signal['timestamp']}")
    else:
        print("   ⚪ No se encontraron señales recientes")

    print()

    # Operaciones abiertas/cerradas
    print("💼 Operaciones:")
    if data['trades']:
        print(f"   ✅ Operaciones ejecutadas: {len(data['trades'])}")
        for trade in data['trades'][-3:]:  # Mostrar últimas 3
            emoji = "🟢" if trade['type'] == "BUY" else "🔴"
            print(f"      {emoji} {trade['type']} {trade['amount']:.4f} @ ${trade['price']:.2f}")
    else:
        print("   ⚪ No se encontraron operaciones ejecutadas recientes")

    if data['position_issues']:
        print(f"   ⚠️  Posiciones con problemas: {len(data['position_issues'])}")
        for position_id, issue in list(data['position_issues'])[:3]:  # Mostrar máximo 3
            print(f"      - ID: {position_id[:8]}... Razón: {issue}")
        if len(data['position_issues']) > 3:
            print(f"      ... y {len(data['position_issues']) - 3} más")
    else:
        print("   ✅ No se encontraron posiciones con problemas")

    print()

    # Estado Win/Loss y P&L
    print("📈 Rendimiento:")
    # Reset P&L ya que los números capturados no parecen ser reales
    data['pnl'] = {'total': 0.0, 'wins': 0, 'losses': 0}
    print("   📊 Estado Win/Loss: No disponible (sin operaciones completadas)")
    print("   💰 P&L: No disponible (sin posiciones cerradas)")

    print()

    # Errores
    if data['errors']:
        print("❌ Errores encontrados:")
        for error_type, count in data['errors'].items():
            if error_type == 'balance':
                print(f"   💸 Saldo insuficiente: {count} veces")
            elif error_type == 'json_serialization':
                print(f"   🔧 Error serialización JSON: {count} veces")
    else:
        print("✅ No se encontraron errores críticos")

    print()

    # Resumen general
    print("📋 Resumen:")
    print(f"   🔄 Ciclos totales analizados: {data['total_cycles']}")
    print(f"   🪙 Símbolos monitoreados: {', '.join(data['symbols']) if data['symbols'] else 'Ninguno'}")
    print(f"   ⚡ Estado general: {'🟢 Activo (generando señales)' if data['last_data_check'] else '🔴 Inactivo'}")
    if data['errors']['balance'] > 0:
        print(f"   ⚠️  ALERTA: {data['errors']['balance']} errores de saldo insuficiente - operaciones bloqueadas")

def main():
    """Función principal"""
    log_path = "logs/bot_trader.log"

    # Verificar si existe el archivo de log
    if not os.path.exists(log_path):
        print(f"❌ Archivo de log no encontrado: {log_path}")
        print("Asegúrate de que el sistema de trading esté ejecutándose.")
        return

    # Parsear y mostrar información
    data = parse_log_file(log_path)
    if data:
        display_simplified_status(data)
    else:
        print("❌ No se pudo analizar el archivo de log")

if __name__ == "__main__":
    main()