from utils.data_audit import run_data_audit
from config.config_loader import load_config_from_yaml

print('🔍 Ejecutando auditoría completa con todas las mejoras...')

cfg = load_config_from_yaml()
report = run_data_audit(cfg, auto_fetch_missing=False, incremental_edges=False)

print('AUDITORÍA COMPLETA - RESULTADOS FINALES')
print('=' * 60)
print(f'Total símbolos: {report["summary"]["symbols_total"]}')
print(f'Símbolos OK: {report["summary"]["symbols_ok"]}')
print(f'Símbolos insuficientes: {report["summary"]["symbols_insufficient"]}')
print(f'Símbolos faltantes: {report["summary"]["symbols_missing"]}')
print(f'Puntaje promedio: {report["summary"]["integrity_score_avg"]:.1f}%')

print('\nANÁLISIS DETALLADO:')
print('-' * 40)

# Analizar por clase de activo
crypto_scores = []
forex_scores = []
equity_scores = []

for symbol, data in report['results'].items():
    integrity = data.get('integrity_score', 0)
    if '/' in symbol:  # Crypto
        crypto_scores.append(integrity)
    elif symbol.replace('_', '').upper() in ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY']:
        forex_scores.append(integrity)
    elif symbol.endswith(('_US', '.US')) or symbol in ['NVDA', 'META', 'JPM', 'V', 'JNJ']:
        equity_scores.append(integrity)

print(f'📊 Criptomonedas: {len(crypto_scores)} símbolos, promedio {sum(crypto_scores)/len(crypto_scores):.1f}%')
print(f'📊 Forex: {len(forex_scores)} símbolos, promedio {sum(forex_scores)/len(forex_scores):.1f}%')
print(f'📊 Acciones US: {len(equity_scores)} símbolos, promedio {sum(equity_scores)/len(equity_scores):.1f}%')

print('\nDETALLE DE SÍMBOLOS INSUFICIENTES:')
print('-' * 40)

insufficient_symbols = []
for symbol, data in report['results'].items():
    if data['status'] == 'insufficient':
        integrity = data.get('integrity_score', 0)
        records = data.get('records', 0)
        insufficient_symbols.append((symbol, integrity, records))

if insufficient_symbols:
    for symbol, integrity, records in sorted(insufficient_symbols, key=lambda x: x[1]):
        print(f'{symbol}: {integrity:.1f}% integridad ({records} velas)')
else:
    print('🎯 ¡NINGÚN SÍMBOLO INSUFICIENTE!')

# Verificar objetivo: todos >90%
all_above_90 = all(data.get('integrity_score', 0) >= 90 for data in report['results'].values())
insufficient_count = report['summary']['symbols_insufficient']

print(f'\nRESULTADO FINAL:')
print('=' * 20)
if insufficient_count == 0 and all_above_90:
    print('🎯 OBJETIVO ALCANZADO: Todos los símbolos tienen >90% integridad!')
    print('✅ Sistema listo para backtesting de alta calidad')
else:
    print(f'⚠️ Aún hay {insufficient_count} símbolos insuficientes')
    print('🔧 Se necesitan mejoras adicionales')