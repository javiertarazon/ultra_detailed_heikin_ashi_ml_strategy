"""
Sistema avanzado de validación de datos financieros.
Detecta anomalías, inconsistencias y problemas comunes en datos OHLCV.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from utils.logger import get_logger

logger = get_logger("__name__")
        
        # Configuración por defecto
        self.config = config or {}
        self.price_spike_threshold = self.config.get('price_spike_threshold', 3.0)  # Z-score
        self.volume_spike_threshold = self.config.get('volume_spike_threshold', 5.0)  # Z-score
        self.gap_threshold = self.config.get('gap_threshold', 1.5)  # % de diferencia
        self.min_data_points = self.config.get('min_data_points', 30)
        self.max_zero_volume_ratio = self.config.get('max_zero_volume_ratio', 0.1)  # Máximo % de volumen cero
    
    def validate_ohlcv(self, df: pd.DataFrame) -> ValidationResult:
        """
        Valida datos OHLCV completos.
        
        Args:
            df: DataFrame con datos OHLCV (open, high, low, close, volume)
            
        Returns:
            ValidationResult con resultados de validación
        """
        result = ValidationResult(valid=True)
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            result.add_error("El DataFrame está vacío")
            return result
            
        # Verificar tamaño mínimo
        if len(df) < self.min_data_points:
            result.add_error(f"Datos insuficientes ({len(df)} filas). Mínimo: {self.min_data_points}")
            return result
        
        # 1. Verificar columnas requeridas
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            result.add_error(f"Faltan columnas OHLCV requeridas: {missing_columns}")
            return result
        
        # 2. Verificar valores nulos
        null_check = df[required_columns].isnull().any()
        if null_check.any():
            null_cols = null_check[null_check].index.tolist()
            null_counts = df[null_cols].isnull().sum().to_dict()
            result.add_error(f"Hay valores nulos en columnas OHLCV: {null_counts}")
            return result
        
        # 3. Verificar consistencia de precios
        # 3.1. Precios positivos
        negative_prices = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1)
        if negative_prices.any():
            indices = df.index[negative_prices].tolist()
            result.add_error(f"Hay precios negativos o cero en {len(indices)} registros")
        
        # 3.2. High >= Low
        invalid_hl = df[df['high'] < df['low']]
        if not invalid_hl.empty:
            indices = invalid_hl.index.tolist()
            result.add_error(f"Hay {len(invalid_hl)} registros donde high < low")
        
        # 3.3. Open/Close entre High y Low
        price_logic = (
            (df['open'] <= df['high']) & 
            (df['open'] >= df['low']) & 
            (df['close'] <= df['high']) & 
            (df['close'] >= df['low'])
        )
        
        if not price_logic.all():
            indices = df.index[~price_logic].tolist()
            result.add_error(f"Hay {len(indices)} registros donde open/close están fuera del rango high-low")
        
        # 4. Verificar volumen
        # 4.1. Volumen no negativo
        if (df['volume'] < 0).any():
            indices = df.index[df['volume'] < 0].tolist()
            result.add_error(f"Hay {len(indices)} valores negativos en el volumen")
        
        # 4.2. Demasiados volúmenes cero
        zero_volume = df['volume'] == 0
        zero_volume_ratio = zero_volume.mean()
        if zero_volume_ratio > self.max_zero_volume_ratio:
            result.add_warning(
                f"Alta proporción de volumen cero: {zero_volume_ratio:.1%} "
                f"(umbral: {self.max_zero_volume_ratio:.1%})"
            )
        
        # 5. Verificar índice temporal y duplicados
        if 'timestamp' in df.columns or pd.api.types.is_datetime64_any_dtype(df.index):
            # Si el índice es datetime o hay columna timestamp
            if 'timestamp' in df.columns:
                # Verificar ordenamiento
                if not df['timestamp'].is_monotonic_increasing:
                    result.add_error("Los timestamps no están en orden cronológico")
                
                # Verificar duplicados
                duplicates = df.duplicated(subset=['timestamp'])
                if duplicates.any():
                    result.add_error(f"Hay {duplicates.sum()} timestamps duplicados")
            elif pd.api.types.is_datetime64_any_dtype(df.index):
                # Verificar ordenamiento del índice
                if not df.index.is_monotonic_increasing:
                    result.add_error("Los timestamps en el índice no están en orden cronológico")
                
                # Verificar duplicados en el índice
                if df.index.duplicated().any():
                    result.add_error(f"Hay {df.index.duplicated().sum()} timestamps duplicados en el índice")
        
        # Si no hay errores críticos, realizar detección de anomalías
        if not result.has_errors:
            self._check_price_anomalies(df, result)
            self._check_volume_anomalies(df, result)
            self._check_gaps(df, result)
        
        # Calcular métricas de calidad
        result.metrics.update({
            'row_count': len(df),
            'price_range': df['high'].max() - df['low'].min(),
            'price_volatility': df['close'].pct_change().std(),
            'zero_volume_ratio': zero_volume_ratio,
            'avg_volume': df['volume'].mean(),
            'close_range_ratio': (df['close'].max() - df['close'].min()) / df['close'].mean() 
                                if df['close'].mean() > 0 else 0
        })
        
        return result
    
    def validate_indicators(self, df: pd.DataFrame, required_indicators: List[str] = None) -> ValidationResult:
        """
        Valida la calidad de los indicadores técnicos.
        
        Args:
            df: DataFrame con indicadores técnicos
            required_indicators: Lista de indicadores requeridos
            
        Returns:
            ValidationResult con resultados de validación
        """
        result = ValidationResult(valid=True)
        
        if df.empty:
            result.add_error("El DataFrame está vacío")
            return result
            
        # Si no se especifican indicadores, usar lista predeterminada
        if required_indicators is None:
            required_indicators = ['ema_10', 'ema_20', 'ema_200', 'rsi', 'macd', 'atr', 'sar']
        
        # 1. Verificar indicadores requeridos
        available_indicators = [col for col in required_indicators if col in df.columns]
        missing_indicators = [col for col in required_indicators if col not in df.columns]
        
        if missing_indicators:
            result.add_warning(f"Faltan indicadores: {missing_indicators}")
        
        # 2. Verificar calidad de los indicadores disponibles
        for indicator in available_indicators:
            # Verificar nulos
            null_count = df[indicator].isnull().sum()
            if null_count > 0:
                null_ratio = null_count / len(df)
                if null_ratio > 0.2:  # Más del 20% de valores nulos
                    result.add_warning(f"El indicador {indicator} tiene {null_ratio:.1%} de valores nulos")
                
            # Verificar valores inválidos según el tipo de indicador
            if indicator in ['atr', 'volume', 'volatility']:
                # No deberían ser negativos
                if (df[indicator] < 0).any():
                    result.add_warning(f"El indicador {indicator} tiene valores negativos")
                    
            if indicator in ['rsi']:
                # RSI debe estar entre 0 y 100
                if ((df[indicator] < 0) | (df[indicator] > 100)).any():
                    result.add_warning(f"El indicador {indicator} tiene valores fuera de rango [0, 100]")
        
        # 3. Verificar consistencia entre indicadores relacionados
        if 'ema_10' in available_indicators and 'ema_20' in available_indicators:
            # Las EMAs deben tener relación coherente (no demasiado dispares)
            ratio = (df['ema_10'] / df['ema_20']).mean()
            if ratio < 0.8 or ratio > 1.2:
                result.add_warning(f"Las EMAs muestran relación inusual (ratio EMA10/EMA20 = {ratio:.2f})")
        
        # 4. Verificar indicadores de tendencia
        trend_indicators = ['adx', 'trend', 'direction']
        available_trends = [ind for ind in trend_indicators if ind in df.columns]
        
        for indicator in available_trends:
            # Verificar cambios excesivos de tendencia
            if indicator in df.columns:
                changes = (df[indicator].shift() != df[indicator]).sum()
                change_rate = changes / len(df)
                if change_rate > 0.5:  # Más del 50% de los puntos son cambios de tendencia
                    result.add_warning(f"El indicador {indicator} muestra cambios excesivos de tendencia")
        
        return result
    
    def _check_price_anomalies(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Detecta anomalías en los precios."""
        # Calcular retornos y Z-score
        returns = df['close'].pct_change()
        returns_z = (returns - returns.mean()) / returns.std()
        
        # Detectar picos basados en Z-score
        price_spikes = np.abs(returns_z) > self.price_spike_threshold
        
        if price_spikes.any():
            indices = df.index[price_spikes].tolist()
            result.add_anomaly('price_spikes', indices)
            
        # Detectar precios planos (sin variación durante períodos largos)
        flat_prices = df['close'].diff() == 0
        if flat_prices.sum() >= 3:  # Al menos 3 períodos consecutivos sin variación
            # Encontrar secuencias consecutivas
            flat_sequences = []
            current_seq = []
            
            for i, is_flat in enumerate(flat_prices):
                if is_flat:
                    current_seq.append(i)
                else:
                    if len(current_seq) >= 3:
                        flat_sequences.append(current_seq)
                    current_seq = []
            
            if current_seq and len(current_seq) >= 3:
                flat_sequences.append(current_seq)
            
            if flat_sequences:
                # Combinar todas las secuencias
                all_flat = [idx for seq in flat_sequences for idx in seq]
                result.add_anomaly('flat_prices', all_flat)
    
    def _check_volume_anomalies(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Detecta anomalías en el volumen."""
        # No podemos usar Z-score directamente porque volumen suele no ser normal
        # Usar log para normalizar y luego calcular Z
        log_volume = np.log1p(df['volume'])
        volume_z = (log_volume - log_volume.mean()) / log_volume.std()
        
        # Detectar picos de volumen
        volume_spikes = volume_z > self.volume_spike_threshold
        if volume_spikes.any():
            indices = df.index[volume_spikes].tolist()
            result.add_anomaly('volume_spikes', indices)
        
        # Detectar volumen anormalmente bajo
        low_volume = (df['volume'] == 0) | (volume_z < -2.0)
        if low_volume.sum() > len(df) * 0.05:  # Más del 5% son volúmenes bajos
            indices = df.index[low_volume].tolist()
            result.add_anomaly('low_volume', indices)
    
    def _check_gaps(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Detecta gaps en los datos."""
        # Verificar si tenemos timestamp o es índice datetime
        if 'timestamp' in df.columns:
            timestamp = df['timestamp']
        elif pd.api.types.is_datetime64_any_dtype(df.index):
            timestamp = df.index
        else:
            return  # No podemos verificar gaps sin timestamps
            
        # Detectar gaps de precio
        price_changes = df['close'].pct_change().abs()
        gaps = price_changes > self.gap_threshold
        
        if gaps.any():
            indices = df.index[gaps].tolist()
            result.add_anomaly('price_gaps', indices)
            
        # Detectar gaps de tiempo (si es datetime)
        if isinstance(timestamp, pd.DatetimeIndex) or pd.api.types.is_datetime64_any_dtype(timestamp):
            # Calcular diferencias de tiempo
            time_diff = pd.Series(timestamp).diff()
            
            # Intentar determinar el intervalo normal
            most_common_diff = time_diff.value_counts().idxmax()
            
            # Detectar diferencias mayores al doble del intervalo normal
            time_gaps = time_diff > (most_common_diff * 2)
            
            if time_gaps.any():
                indices = df.index[time_gaps].tolist()
                result.add_anomaly('time_gaps', indices)
    
    def plot_anomalies(self, df: pd.DataFrame, result: ValidationResult, figsize: Tuple[int, int] = (12, 8)) -> None:
        """
        Genera un gráfico para visualizar las anomalías detectadas.
        
        Args:
            df: DataFrame con datos OHLCV
            result: Resultado de la validación con anomalías
            figsize: Tamaño de la figura (ancho, alto)
        """
        if not result.anomalies or df.empty:
            print("No hay anomalías que visualizar")
            return
            
        plt.figure(figsize=figsize)
        
        # Plot principal con precios
        plt.subplot(2, 1, 1)
        plt.plot(df['close'], label='Precio de cierre', color='blue')
        plt.title('Anomalías Detectadas en Datos OHLCV')
        
        # Visualizar las anomalías de precio
        if 'price_spikes' in result.anomalies:
            indices = result.anomalies['price_spikes']
            plt.scatter(df.index[indices], df.loc[df.index[indices], 'close'], 
                       color='red', marker='^', s=100, label='Picos de precio')
                       
        if 'price_gaps' in result.anomalies:
            indices = result.anomalies['price_gaps']
            plt.scatter(df.index[indices], df.loc[df.index[indices], 'close'], 
                       color='purple', marker='s', s=80, label='Gaps de precio')
                       
        if 'flat_prices' in result.anomalies:
            indices = result.anomalies['flat_prices']
            plt.scatter(df.index[indices], df.loc[df.index[indices], 'close'], 
                       color='orange', marker='o', s=60, label='Precios planos')
        
        plt.legend()
        plt.grid(True)
        
        # Plot inferior con volumen
        plt.subplot(2, 1, 2)
        plt.bar(df.index, df['volume'], color='gray', alpha=0.7, label='Volumen')
        
        if 'volume_spikes' in result.anomalies:
            indices = result.anomalies['volume_spikes']
            plt.scatter(df.index[indices], df.loc[df.index[indices], 'volume'], 
                       color='green', marker='^', s=100, label='Picos de volumen')
                       
        if 'low_volume' in result.anomalies:
            indices = result.anomalies['low_volume']
            plt.scatter(df.index[indices], df.loc[df.index[indices], 'volume'], 
                       color='red', marker='v', s=80, label='Volumen bajo')
        
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        return plt
    
    def generate_validation_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Genera un informe detallado de validación.
        
        Args:
            df: DataFrame para validar
            
        Returns:
            Dict con resultados y métricas de validación
        """
        # Validar datos OHLCV
        ohlcv_result = self.validate_ohlcv(df)
        
        # Validar indicadores si están presentes
        indicator_columns = []
        for col in df.columns:
            if col not in ['open', 'high', 'low', 'close', 'volume', 'timestamp']:
                indicator_columns.append(col)
        
        if indicator_columns:
            indicator_result = self.validate_indicators(df, indicator_columns)
            ohlcv_result.merge(indicator_result)
        
        # Generar reporte
        report = {
            'valid': ohlcv_result.valid,
            'timestamp': datetime.now().isoformat(),
            'rows': len(df),
            'errors': ohlcv_result.errors,
            'warnings': ohlcv_result.warnings,
            'metrics': ohlcv_result.metrics,
            'anomalies_count': {k: len(v) for k, v in ohlcv_result.anomalies.items()},
            'columns': list(df.columns)
        }
        
        # Si hay fechas, añadir rango temporal
        if 'timestamp' in df.columns:
            report['time_range'] = {
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            }
        elif pd.api.types.is_datetime64_any_dtype(df.index):
            report['time_range'] = {
                'start': df.index.min(),
                'end': df.index.max()
            }
            
        return report


# Función para facilitar la creación de una instancia
def get_data_validator(config=None):
    """
    Obtiene una instancia del validador avanzado de datos.
    
    Args:
        config: Configuración opcional
        
    Returns:
        EnhancedDataValidator: Una instancia del validador
    """
    return EnhancedDataValidator(config)
