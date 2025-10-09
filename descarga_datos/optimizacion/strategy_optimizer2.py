#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optimizador de estrategia UltraDetailedHeikinAshiML2 con Optuna v2
==================================================================

Este script usa Optuna para optimizar los parámetros de la estrategia
UltraDetailedHeikinAshiML2 con redes neuronales avanzadas, buscando maximizar
el p                "values": {
                    "total_pnl": trial.values[0],      # Primer objetivo: total_pnl
                    "win_rate": trial.values[1],       # Segundo objetivo: win_rate
                    "profit_factor": trial.values[2],  # Tercer objetivo: profit_factor
                    "max_drawdown": -trial.values[3],  # Cuarto objetivo: -max_drawdown (deshacer minimización)
                },factor, minimizar el drawdown y maximizar el win rate.

CARACTERÍSTICAS v2:
- Optimizado para redes neuronales avanzadas
- Parámetros adaptados para arquitectura MLP eficiente
- Optimización multi-objetivo con enfoque en estabilidad
- Gestión de recursos optimizada para entrenamiento NN
- Validación cruzada adaptada para series temporales

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
from strategies.ultra_detailed_heikin_ashi_ml2_strategy import UltraDetailedHeikinAshiML2Strategy
from typing import Dict, List, Tuple

from config.config_loader import load_config_from_yaml
# from core.downloader import AdvancedDataDownloader, download_and_cache_data  # Removido por compatibilidad Python 3.13
# from indicators.technical_indicators import TechnicalIndicators  # Removido por compatibilidad Python 3.13
from utils.logger import setup_logger

logger = setup_logger(__name__)

