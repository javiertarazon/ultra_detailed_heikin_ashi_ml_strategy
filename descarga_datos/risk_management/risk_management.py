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
    logger.info(f"Aplicando gestión de riesgo a señal: {signal}")
    
    # Obtener gestor de riesgo
    rm = get_risk_manager()
    
    # Calcular tamaño de posición
    risk_percent = config.get('risk_percent', 1.0)
    position_size = rm.calculate_position_size(
        direction=signal.get('direction', 'buy'),
        entry_price=signal.get('price', 0.0),
        stop_loss_price=signal.get('stop_loss', 0.0),
        account_balance=account_balance,
        risk_percent=risk_percent,
        symbol=signal.get('symbol', ''),
        symbol_info=symbol_info
    )
    
    # Verificar límites de drawdown
    max_drawdown = config.get('max_drawdown_limit', 20.0)
    if rm.current_drawdown > max_drawdown:
        logger.warning(f"Señal rechazada - Drawdown ({rm.current_drawdown}%) excede límite ({max_drawdown}%)")
        signal['rejected'] = True
        signal['rejection_reason'] = f"Drawdown excede límite: {rm.current_drawdown}%"
        return signal
        
    # Aplicar ajustes a la señal
    signal['position_size'] = position_size
    signal['risk_applied'] = True
    signal['max_risk_percent'] = risk_percent
    
    logger.info(f"Gestión de riesgo aplicada: size={position_size}, risk={risk_percent}%")
    
    return signal
