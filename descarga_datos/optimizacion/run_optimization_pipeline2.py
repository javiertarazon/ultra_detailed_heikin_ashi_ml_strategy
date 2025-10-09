#!/usr/bin/env python3
"""
Pipeline de Optimización Completo para UltraDetailedHeikinAshi

Este script implementa el pipeline completo de optimización:
1. Entrena modelos ML con datos históricos
2. Optimiza parámetros de la estrategia con Optuna
3. Ejecuta un backtest final con los mejores parámetros

Pasos:
- Entrenamiento ML: 2024 H1 (train), 2024 H2 (validation)
- Optimización: 2024 completo (datos específicos de optimización)
- Backtest final: Mejor configuración en todo 2024
"""

import sys, os
# Añadir el directorio padre (descarga_datos) al path para importar módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple
import dataclasses

from config.config_loader import load_config_from_yaml
# Importaciones lazy para evitar KeyboardInterrupt en Python 3.13
# from ml_trainer import MLTrainer  # Importado solo cuando se necesita
# from strategy_optimizer import StrategyOptimizer  # Importado solo cuando se necesita
from strategies.ultra_detailed_heikin_ashi_ml_strategy import UltraDetailedHeikinAshiMLStrategy
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OptimizationPipeline:
    def __init__(self,
                 symbols=None,
                 timeframe="4h",
                 train_start="2022-01-01",
                 train_end="2023-06-30",
                 val_start="2022-07-01",
                 val_end="2023-12-31",
                 opt_start="2022-01-01",
                 opt_end="2023-12-31",
                 n_trials=50):
        """
        Inicializa el pipeline de optimización completo.

        Args:
            symbols: Lista de símbolos a procesar
            timeframe: Timeframe para los datos
            train_start/end: Período de entrenamiento ML
            val_start/end: Período de validación ML
            opt_start/end: Período para optimización
            n_trials: Número de pruebas para Optuna
        """
        self.symbols = symbols if symbols else ["BTC/USDT"]
        self.timeframe = timeframe
        self.train_start = train_start
        self.train_end = train_end
        self.val_start = val_start
        self.val_end = val_end
        self.opt_start = opt_start
        self.opt_end = opt_end
        self.n_trials = n_trials

        # Cargar configuración
        self.config = load_config_from_yaml()
        logger.info(f"Pipeline inicializado para símbolos: {self.symbols}")
        logger.info(f"Timeframe: {timeframe}, Trials: {n_trials}")

    async def run_complete_pipeline(self):
        """
        Ejecuta el pipeline completo de optimización para todos los símbolos.
        """
        start_time = time.time()
        pipeline_results = {}

        for symbol in self.symbols:
            try:
                symbol_start = time.time()
                logger.info(f"=== INICIANDO PIPELINE PARA {symbol} ===")

                # Paso 1: Entrenamiento ML (opcional en modo seguro)
                await self._train_ml_models(symbol)

                # Paso 2: Optimización de parámetros
                opt_results = self._optimize_strategy_parameters(symbol)

                # Paso 3: Backtest final con mejores parámetros
                backtest_results = self._run_final_backtest(symbol, opt_results)

                # Guardar resultados de este símbolo
                pipeline_results[symbol] = {
                    "optimization_results": opt_results,
                    "backtest_results": backtest_results,
                    "execution_time": time.time() - symbol_start
                }

                logger.info(f"Pipeline para {symbol} completado en {(time.time() - symbol_start)/60:.2f} minutos")

            except Exception as e:
                logger.error(f"Error en el pipeline para {symbol}: {e}")
                import traceback
                traceback.print_exc()

        # Guardar resultados completos
        self._save_pipeline_results(pipeline_results)

        total_time = time.time() - start_time
        logger.info(f"Pipeline completo finalizado en {total_time/60:.2f} minutos")

        return pipeline_results

    async def _train_ml_models(self, symbol):
        """
        Entrena los modelos ML para el símbolo dado.

        Args:
            symbol (str): Símbolo a entrenar
        """
        logger.info(f"Iniciando entrenamiento ML para {symbol}")

        # Verificar si está en modo seguro (Python 3.13 compatibility)
        safe_mode = False
        if hasattr(self.config, 'ml_training'):
            ml_training = self.config.ml_training
            if hasattr(ml_training, 'safe_mode'):
                safe_mode = ml_training.safe_mode
        
        if safe_mode:
            logger.info("🛡️ MODO SEGURO ACTIVADO - Saltando entrenamiento ML")
            logger.info("Los modelos ML existentes serán usados si están disponibles")
            return {
                'ml_training_completed': False,
                'safe_mode': True,
                'message': 'Modo seguro activado - usando modelos existentes o sin ML'
            }

        # Importación lazy de MLTrainer para evitar KeyboardInterrupt en Python 3.13
        try:
            from .ml_trainer import MLTrainer
            logger.info("MLTrainer importado correctamente")
        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt durante importación de MLTrainer")
            logger.error("Esto puede deberse a problemas de compatibilidad con Python 3.13 y sklearn")
            raise RuntimeError("No se puede importar MLTrainer. Considere usar Python 3.11 para ML")

        # Crear instancia del entrenador ML
        trainer = MLTrainer(symbol, self.timeframe)
        trainer.train_start = self.train_start
        trainer.train_end = self.train_end
        trainer.val_start = self.val_start
        trainer.val_end = self.val_end

        # Ejecutar entrenamiento
        try:
            training_results = await trainer.run()
            logger.info(f"Entrenamiento ML completado para {symbol}")
            return training_results
        except Exception as e:
            logger.error(f"Error durante entrenamiento ML: {e}")
            raise

    def _optimize_strategy_parameters(self, symbol, n_trials=None):
        """
        Optimiza los parámetros de la estrategia usando Optuna.

        Args:
            symbol (str): Símbolo a optimizar
            n_trials (int): Número de trials (opcional)

        Returns:
            dict: Resultados de la optimización
        """
        if n_trials is None:
            n_trials = self.n_trials

        logger.info(f"Iniciando optimización de parámetros para {symbol} con {n_trials} trials")

        # Importación lazy de StrategyOptimizer
        try:
            from .strategy_optimizer import StrategyOptimizer
            logger.info("StrategyOptimizer importado correctamente")
        except ImportError as e:
            logger.error(f"No se puede importar StrategyOptimizer: {e}")
            # Fallback: devolver parámetros por defecto en formato correcto (None, [])
            return None, []

        # Crear optimizador
        optimizer = StrategyOptimizer(
            symbol=symbol,
            timeframe=self.timeframe,
            start_date=self.opt_start,
            end_date=self.opt_end,
            n_trials=n_trials
        )

        # Ejecutar optimización
        try:
            opt_results = optimizer.run_optimization()
            logger.info(f"Optimización completada para {symbol}")
            return opt_results
        except Exception as e:
            logger.error(f"Error durante optimización: {e}")
            # Fallback: devolver parámetros por defecto en formato correcto
            return None, []

    def _run_final_backtest(self, symbol, opt_results):
        """
        Ejecuta el backtest final con los mejores parámetros.

        Args:
            symbol (str): Símbolo a testear
            opt_results (tuple): Tupla (study, pareto_trials) de optimización

        Returns:
            dict: Resultados del backtest
        """
        logger.info(f"Ejecutando backtest final para {symbol}")

        # Verificar que opt_results sea válido
        if opt_results is None or not isinstance(opt_results, tuple):
            logger.error(f"opt_results inválido: {opt_results}")
            return {
                "error": "No se pudo realizar optimización - parámetros inválidos",
                "symbol": symbol
            }

        # Extraer mejores parámetros del frente de Pareto
        study, pareto_trials = opt_results
        if pareto_trials and len(pareto_trials) > 0:
            best_trial = pareto_trials[0]  # Tomar el primer trial del frente de Pareto
            best_params = best_trial.params
            logger.info(f"Mejores parámetros encontrados: {best_params}")
        else:
            logger.warning("No se encontraron trials en el frente de Pareto, usando parámetros por defecto")
            best_params = {}

        # Crear estrategia con parámetros optimizados
        if isinstance(self.config, dict):
            strategy_config = self.config.copy()
            strategy_config.update(best_params)
        else:
            # Es un objeto Config - convertir a dict y actualizar
            strategy_config = dataclasses.asdict(self.config)
            strategy_config.update(best_params)

        strategy = UltraDetailedHeikinAshiMLStrategy(config=strategy_config)

        # ACTIVAR MODO OPTIMIZACIÓN para evitar re-entrenamiento ML durante backtest final
        strategy._optimization_mode = True

        # Cargar datos para backtest desde SQLite (SOLO DATOS REALES)
        logger.info("Cargando datos para backtest final desde base de datos...")

        # Importar StorageManager para acceder a datos reales
        from utils.storage import DataStorage
        
        # Crear conexión a la base de datos
        storage = DataStorage(db_path=f"{self.config.storage.path}/data.db")
        
        # Convertir fechas a timestamps
        start_ts = int(pd.Timestamp(self.opt_start).timestamp()) if self.opt_start else None
        end_ts = int(pd.Timestamp(self.opt_end).timestamp()) if self.opt_end else None
        
        # Tabla para el símbolo y timeframe
        table_name = f"{symbol.replace('/', '_')}_{self.timeframe}"
        
        # Cargar datos reales desde SQLite
        data = storage.query_data(table_name, start_ts=start_ts, end_ts=end_ts)
        
        if data is None or data.empty:
            logger.error(f"❌ No se encontraron datos reales para {symbol} en el período de optimización")
            return {
                "error": f"No hay datos disponibles para {symbol} en período {self.opt_start} a {self.opt_end}",
                "status": "error"
            }

        # Asegurar high >= max(open, close) y low <= min(open, close)
        data['high'] = np.maximum(data[['open', 'close']].max(axis=1), data['high'])
        data['low'] = np.minimum(data[['open', 'close']].min(axis=1), data['low'])

        # Ejecutar backtest
        try:
            backtest_results = strategy.run(data, symbol, self.timeframe)
            logger.info(f"Backtest final completado para {symbol}")
            return backtest_results
        except Exception as e:
            logger.error(f"Error durante backtest final: {e}")
            raise

    def _get_default_parameters(self, symbol):
        """
        Devuelve parámetros por defecto cuando la optimización falla.

        Args:
            symbol (str): Símbolo

        Returns:
            dict: Parámetros por defecto
        """
        return {
            'best_params': {
                'ml_threshold': 0.7,
                'stoch_overbought': 85,
                'stoch_oversold': 15
            },
            'best_value': 0.0,
            'optimization_completed': False,
            'fallback': True
        }

    def _save_pipeline_results(self, results):
        """
        Guarda los resultados del pipeline completo.

        Args:
            results (dict): Resultados a guardar
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path("descarga_datos/data/optimization_pipeline")
        results_dir.mkdir(parents=True, exist_ok=True)

        results_file = results_dir / f"pipeline_complete_{timestamp}.json"

        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Resultados del pipeline guardados en: {results_file}")
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

    def run_quick_test(self):
        """
        Ejecuta un test rápido del pipeline con 5 trials por símbolo
        """
        logger.info("🚀 Iniciando test rápido del pipeline de optimización")

        start_time = time.time()
        test_results = {}

        for symbol in self.symbols:
            logger.info(f"Test rápido para {symbol}")
            symbol_start = time.time()

            try:
                # Paso 1: Entrenamiento ML rápido
                self._train_ml_models(symbol)

                # Paso 2: Optimización con solo 5 trials
                opt_results = self._optimize_strategy_parameters(symbol, n_trials=5)

                # Paso 3: Backtest final con mejores parámetros
                backtest_results = self._run_final_backtest(symbol, opt_results)

                test_results[symbol] = {
                    "optimization_results": opt_results,
                    "backtest_results": backtest_results,
                    "execution_time": time.time() - symbol_start
                }

                logger.info(f"Test rápido para {symbol} completado en {(time.time() - symbol_start)/60:.2f} minutos")

            except Exception as e:
                logger.error(f"Error en test rápido para {symbol}: {e}")
                import traceback
                traceback.print_exc()

        # Guardar resultados del test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path("descarga_datos/data/optimization_pipeline")
        results_dir.mkdir(parents=True, exist_ok=True)

        test_file = results_dir / f"quick_test_{timestamp}.json"

        try:
            with open(test_file, 'w') as f:
                json.dump(test_results, f, indent=2, default=str)
            logger.info(f"Resultados del test rápido guardados en: {test_file}")
        except Exception as e:
            logger.error(f"Error guardando resultados del test: {e}")

        total_time = time.time() - start_time
        logger.info(f"Test rápido completado en {total_time/60:.2f} minutos")

        return test_results


async def main():
    """
    Función principal para ejecutar el pipeline desde línea de comandos.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Pipeline de Optimización Completo')
    parser.add_argument('--symbols', nargs='+', default=['SOL/USDT'],
                        help='Símbolos a optimizar')
    parser.add_argument('--timeframe', default='4h',
                        help='Timeframe para los datos')
    parser.add_argument('--trials', type=int, default=50,
                        help='Número de trials para optimización')
    parser.add_argument('--quick-test', action='store_true',
                        help='Ejecutar test rápido con 5 trials')

    args = parser.parse_args()

    pipeline = OptimizationPipeline(
        symbols=args.symbols,
        timeframe=args.timeframe,
        train_start="2025-01-01",
        train_end="2025-06-30",
        val_start="2025-07-01",
        val_end="2025-08-31",
        opt_start="2025-01-01",
        opt_end="2025-08-31",
        n_trials=args.trials
    )

    # Ejecutar pipeline
    try:
        if args.quick_test:
            results = pipeline.run_quick_test()
        else:
            results = await pipeline.run_complete_pipeline()

        logger.info("Pipeline ejecutado exitosamente")
        return results

    except Exception as e:
        logger.error(f"Error ejecutando pipeline: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
