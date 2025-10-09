
#!/usr/bin/env python3
"""
Backtester avanzado para estrategias de trading
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger
from risk_management.risk_management import AdvancedRiskManager

logger = get_logger(__name__)

@dataclass
class Trade:
    """Clase para representar una operación de trading"""
    entry_time: Union[str, datetime]
    exit_time: Union[str, datetime]
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    type: str  # 'long' o 'short'
    symbol: str
    exit_reason: str = ""
    trade_id: Optional[int] = None
    commission: float = 0.0
    slippage: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class Backtester:
    """Clase principal del backtester"""
    
    def __init__(self):
        """Inicializa el backtester"""
        # Sistema de compensación integrado
        self.risk_manager = AdvancedRiskManager()
        self.compensation_enabled = True
        
class AdvancedBacktester(Backtester):
    """Versión avanzada del backtester con características adicionales"""
    
    def __init__(self):
        """Inicializa el backtester avanzado"""
        super().__init__()
        self.logger = get_logger(__name__ + ".AdvancedBacktester")
        self.metrics_enabled = True
        
        # Parámetros de capital inicial
        self.initial_capital = 10000.0  # Capital inicial por defecto
        
        # Parámetros de comisión y slippage (inicializados con valores por defecto)
        self.commission = 0.0005  # 0.05% por defecto para crypto
        self.slippage = 0.0002   # 0.02% por defecto

    def run(self, strategy, data: pd.DataFrame, symbol: str, timeframe: str = '1d') -> Dict:
        """
        Ejecuta el backtesting invocando la lógica interna de la estrategia.

        Args:
            strategy: Instancia de la estrategia a probar (debe tener un método `run`).
            data: DataFrame con datos OHLCV.
            symbol: Símbolo del activo.
            timeframe: Timeframe de los datos (ej: '1d', '1h', '4h').

        Returns:
            Diccionario con resultados del backtesting.
        """
        self.logger.info(f"Iniciando backtesting para {symbol} {timeframe} con estrategia {type(strategy).__name__}")
        # Ajuste dinámico de comisión y slippage según volatilidad (ATR/Precio)
        if 'atr' in data.columns and 'close' in data.columns:
            rel_atr = data['atr'] / data['close']
            vol_factor = rel_atr.mean()
            self.logger.info(f"Ajustando comisión y slippage por volatilidad: factor={vol_factor:.4f}")
            self.commission *= (1 + vol_factor)
            self.slippage *= (1 + vol_factor)

        try:
            # La estrategia debe tener un método `run` que devuelva un diccionario de resultados.
            if not hasattr(strategy, 'run'):
                raise AttributeError(f"La estrategia {type(strategy).__name__} no tiene un método `run`.")

            # Ejecutar la lógica de la estrategia, que se encarga de todo el proceso.
            strategy_results = strategy.run(data=data, symbol=symbol, timeframe=timeframe)
            
            self.logger.info(f"Estrategia devolvió: {type(strategy_results)}, keys: {list(strategy_results.keys()) if isinstance(strategy_results, dict) else 'N/A'}")

            # Validar que los resultados de la estrategia son un diccionario
            if not isinstance(strategy_results, dict):
                self.logger.error(f"La estrategia no devolvió un diccionario para {symbol}. Se recibió: {type(strategy_results)}")
                return self._get_empty_metrics()

            # Extraer trades y curva de equity de los resultados de la estrategia
            trades = strategy_results.get('trades', [])
            equity_curve = strategy_results.get('equity_curve', pd.Series(dtype=float))
            # Normalizar equity_curve a pd.Series si viene como lista o array
            if not isinstance(equity_curve, pd.Series):
                try:
                    equity_curve = pd.Series(equity_curve)
                except Exception as e:
                    self.logger.warning(f"Error al convertir equity_curve a Series para {symbol}: {e}")
                    equity_curve = pd.Series(dtype=float)
            # Reconstruir equity_curve si está vacía pero hay trades
            if equity_curve.empty and trades:
                balances = [self.initial_capital]
                for t in trades:
                    balances.append(balances[-1] + t.get('pnl', 0))
                equity_curve = pd.Series(balances)
            # Usar la lista de datos de compensación (dicts) en vez de cantidad
            compensation_trades_list = strategy_results.get('compensation_trades_data', [])
            if not isinstance(compensation_trades_list, list):
                # A veces 'compensation_trades' puede ser entero; ignorar
                compensation_trades_list = []

            # Si la estrategia ya calculó métricas (parciales o completas), priorizarlas
            # Desactivamos uso de métricas pre-calc por estrategia para forzar cálculo avanzado
            # has_strategy_metrics = any(k in strategy_results for k in [
            #     'total_trades', 'win_rate', 'total_pnl', 'equity_curve', 'profit_factor', 'max_drawdown'
            # ])
            # if has_strategy_metrics:
            #     strategy_results.setdefault('symbol', symbol)
            #     # Normalizar equity_curve...
            #     eq = strategy_results.get('equity_curve')
            #     try:
            #         if isinstance(eq, pd.Series):
            #             strategy_results['equity_curve'] = eq.to_list()
            #         elif hasattr(eq, 'tolist') and not isinstance(eq, list):
            #             strategy_results['equity_curve'] = eq.tolist()
            #     except Exception:
            #         pass
            #     self.logger.info(f"Ignorando métricas proporcionadas por la estrategia para {symbol}")
            #     # Continuar para cálculo de métricas avanzadas
            

            if not trades:
                self.logger.warning(f"No se generaron trades para {symbol}.")
                return self._get_empty_metrics()

            # Calcular métricas avanzadas basadas en los trades y la equity curve
            # El método `calculate_advanced_metrics` ahora recibirá los trades de compensación
            metrics = self.calculate_advanced_metrics(
                trades=trades,
                equity_curve=equity_curve,
                compensation_trades_list=compensation_trades_list,
                symbol=symbol
            )

            self.logger.info(f"[SUCCESS] Backtesting para {symbol} completado. "
                           f"Trades: {metrics.get('total_trades', 0)}, "
                           f"P&L Total: ${metrics.get('total_pnl', 0):.2f}, "
                           f"Compensaciones: {metrics.get('compensated_trades', 0)}")
            
            return metrics

        except Exception as e:
            self.logger.error(f"[CRITICAL] Error fatal durante el backtesting de {symbol}: {e}", exc_info=True)
            return self._get_empty_metrics()

    def _create_mock_result(self, symbol: str) -> Dict:
        """Crea un resultado mock básico"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'symbol': symbol
        }

    def _ensure_complete_result(self, result: Dict, symbol: str) -> Dict:
        """Asegura que el resultado tenga todos los campos necesarios"""
        required_fields = [
            'total_trades', 'winning_trades', 'win_rate',
            'total_pnl', 'max_drawdown', 'sharpe_ratio', 'symbol'
        ]

        for field in required_fields:
            if field not in result:
                if field == 'symbol':
                    result[field] = symbol
                elif field in ['total_trades', 'winning_trades']:
                    result[field] = 0
                else:
                    result[field] = 0.0

        # Calcular win_rate si no está presente pero tenemos los datos
        if result.get('win_rate', 0) == 0 and result.get('total_trades', 0) > 0:
            result['win_rate'] = (result.get('winning_trades', 0) / result['total_trades'])

        return result

    def calculate_advanced_metrics(self, trades: List[Trade], equity_curve: pd.Series, 
                                     compensation_trades_list: List[Trade], symbol: str = "UNKNOWN") -> Dict:
        """
        Calcula métricas avanzadas de rendimiento a partir de los resultados de la estrategia.

        Args:
            trades: Lista de operaciones principales.
            equity_curve: Curva de equity.
            compensation_trades_list: Lista de operaciones de compensación.
            symbol: Símbolo del activo.

        Returns:
            Diccionario con métricas avanzadas.
        """
        # Normalizar equity_curve a pd.Series si viene como lista o array
        if not isinstance(equity_curve, pd.Series):
            try:
                equity_curve = pd.Series(equity_curve)
            except Exception:
                equity_curve = pd.Series([], dtype=float)
        if not trades:
            return self._get_empty_metrics()
        # Calcular porcentaje de P&L por trade para avg_trade_pct
        for t in trades:
            entry = t.get('entry_price', 0)
            pnl = t.get('pnl', 0)
            t['pnl_percent'] = (pnl / entry * 100) if entry else 0.0

        # --- Métricas de Trades Principales ---
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        # --- Métricas de Equity y Riesgo ---
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
        sortino_ratio = self._calculate_sortino_ratio(equity_curve)

        # Calcular retorno anualizado usando media geométrica (CORRECCIÓN)
        if not equity_curve.empty and len(equity_curve) > 1:
            returns = equity_curve.pct_change().dropna()
            if len(returns) > 0:
                gmean_daily_return = np.exp(np.log(returns + 1).sum() / len(returns)) - 1
                annual_trading_days = 252
                annualized_return = (1 + gmean_daily_return) ** annual_trading_days - 1
                annual_return_pct = annualized_return * 100  # Para mantener compatibilidad
            else:
                annual_return_pct = 0.0
        else:
            annual_return_pct = 0.0

        # Calmar Ratio corregido: usa retorno anualizado, no retorno total
        calmar_ratio = annual_return_pct / max_drawdown if max_drawdown != 0 else 0

        # --- Métricas de P&L ---
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # --- Métricas de Compensación (basadas en datos reales) ---
        compensated_trades_count = len(compensation_trades_list)
        successful_compensations = len([ct for ct in compensation_trades_list if ct.get('pnl', 0) > 0])
        
        compensation_success_rate = (successful_compensations / compensated_trades_count) * 100 if compensated_trades_count > 0 else 0
        total_compensation_pnl = sum(ct.get('pnl', 0) for ct in compensation_trades_list)
        
        # El número de trades perdedores que activaron una compensación.
        # Esto asume que cada operación de compensación corresponde a una operación perdedora.
        losing_trades_that_were_compensated = compensated_trades_count
        
        compensation_ratio = (losing_trades_that_were_compensated / losing_trades) * 100 if losing_trades > 0 else 0

        # --- P&L Total Ajustado ---
        adjusted_total_pnl = total_pnl + total_compensation_pnl

        # --- Métricas Adicionales: CAGR y Volatilidad ---
        # CAGR como retorno anualizado en porcentaje
        cagr = annual_return_pct
        # Volatilidad de retornos por trade en porcentaje
        try:
            returns = equity_curve.pct_change().dropna()
            volatility = returns.std() * 100
        except Exception:
            volatility = 0.0
        # --- Recovery Factor, Average Trade Net Profit %, Risk of Ruin ---
        # Recovery Factor: Net Profit ÷ Max Drawdown
        recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else float('inf')
        # Avg Trade Net Profit %
        avg_trade_pct = (sum(t.get('pnl_percent',0) for t in trades) / total_trades) if total_trades > 0 else 0
        # Risk of Ruin (probabilidad de perder 50% del capital)
        p = win_rate  # win_rate ya está en decimal (0-1)
        avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0
        expectancy = p * avg_win - (1 - p) * avg_loss

        # Calcular riesgo de perder 50% del capital (más práctico que perder 100%)
        capital_to_lose = self.initial_capital * 0.5  # 50% del capital
        if avg_loss > 0:
            consecutive_losses_needed = capital_to_lose / avg_loss
            # Probabilidad de 'consecutive_losses_needed' losses consecutivos
            q = 1 - p  # probabilidad de perder
            risk_of_ruin = q ** consecutive_losses_needed
        else:
            risk_of_ruin = 0.0
        # Compilar resultados finales
        result = {
            'symbol': symbol,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'profit_factor': profit_factor,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'avg_win_pnl': gross_profit / winning_trades if winning_trades > 0 else 0,
            'avg_loss_pnl': -gross_loss / losing_trades if losing_trades > 0 else 0,
            'largest_win': max([t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0], default=0),
            'largest_loss': min([t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0], default=0),
            # Métricas de compensación reales
            'compensated_trades': compensated_trades_count,
            'compensation_success_rate': compensation_success_rate,
            'total_compensation_pnl': total_compensation_pnl,
            'avg_compensation_pnl': total_compensation_pnl / compensated_trades_count if compensated_trades_count > 0 else 0,
            'compensation_ratio': compensation_ratio,
            # P&L ajustado
            'adjusted_total_pnl': adjusted_total_pnl,
            # Datos para análisis posterior (compatibles con dict o dataclass)
            'trades': [t if isinstance(t, dict) else getattr(t, '__dict__', {}) for t in trades],
            'compensation_trades_data': [ct if isinstance(ct, dict) else getattr(ct, '__dict__', {}) for ct in compensation_trades_list],
            'equity_curve': equity_curve.to_list() if not equity_curve.empty else [],
            # Métricas adicionales de evaluación
            'cagr': cagr,
            'volatility': volatility,
            'recovery_factor': recovery_factor,
            'avg_trade_pct': avg_trade_pct,
            'risk_of_ruin': risk_of_ruin
        }
        return result

    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calcula el drawdown máximo como porcentaje"""
        if equity_curve.empty:
            return 0.0

        peak = equity_curve.expanding().max()
        # Evitar división por cero
        peak = peak.replace(0, np.nan).ffill().fillna(1e-8)

        # Calcular drawdown como porcentaje del pico
        drawdown_pct = (equity_curve - peak) / peak * 100

        # El drawdown máximo es el valor más negativo (pérdida máxima)
        max_drawdown_pct = drawdown_pct.min()

        # Limitar a 100% máximo (pérdida total) para valores realistas
        # Pero permitir >100% para mostrar severidad en backtesting
        return abs(max_drawdown_pct)

    def _calculate_sharpe_ratio(self, equity_curve: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calcula el ratio de Sharpe CORREGIDO usando media geométrica"""
        if len(equity_curve) < 2:
            return 0.0

        # Calcular retornos diarios
        returns = equity_curve.pct_change().dropna()
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # Media geométrica de retornos diarios (CORRECCIÓN CRÍTICA)
        gmean_daily_return = np.exp(np.log(returns + 1).sum() / len(returns)) - 1

        # Retorno anualizado (asumiendo ~252 días de trading)
        annual_trading_days = 252
        annualized_return = (1 + gmean_daily_return) ** annual_trading_days - 1

        # Volatilidad anualizada
        volatility_annualized = returns.std() * np.sqrt(annual_trading_days)

        # Sharpe Ratio correcto: (Retorno_Anualizado - Tasa_Libre) / Volatilidad_Anualizada
        if volatility_annualized == 0:
            return 0.0

        sharpe = (annualized_return - risk_free_rate) / volatility_annualized
        return sharpe

    def _calculate_sortino_ratio(self, equity_curve: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calcula el ratio de Sortino CORREGIDO usando media geométrica"""
        if len(equity_curve) < 2:
            return 0.0

        returns = equity_curve.pct_change().dropna()
        if len(returns) == 0:
            return 0.0

        # Retornos negativos para downside deviation
        negative_returns = returns[returns < 0]

        # Media geométrica de retornos diarios (CORRECCIÓN CRÍTICA)
        gmean_daily_return = np.exp(np.log(returns + 1).sum() / len(returns)) - 1

        # Retorno anualizado
        annual_trading_days = 252
        annualized_return = (1 + gmean_daily_return) ** annual_trading_days - 1

        # Downside deviation anualizada
        if len(negative_returns) == 0:
            return float('inf')  # No hay retornos negativos

        downside_deviation_daily = negative_returns.std()
        downside_deviation_annualized = downside_deviation_daily * np.sqrt(annual_trading_days)

        # Sortino Ratio correcto: (Retorno_Anualizado - Tasa_Libre) / Downside_Deviation_Anualizada
        if downside_deviation_annualized == 0:
            return float('inf')

        sortino = (annualized_return - risk_free_rate) / downside_deviation_annualized
        return sortino

    def _calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """Calcula el ratio de Calmar"""
        if max_drawdown == 0:
            return float('inf')

        return total_return / max_drawdown

    def _get_empty_metrics(self) -> Dict:
        """Retorna métricas vacías"""
        return {
            # Datos generales
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'total_pnl_percent': 0.0,
            # Riesgo y retornos
            'max_drawdown': 0.0,
            'max_drawdown_percent': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'profit_factor': 0.0,
            # P&L por trade
            'avg_trade_pnl': 0.0,
            'avg_win_pnl': 0.0,
            'avg_loss_pnl': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'avg_holding_period': 0.0,
            # === MÉTRICAS DE COMPENSACIÓN ===
            'compensated_trades': 0,
            'compensation_success_rate': 0.0,
            'total_compensation_pnl': 0.0,
            'avg_compensation_pnl': 0.0,
            'compensation_ratio': 0.0,
            'net_compensation_impact': 0.0,
            # Métricas avanzadas vacías
            'cagr': 0.0,
            'volatility': 0.0,
            'recovery_factor': 0.0,
            'avg_trade_pct': 0.0,
            'risk_of_ruin': 0.0,
            # Datos para dashboard
            'equity_curve': [],
            'trades': [],
            'compensation_trades_data': []
        }

    def _calculate_compensation_metrics(self, trades: List[Trade], symbol: str) -> Dict:
        """
        Calcula métricas específicas del sistema de compensación

        Args:
            trades: Lista de operaciones principales
            symbol: Símbolo del activo

        Returns:
            Diccionario con métricas de compensación
        """
        if not self.compensation_enabled or not trades:
            return self._get_empty_metrics()

        # Simular posiciones en el risk manager para calcular compensaciones
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        compensation_metrics = {
            'compensated_trades': 0,
            'compensation_success_rate': 0.0,
            'total_compensation_pnl': 0.0,
            'avg_compensation_pnl': 0.0,
            'compensation_ratio': 0.0,
            'net_compensation_impact': 0.0
        }

        if not losing_trades:
            return compensation_metrics

        # Simular compensaciones para trades perdedores
        total_compensation_pnl = 0.0
        successful_compensations = 0

        for trade in losing_trades:
            # Calcular tamaño de compensación (50% del trade original)
            compensation_size = abs(trade.get('pnl', 0)) * 0.5

            # Determinar resultado de compensación basado en datos reales del mercado
            # La tendencia del mercado determina el éxito de la compensación
            # Si el mercado sigue en la dirección favorable, hay mayor probabilidad de éxito
            
            # Usar el período posterior al trade para determinar probabilidad de éxito
            trade_exit_index = trade.get('exit_time', 0)
            direction = trade.get('direction', 'long')
            
            if trade_exit_index + 5 < len(data):  # Verificar que hay datos después del trade
                future_price_move = data['close'].iloc[trade_exit_index + 5] - data['close'].iloc[trade_exit_index]
                # Si el mercado se mueve favorable a la dirección original del trade
                favorable_move = (direction == 'long' and future_price_move > 0) or (direction == 'short' and future_price_move < 0)
                compensation_success = favorable_move  # Basado en datos reales, no en random

            if compensation_success:
                # Compensación exitosa recupera parte de la pérdida
                compensation_pnl = compensation_size * 0.8  # 80% de recuperación
                successful_compensations += 1
            else:
                # Compensación fallida genera pérdida adicional
                compensation_pnl = -compensation_size * 0.3  # 30% de pérdida adicional

            total_compensation_pnl += compensation_pnl

        # Calcular métricas
        total_losing_trades = len(losing_trades)
        compensation_metrics['compensated_trades'] = successful_compensations
        compensation_metrics['compensation_success_rate'] = (successful_compensations / total_losing_trades) * 100 if total_losing_trades > 0 else 0
        compensation_metrics['total_compensation_pnl'] = total_compensation_pnl
        compensation_metrics['avg_compensation_pnl'] = total_compensation_pnl / total_losing_trades if total_losing_trades > 0 else 0
        compensation_metrics['compensation_ratio'] = (successful_compensations / total_losing_trades) * 100 if total_losing_trades > 0 else 0

        # Calcular impacto neto de compensaciones
        original_total_pnl = sum(t.get('pnl', 0) for t in trades)
        net_total_pnl = original_total_pnl + total_compensation_pnl
        compensation_metrics['net_compensation_impact'] = ((net_total_pnl - original_total_pnl) / abs(original_total_pnl)) * 100 if original_total_pnl != 0 else 0

        self.logger.info(f"[COMPENSATION] {symbol}: {successful_compensations}/{total_losing_trades} trades compensados")
        self.logger.info(f"[COMPENSATION] {symbol}: P&L compensación: ${total_compensation_pnl:.2f}")
        self.logger.info(f"[COMPENSATION] {symbol}: Tasa éxito: {compensation_metrics['compensation_success_rate']:.1f}%")

        return compensation_metrics