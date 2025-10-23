"""
MÓDULO DE GESTIÓN DE RIESGO
===========================

Sistema avanzado de gestión de riesgo para trading cuantitativo.
Responsabilidades:
- Cálculo de tamaños de posición
- Gestión de stop loss y take profit dinámicos
- Monitoreo de drawdown en tiempo real
- Implementación de Kelly Criterion
- Gestión de correlaciones entre posiciones
- Límites de exposición por sector/activo
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from utils.logger import get_logger

logger = get_logger(__name__)

class AlertType(Enum):
    """Tipos de alertas de riesgo"""
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"
    SUCCESS = "success"

@dataclass
class Position:
    """Representa una posición de trading"""
    symbol: str
    direction: str  # "long" o "short"
    size: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompensationPosition(Position):
    """Posición de compensación para equilibrar riesgos"""
    related_position_id: str = ""
    compensation_factor: float = 1.0

@dataclass
class RiskMetrics:
    """Métricas de riesgo"""
    drawdown: float = 0.0
    exposure: float = 0.0
    var_95: float = 0.0  # Value at Risk (95%)
    kelly_fraction: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0

@dataclass
class RiskConfig:
    """Configuración de gestión de riesgo"""
    max_position_size: float = 0.05  # Porcentaje máximo del capital
    max_risk_per_trade: float = 0.01  # Riesgo máximo por operación
    max_drawdown: float = 0.20  # Drawdown máximo permitido
    max_leverage: float = 2.0  # Apalancamiento máximo
    max_correlation_exposure: float = 0.3  # Exposición máxima a activos correlacionados
    kelly_confidence_factor: float = 0.5  # Factor de ajuste para Kelly
    use_dynamic_sizing: bool = True  # Usar tamaño dinámico basado en volatilidad

class AdvancedRiskManager:
    """Gestor avanzado de riesgo para trading"""
    
    def __init__(self):
        self.logger = get_logger(__name__ + ".AdvancedRiskManager")
        self.trade_history = []
        self.lookback_period = 100  # Número de trades para calcular métricas
        
    def calculate_kelly_fraction(self, 
                                win_rate: float, 
                                avg_win: float, 
                                avg_loss: float,
                                confidence_factor: float = 0.25) -> float:
        """
        Calcula la fracción óptima de Kelly
        
        Args:
            win_rate: Tasa de ganancia (0-1)
            avg_win: Ganancia promedio
            avg_loss: Pérdida promedio (valor positivo)
            confidence_factor: Factor de confianza para reducir el Kelly (0-1)
            
        Returns:
            Fracción de Kelly ajustada
        """
        if avg_loss <= 0 or win_rate <= 0:
            return 0.0
            
        # Fórmula de Kelly: f = (bp - q) / b
        # b = avg_win / avg_loss (odds)
        # p = win_rate
        # q = 1 - win_rate
        
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Aplicar factor de confianza para ser más conservadores
        kelly_adjusted = kelly_fraction * confidence_factor
        
        # Limitar el Kelly máximo al 25% del capital
        kelly_final = min(max(kelly_adjusted, 0.01), 0.25)
        
        self.logger.info(f"Kelly calculado: {kelly_fraction:.3f}, Ajustado: {kelly_final:.3f}")
        
        return kelly_final
    
    def calculate_position_risk(self, entry_price: float, current_price: float, 
                               stop_loss: float, position_size: float, direction: str) -> Dict[str, Any]:
        """
        Calcula métricas de riesgo para una posición específica.
        
        Args:
            entry_price: Precio de entrada
            current_price: Precio actual
            stop_loss: Precio de stop loss
            position_size: Tamaño de la posición
            direction: Dirección ('buy' o 'sell')
            
        Returns:
            Diccionario con métricas de riesgo
        """
        try:
            # Calcular P&L actual
            if direction.lower() == 'buy':
                current_pnl_pct = (current_price / entry_price - 1) * 100
                unrealized_pnl = position_size * (current_price - entry_price)
            else:  # sell
                current_pnl_pct = (entry_price / current_price - 1) * 100
                unrealized_pnl = position_size * (entry_price - current_price)
            
            # Calcular riesgo restante (distancia al stop loss)
            if direction.lower() == 'buy':
                risk_distance = abs(current_price - stop_loss) / current_price * 100
                risk_amount = position_size * abs(current_price - stop_loss)
            else:  # sell
                risk_distance = abs(stop_loss - current_price) / current_price * 100
                risk_amount = position_size * abs(stop_loss - current_price)
            
            # Calcular ratio riesgo/recompensa actual
            if direction.lower() == 'buy':
                potential_reward = abs(current_price - entry_price) if current_price > entry_price else 0
            else:  # sell
                potential_reward = abs(entry_price - current_price) if current_price < entry_price else 0
                
            risk_reward_ratio = potential_reward / abs(current_price - stop_loss) if abs(current_price - stop_loss) > 0 else 0
            
            return {
                'current_pnl_pct': current_pnl_pct,
                'unrealized_pnl': unrealized_pnl,
                'risk_distance_pct': risk_distance,
                'risk_amount': risk_amount,
                'risk_reward_ratio': risk_reward_ratio,
                'position_exposure': position_size * current_price,
                'stop_distance_pct': abs(stop_loss - entry_price) / entry_price * 100
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando riesgo de posición: {e}")
            return {
                'current_pnl_pct': 0.0,
                'unrealized_pnl': 0.0,
                'risk_distance_pct': 0.0,
                'risk_amount': 0.0,
                'risk_reward_ratio': 0.0,
                'position_exposure': 0.0,
                'stop_distance_pct': 0.0
            }
    
    def update_trade_history(self, pnl: float, success: bool):
        """Actualiza el historial de trades para el cálculo de Kelly"""
        self.trade_history.append({
            'pnl': pnl,
            'success': success,
            'timestamp': datetime.now()
        })
        
        # Mantener solo el período de lookback
        if len(self.trade_history) > self.lookback_period:
            self.trade_history = self.trade_history[-self.lookback_period:]
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Obtiene las métricas actuales para el cálculo de Kelly"""
        if len(self.trade_history) < 10:  # Mínimo 10 trades
            return {
                'win_rate': 0.5,
                'avg_win': 0.02,
                'avg_loss': 0.01,
                'kelly_fraction': 0.01
            }
        
        wins = [t['pnl'] for t in self.trade_history if t['success']]
        losses = [abs(t['pnl']) for t in self.trade_history if not t['success']]
        
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean(wins) if wins else 0.02
        avg_loss = np.mean(losses) if losses else 0.01
        
        kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'kelly_fraction': kelly_fraction
        }

