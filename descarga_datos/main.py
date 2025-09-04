import asyncio
import pandas as pd
from datetime import datetime
import os

from descarga_datos.core.downloader import DataDownloader
from descarga_datos.core.mt5_downloader import MT5Downloader, MT5_AVAILABLE
from descarga_datos.indicators.technical_indicators import TechnicalIndicators
from descarga_datos.utils.normalization import DataNormalizer
from descarga_datos.utils.storage import DataStorage, save_to_csv
from descarga_datos.config.config_loader import load_config_from_yaml
from descarga_datos.utils.logger import setup_logging, get_logger
from descarga_datos.strategies.ut_bot_psar import UTBotPSARStrategy
from descarga_datos.strategies.optimized_utbot_strategy import OptimizedUTBotStrategy
from descarga_datos.backtesting.backtester import AdvancedBacktester

def validate_data(df: pd.DataFrame, logger=None) -> bool:
    """
    Valida la integridad de los datos antes del backtesting.
    
    Args:
        df: DataFrame con los datos a validar
        logger: Logger opcional para mensajes
        
    Returns:
        bool: True si los datos son válidos, False en caso contrario
    """
    if logger is None:
        logger = get_logger(__name__)
    
    # 1. Verificar que el DataFrame no está vacío
    if df.empty:
        logger.error("El DataFrame está vacío")
        return False
    
    # 2. Verificar columnas OHLCV y técnicas requeridas
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    technical_columns = ['sar', 'atr', 'adx']
    all_required = required_columns + technical_columns
    
    missing_columns = [col for col in all_required if col not in df.columns]
    if missing_columns:
        logger.error(f"Faltan columnas requeridas: {missing_columns}")
        return False
    
    # 3. Verificar valores nulos en columnas críticas
    null_check = df[required_columns].isnull().any()
    if null_check.any():
        null_cols = null_check[null_check].index.tolist()
        logger.error(f"Hay valores nulos en las columnas OHLCV: {null_cols}")
        return False
    
    # 4. Verificar validez de precios
    price_columns = ['open', 'high', 'low', 'close']
    
    # 4.1 Verificar precios positivos
    if (df[price_columns] <= 0).any().any():
        logger.error("Hay precios negativos o cero en los datos")
        return False
    
    # 4.2 Verificar relación high-low
    invalid_hl = df[df['high'] < df['low']].index
    if not invalid_hl.empty:
        logger.error(f"Hay {len(invalid_hl)} registros donde high < low")
        return False
    
    # 4.3 Verificar que open/close están entre high y low
    price_logic = (
        (df['open'] <= df['high']) & 
        (df['open'] >= df['low']) & 
        (df['close'] <= df['high']) & 
        (df['close'] >= df['low'])
    )
    if not price_logic.all():
        logger.error("Hay precios open/close fuera del rango high-low")
        return False
    
    # 5. Verificar volumen
    if (df['volume'] < 0).any():
        logger.error("Hay valores negativos en el volumen")
        return False
    
    # 6. Verificar indicadores técnicos
    tech_check = df[technical_columns].isnull().any()
    if tech_check.any():
        tech_null = tech_check[tech_check].index.tolist()
        logger.warning(f"Hay valores nulos en indicadores técnicos: {tech_null}")
    
    logger.info("Validación de datos completada exitosamente")
    return True

def check_data_exists(storage: DataStorage, table_name: str, start_date: str, end_date: str, timeframe: str) -> tuple[bool, pd.DataFrame]:
    """
    Verifica si los datos ya existen en la base de datos para el período especificado y los retorna.
    
    Args:
        storage: Instancia de DataStorage para acceder a los datos
        table_name: Nombre de la tabla a verificar
        start_date: Fecha de inicio en formato 'YYYY-MM-DD'
        end_date: Fecha de fin en formato 'YYYY-MM-DD'
        timeframe: El timeframe de los datos (ej. '1h', '1d') para verificar la continuidad.
        
    Returns:
        tuple[bool, pd.DataFrame]: (True si los datos existen y están completos, DataFrame con los datos)
                                 Si los datos no existen o están incompletos, retorna (False, DataFrame vacío)
    """
    # Convertir fechas a timestamps para comparación (en segundos)
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
    
    # Verificar si la tabla existe y obtener datos
    if not storage.table_exists(table_name):
        return False, pd.DataFrame()
        
    # Obtener los datos del rango temporal
    df = storage.query_data(table_name, start_ts, end_ts)
    
    if df.empty:
        return False, df
        
    # Verificar continuidad de los datos según el timeframe
    if timeframe == '1h':
        expected_interval = 3600  # 1 hora en segundos
    elif timeframe == '1d':
        expected_interval = 86400  # 1 día en segundos
    else:
        raise ValueError(f"Timeframe no soportado: {timeframe}")
        
    timestamps = df['timestamp'].values
    gaps = timestamps[1:] - timestamps[:-1]
    
    # Permitir una pequeña tolerancia en los intervalos (1 minuto)
    tolerance = 60  # 1 minuto en segundos
    
    if not all((expected_interval - tolerance) <= gap <= (expected_interval + tolerance) for gap in gaps):
        return False, df
        
    return True, df

