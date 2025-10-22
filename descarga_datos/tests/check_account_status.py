"""
Script para consultar el estado actual de la cuenta en Binance Testnet.
Muestra balance, posiciones abiertas y últimas operaciones.
"""

import asyncio
import ccxt
import os
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Intentar cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv('descarga_datos/.env')
except ImportError:
    pass

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from descarga_datos.config.config_loader import load_config


class AccountStatusChecker:
    """Consulta y muestra el estado de la cuenta en el exchange."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el checker con la configuración del exchange.
        
        Args:
            config_path: Ruta al archivo de configuración (opcional)
        """
        if config_path is None:
            config_path = root_dir / "descarga_datos" / "config" / "config.yaml"
        
        self.config = load_config(str(config_path))
        self.exchange = self._initialize_exchange()
    
    def _initialize_exchange(self) -> ccxt.Exchange:
        """Inicializa la conexión con el exchange."""
        exchange_config = self.config['exchanges']['binance']
        
        # Obtener API keys desde variables de entorno o config
        api_key = os.getenv('BINANCE_API_KEY') or exchange_config.get('api_key', '')
        api_secret = os.getenv('BINANCE_API_SECRET') or exchange_config.get('api_secret', '')
        
        if not api_key or not api_secret:
            raise ValueError("API key y secret son requeridos. Configure BINANCE_API_KEY y BINANCE_API_SECRET en variables de entorno o en config.yaml")
        
        # Obtener configuración de sandbox
        sandbox_mode = os.getenv('SANDBOX_MODE', 'false').lower() == 'true' or exchange_config.get('sandbox', True)
        
        print(f"🔑 Usando API Key: {api_key[:10]}...")
        print(f"🧪 Modo Sandbox: {sandbox_mode}")
        
        # Configuración del exchange
        exchange_params = {
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': sandbox_mode,
            'timeout': exchange_config.get('timeout', 30000),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Forzar spot trading
            }
        }
        
        exchange = ccxt.binance(exchange_params)
        
        return exchange
    
    def get_balance(self) -> Dict:
        """Obtiene el balance actual de la cuenta."""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            print(f"❌ Error obteniendo balance: {e}")
            return {}
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Obtiene las órdenes abiertas."""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            print(f"❌ Error obteniendo órdenes abiertas: {e}")
            return []
    
    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Obtiene las últimas operaciones ejecutadas."""
        try:
            trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            print(f"❌ Error obteniendo trades recientes: {e}")
            return []
    
    def get_ticker(self, symbol: str) -> Dict:
        """Obtiene el ticker actual del símbolo."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            print(f"❌ Error obteniendo ticker: {e}")
            return {}
    
    def print_balance_summary(self, balance: Dict):
        """Imprime un resumen del balance."""
        print("\n" + "="*80)
        print("💰 BALANCE DE CUENTA")
        print("="*80)
        
        if not balance:
            print("❌ No se pudo obtener el balance")
            return
        
        # Mostrar solo monedas con balance > 0
        total_balances = balance.get('total', {})
        free_balances = balance.get('free', {})
        used_balances = balance.get('used', {})
        
        print(f"\n{'Moneda':<10} {'Total':<20} {'Disponible':<20} {'En Uso':<20}")
        print("-" * 80)
        
        for currency, total in total_balances.items():
            if total > 0.00001:  # Filtrar cantidades muy pequeñas
                free = free_balances.get(currency, 0)
                used = used_balances.get(currency, 0)
                print(f"{currency:<10} {total:<20.8f} {free:<20.8f} {used:<20.8f}")
    
    def print_open_orders(self, orders: List[Dict]):
        """Imprime las órdenes abiertas."""
        print("\n" + "="*80)
        print("📋 ÓRDENES ABIERTAS")
        print("="*80)
        
        if not orders:
            print("✅ No hay órdenes abiertas")
            return
        
        for order in orders:
            print(f"\nOrder ID: {order.get('id')}")
            print(f"  Símbolo: {order.get('symbol')}")
            print(f"  Tipo: {order.get('type')} {order.get('side').upper()}")
            print(f"  Cantidad: {order.get('amount')}")
            print(f"  Precio: {order.get('price')}")
            print(f"  Status: {order.get('status')}")
            print(f"  Fecha: {datetime.fromtimestamp(order.get('timestamp', 0)/1000)}")
    
    def print_recent_trades(self, trades: List[Dict], symbol: str, current_price: float):
        """Imprime las operaciones recientes con P&L."""
        print("\n" + "="*80)
        print(f"📊 OPERACIONES RECIENTES - {symbol}")
        print("="*80)
        
        if not trades:
            print("ℹ️ No hay trades recientes")
            return
        
        # Agrupar por orden
        orders_dict = {}
        for trade in trades:
            order_id = trade.get('order')
            if order_id not in orders_dict:
                orders_dict[order_id] = []
            orders_dict[order_id].append(trade)
        
        print(f"\nPrecio actual de {symbol}: {current_price:.2f}")
        print("\n" + "-"*80)
        
        # Rastrear posición acumulada
        total_position = 0.0
        total_cost = 0.0
        
        for order_id, order_trades in orders_dict.items():
            # Sumar todos los trades de esta orden
            total_amount = sum(t.get('amount', 0) for t in order_trades)
            total_cost_order = sum(t.get('cost', 0) for t in order_trades)
            avg_price = total_cost_order / total_amount if total_amount > 0 else 0
            
            first_trade = order_trades[0]
            side = first_trade.get('side', '').upper()
            timestamp = first_trade.get('timestamp', 0)
            date = datetime.fromtimestamp(timestamp/1000)
            
            print(f"\n🔹 Order ID: {order_id}")
            print(f"  Fecha: {date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Tipo: {side}")
            print(f"  Cantidad: {total_amount:.8f}")
            print(f"  Precio promedio: {avg_price:.2f}")
            print(f"  Costo total: {total_cost_order:.2f} USDT")
            
            # Actualizar posición acumulada
            if side == 'BUY':
                total_position += total_amount
                total_cost += total_cost_order
            elif side == 'SELL':
                # Calcular P&L de la venta
                if total_position > 0:
                    avg_buy_price = total_cost / total_position
                    pnl = (avg_price - avg_buy_price) * total_amount
                    pnl_pct = ((avg_price / avg_buy_price) - 1) * 100
                    print(f"  💵 P&L: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)")
                
                total_position -= total_amount
                if total_position > 0:
                    total_cost = (total_cost / (total_position + total_amount)) * total_position
                else:
                    total_cost = 0
        
        # Mostrar posición actual
        print("\n" + "="*80)
        print("📌 POSICIÓN ACTUAL")
        print("="*80)
        
        if total_position > 0.00001:
            avg_entry = total_cost / total_position
            current_value = total_position * current_price
            unrealized_pnl = current_value - total_cost
            unrealized_pnl_pct = ((current_price / avg_entry) - 1) * 100
            
            print(f"\n  Cantidad: {total_position:.8f} {symbol.split('/')[0]}")
            print(f"  Precio entrada promedio: {avg_entry:.2f} USDT")
            print(f"  Precio actual: {current_price:.2f} USDT")
            print(f"  Valor actual: {current_value:.2f} USDT")
            print(f"  Costo total: {total_cost:.2f} USDT")
            print(f"  P&L no realizado: {unrealized_pnl:+.2f} USDT ({unrealized_pnl_pct:+.2f}%)")
            
            # Calcular distancia a niveles típicos
            distance_to_break = ((avg_entry / current_price) - 1) * 100
            print(f"\n  📊 Análisis:")
            print(f"     • Distancia a break-even: {distance_to_break:+.2f}%")
            
            if unrealized_pnl > 0:
                print(f"     • ✅ Posición en GANANCIA")
            else:
                print(f"     • ⚠️ Posición en PÉRDIDA")
        else:
            print("\n  ℹ️ No hay posición abierta")
    
    def run_check(self, symbol: str = "BTC/USDT"):
        """Ejecuta la verificación completa del estado de la cuenta."""
        print("\n" + "="*80)
        print(f"🔍 VERIFICACIÓN DE CUENTA - Binance {'Testnet' if self.config['exchanges']['binance'].get('sandbox') else 'Production'}")
        print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Obtener datos
        balance = self.get_balance()
        open_orders = self.get_open_orders(symbol)
        ticker = self.get_ticker(symbol)
        current_price = ticker.get('last', 0)
        recent_trades = self.get_recent_trades(symbol, limit=20)
        
        # Imprimir resúmenes
        self.print_balance_summary(balance)
        self.print_open_orders(open_orders)
        self.print_recent_trades(recent_trades, symbol, current_price)
        
        print("\n" + "="*80)
        print("✅ Verificación completada")
        print("="*80 + "\n")


def main():
    """Función principal."""
    # Símbolo a consultar (puedes cambiarlo)
    symbol = "BTC/USDT"
    
    # Si se pasa un símbolo como argumento, usarlo
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    
    print(f"\n🚀 Iniciando verificación de cuenta para {symbol}...\n")
    
    try:
        checker = AccountStatusChecker()
        checker.run_check(symbol)
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
