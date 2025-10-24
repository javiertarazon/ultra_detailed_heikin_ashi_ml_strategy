#!/usr/bin/env python3
"""
Live Trading Tracker - Sistema avanzado de tracking para métricas profesionales en tiempo real.

Este módulo proporciona un sistema completo de tracking para operaciones de live trading,
calculando todas las métricas profesionales utilizadas por traders institucionales:

- Métricas básicas: Win rate, profit factor, total P&L
- Métricas de riesgo: Maximum drawdown, Sharpe ratio, Sortino ratio
- Métricas avanzadas: Expectancy, Calmar ratio, recovery factor
- Métricas de rendimiento: Return on investment, compound annual growth rate

Author: GitHub Copilot
Date: Octubre 2025
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import math
from utils.logger import setup_logger

logger = setup_logger('LiveTradingTracker')

class LiveTradingTracker:
    """
    Sistema avanzado de tracking para métricas profesionales de live trading.

    Esta clase mantiene un registro completo de todas las operaciones realizadas
    y calcula métricas profesionales en tiempo real.
    """

    def __init__(self, initial_balance: float = 100000.0):
        """
        Inicializa el tracker de live trading.

        Args:
            initial_balance: Balance inicial de la cuenta
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

        # Historial de operaciones
        self.trades_history: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # Métricas básicas
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.total_winning_pnl = 0.0
        self.total_losing_pnl = 0.0

        # Métricas de riesgo
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.peak_balance = initial_balance

        # Métricas avanzadas
        self.win_rate = 0.0
        self.profit_factor = 0.0
        self.expectancy = 0.0
        self.sharpe_ratio = 0.0
        self.sortino_ratio = 0.0
        self.calmar_ratio = 0.0
        self.recovery_factor = 0.0

        # Información temporal
        self.start_time = datetime.now()
        self.last_update = datetime.now()

        # Configuración
        self.risk_free_rate = 0.02  # 2% anual como tasa libre de riesgo
        self.save_interval = 30  # Guardar cada 30 segundos

        logger.info(f"LiveTradingTracker inicializado con balance inicial: ${initial_balance:.2f}")

    def add_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Agrega una nueva operación al tracking.

        Args:
            trade_data: Diccionario con datos de la operación
        """
        try:
            # Validar datos de la operación
            required_fields = ['symbol', 'side', 'entry_price', 'exit_price', 'quantity', 'pnl', 'open_time', 'close_time']
            for field in required_fields:
                if field not in trade_data:
                    logger.error(f"Campo requerido faltante en trade_data: {field}")
                    return

            # Calcular P&L si no está proporcionado
            if 'pnl' not in trade_data or trade_data['pnl'] is None:
                if trade_data['side'].lower() == 'buy':
                    trade_data['pnl'] = (trade_data['exit_price'] - trade_data['entry_price']) * trade_data['quantity']
                else:
                    trade_data['pnl'] = (trade_data['entry_price'] - trade_data['exit_price']) * trade_data['quantity']

            # Agregar timestamp si no existe
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.now().isoformat()

            # Agregar al historial
            self.trades_history.append(trade_data)

            # Actualizar métricas básicas
            self.total_trades += 1
            pnl = trade_data['pnl']

            if pnl > 0:
                self.winning_trades += 1
                self.total_winning_pnl += pnl
            else:
                self.losing_trades += 1
                self.total_losing_pnl += abs(pnl)

            self.total_pnl += pnl
            self.current_balance += pnl

            # Actualizar equity curve
            self._update_equity_curve(trade_data)

            # Recalcular todas las métricas
            self._calculate_all_metrics()

            # Actualizar drawdown
            self._update_drawdown()

            logger.info(f"Trade agregado: {trade_data['symbol']} {trade_data['side']} - P&L: ${pnl:.2f}")

        except Exception as e:
            logger.error(f"Error agregando trade: {e}")

    def _update_equity_curve(self, trade_data: Dict[str, Any]) -> None:
        """
        Actualiza la curva de equity con la nueva operación.
        """
        equity_point = {
            'timestamp': trade_data.get('close_time', datetime.now()),
            'balance': self.current_balance,
            'pnl': trade_data['pnl'],
            'trade_count': self.total_trades
        }
        self.equity_curve.append(equity_point)

    def _update_drawdown(self) -> None:
        """
        Actualiza el cálculo de drawdown máximo y actual.
        """
        # Actualizar peak balance
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        # Calcular drawdown actual
        if self.peak_balance > 0:
            self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance

        # Actualizar drawdown máximo
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown

    def _calculate_all_metrics(self) -> None:
        """
        Calcula todas las métricas profesionales.
        """
        if self.total_trades == 0:
            return

        # Win Rate
        total_closed = self.winning_trades + self.losing_trades
        if total_closed > 0:
            self.win_rate = self.winning_trades / total_closed

        # Profit Factor
        if self.total_losing_pnl > 0:
            self.profit_factor = self.total_winning_pnl / self.total_losing_pnl
        else:
            self.profit_factor = float('inf') if self.total_winning_pnl > 0 else 0.0

        # Expectancy
        if total_closed > 0:
            avg_win = self.total_winning_pnl / self.winning_trades if self.winning_trades > 0 else 0
            avg_loss = self.total_losing_pnl / self.losing_trades if self.losing_trades > 0 else 0
            win_prob = self.win_rate
            loss_prob = 1 - win_prob
            self.expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)

        # Sharpe Ratio (simplificado - requiere más datos históricos)
        self._calculate_sharpe_ratio()

        # Sortino Ratio
        self._calculate_sortino_ratio()

        # Calmar Ratio
        self._calculate_calmar_ratio()

        # Recovery Factor
        self._calculate_recovery_factor()

    def _calculate_sharpe_ratio(self) -> None:
        """
        Calcula el Sharpe Ratio basado en la volatilidad de retornos.
        """
        if len(self.equity_curve) < 2:
            self.sharpe_ratio = 0.0
            return

        # Calcular retornos diarios
        balances = [point['balance'] for point in self.equity_curve]
        returns = []

        for i in range(1, len(balances)):
            if balances[i-1] > 0:
                ret = (balances[i] - balances[i-1]) / balances[i-1]
                returns.append(ret)

        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return > 0:
                # Sharpe ratio anualizado (asumiendo datos diarios)
                self.sharpe_ratio = (avg_return - self.risk_free_rate/365) / std_return * np.sqrt(365)
            else:
                self.sharpe_ratio = 0.0
        else:
            self.sharpe_ratio = 0.0

    def _calculate_sortino_ratio(self) -> None:
        """
        Calcula el Sortino Ratio (solo penaliza volatilidad a la baja).
        """
        if len(self.equity_curve) < 2:
            self.sortino_ratio = 0.0
            return

        balances = [point['balance'] for point in self.equity_curve]
        returns = []

        for i in range(1, len(balances)):
            if balances[i-1] > 0:
                ret = (balances[i] - balances[i-1]) / balances[i-1]
                returns.append(ret)

        if len(returns) > 1:
            avg_return = np.mean(returns)
            # Solo volatilidad de retornos negativos
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    self.sortino_ratio = (avg_return - self.risk_free_rate/365) / downside_std * np.sqrt(365)
                else:
                    self.sortino_ratio = 0.0
            else:
                self.sortino_ratio = float('inf')  # No hay retornos negativos
        else:
            self.sortino_ratio = 0.0

    def _calculate_calmar_ratio(self) -> None:
        """
        Calcula el Calmar Ratio (return anualizado / max drawdown).
        """
        if self.max_drawdown <= 0:
            self.calmar_ratio = 0.0
            return

        # Calcular tiempo de trading en años
        runtime_years = (datetime.now() - self.start_time).total_seconds() / (365 * 24 * 3600)
        if runtime_years <= 0:
            runtime_years = 1/365  # Mínimo 1 día

        # Return total anualizado
        total_return = (self.current_balance - self.initial_balance) / self.initial_balance
        annualized_return = total_return / runtime_years

        self.calmar_ratio = annualized_return / self.max_drawdown

    def _calculate_recovery_factor(self) -> None:
        """
        Calcula el Recovery Factor (total P&L / max drawdown).
        """
        if self.max_drawdown <= 0:
            self.recovery_factor = 0.0
        else:
            self.recovery_factor = abs(self.total_pnl) / (self.max_drawdown * self.initial_balance)

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Retorna todas las métricas profesionales calculadas.

        Returns:
            Diccionario con todas las métricas
        """
        runtime_minutes = (datetime.now() - self.start_time).total_seconds() / 60

        return {
            # Métricas básicas
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_winning_pnl': self.total_winning_pnl,
            'total_losing_pnl': self.total_losing_pnl,

            # Balance y capital
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,

            # Métricas de riesgo
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,

            # Métricas avanzadas
            'profit_factor': self.profit_factor,
            'expectancy': self.expectancy,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'recovery_factor': self.recovery_factor,

            # Información temporal
            'start_time': self.start_time.isoformat(),
            'runtime_minutes': runtime_minutes,
            'last_update': self.last_update.isoformat(),

            # Rendimiento porcentual
            'total_return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'avg_trade_pnl': self.total_pnl / self.total_trades if self.total_trades > 0 else 0,

            # Estadísticas adicionales
            'largest_win': max([t['pnl'] for t in self.trades_history if t['pnl'] > 0], default=0),
            'largest_loss': min([t['pnl'] for t in self.trades_history if t['pnl'] < 0], default=0),
            'avg_win': self.total_winning_pnl / self.winning_trades if self.winning_trades > 0 else 0,
            'avg_loss': self.total_losing_pnl / self.losing_trades if self.losing_trades > 0 else 0,
        }

    def save_to_file(self, filepath: Optional[str] = None) -> None:
        """
        Guarda el estado completo del tracker a un archivo JSON.

        Args:
            filepath: Ruta del archivo (opcional, usa timestamp si no se proporciona)
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"live_trading_metrics_{timestamp}.json"

        # Crear directorio si no existe
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        data = {
            'metrics': self.get_comprehensive_metrics(),
            'trades_history': self.trades_history,
            'equity_curve': self.equity_curve,
            'last_save': datetime.now().isoformat()
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Métricas guardadas en: {filepath}")
        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")

    def load_from_file(self, filepath: str) -> bool:
        """
        Carga el estado del tracker desde un archivo JSON.

        Args:
            filepath: Ruta del archivo a cargar

        Returns:
            True si la carga fue exitosa, False en caso contrario
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restaurar métricas
            metrics = data.get('metrics', {})
            self.initial_balance = metrics.get('initial_balance', 100000.0)
            self.current_balance = metrics.get('current_balance', self.initial_balance)
            self.peak_balance = metrics.get('peak_balance', self.initial_balance)
            self.total_trades = metrics.get('total_trades', 0)
            self.winning_trades = metrics.get('winning_trades', 0)
            self.losing_trades = metrics.get('losing_trades', 0)
            self.total_pnl = metrics.get('total_pnl', 0.0)
            self.total_winning_pnl = metrics.get('total_winning_pnl', 0.0)
            self.total_losing_pnl = metrics.get('total_losing_pnl', 0.0)
            self.max_drawdown = metrics.get('max_drawdown', 0.0)
            self.current_drawdown = metrics.get('current_drawdown', 0.0)

            # Restaurar historiales
            self.trades_history = data.get('trades_history', [])
            self.equity_curve = data.get('equity_curve', [])

            # Recalcular métricas
            self._calculate_all_metrics()

            logger.info(f"Estado cargado desde: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
            return False

    def should_save(self) -> bool:
        """
        Determina si es momento de guardar el estado basado en el intervalo configurado.

        Returns:
            True si debe guardar, False en caso contrario
        """
        time_since_last_save = (datetime.now() - self.last_update).total_seconds()
        return time_since_last_save >= self.save_interval

    def update_timestamp(self) -> None:
        """
        Actualiza el timestamp de última modificación.
        """
        self.last_update = datetime.now()