async def main():
    # Cargar configuración
    config = load_config_from_yaml()
    
    # Configurar logging
    setup_logging(config)
    logger = get_logger(__name__)
    
    logger.info("Iniciando proceso de verificación y descarga de datos...")
    
    # Inicializar componentes
    downloader = DataDownloader(config)
    
    # Verificar si debemos usar MT5
    mt5_downloader = None
    if config.use_mt5:
        if MT5_AVAILABLE:
            logger.info("Usando MetaTrader 5 como fuente de datos")
            mt5_downloader = MT5Downloader(config)
            await mt5_downloader.initialize_async()
        else:
            logger.warning("MetaTrader 5 está configurado pero no disponible. Instale con: pip install MetaTrader5>=5.0.45")
            logger.info("Continuando con la fuente de datos alternativa...")
    
    storage = DataStorage(f"{config.storage.path}/data.db")
    
    try:
        # Configurar exchanges
        await downloader.setup_exchanges()
        
        # Obtener exchange activo y timeframe
        active_exchange = config.active_exchange
        timeframe = config.exchanges[active_exchange]['timeframe']
        start_date = config.exchanges[active_exchange]['start_date']
        end_date = config.exchanges[active_exchange]['end_date']
        
        # Descargar datos para cada símbolo
        for symbol in config.default_symbols:
            logger.info(f"Verificando datos existentes para {symbol} en {active_exchange}")
            
            symbol_safe = symbol.replace('/', '_').replace('.', '_')
            table_raw = f"{config.active_exchange}_{symbol_safe}_{timeframe}_indicators_raw"
            table_normalized = f"{config.active_exchange}_{symbol_safe}_{timeframe}_indicators_normalized"
            
            # Verificar si los datos finales (normalizados) ya existen y están completos
            data_exists, _ = check_data_exists(storage, table_normalized, start_date, end_date, timeframe)
            
            if data_exists:
                logger.info(f"Datos existentes encontrados para {symbol}, usando datos almacenados")
                # Cargar TODOS los datos disponibles sin filtrar por fecha
                data_with_indicators = storage.query_data(table_normalized)
                logger.info(f"Datos cargados: {len(data_with_indicators)} filas")
            else:
                logger.info(f"Descargando nuevos datos para {symbol}")
                
                # Decidir qué fuente de datos usar basada en el tipo de símbolo
                use_mt5_for_symbol = False
                if config.use_mt5 and mt5_downloader is not None:
                    # Usar MT5 solo para acciones (símbolos que terminan en .US)
                    if symbol.endswith('.US'):
                        use_mt5_for_symbol = True
                        logger.info(f"Usando MT5 para acción: {symbol}")
                    else:
                        logger.info(f"Usando CCXT para cripto: {symbol}")
                
                if use_mt5_for_symbol:
                    # Usar MT5 para descargar datos de acciones
                    logger.info(f"Descargando datos desde MT5 para {symbol}")
                    
                    # Probar diferentes formatos de símbolo para acciones
                    symbol_formats = []
                    if symbol.endswith('.US'):
                        base_symbol = symbol.replace('.US', '')
                        symbol_formats = [
                            symbol,           # TSLA.US
                            base_symbol,      # TSLA
                            f"{base_symbol}USD",  # TSLAUSD
                            f"{base_symbol}USDT", # TSLAUSDT
                        ]
                    else:
                        symbol_formats = [symbol]
                    
                    ohlcv_data = None
                    successful_format = None
                    
                    # Probar diferentes fechas también
                    date_ranges = [
                        (start_date, end_date),  # Fechas originales
                        ("2023-01-01", "2023-06-01"),  # 2023
                        ("2022-01-01", "2022-06-01"),  # 2022
                        ("2021-01-01", "2021-06-01"),  # 2021
                    ]
                    
                    for fmt in symbol_formats:
                        for date_start, date_end in date_ranges:
                            logger.info(f"Intentando MT5 con símbolo: {fmt}, fechas: {date_start} a {date_end}")
                            
                            # Convertir fechas a datetime
                            start_dt = datetime.strptime(date_start, '%Y-%m-%d')
                            end_dt = datetime.strptime(date_end, '%Y-%m-%d')
                            
                            # Intentar descargar
                            ohlcv_data = await mt5_downloader.download_data(
                                fmt,
                                timeframe,
                                start_dt,
                                end_dt
                            )
                            
                            if ohlcv_data is not None and not ohlcv_data.empty:
                                logger.info(f"✅ Éxito con formato: {fmt}, fechas: {date_start} a {date_end}")
                                successful_format = fmt
                                break
                        
                        if successful_format:
                            break
                    
                    if ohlcv_data is None or ohlcv_data.empty:
                        logger.warning(f"No se pudieron descargar datos de MT5 para {symbol} con ningún formato. Intentando con CCXT...")
                        # Fallback a CCXT si MT5 falla
                        ohlcv_data, stats = await downloader.async_download_ohlcv(
                            symbol, 
                            active_exchange, 
                            timeframe=timeframe,
                            limit=1000
                        )
                        if ohlcv_data is not None and not ohlcv_data.empty:
                            logger.info(f"✅ Fallback exitoso: Datos descargados desde CCXT para {symbol}")
                        else:
                            logger.error(f"No se pudieron descargar datos para {symbol} desde MT5 ni CCXT")
                            continue
                    
                    # Crear estadísticas simuladas para mantener consistencia con el flujo existente
                    stats = {
                        'time_range': {
                            'start': date_start if 'date_start' in locals() else start_date,
                            'end': date_end if 'date_end' in locals() else end_date
                        },
                        'row_count': len(ohlcv_data) if ohlcv_data is not None else 0,
                        'price_stats': {
                            'price_volatility': ohlcv_data['close'].pct_change().std() if ohlcv_data is not None and not ohlcv_data.empty else 0
                        }
                    }
                    
                    # Guardar datos en formato CSV para mantener consistencia
                    if ohlcv_data is not None and not ohlcv_data.empty:
                        output_dir = f"{config.storage.path}/csv"
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = f"{output_dir}/mt5_{successful_format or symbol}_{timeframe}_ohlcv.csv"
                        ohlcv_data.to_csv(output_file)
                        logger.info(f"Datos guardados en CSV: {output_file}")
                else:
                    # Usar exchange CCXT para descargar datos de criptos
                    logger.info(f"Descargando datos desde CCXT para {symbol}")
                    ohlcv_data, stats = await downloader.async_download_ohlcv(
                        symbol, 
                        active_exchange, 
                        timeframe=timeframe,
                        limit=1000
                    )
                
                if stats:
                    logger.info(f"Estadísticas de descarga para {symbol}:")
                    logger.info(f"  - Rango temporal: {stats['time_range']['start']} a {stats['time_range']['end']}")
                    logger.info(f"  - Filas descargadas: {stats['row_count']}")
                    logger.info(f"  - Volatilidad de precios: {stats['price_stats']['price_volatility']:.4f}")
                
                if ohlcv_data is not None and not ohlcv_data.empty:
                    logger.info(f"Datos descargados: {len(ohlcv_data)} filas")
                    
                    # Calcular indicadores
                    indicators = TechnicalIndicators(config)
                    data_with_indicators = indicators.calculate_all_indicators(ohlcv_data)
                else:
                    logger.error(f"No se pudieron descargar los datos para {symbol}")
                    continue
            
            if data_with_indicators is not None:
                if not data_exists:
                    logger.info("Indicadores calculados exitosamente")
                    
                    # Guardar datos crudos con indicadores
                    output_dir = f"{config.storage.path}/csv"
                    output_file_raw = f"{output_dir}/{config.active_exchange}_{symbol_safe}_{timeframe}_ohlcv_indicators.csv"
                    
                    save_to_csv(data_with_indicators, output_file_raw)
                    storage.save_data(table_raw, data_with_indicators)
                    logger.info(f"Datos crudos guardados en CSV: {output_file_raw} y DB: {table_raw}")
                    
                    # Normalizar datos
                    logger.info("Normalizando datos...")
                    normalizer = DataNormalizer(config.normalization)
                    normalized_data = normalizer.fit_transform(data_with_indicators)
                    
                    output_file_normalized = f"{output_dir}/{config.active_exchange}_{symbol_safe}_{timeframe}_ohlcv_indicators_normalized.csv"
                    
                    save_to_csv(normalized_data, output_file_normalized)
                    storage.save_data(table_normalized, normalized_data)
                    logger.info(f"Datos normalizados guardados en CSV: {output_file_normalized} y DB: {table_normalized}")
                
                # Ejecutar backtesting
                logger.info(f"Iniciando backtesting para {symbol}...")
                try:
                    # Cargar TODOS los datos disponibles para backtesting
                    logger.info(f"Cargando datos para backtesting de la tabla {table_raw}")
                    data = storage.query_data(table_raw)  # Sin filtrar por fecha
                    
                    if data.empty:
                        logger.error(f"No se encontraron datos en la tabla {table_raw}")
                        continue
                    
                    logger.info(f"Datos cargados para backtesting: {len(data)} filas")
                    
                    # Validar que tenemos todas las columnas necesarias
                    if not validate_data(data, logger):
                        logger.error("Los datos no son válidos para realizar el backtesting")
                        continue
                    
                    # Ejecutar el backtesting
                    results = await run_backtest(data, symbol)
                    logger.info(f"Backtesting completado exitosamente para {symbol}")
                    
                    # Mostrar resultados básicos
                    if results:
                        logger.info("Resumen de resultados:")
                        for strategy_name, result in results.items():
                            logger.info(f"\nEstratégia: {strategy_name}")
                            logger.info(f"Total trades: {result.get('total_trades', 0)}")
                            logger.info(f"Win rate: {result.get('win_rate', 0)*100:.2f}%")
                            logger.info(f"Profit/Loss total: ${result.get('total_pnl', 0):.2f}")
                            
                            # Métricas adicionales para comparación detallada
                            if 'profit_factor' in result:
                                logger.info(f"Profit Factor: {result['profit_factor']:.2f}")
                            if 'expectancy' in result:
                                logger.info(f"Expectancy: ${result['expectancy']:.2f}")
                            if 'avg_win' in result and 'avg_loss' in result:
                                logger.info(f"Avg Win/Loss: ${result['avg_win']:.2f} / ${result['avg_loss']:.2f}")
                            if 'max_drawdown' in result:
                                logger.info(f"Máximo drawdown: {result['max_drawdown']:.2f}%")
                            if 'sharpe_ratio' in result:
                                logger.info(f"Ratio de Sharpe: {result['sharpe_ratio']:.2f}")
                
                except Exception as e:
                    logger.error(f"Error al cargar datos para backtesting: {e}")
            else:
                logger.error("Error al calcular los indicadores")
    
    finally:
        # Cerrar exchanges
        await downloader.close_exchanges()
        
        # Cerrar MT5 si se utilizó
        if config.use_mt5 and mt5_downloader is not None:
            mt5_downloader.shutdown()
            logger.info("Conexión MT5 cerrada")

