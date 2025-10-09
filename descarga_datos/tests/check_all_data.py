#!/usr/bin/env python3
"""
Script simple para verificar datos de todos los símbolos
"""
import asyncio
import sys
import os

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

async def main():
    try:
        from config.config_loader import load_config_from_yaml
        from main import verify_data_availability

        print('🔍 VERIFICACIÓN DE DATOS PARA TODOS LOS SÍMBOLOS')
        print('=' * 60)

        config = load_config_from_yaml()
        symbols = config.backtesting.symbols

        print(f'📊 Símbolos configurados: {len(symbols)}')
        for i, symbol in enumerate(symbols, 1):
            print(f'  {i:2d}. {symbol}')

        print()
        print('🔄 Verificando disponibilidad de datos...')
        print()

        data_status = await verify_data_availability(config)

        print()
        print('📋 RESUMEN FINAL:')
        print('=' * 40)

        success_count = 0
        total_symbols = len(data_status)

        for symbol, status in data_status.items():
            source = status.get('source', 'unknown')
            rows = status.get('rows', 0)
            status_ok = status.get('status', 'unknown')

            if status_ok == 'ok':
                print(f'✅ {symbol:<12} | {source:<8} | {rows:>6} filas')
                success_count += 1
            else:
                print(f'❌ {symbol:<12} | ERROR')

        print()
        print(f'🎯 RESULTADO: {success_count}/{total_symbols} símbolos con datos disponibles')

        if success_count == total_symbols:
            print('🎉 ¡TODOS LOS SÍMBOLOS TIENEN DATOS!')
        elif success_count > 0:
            print('⚠️  Algunos símbolos necesitan descarga')
        else:
            print('❌ Ningún símbolo tiene datos disponibles')

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())