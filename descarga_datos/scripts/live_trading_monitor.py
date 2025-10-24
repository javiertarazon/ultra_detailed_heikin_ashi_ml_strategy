#!/usr/bin/env python3
"""
Script para ejecutar Live Trading CCXT con monitoreo en tiempo real
"""

import asyncio
import time
from datetime import datetime
import pandas as pd
from core.ccxt_live_trading_orchestrator import CCXTLiveTradingOrchestrator
from strategies.heikin_neuronal_ml_pruebas import HeikinNeuronalMLPruebasStrategy

async def run_live_trading_monitor():
    print('🚀 INICIANDO LIVE TRADING CCXT - BINANCE TESTNET')
    print('=' * 60)

    # Inicializar orquestador
    orchestrator = CCXTLiveTradingOrchestrator()

    # Verificar conexión y balance inicial
    if orchestrator.order_executor.connect():
        balance = orchestrator.order_executor.exchange.fetch_balance()
        initial_usdt = balance.get('free', {}).get('USDT', 0)
        initial_btc = balance.get('free', {}).get('BTC', 0)
        print('✅ Conectado a BINANCE TESTNET')
        print(f'💰 Balance inicial: USDT: {initial_usdt:.2f}, BTC: {initial_btc:.6f}')
    else:
        print('❌ Error de conexión')
        return

    # Configurar estrategia
    strategy_config = {
        'symbol': 'BTC/USDT',
        'timeframe': '15m',
        'risk_per_trade': 0.02,
        'portfolio_value': initial_usdt
    }

    print(f'\n🎯 Configuración:')
    print(f'   Estrategia: HeikinNeuronalMLPruebas')
    print(f'   Símbolo: {strategy_config["symbol"]}')
    print(f'   Timeframe: {strategy_config["timeframe"]}')
    print(f'   Riesgo por trade: {strategy_config["risk_per_trade"]*100:.1f}%')

    # Inicializar estrategia
    strategy = HeikinNeuronalMLPruebasStrategy(strategy_config)

    # Obtener datos históricos para la estrategia
    print('📊 Obteniendo datos históricos...')
    try:
        # Usar el exchange ya conectado del order_executor para obtener datos históricos
        ohlcv = orchestrator.order_executor.exchange.fetch_ohlcv('BTC/USDT', '15m', limit=500)
        
        if not ohlcv or len(ohlcv) < 50:
            print('❌ Error: No se pudieron obtener datos históricos suficientes')
            return
            
        # Convertir a DataFrame - mantener timestamp como columna
        historical_data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'], unit='ms')
        # No convertir timestamp a índice para mantener compatibilidad con la estrategia
        
        print(f'✅ Datos históricos obtenidos: {len(historical_data)} velas')
        
        # Preparar datos para la estrategia
        data_processed = strategy._prepare_data_live(historical_data.copy())
        print(f'✅ Datos preparados para live trading: {len(data_processed)} filas')
        
    except Exception as e:
        print(f'❌ Error obteniendo datos históricos: {e}')
        return

    print('\n📊 INICIANDO MONITOREO DE OPERACIONES')
    print('=' * 60)

    start_time = time.time()
    last_balance_check = 0
    operations_count = 0

    while time.time() - start_time < 300:  # 5 minutos de monitoreo
        try:
            current_time = datetime.now().strftime('%H:%M:%S')

            # Verificar balance cada 30 segundos
            if time.time() - last_balance_check > 30:
                balance = orchestrator.order_executor.exchange.fetch_balance()
                usdt = balance.get('free', {}).get('USDT', 0)
                btc = balance.get('free', {}).get('BTC', 0)
                print(f'[{current_time}] 💰 Balance: USDT: {usdt:.2f}, BTC: {btc:.6f}')
                last_balance_check = time.time()

            # Obtener datos frescos para la señal
            try:
                # Obtener datos históricos recientes
                ohlcv_recent = orchestrator.order_executor.exchange.fetch_ohlcv('BTC/USDT', '15m', limit=100)
                if ohlcv_recent and len(ohlcv_recent) > 50:
                    recent_data = pd.DataFrame(ohlcv_recent, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp'], unit='ms')
                    
                    # Preparar datos frescos para la estrategia
                    data_processed = strategy._prepare_data_live(recent_data.copy())
                else:
                    print(f'[{current_time}] ⚠️  No se pudieron obtener datos frescos, usando datos anteriores')
            except Exception as e:
                print(f'[{current_time}] ⚠️  Error obteniendo datos frescos: {e}, usando datos anteriores')

            # Generar señal de la estrategia
            signal_result = strategy.get_live_signal(data_processed, 'BTC/USDT', '15m')
            
            if signal_result and signal_result.get('signal') not in ['NO_SIGNAL', None]:
                operations_count += 1
                action = signal_result.get('signal')
                confidence = signal_result.get('ml_confidence', 0)
                reason = signal_result.get('reason', 'N/A')
                
                print(f'\n[{current_time}] 🚨 SEÑAL GENERADA #{operations_count}')
                print(f'   Acción: {action}')
                print(f'   Confianza ML: {confidence:.3f}')
                print(f'   Razón: {reason}')

                # Ejecutar operación
                if action in ['BUY', 'SELL']:
                    try:
                        # Obtener precio actual del exchange
                        ticker = orchestrator.order_executor.exchange.fetch_ticker('BTC/USDT')
                        current_price = ticker['last'] if ticker else None
                        
                        if current_price:
                            price = current_price
                            
                            # Usar los parámetros de risk management de la estrategia
                            signal_data = signal_result.get('signal_data', {})
                            risk_params = {
                                'quantity': None,  # Se calculará en el order executor
                                'stop_loss': signal_data.get('stop_loss_price'),
                                'take_profit': signal_data.get('take_profit_price'),
                                'risk_amount': None,
                                'risk_percent': signal_data.get('risk_per_trade', 0.02),
                                'required_currency': None,
                                'available_balance': None,
                                'portfolio_value': initial_usdt
                            }
                            
                            print(f'   Precio: ${price:.2f}')
                            print(f'   Stop Loss: ${signal_data.get("stop_loss_price", "N/A"):.2f}')
                            print(f'   Take Profit: ${signal_data.get("take_profit_price", "N/A"):.2f}')
                            print(f'   Riesgo: {signal_data.get("risk_per_trade", 0.02)*100:.2f}%')

                            # Ejecutar orden usando apply_risk_management para calcular quantity
                            final_risk_params = orchestrator.order_executor.apply_risk_management(
                                symbol='BTC/USDT',
                                order_type=action,
                                entry_price=price,
                                stop_loss=signal_data.get('stop_loss_price'),
                                take_profit=signal_data.get('take_profit_price'),
                                risk_per_trade=signal_data.get('risk_per_trade', 0.02),
                                portfolio_value=initial_usdt
                            )
                            
                            if final_risk_params.get('quantity', 0) > 0:
                                print(f'   Cantidad calculada: {final_risk_params["quantity"]:.6f} BTC')
                                
                                # Ejecutar orden
                                order_result = orchestrator.order_executor.open_position(
                                    symbol='BTC/USDT',
                                    order_type=action,
                                    quantity=final_risk_params['quantity'],
                                    stop_loss_price=final_risk_params.get('stop_loss'),
                                    take_profit_price=final_risk_params.get('take_profit')
                                )
                                
                                if order_result:
                                    print(f'   ✅ Orden ejecutada: {order_result}')
                                else:
                                    print(f'   ❌ Error ejecutando orden')
                            else:
                                print(f'   ❌ Cantidad calculada inválida')
                        else:
                            print(f'   ❌ Error obteniendo precio actual')
                            
                    except Exception as e:
                        print(f'   ❌ Error en ejecución: {e}')
            else:
                # No hay señal, mostrar estado cada 2 minutos
                if operations_count == 0 and int(time.time()) % 120 == 0:
                    print(f'[{current_time}] ⏳ Esperando señales... (sin operaciones aún)')            # Esperar antes de siguiente iteración
            await asyncio.sleep(10)  # Verificar cada 10 segundos

        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] ❌ Error en monitoreo: {e}')
            await asyncio.sleep(5)

    print(f'\n⏹️  MONITOREO FINALIZADO')
    print(f'   Duración: {(time.time() - start_time)/60:.1f} minutos')
    print(f'   Operaciones analizadas: {operations_count}')

if __name__ == "__main__":
    asyncio.run(run_live_trading_monitor())