async def run_backtest(data: pd.DataFrame, symbol: str) -> dict:
    """
    Ejecuta el backtesting de la estrategia UT Bot + PSAR usando datos con indicadores precalculados.
    
    Args:
        data: DataFrame con datos OHLCV e indicadores técnicos
        symbol: Símbolo del par de trading
        
    Returns:
        dict: Resultados del backtesting
    """
    logger = get_logger(__name__)
    
    # Configuraciones de estrategia
    strategies = {
        "UTBot_Conservadora": UTBotPSARStrategy(
            sensitivity=0.8,
            atr_period=14,
            use_heikin_ashi=False,
            risk_percent=1.0,
            tp_atr_multiplier=3.0,
            sl_atr_multiplier=1.2,
            psar_start=0.015,
            psar_increment=0.015,
            psar_max=0.15
        ),
        "UTBot_Intermedia": UTBotPSARStrategy(
            sensitivity=1.0,
            atr_period=10,
            use_heikin_ashi=False,
            risk_percent=2.0,
            tp_atr_multiplier=2.0,
            sl_atr_multiplier=1.5,
            psar_start=0.02,
            psar_increment=0.02,
            psar_max=0.2
        ),
        "UTBot_Agresiva": UTBotPSARStrategy(
            sensitivity=1.2,
            atr_period=8,
            use_heikin_ashi=False,
            risk_percent=3.0,
            tp_atr_multiplier=1.5,
            sl_atr_multiplier=2.0,
            psar_start=0.025,
            psar_increment=0.025,
            psar_max=0.25
        ),
        "Optimizada_Ganadora": OptimizedUTBotStrategy(
            sensitivity=1.0,
            atr_period=10,
            take_profit_multiplier=4.5,
            stop_loss_multiplier=2.0,
            psar_acceleration=0.02,
            psar_maximum=0.2,
            min_confidence=0.7
        )
    }
    
    results = {}
    
    # Probar cada configuración
    for strategy_name, strategy in strategies.items():
        logger.info(f"Iniciando backtesting para {symbol} con estrategia {strategy_name}...")
        
        # Configurar backtester
        backtester = AdvancedBacktester(
            initial_capital=10000,
            commission=0.1  # 0.1%
        )
        
        # Ejecutar backtesting
        strategy_results = backtester.run(strategy, data, symbol)
        results[strategy_name] = strategy_results
        
        # Mostrar resultados detallados
        logger.info(f"\n=== RESULTADOS DETALLADOS PARA {symbol.upper()} - {strategy_name.upper()} ===")
        logger.info(f"[+] Total trades: {strategy_results['total_trades']}")
        logger.info(f"[+] Win rate: {strategy_results['win_rate']*100:.2f}%")
        logger.info(f"[+] Profit/Loss total: ${strategy_results['total_pnl']:.2f}")
        logger.info(f"[+] Maximo drawdown: {strategy_results['max_drawdown']:.2f}%")
        logger.info(f"[+] Ratio de Sharpe: {strategy_results['sharpe_ratio']:.2f}")
        
        # Métricas adicionales si están disponibles
        if 'profit_factor' in strategy_results:
            logger.info(f"[+] Profit Factor: {strategy_results['profit_factor']:.2f}")
        if 'expectancy' in strategy_results:
            logger.info(f"[+] Expectancy: ${strategy_results['expectancy']:.2f}")
        if 'avg_win' in strategy_results and 'avg_loss' in strategy_results:
            logger.info(f"[+] Avg Win/Loss: ${strategy_results['avg_win']:.2f} / ${strategy_results['avg_loss']:.2f}")
        if 'total_wins' in strategy_results and 'total_losses' in strategy_results:
            logger.info(f"[+] Wins/Losses: {strategy_results['total_wins']} / {strategy_results['total_losses']}")
        
        logger.info("=" * 60)
        
        # Guardar resultados
        config = load_config_from_yaml()
        output_dir = f"{config.storage.path}/backtest_results/{symbol}/{strategy_name}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Guardar equity curve
        equity_df = pd.DataFrame({
            'equity': strategy_results['equity_curve']
        })
        equity_df.to_csv(f"{output_dir}/equity_curve.csv")
        
        # Guardar trades
        trades_df = pd.DataFrame([
            {
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'position_size': t.position_size,
                'pnl': t.pnl,
                'position_type': t.position_type,
                'exit_reason': t.exit_reason
            }
            for t in strategy_results['trades']
        ])
        trades_df.to_csv(f"{output_dir}/trades.csv")
    
    # Mostrar comparación final entre estrategias
    logger.info(f"\n{'='*80}")
    logger.info(f"COMPARACION FINAL DE ESTRATEGIAS PARA {symbol.upper()}")
    logger.info(f"{'='*80}")
    
    # Ordenar estrategias por profit total
    sorted_strategies = sorted(results.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    
    for i, (strategy_name, result) in enumerate(sorted_strategies, 1):
        medal = "ORO" if i == 1 else "PLATA" if i == 2 else "BRONCE" if i == 3 else "POS"
        logger.info(f"{medal} #{i} {strategy_name}:")
        logger.info(f"   P&L: ${result['total_pnl']:.2f} | Win Rate: {result['win_rate']*100:.1f}% | Sharpe: {result['sharpe_ratio']:.2f}")
    
    # Identificar mejor estrategia
    best_strategy = sorted_strategies[0][0]
    best_pnl = sorted_strategies[0][1]['total_pnl']
    logger.info(f"\nMEJOR ESTRATEGIA: {best_strategy} con P&L de ${best_pnl:.2f}")
    logger.info(f"{'='*80}")
    
    return results

if __name__ == "__main__":
    print("Iniciando el programa...")
    asyncio.run(main())
    print("Programa finalizado.")