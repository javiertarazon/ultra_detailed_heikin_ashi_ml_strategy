#!/usr/bin/env python3
"""
Pipeline de Optimización Completo - UltraDetailedHeikinAshiML2 v3

Este script implementa el pipeline completo de optimización para la estrategia ML2:
1. Entrena redes neuronales avanzadas optimizadas con datos históricos
2. Optimiza parámetros de la estrategia con Optuna (versión optimizada)
3. Ejecuta un backtest final con los mejores parámetros

CARACTERÍSTICAS v3:
- Optimizado para redes neuronales avanzadas pero eficientes
- Arquitecturas MLP optimizadas para recursos limitados
- Entrenamiento con early stopping y regularización avanzada
- Optimización Optuna adaptada para parámetros de red neuronal
- Gestión de memoria optimizada para sistemas con recursos limitados

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
# from ml_trainer2 import MLTrainer2  # Importado solo cuando se necesita
from optimizacion.strategy_optimizer2 import StrategyOptimizer2  # Optimizador v2 para NN
from strategies.ultra_detailed_heikin_ashi_ml2_strategy import UltraDetailedHeikinAshiML2Strategy
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OptimizationPipeline:
    def __init__(self,
                 symbols=None,
                 timeframe="4h",
                 train_start=None,
                 train_end=None,
                 val_start=None,
                 val_end=None,
                 opt_start=None,
                 opt_end=None,
                 test_start=None,
                 test_end=None,
                 n_trials=50):
        """
        Inicializa el pipeline de optimización completo.
        
        PERÍODOS DINÁMICOS Y REALISTAS (fechas calculadas automáticamente):
        - Entrenamiento ML: 2 años atrás completo (datos históricos)
        - Validación ML: 1 año atrás H1 (validación temporal)
        - Optimización: 1 año atrás H2 (optimización parámetros)
        - Test Final: últimos 3 meses (backtest final out-of-sample)

        Args:
            symbols: Lista de símbolos a procesar
            timeframe: Timeframe para los datos
            train_start/end: Período de entrenamiento ML (si None, se calcula automáticamente)
            val_start/end: Período de validación ML (si None, se calcula automáticamente)
            opt_start/end: Período para optimización (si None, se calcula automáticamente)
            test_start/end: Período para backtest final (si None, se calcula automáticamente)
            n_trials: Número de pruebas para Optuna
        """
        from datetime import datetime, timedelta
        
        self.symbols = symbols if symbols else ["SOL/USDT"]
        self.timeframe = timeframe
        
        # 🔧 PERÍODOS DINÁMICOS Y REALISTAS
        current_date = datetime.now()
        
        if train_start is None or train_end is None:
            # Entrenamiento ML: hace 3 años a hace 2 años
            self.train_end = current_date - timedelta(days=730)  # Hace 2 años
            self.train_start = self.train_end - timedelta(days=365)  # 1 año antes
        else:
            self.train_start = train_start
            self.train_end = train_end
            
        if val_start is None or val_end is None:
            # Validación ML: después del entrenamiento con separación de 7 días
            self.val_start = self.train_end + timedelta(days=7)  # 1 semana después del entrenamiento
            self.val_end = current_date - timedelta(days=545)  # Hace 18 meses
        else:
            self.val_start = val_start
            self.val_end = val_end
            
        if opt_start is None or opt_end is None:
            # Optimización: después de validación con separación de 7 días
            self.opt_start = self.val_end + timedelta(days=7)  # 1 semana después de validación
            self.opt_end = current_date - timedelta(days=180)  # Hace 6 meses
        else:
            self.opt_start = opt_start
            self.opt_end = opt_end
            
        if test_start is None or test_end is None:
            # Test final: después de optimización con separación de 7 días
            self.test_start = self.opt_end + timedelta(days=7)  # 1 semana después de optimización
            self.test_end = current_date - timedelta(days=30)  # Hace 1 mes
        else:
            self.test_start = test_start
            self.test_end = test_end
        
        # Convertir a strings para compatibilidad
        if isinstance(self.train_start, datetime):
            self.train_start = self.train_start.strftime('%Y-%m-%d')
        if isinstance(self.train_end, datetime):
            self.train_end = self.train_end.strftime('%Y-%m-%d')
        if isinstance(self.val_start, datetime):
            self.val_start = self.val_start.strftime('%Y-%m-%d')
        if isinstance(self.val_end, datetime):
            self.val_end = self.val_end.strftime('%Y-%m-%d')
        if isinstance(self.opt_start, datetime):
            self.opt_start = self.opt_start.strftime('%Y-%m-%d')
        if isinstance(self.opt_end, datetime):
            self.opt_end = self.opt_end.strftime('%Y-%m-%d')
        if isinstance(self.test_start, datetime):
            self.test_start = self.test_start.strftime('%Y-%m-%d')
        if isinstance(self.test_end, datetime):
            self.test_end = self.test_end.strftime('%Y-%m-%d')
            
        self.n_trials = n_trials

        # Validación de períodos no solapados (CRÍTICO)
        self._validate_period_separation()
        
        # Cargar configuración
        self.config = load_config_from_yaml()
        logger.info(f"Pipeline inicializado para símbolos: {self.symbols}")
        logger.info(f"Timeframe: {timeframe}, Trials: {n_trials}")
        logger.info(f"📊 Períodos separados - Train: {train_start} a {train_end}")
        logger.info(f"📊 Val: {val_start} a {val_end}, Opt: {opt_start} a {opt_end}")
        logger.info(f"📊 Test Final: {test_start} a {test_end}")

    def _validate_period_separation(self):
        """
        Validar que los períodos estén completamente separados para evitar overfitting.
        CRÍTICO: No debe haber solapamiento entre períodos.
        """
        from datetime import datetime
        
        periods = [
            ("Train", self.train_start, self.train_end),
            ("Validation", self.val_start, self.val_end),
            ("Optimization", self.opt_start, self.opt_end),
            ("Test", self.test_start, self.test_end)
        ]
        
        # Convertir a datetime para comparación
        period_dates = []
        for name, start, end in periods:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            period_dates.append((name, start_dt, end_dt))
        
        # Verificar separación temporal
        for i, (name1, start1, end1) in enumerate(period_dates):
            for j, (name2, start2, end2) in enumerate(period_dates):
                if i != j:
                    # Verificar que no haya solapamiento
                    if not (end1 < start2 or end2 < start1):
                        raise ValueError(f"🛑 CRÍTICO: Solapamiento entre períodos {name1} y {name2}. "
                                       f"Esto causa overfitting severo. "
                                       f"{name1}: {start1.date()} a {end1.date()}, "
                                       f"{name2}: {start2.date()} a {end2.date()}")
        
        logger.info("✅ Validación de períodos: Todos los períodos están correctamente separados")

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

        # Importación lazy de MLTrainer2 para evitar KeyboardInterrupt en Python 3.13
        try:
            from optimizacion.ml_trainer2 import MLTrainer2
            logger.info("MLTrainer2 importado correctamente")
        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt durante importación de MLTrainer2")
            logger.error("Esto puede deberse a problemas de compatibilidad con Python 3.13 y sklearn")
            raise RuntimeError("No se puede importar MLTrainer2. Considere usar Python 3.11 para ML")

        # Crear instancia del entrenador ML
        trainer = MLTrainer2(symbol, self.timeframe)
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

        # Importación lazy de StrategyOptimizer2
        try:
            from optimizacion.strategy_optimizer2 import StrategyOptimizer2
            logger.info("StrategyOptimizer2 importado correctamente")
        except ImportError as e:
            logger.error(f"No se puede importar StrategyOptimizer2: {e}")
            # Fallback: devolver parámetros por defecto
            return self._get_default_parameters(symbol)

        # Configurar targets específicos para optimización con trade-offs
        optimization_targets = {
            'primary_target': {
                'metric': 'total_pnl',
                'target_value': 5000.0,  # P&L objetivo en dólares - AUMENTADO A $5,000
                'weight': 1.0
            },
            'acceptable_tradeoffs': {
                'max_drawdown': {
                    'min': 0.05,  # 5% mínimo aceptable
                    'max': 0.15,  # 15% máximo aceptable
                    'weight': 0.3
                },
                'win_rate': {
                    'min': 0.55,  # 55% mínimo aceptable
                    'max': 0.70,  # 70% máximo aceptable
                    'weight': 0.2
                }
            },
            'secondary_targets': ['profit_factor', 'sharpe_ratio'],
            'constraints': {
                'min_trades': 20,
                'max_drawdown_limit': 0.20,  # Límite absoluto
                'min_win_rate': 0.50
            }
        }

        # Crear optimizador
        optimizer = StrategyOptimizer2(
            symbol=symbol,
            timeframe=self.timeframe,
            start_date=self.opt_start,
            end_date=self.opt_end,
            n_trials=n_trials,
            optimization_targets=optimization_targets
        )

        # Ejecutar optimización
        try:
            opt_results = optimizer.run_optimization()
            logger.info(f"Optimización completada para {symbol}")
            return opt_results
        except Exception as e:
            logger.error(f"Error durante optimización: {e}")
            # Fallback: devolver parámetros por defecto
            return self._get_default_parameters(symbol)

    def _run_final_backtest(self, symbol, opt_results):
        """
        Ejecuta el backtest final con los mejores parámetros.

        Args:
            symbol (str): Símbolo a testear
            opt_results (dict): Resultados de optimización

        Returns:
            dict: Resultados del backtest
        """
        logger.info(f"Ejecutando backtest final para {symbol}")

        # Extraer mejores parámetros - manejar tanto optimización exitosa como fallback
        if isinstance(opt_results, tuple) and len(opt_results) == 2:
            # Caso exitoso: (study, pareto_trials)
            study, pareto_trials = opt_results
            if pareto_trials:
                best_trial = pareto_trials[0]  # Tomar el primer trial del frente de Pareto
                best_params = best_trial.params
                logger.info(f"Mejores parámetros encontrados: {best_params}")
            else:
                logger.warning("No se encontraron trials en el frente de Pareto, usando parámetros por defecto")
                best_params = {}
        elif isinstance(opt_results, dict) and 'best_params' in opt_results:
            # Caso fallback: parámetros por defecto
            best_params = opt_results['best_params']
            logger.info(f"Usando parámetros por defecto: {best_params}")
        else:
            logger.error(f"Formato de resultados de optimización inesperado: {type(opt_results)}")
            best_params = {}

        # Crear estrategia con parámetros optimizados
        if isinstance(self.config, dict):
            strategy_config = self.config.copy()
            strategy_config.update(best_params)
        else:
            # Es un objeto Config - convertir a dict y actualizar
            strategy_config = dataclasses.asdict(self.config)
            strategy_config.update(best_params)

        strategy = UltraDetailedHeikinAshiML2Strategy(config=strategy_config)

        # Cargar datos para backtest
        # Aquí necesitaríamos cargar los datos - por ahora simulamos
        logger.info("Cargando datos para backtest final...")

        # 🔧 CARGAR DATOS REALES (no simulados)
        try:
            # Construir nombre del archivo CSV
            symbol_clean = symbol.replace('/', '_')
            filename = f"{symbol_clean}_{self.timeframe}.csv"
            # Usar ruta absoluta basada en el directorio del script
            script_dir = Path(__file__).parent.parent  # optimizacion/ -> descarga_datos/
            csv_path = script_dir / 'data' / 'csv' / filename

            if not csv_path.exists():
                raise FileNotFoundError(f'Archivo CSV no encontrado: {csv_path}')

            # Cargar datos del CSV
            data = pd.read_csv(csv_path)
            logger.info(f'Datos reales cargados desde {csv_path}: {len(data)} registros')

            # Convertir timestamp si existe
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data = data.set_index('timestamp')
                
                # Filtrar por período de TEST FINAL (out-of-sample)
                mask = (data.index >= self.test_start) & (data.index <= self.test_end)
                data = data[mask]
                logger.info(f'Datos filtrados para período de test final: {len(data)} registros')
                logger.info(f'Período de test: {self.test_start} a {self.test_end}')

            if len(data) == 0:
                raise ValueError(f"No hay datos para el período de test final: {self.test_start} a {self.test_end}")

        except Exception as e:
            logger.error(f"Error cargando datos reales: {e}")
            logger.error("No se pueden utilizar datos sintéticos - abortando proceso")
            return {
                "error": f"No hay datos reales disponibles para {symbol} en período {self.test_start} a {self.test_end}",
                "status": "error",
                "message": "El sistema requiere datos reales para operar. Por favor asegúrate de que hay datos disponibles en SQLite o CSV antes de ejecutar la optimización."
            }

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

    # Crear pipeline
    pipeline = OptimizationPipeline(
        symbols=args.symbols,
        timeframe=args.timeframe,
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