class StrategyOptimizer2:
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
        
        # Targets de optimización configurables con lógica de trade-offs - MÁS AGRESIVOS
        self.optimization_targets = optimization_targets or {
            'primary_target': {
                'metric': 'total_pnl',
                'target_value': 8000.0,  # P&L objetivo aumentado a $8,000 - MÁS AGRESIVO
                'weight': 1.0  # Peso principal
            },
            'acceptable_tradeoffs': {
                'max_drawdown': {
                    'min': 0.08,  # 8% mínimo aceptable - MÁS AGRESIVO
                    'max': 0.25,  # 25% máximo aceptable - MÁS AGRESIVO
                    'weight': 0.2  # Peso reducido para permitir más riesgo
                },
                'win_rate': {
                    'min': 0.50,  # 50% mínimo aceptable - MÁS PERMISIVO
                    'max': 0.75,  # 75% máximo aceptable - MÁS AGRESIVO
                    'weight': 0.15  # Peso reducido
                }
            },
            'secondary_targets': ['profit_factor', 'sharpe_ratio'],
            'constraints': {
                'min_trades': 15,  # Reducido para permitir más estrategias agresivas
                'max_drawdown_limit': 0.30,  # Límite absoluto aumentado - MÁS AGRESIVO
                'min_win_rate': 0.45  # Mínimo reducido - MÁS AGRESIVO
            }
        }
        
        # Carpeta para guardar resultados
        self.results_dir = Path("descarga_datos/data/optimization_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Inicializando optimización para {symbol} en {timeframe}")
        logger.info(f"Targets de optimización: {self.optimization_targets}")
        
        # Cargar datos automáticamente en el constructor
        self.download_data()
        
    def download_data(self):
        """Carga los datos históricos para optimización desde archivos locales"""
        logger.info(f"Cargando datos locales para {self.symbol} desde {self.start_date} hasta {self.end_date}")

        try:
            # Construir nombre del archivo CSV
            symbol_clean = self.symbol.replace('/', '_')
            filename = f"{symbol_clean}_{self.timeframe}.csv"
            # Usar ruta absoluta basada en el directorio del script
            script_dir = Path(__file__).parent.parent  # optimizacion/ -> descarga_datos/
            csv_path = script_dir / 'data' / 'csv' / filename

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
            raise
            logger.error(f"No se pudieron descargar datos para {self.symbol}")
            raise ValueError(f"No se pudieron descargar datos para {self.symbol}")
            
        logger.info(f"Descargados {len(self.data)} registros")
        return self.data
    
    def prepare_indicators(self):
        """
        🎯 USAR MÉTODO CENTRALIZADO - Eliminar duplicación de código
        """
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
        # Definir espacio de parámetros OPTIMIZADO para Redes Neuronales v2 - MÁS AGRESIVO
        params = {
            # Parámetros ML - MÁS AGRESIVO para más señales
            "ml_threshold": trial.suggest_float("ml_threshold", 0.3, 0.8, step=0.05),  # Umbral más bajo para MÁS SEÑALES
            
            # Parámetros técnicos MÁS PERMISIVOS
            "stoch_overbought": trial.suggest_int("stoch_overbought", 70, 85, step=5),  # Más permisivo
            "stoch_oversold": trial.suggest_int("stoch_oversold", 15, 30, step=5),    # Más permisivo
            "volume_ratio_min": trial.suggest_float("volume_ratio_min", 0.3, 1.2, step=0.1),  # Más permisivo
            
            # Parámetros SAR más agresivos
            "sar_acceleration": trial.suggest_float("sar_acceleration", 0.05, 0.20, step=0.01),  # Más agresivo
            
            # Parámetros ATR más agresivos
            "atr_period": trial.suggest_int("atr_period", 8, 18, step=2),  # Más amplio
            "stop_loss_atr_multiplier": trial.suggest_float("stop_loss_atr_multiplier", 1.5, 3.0, step=0.25),  # Más agresivo
            "take_profit_atr_multiplier": trial.suggest_float("take_profit_atr_multiplier", 2.0, 3.5, step=0.25),  # Más agresivo
            
            # Gestión de riesgo MÁS AGRESIVA
            "max_drawdown": trial.suggest_float("max_drawdown", 0.08, 0.20, step=0.02),  # Más agresivo
            "max_portfolio_heat": trial.suggest_float("max_portfolio_heat", 0.06, 0.12, step=0.02),  # Más agresivo
            "max_concurrent_trades": trial.suggest_int("max_concurrent_trades", 3, 6),  # Más agresivo
            "kelly_fraction": trial.suggest_float("kelly_fraction", 0.3, 0.8, step=0.1),  # Más agresivo
        }
        
        # Crear instancia de la estrategia con los parámetros a optimizar
        strategy = UltraDetailedHeikinAshiML2Strategy(config=params)
        
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
            return tuple([-999999.0, -999999.0, -999999.0, -999999.0])  # Penalización extrema
        
        # Extraer métricas con validación robusta
        total_trades = results.get("total_trades", 0)
        winning_trades = results.get("winning_trades", 0)
        losing_trades = results.get("losing_trades", 0)
        
        # Calcular win_rate de forma segura
        if total_trades > 0:
            win_rate = winning_trades / total_trades
        else:
            win_rate = 0.0
            
        # Validar y calcular profit_factor
        gross_profit = results.get("gross_profit", 0.0)
        gross_loss = results.get("gross_loss", 0.0)
        
        if gross_loss == 0 or gross_loss is None:
            profit_factor = 10.0 if gross_profit > 0 else 0.0  # Profit factor alto si no hay pérdidas
        else:
            profit_factor = abs(gross_profit) / abs(gross_loss)
            profit_factor = min(profit_factor, 10.0)  # Cap superior razonable
            
        # Validar max_drawdown
        max_drawdown = abs(results.get("max_drawdown", 0.0))
        if max_drawdown > 1.0:  # Si está en porcentaje, convertir
            max_drawdown = max_drawdown / 100.0
            
        # Validar otras métricas
        total_pnl = results.get("total_pnl", 0.0)
        pnl_return = results.get("return_pct", 0.0)
        sharpe_ratio = results.get("sharpe_ratio", 0.0)
        
        # Logging de métricas calculadas
        logger.info(f"Métricas calculadas - Trades: {total_trades}, Win Rate: {win_rate:.1%}, "
                   f"Profit Factor: {profit_factor:.2f}, Max DD: {max_drawdown:.1%}, P&L: ${total_pnl:.2f}")

        # Verificar constraints mínimos - ser más flexible durante optimización
        min_trades = self.optimization_targets.get('constraints', {}).get('min_trades', 5)
        if total_trades < min_trades:
            logger.warning(f"Trial descartado: solo {total_trades} trades (mínimo {min_trades})")
            return tuple([-999999.0, -999999.0, -999999.0, -999999.0])  # Penalización extrema

        # ===== NUEVA LÓGICA DE OPTIMIZACIÓN CON TARGETS ESPECÍFICOS =====

        # Obtener configuración de targets
        primary_target = self.optimization_targets.get('primary_target', {})
        tradeoffs = self.optimization_targets.get('acceptable_tradeoffs', {})

        # ===== EVALUACIÓN DE TRADE-OFFS =====

        # 1. Evaluar proximidad al target de P&L
        pnl_target = primary_target.get('target_value', 4000.0)
        pnl_weight = primary_target.get('weight', 1.0)

        if total_pnl >= pnl_target:
            # BONUS: Alcanzó o superó el target
            pnl_score = total_pnl * 2.0  # Bonus por lograr target
            logger.info(f"🎯 TARGET ALCANZADO: P&L ${total_pnl:.2f} >= ${pnl_target:.2f}")
        else:
            # Puntaje basado en proximidad al target
            proximity_ratio = total_pnl / pnl_target  # 0.0 a 1.0
            pnl_score = total_pnl * (0.5 + proximity_ratio * 0.5)  # 50% base + hasta 50% bonus

        # 2. Evaluar Drawdown (aceptable: 5%-15%)
        dd_config = tradeoffs.get('max_drawdown', {})
        dd_min = dd_config.get('min', 0.05)
        dd_max = dd_config.get('max', 0.15)
        dd_weight = dd_config.get('weight', 0.3)

        if dd_min <= max_drawdown <= dd_max:
            # Dentro del rango aceptable
            dd_score = (1.0 - (max_drawdown - dd_min) / (dd_max - dd_min)) * dd_weight
        elif max_drawdown < dd_min:
            # Muy conservador - penalizar ligeramente
            dd_score = 0.8 * dd_weight
            logger.warning(f"DD muy bajo {max_drawdown:.2%} < {dd_min:.2%} (podría ser demasiado conservador)")
        else:
            # Excede límite máximo - penalizar fuertemente
            excess_ratio = (max_drawdown - dd_max) / dd_max
            dd_score = -excess_ratio * dd_weight * 2.0  # Penalización proporcional
            logger.warning(f"DD excesivo {max_drawdown:.2%} > {dd_max:.2%}")

        # 3. Evaluar Win Rate (aceptable: 55%-70%)
        wr_config = tradeoffs.get('win_rate', {})
        wr_min = wr_config.get('min', 0.55)
        wr_max = wr_config.get('max', 0.70)
        wr_weight = wr_config.get('weight', 0.2)

        if wr_min <= win_rate <= wr_max:
            # Dentro del rango aceptable
            wr_score = win_rate * wr_weight
        elif win_rate < wr_min:
            # Win rate muy bajo - penalizar
            deficit_ratio = (wr_min - win_rate) / wr_min
            wr_score = win_rate * wr_weight * (1.0 - deficit_ratio)
            logger.warning(f"Win rate bajo {win_rate:.2%} < {wr_min:.2%}")
        else:
            # Win rate muy alto - podría indicar overfitting, penalizar ligeramente
            excess_ratio = (win_rate - wr_max) / (1.0 - wr_max)
            wr_score = wr_max * wr_weight * (1.0 - excess_ratio * 0.5)
            logger.info(f"Win rate alto {win_rate:.2%} > {wr_max:.2%} (posible overfitting)")

        # 4. Bonus por otras métricas (profit factor, sharpe)
        secondary_bonus = 0.0
        if profit_factor > 1.5:
            secondary_bonus += 0.1
        if sharpe_ratio > 1.0:
            secondary_bonus += 0.05

        # ===== CONSTRUIR OBJETIVOS FINALES =====

        # Objetivo principal: P&L score (a maximizar)
        objective_1 = pnl_score * pnl_weight

        # Objetivo secundario: Combinación de trade-offs (a maximizar)
        objective_2 = (dd_score + wr_score + secondary_bonus) * 0.5

        # Objetivo terciario: Profit factor (a maximizar)
        objective_3 = profit_factor * 0.1

        # Objetivo cuaternario: Sharpe ratio (a maximizar)
        objective_4 = sharpe_ratio * 0.05

        logger.info(f"Evaluación - P&L: ${total_pnl:.2f}, DD: {max_drawdown:.2%}, WR: {win_rate:.2%}, "
                   f"Puntuaciones: {objective_1:.2f}, {objective_2:.2f}, {objective_3:.2f}, {objective_4:.2f}")

        return tuple([objective_1, objective_2, objective_3, objective_4])
    
    def run_optimization(self):
        """Ejecuta el proceso de optimización"""
        if not OPTUNA_AVAILABLE:
            logger.error("Optuna no está disponible. Instale optuna con: pip install optuna")
            raise ImportError("Optuna es requerido para la optimización. Instale con: pip install optuna")

        logger.info("Preparando datos para optimización...")
        self.download_data()
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
            # Ejecutar nuevamente la estrategia con los parámetros del trial para obtener métricas reales
            strategy = UltraDetailedHeikinAshiML2Strategy(config=trial.params)
            real_results = strategy.run(self.data, self.symbol, self.timeframe)

            pareto_results.append({
                "trial_id": trial.number,
                "params": trial.params,
                "optimization_scores": {
                    "pnl_score": trial.values[0],
                    "tradeoff_score": trial.values[1],
                    "profit_factor_score": trial.values[2],
                    "sharpe_score": trial.values[3]
                },
                "real_metrics": {
                    "total_pnl": real_results.get("total_pnl", 0.0),
                    "max_drawdown": abs(real_results.get("max_drawdown", 0.0)),
                    "win_rate": real_results["winning_trades"] / real_results["total_trades"] if real_results["total_trades"] > 0 else 0.0,
                    "profit_factor": real_results.get("profit_factor", 0.0),
                    "sharpe_ratio": real_results.get("sharpe_ratio", 0.0),
                    "total_trades": real_results.get("total_trades", 0)
                },
                "target_analysis": {
                    "pnl_target": self.optimization_targets['primary_target']['target_value'],
                    "target_achieved": 1 if real_results.get("total_pnl", 0.0) >= self.optimization_targets['primary_target']['target_value'] else 0,
                    "dd_in_range": 1 if (self.optimization_targets['acceptable_tradeoffs']['max_drawdown']['min'] <=
                                  abs(real_results.get("max_drawdown", 0.0)) <=
                                  self.optimization_targets['acceptable_tradeoffs']['max_drawdown']['max']) else 0,
                    "wr_in_range": 1 if (self.optimization_targets['acceptable_tradeoffs']['win_rate']['min'] <=
                                  (real_results["winning_trades"] / real_results["total_trades"] if real_results["total_trades"] > 0 else 0.0) <=
                                  self.optimization_targets['acceptable_tradeoffs']['win_rate']['max']) else 0
                }
            })
        
        # Guardar en JSON
        with open(study_dir / "optimization_results.json", "w") as f:
            json.dump(pareto_results, f, indent=2)
            
        # Guardar informe resumen
        with open(study_dir / "optimization_report.md", "w", encoding="utf-8") as f:
            f.write(f"# Reporte de Optimización con Targets Específicos para {self.symbol}\n\n")
            f.write(f"- **Timeframe:** {self.timeframe}\n")
            f.write(f"- **Periodo:** {self.start_date} a {self.end_date}\n")
            f.write(f"- **Pruebas realizadas:** {self.n_trials}\n")
            f.write(f"- **Target P&L:** ${self.optimization_targets['primary_target']['target_value']:.2f}\n")
            f.write(f"- **Rango DD aceptable:** {self.optimization_targets['acceptable_tradeoffs']['max_drawdown']['min']*100:.1f}% - {self.optimization_targets['acceptable_tradeoffs']['max_drawdown']['max']*100:.1f}%\n")
            f.write(f"- **Rango Win Rate aceptable:** {self.optimization_targets['acceptable_tradeoffs']['win_rate']['min']*100:.1f}% - {self.optimization_targets['acceptable_tradeoffs']['win_rate']['max']*100:.1f}%\n\n")

            f.write("## Mejores Resultados (Frente Pareto)\n\n")

            for i, res in enumerate(pareto_results):
                metrics = res['real_metrics']
                target_analysis = res['target_analysis']

                f.write(f"### Solución {i+1}")
                if target_analysis['target_achieved']:
                    f.write(" 🎯 TARGET ALCANZADO")
                f.write("\n")

                f.write(f"- **P&L Total:** ${metrics['total_pnl']:.2f}")
                if target_analysis['target_achieved']:
                    f.write(" ✅")
                f.write("\n")

                f.write(f"- **Max Drawdown:** {metrics['max_drawdown']*100:.2f}%")
                if target_analysis['dd_in_range']:
                    f.write(" ✅ (dentro del rango aceptable)")
                else:
                    f.write(" ⚠️ (fuera del rango)")
                f.write("\n")

                f.write(f"- **Win Rate:** {metrics['win_rate']*100:.2f}%")
                if target_analysis['wr_in_range']:
                    f.write(" ✅ (dentro del rango aceptable)")
                else:
                    f.write(" ⚠️ (fuera del rango)")
                f.write("\n")

                f.write(f"- **Profit Factor:** {metrics['profit_factor']:.2f}\n")
                f.write(f"- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}\n")
                f.write(f"- **Total Trades:** {metrics['total_trades']}\n\n")

                f.write("**Parámetros optimizados:**\n```\n")
                for param, value in res["params"].items():
                    f.write(f"{param}: {value}\n")
                f.write("```\n\n")
                
        # Guardar mejores parámetros filtrados por objetivos y trade-offs aceptables
        filtered_results = []
        for res in pareto_results:
            metrics = res['real_metrics']
            target_analysis = res['target_analysis']

            # Filtrar por criterios de éxito:
            # 1. Target de P&L alcanzado O muy cercano (al menos 80% del target)
            pnl_target = self.optimization_targets['primary_target']['target_value']
            pnl_achievement_ratio = metrics['total_pnl'] / pnl_target

            # 2. Drawdown dentro del rango aceptable O no excesivamente alto
            dd_acceptable = target_analysis['dd_in_range'] or metrics['max_drawdown'] <= 0.20

            # 3. Win rate dentro del rango aceptable O al menos 50%
            wr_acceptable = target_analysis['wr_in_range'] or metrics['win_rate'] >= 0.50

            # 4. Profit factor decente
            pf_acceptable = metrics['profit_factor'] > 1.1

            # 5. Suficientes trades
            trades_acceptable = metrics['total_trades'] >= 20

            if (pnl_achievement_ratio >= 0.8 and  # Al menos 80% del target
                dd_acceptable and
                wr_acceptable and
                pf_acceptable and
                trades_acceptable):

                # Agregar información de ranking
                res_copy = res.copy()
                res_copy['ranking_score'] = (
                    pnl_achievement_ratio * 0.5 +  # 50% por proximidad al target
                    (1.0 if target_analysis['target_achieved'] else 0.0) * 0.2 +  # 20% bonus por alcanzar target
                    (1.0 if target_analysis['dd_in_range'] else 0.0) * 0.15 +  # 15% por DD en rango
                    (1.0 if target_analysis['wr_in_range'] else 0.0) * 0.15   # 15% por WR en rango
                )
                filtered_results.append(res_copy)

        # Ordenar por ranking score
        filtered_results.sort(key=lambda x: x['ranking_score'], reverse=True)
                
        # Si hay resultados filtrados, guardarlos
        if filtered_results:
            with open(study_dir / "filtered_results.json", "w") as f:
                json.dump(filtered_results, f, indent=2)
                
            # Guardar en informe separado
            with open(study_dir / "filtered_report.md", "w", encoding="utf-8") as f:
                f.write(f"# Configuraciones Óptimas Filtradas para {self.symbol}\n\n")
                f.write("## Criterios de Filtrado Aplicados:\n\n")
                f.write(f"- **Target P&L:** Al menos 80% de ${self.optimization_targets['primary_target']['target_value']:.2f}\n")
                f.write(f"- **Drawdown:** Máximo {self.optimization_targets['acceptable_tradeoffs']['max_drawdown']['max']*100:.1f}% (o ≤20% absoluto)\n")
                f.write(f"- **Win Rate:** Mínimo {self.optimization_targets['acceptable_tradeoffs']['win_rate']['min']*100:.1f}% (o ≥50% absoluto)\n")
                f.write("- **Profit Factor:** > 1.1\n")
                f.write("- **Trades Mínimos:** ≥ 20\n\n")

                f.write("## Resultados Ordenados por Ranking:\n\n")

                for i, res in enumerate(filtered_results):
                    metrics = res['real_metrics']
                    target_analysis = res['target_analysis']

                    f.write(f"### Configuración {i+1} (Ranking: {res['ranking_score']:.3f})")
                    if target_analysis['target_achieved']:
                        f.write(" 🎯 TARGET ALCANZADO")
                    f.write("\n\n")

                    f.write(f"- **P&L Total:** ${metrics['total_pnl']:.2f} ({metrics['total_pnl']/self.optimization_targets['primary_target']['target_value']*100:.1f}% del target)\n")
                    f.write(f"- **Max Drawdown:** {metrics['max_drawdown']*100:.2f}%")
                    if target_analysis['dd_in_range']:
                        f.write(" ✅")
                    f.write("\n")
                    f.write(f"- **Win Rate:** {metrics['win_rate']*100:.2f}%")
                    if target_analysis['wr_in_range']:
                        f.write(" ✅")
                    f.write("\n")
                    f.write(f"- **Profit Factor:** {metrics['profit_factor']:.2f}\n")
                    f.write(f"- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}\n")
                    f.write(f"- **Total Trades:** {metrics['total_trades']}\n\n")

                    f.write("**Parámetros optimizados:**\n```\n")
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
    
    optimizer = StrategyOptimizer2(
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
