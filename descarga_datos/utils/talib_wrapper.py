"""
Wrapper de compatibilidad para talib usando implementaciones numpy/pandas
Proporciona la misma interfaz que talib sin dependencias externas problemáticas
"""

import pandas as pd
import numpy as np

class TalibWrapper:
    """Wrapper que emula la interfaz de talib usando numpy/pandas"""

    @staticmethod
    def SMA(data, timeperiod=30):
        """Simple Moving Average"""
        return pd.Series(data).rolling(window=timeperiod).mean()

    @staticmethod
    def EMA(data, timeperiod=30):
        """Exponential Moving Average"""
        return pd.Series(data).ewm(span=timeperiod).mean()

    @staticmethod
    def RSI(data, timeperiod=14):
        """Relative Strength Index"""
        delta = pd.Series(data).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def ATR(high, low, close, timeperiod=14):
        """Average True Range"""
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=timeperiod).mean()

    @staticmethod
    def ADX(high, low, close, timeperiod=14):
        """Average Directional Index - Implementación completa"""
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        
        # Calcular True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calcular Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Smooth TR, +DM, -DM usando EMA de período especificado
        tr_smooth = tr.ewm(span=timeperiod, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(span=timeperiod, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(span=timeperiod, adjust=False).mean()
        
        # Calcular DI+ y DI-
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # Calcular DX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        dx = dx.fillna(0)  # Reemplazar NaN con 0
        
        # Calcular ADX como EMA del DX
        adx = dx.ewm(span=timeperiod, adjust=False).mean()
        
        return adx.fillna(25)  # Valor por defecto para NaN

    @staticmethod
    def SAR(high, low, acceleration=0.02, maximum=0.2):
        """Parabolic SAR - Implementación simplificada"""
        high = pd.Series(high)
        low = pd.Series(low)

        sar = pd.Series(index=high.index, dtype=float)
        sar.iloc[0] = low.iloc[0]  # Inicializar con el primer low

        for i in range(1, len(high)):
            if high.iloc[i-1] > sar.iloc[i-1]:
                # Tendencia alcista
                sar.iloc[i] = sar.iloc[i-1] + acceleration * (high.iloc[i-1] - sar.iloc[i-1])
                sar.iloc[i] = min(sar.iloc[i], low.iloc[i])  # No puede estar por encima del low actual
            else:
                # Tendencia bajista
                sar.iloc[i] = sar.iloc[i-1] - acceleration * (sar.iloc[i-1] - low.iloc[i-1])
                sar.iloc[i] = max(sar.iloc[i], high.iloc[i])  # No puede estar por debajo del high actual

        return sar

# Crear instancia singleton para usar como talib
talib = TalibWrapper()