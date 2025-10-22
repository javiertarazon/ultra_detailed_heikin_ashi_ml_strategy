#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optimizador de estrategia UltraDetailedHeikinAshi con Optuna
===========================================================

Este script usa Optuna para optimizar los parámetros de la estrategia
UltraDetailedHeikinAshi buscando maximizar el profit factor, minimizar
el drawdown y maximizar el win rate.

Utiliza optimización con múltiples objetivos (Pareto front).
"""

import sys
import os
# Añadir el directorio padre (descarga_datos) al path para importar módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import pandas as pd
import numpy as np
try:
    import optuna  # type: ignore
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None
from datetime import datetime
from pathlib import Path
import json
from strategies.ultra_detailed_heikin_ashi_ml_strategy import UltraDetailedHeikinAshiMLStrategy
from typing import Dict, List, Tuple

from config.config_loader import load_config_from_yaml
# from core.downloader import AdvancedDataDownloader, download_and_cache_data  # Removido por compatibilidad Python 3.13
from core.downloader import AdvancedDataDownloader, download_and_cache_data
# from indicators.technical_indicators import TechnicalIndicators  # Removido por compatibilidad Python 3.13
from indicators.technical_indicators import TechnicalIndicators
from utils.logger import setup_logger

logger = setup_logger(__name__)

class StrategyOptimizer:
    def __init__(self, 
                 symbol="BTC/USDT", 
                 timeframe="4h", 
                 start_date="2022-01-01", 
                 end_date="2023-12-31",
                 n_trials=100,
                 study_name="ultra_detailed_heikin_ashi",
                 config=None,
                 optimization_targets=None):
        """
        Inicializa el optimizador de estrategia.
        
        Args:
            symbol (str): Símbolo a optimizar
            timeframe (str): Timeframe a usar
            start_date (str): Fecha inicial para datos
            end_date (str): Fecha final para datos
            n_trials (int): Número de pruebas Optuna
            study_name (str): Nombre del estudio
            config: Configuración del sistema
            optimization_targets (dict): Objetivos de optimización personalizados
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.n_trials = n_trials
        self.study_name = study_name
        self.config = config if config is not None else load_config_from_yaml()
        self.data = None
        
        # Targets de optimización configurables
        self.optimization_targets = optimization_targets or {
            'maximize': ['total_pnl', 'win_rate', 'profit_factor', 'sharpe_ratio'],
            'minimize': ['max_drawdown'],
            'constraints': {
                'min_trades': 20,
                'max_drawdown_limit': 0.15,
                'max_pnl_limit': 20647.89,  # 50% menos del P&L actual de $41,295.77
                'min_win_rate': 0.55
            }
        }
        
        # Carpeta para guardar resultados
        self.results_dir = Path("descarga_datos/data/optimization_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Inicializando optimización para {symbol} en {timeframe}")
        logger.info(f"Targets de optimización: {self.optimization_targets}")
        
    def download_data(self):
        """Carga los datos históricos para optimización desde SQLite o CSV"""
        logger.info(f"Cargando datos para {self.symbol} desde {self.start_date} hasta {self.end_date}")

        try:
            # OPCIÓN 1: Intentar cargar desde SQLite primero
            logger.info("🔍 Intentando cargar desde SQLite...")
            from utils.storage import DataStorage
            
            storage = DataStorage()
            table_name = f"{self.symbol.replace('/', '_')}_{self.timeframe}"
            
            # Convertir fechas a timestamps
            start_ts = int(pd.Timestamp(self.start_date).timestamp())
            end_ts = int(pd.Timestamp(self.end_date).timestamp())
            
            # Cargar datos desde SQLite
            df = storage.query_data(table_name, start_ts=start_ts, end_ts=end_ts)
            
            if df is not None and not df.empty:
                logger.info(f'✅ Datos SQLite cargados: {len(df)} registros')
                self.data = df
                logger.info(f"Datos cargados exitosamente desde SQLite: {len(self.data)} registros")
                return self.data
            
            # OPCIÓN 2: Si no hay datos en SQLite, intentar CSV
            logger.info("⚠️ SQLite vacío, intentando CSV...")
            symbol_clean = self.symbol.replace('/', '_')
            filename = f"{symbol_clean}_{self.timeframe}.csv"
            csv_path = Path(__file__).parent.parent / 'data' / 'csv' / filename

            if not csv_path.exists():
                raise FileNotFoundError(f'Archivo CSV no encontrado: {csv_path}')

            # Cargar datos del CSV
            df = pd.read_csv(csv_path)
            logger.info(f'Datos locales cargados desde {csv_path}: {len(df)} registros')

            # Convertir timestamp si existe
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
                # Filtrar por período
                mask = (df.index >= self.start_date) & (df.index <= self.end_date)
                df = df[mask]
                logger.info(f'Datos filtrados por período: {len(df)} registros')

            self.data = df

            if self.data is None or len(self.data) == 0:
                raise ValueError(f"No se pudieron cargar datos para {self.symbol}")

            logger.info(f"Datos cargados exitosamente: {len(self.data)} registros")

        except Exception as e:
            logger.error(f"Error cargando datos para {self.symbol}: {e}")
            # Si no se pudieron cargar datos, intentar descargar
            logger.info("📥 Intentando descargar datos desde exchange...")
            try:
                downloader = AdvancedDataDownloader()
                self.data = download_and_cache_data(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    start_date=self.start_date,
                    end_date=self.end_date
                )
                if self.data is None or len(self.data) == 0:
                    raise ValueError(f"No se pudieron descargar datos para {self.symbol}")
                logger.info(f"✅ Datos descargados: {len(self.data)} registros")
            except Exception as download_error:
                logger.error(f"Error descargando datos: {download_error}")
                raise ValueError(f"No se pudieron obtener datos para {self.symbol} ni desde almacenamiento ni desde exchange") from e
            
        logger.info(f"Descargados {len(self.data)} registros")
        return self.data
    
    def prepare_indicators(self):
        """Prepara los indicadores técnicos utilizando la clase TechnicalIndicators centralizada"""
        if self.data is None:
            self.download_data()

        logger.info("🔧 Usando método centralizado de indicadores técnicos")
        
        # Importar método centralizado
        from indicators.technical_indicators import TechnicalIndicators
        
        # Crear instancia y calcular todos los indicadores
        indicators = TechnicalIndicators()
        df = indicators.calculate_all_indicators_unified(self.data)
        
        # Limpiar NaN
        df = df.dropna()

        self.data = df
        logger.info(f"✅ Indicadores calculados (centralizado): {len(df)} filas válidas")

        return self.data
    
    def objective(self, trial):
        """
        Función objetivo para Optuna que devuelve tres métricas:
        - Profit Factor (a maximizar)
        - Max Drawdown (a minimizar)
        - Win Rate (a maximizar)
        """
        # Definir espacio de parámetros CRYPTO-OPTIMIZED
        params = {
            # Parámetros ML - ULTRA PERMISIVO para crypto volatilidad
            "ml_threshold": trial.suggest_float("ml_threshold", 0.15, 0.45, step=0.05),  # 🔥 CRYPTO: 0.15-0.45 (más señales)
            
            # Parámetros de indicadores - CRYPTO FLEXIBLES
            "stoch_overbought": trial.suggest_int("stoch_overbought", 60, 85, step=5),  # 🔥 Más bajo para crypto
            "stoch_oversold": trial.suggest_int("stoch_oversold", 15, 40, step=5),  # 🔥 Más alto para crypto
            "cci_threshold": trial.suggest_int("cci_threshold", 50, 250, step=10),  # 🔥 Más amplitud
            "volume_ratio_min": trial.suggest_float("volume_ratio_min", 0.2, 1.0, step=0.1),  # 🔥 Mínimo más bajo
            
            # Parámetros SAR - CRYPTO ALTA SENSIBILIDAD
            "sar_acceleration": trial.suggest_float("sar_acceleration", 0.02, 0.30, step=0.01),  # 🔥 Hasta 0.30
            "sar_maximum": trial.suggest_float("sar_maximum", 0.10, 0.35, step=0.01),  # 🔥 Rango amplio
            
            # Parámetros ATR - CRYPTO AGRESIVO (volatilidad alta)
            "atr_period": trial.suggest_int("atr_period", 7, 21, step=1),  # 🔥 Rango medio
            "stop_loss_atr_multiplier": trial.suggest_float("stop_loss_atr_multiplier", 1.5, 4.5, step=0.25),  # 🔥 Stops amplios
            "take_profit_atr_multiplier": trial.suggest_float("take_profit_atr_multiplier", 2.0, 7.0, step=0.25),  # 🔥 Targets altos
            
            # Parámetros EMA - CRYPTO TRENDS RÁPIDOS
            "ema_trend_period": trial.suggest_int("ema_trend_period", 15, 120, step=5),  # 🔥 Trends más cortos
            
            # Parámetros de gestión de riesgo - CRYPTO ULTRA AGRESIVO
            "max_drawdown": trial.suggest_float("max_drawdown", 0.03, 0.15, step=0.01),  # 🔥 Hasta 15% DD
            "max_portfolio_heat": trial.suggest_float("max_portfolio_heat", 0.08, 0.20, step=0.01),  # 🔥 Hasta 20% heat
            "max_concurrent_trades": trial.suggest_int("max_concurrent_trades", 3, 10),  # 🔥 Hasta 10 trades simultáneos
            "kelly_fraction": trial.suggest_float("kelly_fraction", 0.25, 0.80, step=0.05),  # 🔥 Kelly agresivo
            # "trailing_stop_pct": FIJADO EN 70% EN LA ESTRATEGIA - NO OPTIMIZABLE
        }
        
        # Crear instancia de la estrategia con los parámetros a optimizar
        strategy = UltraDetailedHeikinAshiMLStrategy(config=params)

        # ACTIVAR MODO OPTIMIZACIÓN para evitar re-entrenamiento ML en cada trial
        strategy._optimization_mode = True

        # Ejecutar la estrategia
        results = strategy.run(self.data, self.symbol, self.timeframe)
        
        # Obtener constraints de configuración
        constraints = self.optimization_targets.get('constraints', {})
        min_trades = constraints.get('min_trades', 20)
        max_dd_limit = constraints.get('max_drawdown_limit', 0.15)
        min_wr = constraints.get('min_win_rate', 0.55)
        
        # Si no cumple constraints, penalizar fuertemente
        if results["total_trades"] < min_trades:
            logger.warning(f"Trial penalizado: solo {results['total_trades']} trades (mínimo {min_trades})")
            return tuple([0.0] * 4)  # Devolver 4 valores para multi-objetivo
        
        # Extraer métricas
        profit_factor = results["profit_factor"] if results["profit_factor"] != float("inf") else 10.0
        max_drawdown = abs(results["max_drawdown"])
        win_rate = results["winning_trades"] / results["total_trades"] if results["total_trades"] > 0 else 0.0
        total_pnl = results.get("total_pnl", 0.0)
        pnl_return = results.get("return_pct", 0.0)
        sharpe_ratio = results.get("sharpe_ratio", 0.0)
        
        # Aplicar constraints configurables
        penalty = 1.0
        
        if max_drawdown > max_dd_limit:
            penalty *= 0.1  # Penalización más fuerte para drawdown > 15%
            logger.warning(f"Trial penalizado: DD {max_drawdown:.2%} > límite {max_dd_limit:.2%}")
        
        if win_rate < min_wr:
            penalty *= 0.7
            logger.warning(f"Trial penalizado: WR {win_rate:.2%} < mínimo {min_wr:.2%}")
        
        max_pnl_limit = constraints.get('max_pnl_limit', float('inf'))
        if total_pnl > max_pnl_limit:
            penalty *= 0.5
            logger.warning(f"Trial penalizado: P&L {total_pnl:.2f} > límite {max_pnl_limit:.2f}")
        
        # Construir retorno basado en targets configurados
        maximize_targets = self.optimization_targets.get('maximize', ['total_pnl', 'win_rate'])
        minimize_targets = self.optimization_targets.get('minimize', ['max_drawdown'])
        
        # Mapeo de métricas
        metrics_map = {
            'total_pnl': total_pnl * penalty,
            'win_rate': win_rate * penalty,
            'profit_factor': profit_factor * penalty,
            'sharpe_ratio': sharpe_ratio * penalty,
            'pnl_return': pnl_return * penalty
        }
        
        minimize_map = {
            'max_drawdown': -max_drawdown  # Negativo para minimizar
        }
        
        # Construir tupla de retorno (máximo 4 objetivos para Optuna)
        objectives = []
        for target in maximize_targets[:3]:  # Máximo 3 para maximizar
            objectives.append(metrics_map.get(target, 0.0))
        
        for target in minimize_targets[:1]:  # Máximo 1 para minimizar
            objectives.append(minimize_map.get(target, 0.0))
        
        # Asegurar que siempre devolvemos 4 valores
        while len(objectives) < 4:
            objectives.append(0.0)
        
        return tuple(objectives[:4])
    
    def run_optimization(self):
        """Ejecuta el proceso de optimización"""
        if not OPTUNA_AVAILABLE:
            logger.error("Optuna no está disponible. Instale optuna con: pip install optuna")
            raise ImportError("Optuna es requerido para la optimización. Instale con: pip install optuna")

        logger.info("Preparando datos para optimización...")
        self.prepare_indicators()

        logger.info(f"Iniciando optimización con {self.n_trials} pruebas")

        # Crear estudio multi-objetivo
        study = optuna.create_study(
            study_name=self.study_name,
            directions=["maximize", "maximize", "maximize", "maximize"],  # PF, -DD, WR, P&L
            sampler=optuna.samplers.TPESampler(seed=42)
        )

        # Ejecutar optimización
        study.optimize(self.objective, n_trials=self.n_trials)

        # Obtener mejores trials del frente de Pareto
        pareto_trials = study.best_trials

        # Guardar resultados
        self.save_results(study, pareto_trials)

        return study, pareto_trials
    
    def save_results(self, study, pareto_trials):
        """Guarda los resultados de la optimización"""
        # Crear directorio para este estudio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        study_dir = self.results_dir / f"{self.study_name}_{self.symbol.replace('/', '_')}_{timestamp}"
        study_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Guardando resultados en: {study_dir}")
        
        # Verificar que el directorio existe
        if not study_dir.exists():
            logger.error(f"No se pudo crear el directorio: {study_dir}")
            return
        
        # Guardar los trials de Pareto
        pareto_results = []
        for trial in pareto_trials:
            pareto_results.append({
                "trial_id": trial.number,
                "params": trial.params,
                "values": {
                    "profit_factor": trial.values[0],
                    "max_drawdown": -trial.values[1],  # Deshacer la negación
                    "win_rate": trial.values[2],
                    "total_pnl": trial.values[3]  # Nuevo: P&L total
                }
            })
        
        # Guardar en JSON
        with open(study_dir / "optimization_results.json", "w") as f:
            json.dump(pareto_results, f, indent=2)
            
        # Guardar informe resumen
        with open(study_dir / "optimization_report.md", "w") as f:
            f.write(f"# Reporte de Optimización para {self.symbol}\n\n")
            f.write(f"- **Timeframe:** {self.timeframe}\n")
            f.write(f"- **Periodo:** {self.start_date} a {self.end_date}\n")
            f.write(f"- **Pruebas realizadas:** {self.n_trials}\n\n")
            
            f.write("## Mejores Resultados (Frente Pareto)\n\n")
            
            for i, res in enumerate(pareto_results):
                f.write(f"### Solución {i+1}\n")
                f.write(f"- Profit Factor: {res['values']['profit_factor']:.2f}\n")
                f.write(f"- Max Drawdown: {res['values']['max_drawdown']*100:.2f}%\n")
                f.write(f"- Win Rate: {res['values']['win_rate']*100:.2f}%\n")
                f.write(f"- P&L Total: ${res['values']['total_pnl']:.2f}\n\n")
                f.write("Parámetros:\n```\n")
                for param, value in res["params"].items():
                    f.write(f"{param}: {value}\n")
                f.write("```\n\n")
                
        # Guardar mejores parámetros filtrados por objetivos REALISTAS
        filtered_results = []
        for res in pareto_results:
            # Filtrar según objetivos realistas basados en datos disponibles: 
            # PF > 0.15, DD 0.3%-2%, WR > 50%, P&L > 0.01%
            if (res["values"]["profit_factor"] > 0.15 and 
                res["values"]["max_drawdown"] >= 0.003 and res["values"]["max_drawdown"] <= 0.02 and 
                res["values"]["win_rate"] > 0.5 and
                res["values"]["total_pnl"] > 0.0001):
                filtered_results.append(res)
                
        # Si hay resultados filtrados, guardarlos
        if filtered_results:
            with open(study_dir / "filtered_results.json", "w") as f:
                json.dump(filtered_results, f, indent=2)
                
            # Guardar en informe separado
            with open(study_dir / "filtered_report.md", "w") as f:
                f.write(f"# Configuraciones Óptimas Filtradas para {self.symbol}\n\n")
                f.write("Criterios aplicados (ajustados a datos disponibles):\n")
                f.write("- Profit Factor > 0.15\n")
                f.write("- Max Drawdown entre 0.3% y 2%\n")
                f.write("- Win Rate > 50%\n")
                f.write("- P&L Total > 0.01%\n\n")
                
                for i, res in enumerate(filtered_results):
                    f.write(f"## Configuración {i+1}\n")
                    f.write(f"- Profit Factor: {res['values']['profit_factor']:.2f}\n")
                    f.write(f"- Max Drawdown: {res['values']['max_drawdown']*100:.2f}%\n")
                    f.write(f"- Win Rate: {res['values']['win_rate']*100:.2f}%\n")
                    f.write(f"- P&L Total: ${res['values']['total_pnl']:.2f}\n\n")
                    f.write("Parámetros:\n```\n")
                    for param, value in res["params"].items():
                        f.write(f"{param}: {value}\n")
                    f.write("```\n\n")
        
        logger.info(f"Resultados guardados en {study_dir}")
        
    def plot_optimization_results(self, study):
        """Genera gráficas de visualización de la optimización"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            study_dir = self.results_dir / f"{self.study_name}_{self.symbol.replace('/', '_')}_{timestamp}"
            study_dir.mkdir(parents=True, exist_ok=True)
            
            # Graficar frente de Pareto
            # fig = plot_pareto_front(study)
            # fig.write_html(str(study_dir / "pareto_front.html"))
            
            # Graficar importancia de parámetros
            # fig = plot_param_importances(study)
            # fig.write_html(str(study_dir / "param_importance.html"))
            
            logger.info(f"Gráficas guardadas en {study_dir}")
        except Exception as e:
            logger.error(f"Error al generar gráficas: {e}")

def main():
    """Función principal"""
    import argparse
    parser = argparse.ArgumentParser(description="Optimizador de estrategia UltraDetailedHeikinAshi")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Símbolo a optimizar")
    parser.add_argument("--timeframe", type=str, default="4h", help="Timeframe a usar")
    parser.add_argument("--start", type=str, default="2022-01-01", help="Fecha inicial")
    parser.add_argument("--end", type=str, default="2022-12-31", help="Fecha final")
    parser.add_argument("--trials", type=int, default=50, help="Número de pruebas")
    
    args = parser.parse_args()
    
    optimizer = StrategyOptimizer(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end,
        n_trials=args.trials
    )
    
    study, pareto_trials = optimizer.run_optimization()
    optimizer.plot_optimization_results(study)
    
    # Mostrar el mejor resultado según profit factor
    best_pf = max(pareto_trials, key=lambda t: t.values[0])
    print(f"\n Mejor resultado por profit factor:")
    print(f"- Profit Factor: {best_pf.values[0]:.2f}")
    print(f"- Max Drawdown: {-best_pf.values[1]*100:.2f}%")
    print(f"- Win Rate: {best_pf.values[2]*100:.2f}%")
    print("\nParámetros:")
    for param, value in best_pf.params.items():
        print(f"  {param}: {value}")

if __name__ == "__main__":
    main()
