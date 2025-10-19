#!/usr/bin/env python3
"""
Script para optimización con datos de mercado LIVE
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Agregar directorio descarga_datos al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'descarga_datos'))

# Importaciones básicas que no dependen de configuración completa
try:
    from core.ccxt_live_data import CCXTLiveDataProvider
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("⚠️ CCXT no disponible")

class SimpleLiveOptimizer:
    """Optimizador simple que usa datos live directamente"""

    def __init__(self):
        self.symbol = 'BTC/USDT'
        self.timeframe = '15m'
        self.live_data_provider = None

    async def initialize_provider(self):
        """Inicializar proveedor de datos live con configuración mínima"""
        if not CCXT_AVAILABLE:
            print("❌ CCXT no disponible")
            return False

        try:
            # Usar CCXT directamente para datos públicos
            import ccxt
            self.exchange = ccxt.binance({
                'timeout': 30000,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                },
            })

            print("✅ Exchange Binance inicializado para datos públicos")
            return True

        except Exception as e:
            print(f"❌ Error inicializando exchange: {e}")
            return False

    async def download_live_data(self, bars=300):
        """Descargar datos live usando CCXT directamente"""
        try:
            print(f"📥 Descargando {bars} barras live de {self.symbol} {self.timeframe}...")

            # Obtener datos OHLCV directamente
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=bars)

            if not ohlcv or len(ohlcv) < 100:
                print(f"❌ Datos insuficientes: {len(ohlcv) if ohlcv else 0} barras")
                return None

            # Convertir a DataFrame
            import pandas as pd
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            print(f"✅ Datos descargados: {len(df)} barras")
            print(f"📅 Período: {df.index[0]} → {df.index[-1]}")

            # Calcular indicadores básicos
            df = self._calculate_basic_indicators(df)

            # Guardar datos
            data_path = Path("data/live_optimization_data")
            data_path.mkdir(exist_ok=True)

            filename = f"{self.symbol.replace('/', '_')}_{self.timeframe}_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(data_path / filename)
            print(f"💾 Datos guardados en: {data_path / filename}")

            return df

        except Exception as e:
            print(f"❌ Error descargando datos: {e}")
            return None

    def _calculate_basic_indicators(self, df):
        """Calcular indicadores básicos para análisis"""
        try:
            # Calcular retornos
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

            # Calcular volatilidad (ATR aproximado)
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['atr'] = df['tr'].rolling(window=14).mean()

            # Calcular RSI aproximado
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # Calcular volumen ratio
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

            return df

        except Exception as e:
            print(f"⚠️ Error calculando indicadores: {e}")
            return df

    def analyze_live_data(self, data):
        """Análisis básico de los datos live y cálculo de parámetros optimizados"""
        try:
            print("\n📊 ANÁLISIS DE DATOS LIVE")
            print("=" * 40)

            # Estadísticas básicas
            current_price = data['close'].iloc[-1]
            avg_volume = data['volume'].mean()
            current_atr = data['atr'].iloc[-1] if 'atr' in data.columns else data['tr'].rolling(14).mean().iloc[-1]
            current_rsi = data['rsi'].iloc[-1] if 'rsi' in data.columns else 50

            print(f"Precio actual: ${current_price:.2f}")
            print(f"Volumen promedio: {avg_volume:.2f}")
            print(f"Volatilidad (ATR): {current_atr:.4f}")
            print(f"RSI actual: {current_rsi:.2f}")

            # Análisis de tendencias
            recent_prices = data['close'].tail(20)
            trend = "ALCISTA" if recent_prices.iloc[-1] > recent_prices.iloc[0] else "BAJISTA"
            change_pct = ((recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]) * 100

            print(f"Tendencia reciente (20 velas): {trend} ({change_pct:.2f}%)")

            # Calcular parámetros optimizados basados en condiciones actuales
            optimized_params = self._calculate_optimized_parameters(data, current_price, current_atr, avg_volume)

            return optimized_params

        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            return None

    def _calculate_optimized_parameters(self, data, current_price, current_atr, avg_volume):
        """Calcular parámetros optimizados basados en condiciones de mercado actuales"""
        try:
            print("\n🎯 CÁLCULO DE PARÁMETROS OPTIMIZADOS")
            print("=" * 45)

            # Analizar volatilidad relativa
            atr_percentage = (current_atr / current_price) * 100
            print(f"Volatilidad relativa: {atr_percentage:.2f}%")

            # Ajustar parámetros basados en volatilidad
            if atr_percentage > 1.0:  # Mercado muy volátil
                print("📈 Mercado de alta volatilidad detectado")
                risk_per_trade = 0.015  # Reducir riesgo
                atr_multiplier_sl = 2.0  # Stop loss más amplio
                atr_multiplier_tp = 4.0  # Take profit más amplio
                ml_threshold_min = 0.5   # ML confidence más alto
                liquidity_min = 3        # Liquidez más baja requerida

            elif atr_percentage > 0.5:  # Mercado moderadamente volátil
                print("📊 Mercado de volatilidad moderada")
                risk_per_trade = 0.02
                atr_multiplier_sl = 1.5
                atr_multiplier_tp = 3.0
                ml_threshold_min = 0.45
                liquidity_min = 4

            else:  # Mercado de baja volatilidad
                print("📉 Mercado de baja volatilidad")
                risk_per_trade = 0.025
                atr_multiplier_sl = 1.2
                atr_multiplier_tp = 2.5
                ml_threshold_min = 0.4
                liquidity_min = 5

            # Ajustar basado en volumen
            volume_ratio = data['volume'].iloc[-1] / avg_volume
            if volume_ratio > 1.5:  # Alto volumen
                liquidity_min *= 0.8  # Reducir requerimiento de liquidez
                print("💹 Alto volumen detectado - relajando filtros de liquidez")

            # Ajustar basado en tendencia
            recent_trend = data['close'].tail(10).pct_change().sum()
            if abs(recent_trend) < 0.005:  # Mercado lateral
                ml_threshold_min += 0.05  # Requerir más confianza ML
                print("🔄 Mercado lateral detectado - aumentando umbral ML")

            # Parámetros finales
            optimized_params = {
                'atr_period': 14,
                'stop_loss_atr_multiplier': round(atr_multiplier_sl, 2),
                'take_profit_atr_multiplier': round(atr_multiplier_tp, 2),
                'min_rr_ratio': 2.5,
                'risk_per_trade': round(risk_per_trade, 4),
                'max_concurrent_trades': 3,
                'ml_threshold_min': round(ml_threshold_min, 2),
                'ml_threshold_max': 0.8,
                'liquidity_score_min': round(liquidity_min, 1)
            }

            print("\n✅ PARÁMETROS OPTIMIZADOS:")
            for key, value in optimized_params.items():
                print(f"  {key}: {value}")

            return optimized_params

        except Exception as e:
            print(f"❌ Error calculando parámetros: {e}")
            return None

    def apply_optimized_parameters(self, optimized_params):
        """Aplicar parámetros optimizados a la configuración"""
        try:
            print("\n💾 APLICANDO PARÁMETROS OPTIMIZADOS")
            print("=" * 40)

            # Leer configuración actual
            config_path = Path("descarga_datos/config/config.yaml")

            if not config_path.exists():
                print("❌ Archivo de configuración no encontrado")
                return False

            import yaml

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Actualizar sección de backtesting
            if 'backtesting' not in config:
                config['backtesting'] = {}

            if 'optimized_parameters' not in config['backtesting']:
                config['backtesting']['optimized_parameters'] = {}

            # Aplicar parámetros optimizados
            config['backtesting']['optimized_parameters'].update(optimized_params)

            # Guardar configuración
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            print(f"✅ Configuración actualizada en {config_path}")
            print("💡 Reinicia el sistema de trading para usar los nuevos parámetros")

            return True

        except Exception as e:
            print(f"❌ Error aplicando parámetros: {e}")
            return False

async def main():
    print("🔬 OPTIMIZACIÓN CON DATOS DE MERCADO LIVE")
    print("=" * 50)

    optimizer = SimpleLiveOptimizer()

    # Paso 1: Inicializar conexión
    print("\n1️⃣ INICIALIZANDO CONEXIÓN...")
    if not await optimizer.initialize_provider():
        print("❌ Falló inicialización")
        return False

    # Paso 2: Descargar datos live
    print("\n2️⃣ DESCARGANDO DATOS LIVE...")
    live_data = await optimizer.download_live_data(bars=300)

    if live_data is None:
        print("❌ Falló descarga de datos")
        return False

    # Paso 3: Analizar datos y calcular parámetros optimizados
    print("\n3️⃣ ANALIZANDO DATOS Y OPTIMIZANDO PARÁMETROS...")
    optimized_params = optimizer.analyze_live_data(live_data)

    if optimized_params is None:
        print("❌ Falló análisis y optimización")
        return False

    # Paso 4: Aplicar parámetros optimizados
    print("\n4️⃣ APLICANDO PARÁMETROS OPTIMIZADOS...")
    if not optimizer.apply_optimized_parameters(optimized_params):
        print("❌ Falló aplicación de parámetros")
        return False

    print("\n✅ OPTIMIZACIÓN LIVE COMPLETADA EXITOSAMENTE")
    print("💡 Parámetros optimizados aplicados al sistema")
    print("💡 Ejecuta: python descarga_datos/main.py --live-ccxt")
    print("💡 Para probar los nuevos parámetros en modo live")

    return True

if __name__ == "__main__":
    asyncio.run(main())