# Instancia global del gestor de riesgo
risk_manager = AdvancedRiskManager()

def get_risk_manager() -> AdvancedRiskManager:
    """Obtiene la instancia global del gestor de riesgo"""
    return risk_manager
    
def apply_risk_management(signal: Dict[str, Any], 
                         account_balance: float,
                         symbol_info: Dict[str, Any],
                         config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica las reglas de gestión de riesgo a una señal de trading.
    
    Args:
        signal: Señal de trading con dirección, precio, etc.
        account_balance: Balance actual de la cuenta
        symbol_info: Información del símbolo (tick size, lotaje mínimo, etc.)
        config: Configuración de gestión de riesgo
        
    Returns:
        Señal modificada con tamaño de posición, stop loss y take profit ajustados
    """
    logger.info(f"🔄 Iniciando aplicación de gestión de riesgo a señal: {signal['signal'] if 'signal' in signal else 'UNKNOWN'} en {signal.get('symbol', 'UNKNOWN')}")
    logger.debug(f"📊 Detalles completos de la señal: {signal}")
    
    # Obtener gestor de riesgo
    rm = get_risk_manager()
    
    # Verificar balance de cuenta
    logger.info(f"💰 Balance de cuenta disponible: {account_balance}")
    if account_balance <= 0:
        logger.error(f"❌ Balance de cuenta insuficiente: {account_balance}")
        signal['rejected'] = True
        signal['rejection_reason'] = "Balance insuficiente"
        return signal
    
    # Extraer y validar datos críticos
    entry_price = signal.get('price', 0.0)
    stop_loss_price = signal.get('stop_loss', 0.0)
    direction = signal.get('direction', 'buy')
    symbol = signal.get('symbol', '')
    
    logger.info(f"💹 Dirección: {direction}, Precio entrada: {entry_price}, Stop Loss: {stop_loss_price}")
    
    # Validar datos de entrada
    if entry_price <= 0 or stop_loss_price <= 0:
        logger.error(f"❌ Precios inválidos - Entrada: {entry_price}, Stop Loss: {stop_loss_price}")
        signal['rejected'] = True
        signal['rejection_reason'] = "Precios inválidos"
        return signal
    
    # Calcular distancia del stop loss
    if direction.lower() == 'buy':
        stop_distance_pct = abs(entry_price - stop_loss_price) / entry_price * 100
    else:
        stop_distance_pct = abs(stop_loss_price - entry_price) / entry_price * 100
    
    logger.info(f"🛑 Distancia Stop Loss: {stop_distance_pct:.2f}% ({abs(entry_price - stop_loss_price):.2f} puntos)")
    
    # Calcular tamaño de posición usando la fórmula estándar de riesgo
    # risk_amount = account_balance * risk_percent / 100
    # position_size = risk_amount / stop_loss_distance

    risk_percent = config.get('max_risk_per_trade', 1.0)  # Obtener de config
    risk_amount = account_balance * risk_percent / 100
    
    # Calcular distancia del stop loss
    if direction.lower() == 'buy':
        stop_distance = abs(entry_price - stop_loss_price)
    else:  # sell
        stop_distance = abs(stop_loss_price - entry_price)
    
    if stop_distance <= 0:
        logger.error(f"❌ Distancia de stop loss inválida: {stop_distance}")
        signal['rejected'] = True
        signal['rejection_reason'] = "Stop loss distance inválida"
        return signal
    
    # Calcular position_size
    position_size = risk_amount / stop_distance
    
    logger.info(f"� Tamaño posición calculado: {position_size} (riesgo: {risk_amount:.2f}, distancia_SL: {stop_distance:.2f})")
    
    # Verificar límites de exposición
    max_position_size = config.get('max_position_size', 0.25)
    max_position_value = account_balance * max_position_size
    position_value = position_size * entry_price
    
    if position_value > max_position_value:
        logger.warning(f"⚠️ Tamaño ajustado por límite de exposición - Original: {position_size}, Nuevo: {max_position_value/entry_price}")
        position_size = max_position_value / entry_price
    
    # Verificar límites de drawdown
    max_drawdown = config.get('max_drawdown_limit', 20.0)
    # TODO: Implementar cálculo de drawdown actual en AdvancedRiskManager
    current_drawdown = 0.0  # Placeholder hasta implementar
    logger.info(f"📉 Drawdown actual: {current_drawdown:.2f}%, Límite: {max_drawdown:.2f}%")
    
    if current_drawdown > max_drawdown:
        logger.warning(f"❌ Señal rechazada - Drawdown ({current_drawdown:.2f}%) excede límite ({max_drawdown:.2f}%)")
        signal['rejected'] = True
        signal['rejection_reason'] = f"Drawdown excede límite: {current_drawdown:.2f}%"
        return signal
    
    # Verificar correlaciones para diversificación
    # TODO: Implementar cálculo de exposición correlacionada en AdvancedRiskManager
    correlated_exposure = 0.0  # Placeholder hasta implementar
    logger.info(f"🔄 Exposición a activos correlacionados: {correlated_exposure:.2f}%")
    
    # Generar métricas detalladas de riesgo para esta operación
    risk_metrics = {
        'capital': account_balance,
        'position_size': position_size,
        'position_value': position_size * entry_price,
        'risk_amount': risk_amount,
        'risk_percent': risk_percent,
        'stop_distance_pct': stop_distance_pct,
        'max_loss': -risk_amount,
        'exposure_percent': (position_size * entry_price) / account_balance * 100,
        'correlated_exposure': correlated_exposure,
        'current_drawdown': current_drawdown
    }
    
    # Aplicar ajustes a la señal
    signal['position_size'] = position_size
    signal['risk_applied'] = True
    signal['max_risk_percent'] = risk_percent
    signal['risk_amount'] = risk_amount
    signal['risk_metrics'] = risk_metrics
    
    logger.info(f"✅ Gestión de riesgo aplicada: size={position_size}, riesgo={risk_amount:.2f} ({risk_percent}%)")
    
    return signal
