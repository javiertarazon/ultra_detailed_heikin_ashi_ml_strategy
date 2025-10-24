"""
Simulador de balance para Binance Testnet.

Binance Testnet tiene limitaciones: no permite fetch_balance() completo
porque falta soporte para SAPI endpoints. Este módulo proporciona un
balance simulado que se mantiene sincronizado con órdenes ejecutadas.
"""

from datetime import datetime
from typing import Dict, Optional
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TestnetBalanceSimulator:
    """Simula balance de cuenta en Binance Testnet sin acceso a SAPI"""
    
    # Balance inicial para testnet (puedes cambiar esto)
    INITIAL_BALANCE = {
        'USDT': 800.0,      # Capital inicial para trading
        'BTC': 0.0,
        'ETH': 0.0,
        'BNB': 0.0,
    }
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Inicializa el simulador de balance.
        
        Args:
            state_file: Ruta al archivo de estado para persistencia
        """
        self.balance = self.INITIAL_BALANCE.copy()
        self.state_file = state_file or Path(__file__).parent.parent / '.testnet_balance.json'
        self.locked_balance = {}  # Balance bloqueado en órdenes
        
        # Cargar estado anterior si existe
        self._load_state()
    
    def _load_state(self):
        """Carga el estado previo del balance si existe"""
        try:
            if self.state_file and Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.balance = data.get('balance', self.INITIAL_BALANCE.copy())
                    self.locked_balance = data.get('locked', {})
                    logger.info(f"Estado de balance cargado desde {self.state_file}")
        except Exception as e:
            logger.warning(f"No se pudo cargar estado anterior: {e}, usando balance inicial")
            self.balance = self.INITIAL_BALANCE.copy()
    
    def _save_state(self):
        """Guarda el estado actual del balance"""
        try:
            if self.state_file:
                with open(self.state_file, 'w') as f:
                    json.dump({
                        'balance': self.balance,
                        'locked': self.locked_balance,
                        'timestamp': datetime.now().isoformat()
                    }, f, indent=2)
        except Exception as e:
            logger.warning(f"No se pudo guardar estado: {e}")
    
    def get_balance(self) -> Dict[str, Dict[str, float]]:
        """
        Retorna estructura de balance compatible con fetch_balance().
        
        Returns:
            Dict con estructura {'free': {...}, 'used': {...}, 'total': {...}}
        """
        free_balance = self.balance.copy()
        
        # Restar locked balance de free
        for currency, locked_amount in self.locked_balance.items():
            if currency in free_balance:
                free_balance[currency] = max(0, free_balance[currency] - locked_amount)
        
        # Calcular total
        total_balance = {}
        for currency in self.balance:
            total_balance[currency] = self.balance[currency]
        
        return {
            'free': free_balance,
            'used': self.locked_balance.copy(),
            'total': total_balance
        }
    
    def deposit(self, currency: str, amount: float):
        """Simula un depósito"""
        if currency not in self.balance:
            self.balance[currency] = 0.0
        self.balance[currency] += amount
        logger.info(f"Depósito simulado: {amount} {currency}")
        self._save_state()
    
    def lock_balance(self, currency: str, amount: float):
        """Bloquea balance para una orden"""
        if currency not in self.locked_balance:
            self.locked_balance[currency] = 0.0
        self.locked_balance[currency] += amount
        logger.debug(f"Balance bloqueado: {amount} {currency}")
        self._save_state()
    
    def release_balance(self, currency: str, amount: float):
        """Libera balance de una orden cancelada"""
        if currency in self.locked_balance:
            self.locked_balance[currency] = max(0, self.locked_balance[currency] - amount)
        logger.debug(f"Balance liberado: {amount} {currency}")
        self._save_state()
    
    def execute_trade(self, base_currency: str, quote_currency: str, 
                     quantity: float, price: float, is_buy: bool):
        """
        Simula la ejecución de un trade y actualiza balances.
        
        Args:
            base_currency: Moneda base (BTC)
            quote_currency: Moneda de cotización (USDT)
            quantity: Cantidad de moneda base
            price: Precio por unidad
            is_buy: True si es compra, False si es venta
        """
        total_cost = quantity * price
        
        if is_buy:
            # Debit USDT, credit base currency
            if self.balance.get(quote_currency, 0) >= total_cost:
                self.balance[quote_currency] -= total_cost
                if base_currency not in self.balance:
                    self.balance[base_currency] = 0.0
                self.balance[base_currency] += quantity
                logger.info(f"Trade simulado BUY: {quantity} {base_currency} @ {price} {quote_currency}")
                self._save_state()
                return True
            else:
                logger.error(f"Saldo insuficiente para BUY: necesita {total_cost} {quote_currency}")
                return False
        else:
            # Debit base currency, credit USDT
            if self.balance.get(base_currency, 0) >= quantity:
                self.balance[base_currency] -= quantity
                if quote_currency not in self.balance:
                    self.balance[quote_currency] = 0.0
                self.balance[quote_currency] += total_cost
                logger.info(f"Trade simulado SELL: {quantity} {base_currency} @ {price} {quote_currency}")
                self._save_state()
                return True
            else:
                logger.error(f"Saldo insuficiente para SELL: necesita {quantity} {base_currency}")
                return False
    
    def reset_to_initial(self):
        """Resetea el balance al estado inicial"""
        self.balance = self.INITIAL_BALANCE.copy()
        self.locked_balance = {}
        logger.warning("Balance resetado al estado inicial")
        self._save_state()
