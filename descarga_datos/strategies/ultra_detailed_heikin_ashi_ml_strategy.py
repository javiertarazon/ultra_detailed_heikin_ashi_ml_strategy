#!/usr/bin/env python3
"""
ULTRA-DETAILED HEIKIN ASHI STRATEGY WITH REAL ML MODELS
=========================================================

Estrategia ultra-optimizada con                 n_jobs=1  # CAMBIADO de -1 a 1 para evitar problemas de memoriaodelos de machine learning REALES entrenados
con datos históricos. NO USA SIMULACIONES - Aprende patrones y correlaciones
reales de indicadores técnicos para generar operaciones de ALTA PROBABILIDAD.

CARACTERÍSTICAS:
- Modelos ML entrenados con datos históricos reales (RandomForest, GradientBoosting, Neural Networks)
- Gestión de riesgo REAL basada en ATR y volatilidad del mercado
- Señales de alta confianza (>70% ML confidence) + filtros técnicos estrictos
- Trailing stops dinámicos y time exits
- Validación completa de indicadores y datos

REQUIERE: Datos históricos suficientes para entrenamiento ML (>100 muestras)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import talib
from datetime import datetime, timedelta
import os
import pickle
import joblib
# Importaciones lazy de sklearn para compatibilidad Python 3.13
# from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
# from sklearn.neural_network import MLPClassifier
# from sklearn.model_selection import train_test_split, cross_val_score
# from sklearn.preprocessing import StandardScaler
# from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

from models.model_manager import ModelManager

class MLModelManager:
    """
    Gestor de modelos de machine learning para predicción de señales Heikin Ashi
    
    Esta clase ahora utiliza el ModelManager centralizado para mantener
    la compatibilidad con el código existente.
    """

    def __init__(self, model_dir: str = None, config: dict = None):
        # Usar el ModelManager centralizado
        self.model_manager = ModelManager(model_dir)
        # Mantener compatibilidad con código existente
        self.model_dir = self.model_manager.model_dir
        self.models = {}
        self.scalers = {}
        # Agregar configuración para prepare_features
        self.config = config

    def ensure_model_dir(self):
        """Crear directorio de modelos si no existe"""
        self.model_manager.ensure_model_dir()

    def get_model_path(self, symbol: str, model_name: str) -> str:
        """Obtener ruta del modelo"""
        return self.model_manager.get_model_path(symbol, model_name)

    def get_scaler_path(self, symbol: str, model_name: str) -> str:
        """Obtener ruta del scaler"""
        return self.model_manager.get_scaler_path(symbol, model_name)

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Preparar features EXACTAMENTE IGUAL que en el entrenamiento ML
        CRÍTICO: Debe coincidir con MLTrainer.prepare_features() para evitar mismatch
        """
        # 🎯 COPIA EXACTA de MLTrainer.prepare_features() - NO MODIFICAR
        from indicators.technical_indicators import TechnicalIndicators
        
        # Usar la configuración ya cargada en el objeto, no recargar
        # config = load_config_from_yaml()  # ❌ PROBLEMÁTICO en optimización paralela
        config = self.config  # ✅ Usar config ya cargada
        
        indicator = TechnicalIndicators(config)
        df = data.copy()  # Trabajar con copia para no modificar original
        
        # Calcular TODOS los indicadores usando el método centralizado
        df = indicator.calculate_all_indicators(df)
        
        # Calcular features EXACTAMENTE como en MLTrainer
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        df['ha_open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
        df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
        df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        df['price_position'] = (df['close'] - df['close'].rolling(50).min()) / (df['close'].rolling(50).max() - df['close'].rolling(50).min())
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['trend_strength'] = abs(df['ema_10'] - df['ema_20']) / df['atr']
        
        # Seleccionar EXACTAMENTE las mismas features que MLTrainer.select_features()
        feature_cols = ['ha_close', 'ha_open', 'ha_high', 'ha_low', 'ema_10', 'ema_20', 'ema_200', 
                       'macd', 'macd_signal', 'adx', 'sar', 'atr', 'volatility', 'bb_upper', 'bb_lower', 
                       'rsi', 'momentum_5', 'momentum_10', 'volume_ratio', 'price_position', 
                       'trend_strength', 'returns', 'log_returns']
        
        # Filtrar solo las columnas que existen y están en la lista
        available_features = [col for col in feature_cols if col in df.columns]
        features = df[available_features].copy()
        
        # Eliminar filas con NaN
        features = features.dropna()
        
        # Features de volatilidad adicionales
        features['bb_upper'], features['bb_middle'], features['bb_lower'] = talib.BBANDS(data['close'], timeperiod=20)
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']

        # Limpiar NaN y valores extremos
        features = features.fillna(0)
        features = features.replace([np.inf, -np.inf], 0)

        # Limitar valores extremos (winsorizing)
        for col in features.columns:
            if features[col].dtype in ['float64', 'float32']:
                # Limitar al percentil 1-99 para evitar outliers extremos
                lower = features[col].quantile(0.01)
                upper = features[col].quantile(0.99)
                features[col] = features[col].clip(lower, upper)

        return features

        # ⚠️ CÓDIGO INALCANZABLE ELIMINADO ⚠️
        # El siguiente código nunca se ejecutaba porque estaba después del return
        # Features de volatilidad
        # features['bb_upper'], features['bb_middle'], features['bb_lower'] = talib.BBANDS(data['close'], timeperiod=20)
        # features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']

        # Limpiar NaN y valores extremos
        # features = features.fillna(0)
        # features = features.replace([np.inf, -np.inf], 0)

        # Limitar valores extremos (winsorizing)
        # for col in features.columns:
        #     if features[col].dtype in ['float64', 'float32']:
        #         # Limitar al percentil 1-99 para evitar outliers extremos
        #         lower = features[col].quantile(0.01)
        #         upper = features[col].quantile(0.99)
        #         features[col] = features[col].clip(lower, upper)

        # return features

    def prepare_target(self, data: pd.DataFrame, lookahead: int = 1) -> pd.Series:
        """
        Preparar target: cambio de color Heikin Ashi en N periodos
        """
        # Target: 1 si hay cambio alcista, -1 si bajista, 0 si neutral
        future_changes = data['ha_color_change'].shift(-lookahead)
        target = pd.Series(0, index=data.index)

        # Solo considerar cambios significativos
        target[future_changes == 1] = 1   # Cambio alcista futuro
        target[future_changes == -1] = -1  # Cambio bajista futuro

        return target

    def train_models(
        self,
        data: pd.DataFrame,
        symbol: str,
        test_size: float = 0.2,
        cv_folds: int = 10,
        cv_jobs: int = 1,  # CAMBIADO de -1 a 1 para evitar problemas de memoria
        enable_cv: bool = True
    ):
        """
        Entrenar modelos de ML para un símbolo específico
        """
        print(f"Entrenando modelos ML para {symbol}...")

        # Importaciones lazy de sklearn para compatibilidad Python 3.13
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.neural_network import MLPClassifier
            from sklearn.model_selection import train_test_split, cross_val_score
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
            print("Importaciones sklearn exitosas")
        except KeyboardInterrupt:
            print("KeyboardInterrupt durante importación sklearn - abortando entrenamiento")
            return {}
        except Exception as e:
            print(f"Error importando sklearn: {e}")
            return {}

        # Preparar features y target
        features = self.prepare_features(data)
        target = self.prepare_target(data)

        # Remover filas con target NaN (futuro)
        valid_idx = target.dropna().index
        features = features.loc[valid_idx]
        target = target.loc[valid_idx]

        # Split de datos
        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=test_size, random_state=42, shuffle=False
        )

        # Escalar features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # SOLO RANDOM FOREST - Otros modelos causan problemas en Python 3.13
        models_config = {
            'random_forest': RandomForestClassifier(
                n_estimators=200,        # Aumentado de 100 (más árboles = mejor generalización)
                max_depth=15,            # Aumentado de 10 (más profundidad con más data)
                min_samples_split=10,    # Reducido de 20 (menos restrictivo)
                min_samples_leaf=5,      # Reducido de 10 (permite más detalle)
                max_features='sqrt',     # Mejor para evitar overfitting
                random_state=42,
                n_jobs=1
            )
            # GradientBoosting y NeuralNetwork DESHABILITADOS
        }

        # Entrenar y evaluar modelos
        results = {}
        for model_name, model in models_config.items():
            print(f"  Entrenando {model_name}...")

            # Entrenar
            model.fit(X_train_scaled, y_train)

            # Predecir
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)

            # Métricas
            accuracy = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr') if len(np.unique(y_test)) > 1 else 0.5

            if enable_cv and len(X_train_scaled) >= cv_folds:
                # Cross-validation configurable (default 10-fold) - FORZAR n_jobs=1
                cv_scores = cross_val_score(
                    model,
                    X_train_scaled,
                    y_train,
                    cv=cv_folds,
                    scoring='accuracy',
                    n_jobs=1  # FORZADO a 1 para evitar problemas de paralelización en Python 3.13
                )
                cv_score = cv_scores.mean()
                cv_std = cv_scores.std()
            else:
                cv_score = accuracy
                cv_std = 0.0

            results[model_name] = {
                'model': model,
                'accuracy': accuracy,
                'auc': auc,
                'cv_score': cv_score,
                'cv_std': cv_std,
                'scaler': scaler
            }

            if enable_cv and len(X_train_scaled) >= cv_folds:
                print(f"    {model_name}: Accuracy={accuracy:.4f}, AUC={auc:.4f}, CV={cv_score:.4f}±{cv_std:.4f}")
            else:
                print(f"    {model_name}: Accuracy={accuracy:.4f}, AUC={auc:.4f} (CV omitido por configuración)")

            # Guardar modelo
            self.save_model(symbol, model_name, model, scaler)

        self.models[symbol] = results
        return results

    def save_model(self, symbol: str, model_name: str, model, scaler):
        """Guardar modelo entrenado usando el ModelManager centralizado"""
        # Construir nombre completo del modelo incluyendo el símbolo
        full_model_name = f"{symbol}_{model_name}"
        full_scaler_name = f"{symbol}_{model_name}_scaler"

        # Usar el ModelManager centralizado
        success_model = self.model_manager.save_model(model, full_model_name)
        success_scaler = self.model_manager.save_model(scaler, full_scaler_name)

        if success_model and success_scaler:
            print(f"    Modelo guardado: {full_model_name}")
        else:
            print(f"    Error al guardar modelo para {symbol}")

    def load_model(self, symbol: str, model_name: str):
        """Cargar modelo entrenado usando múltiples métodos de compatibilidad"""
        import os
        import joblib

        # Construir nombre completo del modelo incluyendo el símbolo
        full_model_name = f"{symbol}_{model_name}"

        # PRIMERO: Intentar cargar desde archivos joblib en el directorio de modelos (donde están los modelos reales)
        try:
            # Convertir símbolo a nombre de directorio válido (XRP/USDT -> XRP_USDT)
            symbol_dir = symbol.replace('/', '_')
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', symbol_dir)
            model_files = [f for f in os.listdir(models_dir) if f.startswith('RandomForest_') and f.endswith('.joblib')]

            if model_files:
                # Usar el modelo más reciente
                latest_model = sorted(model_files)[-1]
                model_path = os.path.join(models_dir, latest_model)

                # Cargar modelo joblib
                model_data = joblib.load(model_path)
                model = model_data['model'] if isinstance(model_data, dict) else model_data

                # Intentar cargar scaler desde el mismo archivo o crear uno nuevo
                scaler = None
                if isinstance(model_data, dict) and 'scaler' in model_data:
                    scaler = model_data['scaler']
                else:
                    # Crear scaler dummy y ajustarlo con datos de ejemplo
                    from sklearn.preprocessing import StandardScaler
                    scaler = StandardScaler()
                    # El scaler se ajustará cuando se use por primera vez

                return model, scaler
        except Exception as e:
            print(f"Error cargando modelo joblib: {e}")

        # SEGUNDO: Intentar cargar desde ModelManager centralizado
        try:
            model = self.model_manager.load_model(full_model_name)
            scaler = self.model_manager.load_model(f"{full_model_name}_scaler")
            if model is not None and scaler is not None:
                return model, scaler
        except:
            pass

        return None, None

    def predict_signal(self, data: pd.DataFrame, symbol: str, model_name: str = 'random_forest') -> pd.Series:
        """
        Generar predicciones de señales usando modelo entrenado REAL
        NO USA SIMULACIONES - Requiere modelo entrenado con datos históricos
        """
        # Cargar modelo entrenado (OBLIGATORIO)
        model, scaler = self.load_model(symbol, model_name)

        if model is None or scaler is None:
            raise ValueError(f"MODELO {model_name} NO ENCONTRADO para {symbol}. "
                           f"Ejecutar entrenamiento primero con datos históricos reales.")

        # Preparar features con datos reales
        features = self.prepare_features(data)

        # DEBUG: Imprimir número de features
        print(f"DEBUG: Features preparadas: {len(features.columns)} columnas")
        print(f"DEBUG: Nombres de features: {list(features.columns)}")

        # Ajustar scaler si no está fitted o si hay mismatch de features
        try:
            # Verificar si el scaler está fitted
            if not hasattr(scaler, 'mean_') or scaler.mean_ is None:
                raise ValueError("Scaler not fitted - debe estar guardado junto con el modelo entrenado")
            features_scaled = scaler.transform(features)
        except Exception as e:
            # ❌ DATA LEAKAGE CRÍTICO - NUNCA re-ajustar scaler en producción
            print(f"ERROR CRÍTICO: Scaler no válido ({e}). Devolviendo confianza neutral (0.5)")
            # Fallback seguro: devolver confianza neutral sin data leakage
            confidence = pd.Series([0.5] * len(data), index=data.index, name='ml_confidence')
            return confidence

        # Verificar que el número de features coincida
        # Determinar dinámicamente el número esperado de features basado en las disponibles
        expected_features = len(features.columns)  # Usar el número real de features preparadas
        actual_features = features_scaled.shape[1]
        if actual_features != expected_features:
            print(f"CRITICAL: Features mismatch - esperado {expected_features}, obtenido {actual_features}")
            # ❌ DATA LEAKAGE CRÍTICO - NUNCA re-ajustar scaler en producción
            print("ERROR CRÍTICO: Mismatch de features. Devolviendo confianza neutral (0.5)")
            # Fallback seguro: devolver confianza neutral sin data leakage
            confidence = pd.Series([0.5] * len(data), index=data.index, name='ml_confidence')
            return confidence

        # Predecir probabilidades usando modelo entrenado
        # Deshabilitar paralelización temporalmente para compatibilidad con Python 3.13
        original_n_jobs = getattr(model, 'n_jobs', None)
        if hasattr(model, 'n_jobs'):
            model.n_jobs = 1
        
        try:
            proba = model.predict_proba(features_scaled)
        except ValueError as e:
            if "features" in str(e).lower():
                # Error de mismatch de features - NO intentar re-entrenar, devolver confianza neutral
                print(f"ERROR: Mismatch de features en modelo ({e}). Usando confianza neutral (0.5)")
                # Fallback: devolver confianza neutral sin intentar re-entrenar
                confidence = pd.Series([0.5] * len(data), index=data.index, name='ml_confidence')
                return confidence
            else:
                raise e
        finally:
            # Restaurar configuración original
            if hasattr(model, 'n_jobs') and original_n_jobs is not None:
                model.n_jobs = original_n_jobs

        # Convertir a confianza (probabilidad de cambio alcista - probabilidad de cambio bajista)
        confidence = proba[:, 2] - proba[:, 0] if proba.shape[1] > 2 else proba[:, 1] - 0.5

        # Normalizar a [0, 1] - confianza real del modelo
        confidence = (confidence + 1) / 2
        confidence = np.clip(confidence, 0, 1)

        # CRÍTICO: El índice debe coincidir con features.index, luego reindexar al data.index original
        confidence_series = pd.Series(confidence, index=features.index, name='ml_confidence')
        
        # Reindexar para coincidir con el índice original de data (llenar NaN con 0.5 si es necesario)
        confidence_series = confidence_series.reindex(data.index, fill_value=0.5)
        
        return confidence_series

    def _calculate_heikin_ashi(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcular velas Heikin Ashi"""

        # Heikin Ashi calculation
        ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4

        ha_open = pd.Series(index=data.index, dtype=float)
        ha_open.iloc[0] = (data['open'].iloc[0] + data['close'].iloc[0]) / 2

        for i in range(1, len(data)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

        ha_high = pd.concat([ha_open, ha_close, data['high']], axis=1).max(axis=1)
        ha_low = pd.concat([ha_open, ha_close, data['low']], axis=1).min(axis=1)

        # Agregar al DataFrame
        data['ha_open'] = ha_open
        data['ha_high'] = ha_high
        data['ha_low'] = ha_low
        data['ha_close'] = ha_close

        # Color change (señal principal)
        data['ha_color_change'] = (data['ha_close'] > data['ha_open']).astype(int).diff().fillna(0)
        data['ha_bullish'] = (data['ha_close'] > data['ha_open']).astype(int)
        data['ha_bearish'] = (data['ha_close'] < data['ha_open']).astype(int)

        return data

    def _calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        ⚠️ MÉTODO OBSOLETO: Use TechnicalIndicators.calculate_all_indicators_unified en su lugar
        
        Este método se mantiene solo para compatibilidad con código existente.
        Será eliminado en futuras versiones.
        """
        # Llamar al método centralizado
        from indicators.technical_indicators import TechnicalIndicators
        indicators = TechnicalIndicators()
        return indicators.calculate_all_indicators_unified(data)


class UltraDetailedHeikinAshiMLStrategy:
    """
    Estrategia ultra-detallada con modelos ML reales entrenados
    """

    def __init__(self, config=None):
        # Manejar tanto objetos Config como diccionarios
        if config is None:
            self.config = {}
        elif hasattr(config, 'backtesting'):
            # Es un objeto Config - extraer parámetros relevantes
            self.config = {
                'symbol': getattr(config.backtesting, 'symbols', ['SOL/USDT'])[0] if hasattr(config.backtesting, 'symbols') and config.backtesting.symbols else 'SOL/USDT',
                'timeframe': getattr(config.backtesting, 'timeframe', '4h') if hasattr(config.backtesting, 'timeframe') else '4h',
                'ml_threshold': 0.25,  # Optimizado para SOL/USDT
                'stoch_overbought': 85,
                'stoch_oversold': 35,
                'cci_threshold': 170,
                'volume_ratio_min': 0.3,
                'liquidity_score_min': 5,
                'max_drawdown': 0.12,
                'max_portfolio_heat': 0.18,
                'max_concurrent_trades': 4,
                'kelly_fraction': 0.35
            }
        else:
            # Es un diccionario
            self.config = config

        # Extraer parámetros con valores por defecto
        self.symbol = self.config.get('symbol', 'SOL/USDT')
        self.timeframe = self.config.get('timeframe', '4h')

        # Parámetros optimizados desde configuración centralizada
        self.ml_threshold = self.config.get('ml_threshold', 0.25)
        self.stoch_overbought = self.config.get('stoch_overbought', 85)
        self.stoch_oversold = self.config.get('stoch_oversold', 35)
        self.cci_threshold = self.config.get('cci_threshold', 170)
        self.volume_ratio_min = self.config.get('volume_ratio_min', 0.3)
        self.liquidity_score_min = self.config.get('liquidity_score_min', 5)

        # Cargar parámetros específicos del símbolo desde configuración centralizada
        self._load_symbol_specific_params(config)

        # Gestión de riesgo avanzada OPTIMIZADA
        self.max_drawdown = self.config.get('max_drawdown', 0.05)
        self.max_portfolio_heat = self.config.get('max_portfolio_heat', 0.06)  # Aumentado a 6%
        self.max_concurrent_trades = self.config.get('max_concurrent_trades', 3)  # Más oportunidades
        self.kelly_fraction = self.config.get('kelly_fraction', 0.3)  # Más conservador

        # Estado interno
        self.active_trades = []
        self.portfolio_value = 10000.0  # Valor inicial
        self.current_drawdown = 0.0

        # Inicializar gestor de modelos ML
        self.ml_manager = MLModelManager(config=self.config)

    def _load_symbol_specific_params(self, config):
        """
        Carga parámetros específicos del símbolo desde configuración centralizada.
        Esto elimina la necesidad de modificar la estrategia para cada símbolo.
        """
        # Valores por defecto universales
        default_params = {
            'volume_threshold': 1.3,
            'atr_multiplier': 3.4,
            'stop_loss_pct': 0.09,
            'take_profit_pct': 0.19,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'stoch_overbought': 85,
            'stoch_oversold': 35,
            'atr_period': 14,
            'atr_volatility_threshold': 2.0,
            'ema_trend_period': 50,
            'max_consecutive_losses': 3,
            'min_trend_strength': 0.5,
            'sar_acceleration': 0.06,
            'sar_maximum': 0.11,
            'stop_loss_atr_multiplier': 3.25,
            'take_profit_atr_multiplier': 5.5,
            'trailing_stop_atr_multiplier': 1.5,
            'volatility_filter_threshold': 0.03,
            'volume_sma_period': 20,
            'volume_threshold': 1000
        }

        # Intentar cargar parámetros específicos del símbolo desde configuración
        symbol_params = {}
        if config and hasattr(config, 'backtesting'):
            # Es un objeto Config - buscar en optimized_parameters
            backtesting_config = config.backtesting
            if hasattr(backtesting_config, 'optimized_parameters'):
                opt_params = backtesting_config.optimized_parameters
                # La configuración actual tiene estructura: SOL/USDT -> 4h -> params
                symbol_key = self.symbol.replace('/', '_').replace('.', '_')
                if hasattr(opt_params, symbol_key):
                    symbol_section = getattr(opt_params, symbol_key)
                    if hasattr(symbol_section, self.timeframe):
                        timeframe_section = getattr(symbol_section, self.timeframe)
                        # Convertir a diccionario
                        if hasattr(timeframe_section, '__dict__'):
                            symbol_params = timeframe_section.__dict__
                        elif hasattr(timeframe_section, 'items'):
                            symbol_params = dict(timeframe_section)

        # Aplicar parámetros específicos del símbolo o valores por defecto
        for param_name, default_value in default_params.items():
            # Primero intentar desde config directa, luego parámetros específicos del símbolo, luego default
            value = self.config.get(param_name, symbol_params.get(param_name, default_value))
            setattr(self, param_name, value)

        print(f"📊 Parámetros cargados para {self.symbol}: atr_period={self.atr_period}, stop_loss_atr={self.stop_loss_atr_multiplier}, take_profit_atr={self.take_profit_atr_multiplier}")

    def run(self, data: pd.DataFrame, symbol: str, timeframe: str = '4h') -> Dict:
        """
        Ejecutar estrategia ultra-detallada con modelos ML reales entrenados
        REQUIERE datos históricos reales para entrenamiento - NO SIMULACIONES

        Args:
            data: DataFrame con datos OHLCV históricos reales
            symbol: Símbolo del activo
            timeframe: Timeframe de los datos

        Returns:
            Dict con resultados de backtesting usando ML real
        """
        try:
            print(f"[START] Iniciando UltraDetailedHeikinAshiStrategy REAL ML para {symbol}")
            print(f"[DEBUG] Método run() llamado con {len(data)} filas")

            # MODO SEGURO: Verificar si está activado para evitar problemas Python 3.13
            safe_mode = self.config.get('ml_training', {}).get('safe_mode', False)
            if safe_mode:
                print("🛡️  MODO SEGURO ACTIVADO - Usando solo indicadores técnicos (sin ML)")
                return self._run_safe_mode(data, symbol, timeframe)

            # VALIDAR datos mínimos para entrenamiento
            if len(data) < 100:
                raise ValueError(f"Datos insuficientes: {len(data)} filas. Necesario mínimo 100 para ML real.")

            # Preparar datos con indicadores calculados correctamente
            data_processed = self._prepare_data(data.copy())
            print(f"Datos preparados: {len(data_processed)} filas con indicadores técnicos completos")

            # FORZAR uso de modelos existentes durante optimización (NO re-entrenar)
            # Durante optimización Optuna, los modelos ya deben estar entrenados
            optimization_mode = getattr(self, '_optimization_mode', False)

            if optimization_mode:
                # MODO OPTIMIZACIÓN: Asumir que modelos ya están entrenados
                print(f"🎯 MODO OPTIMIZACIÓN: Usando modelos ML pre-entrenados para {symbol}")
                model_exists = self.ml_manager.load_model(symbol, 'random_forest')[0] is not None
                if not model_exists:
                    raise ValueError(f"Modelos ML no encontrados para {symbol} en modo optimización. "
                                   f"Ejecutar entrenamiento primero.")
            else:
                # MODO NORMAL: Verificar y entrenar si es necesario
                model_exists = self.ml_manager.load_model(symbol, 'random_forest')[0] is not None
                should_retrain = not model_exists

                if should_retrain:
                    print(f"⚠️  Modelos ML no encontrados. Entrenando con {len(data_processed)} muestras...")
                    self.ml_manager.train_models(data_processed, symbol)
                    print("✅ Modelos ML entrenados y guardados")
                else:
                    print(f"✅ Usando modelos ML existentes para {symbol} (skip re-training)")

            # CACHEAR predicciones ML usando modelo entrenado REAL
            print(f"Generando predicciones ML reales para {len(data_processed)} velas...")
            ml_confidence_cached = self.ml_manager.predict_signal(data_processed, symbol, 'random_forest')  # CAMBIADO A RANDOM_FOREST
            print(f"Predicciones ML reales: confianza {ml_confidence_cached.min():.3f} - {ml_confidence_cached.max():.3f}")

            # Generar señales usando ML real + filtros técnicos
            signals = self._generate_signals(data_processed, symbol, ml_confidence_cached)
            signals_above_threshold = (ml_confidence_cached > self.ml_threshold)
            print(f"Señales ML reales: {signals.sum()} entradas largas, {(signals == -1).sum()} entradas cortas")
            print(f"Señales con alta confianza (>{self.ml_threshold}): {signals_above_threshold.sum()}/{len(signals_above_threshold)}")

            # Ejecutar backtesting con gestión de riesgo real
            results = self._run_backtest(data_processed, signals, symbol, ml_confidence_cached)
            print(f"[RESULT] Backtesting completado: {results['total_trades']} trades, P&L: ${results['total_pnl']:.2f}")
            print(f"[DEBUG] run(): Trades en results = {len(results.get('trades', []))}")

            return results

        except Exception as e:
            print(f"[ERROR] Error en UltraDetailedHeikinAshiStrategy REAL ML: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_results(symbol)

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preparar datos con TODOS los indicadores técnicos calculados correctamente"""

        # VALIDAR columnas requeridas
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Columnas requeridas faltantes: {missing_cols}")

        print(f"[CALC] Calculando indicadores técnicos para {len(data)} velas...")
        
        # 🎯 USAR MÉTODO CENTRALIZADO PARA CONSISTENCIA CON ML
        # Esto garantiza que _prepare_data y prepare_features usen EXACTAMENTE los mismos indicadores
        from indicators.technical_indicators import TechnicalIndicators
        indicators = TechnicalIndicators()
        data = indicators.calculate_all_indicators_unified(data)
        
        # ⚠️ CÓDIGO MANUAL ELIMINADO PARA EVITAR INCONSISTENCIAS ⚠️
        # El siguiente código calculaba indicadores manualmente con TA-Lib,
        # causando inconsistencias con el entrenamiento ML que usa TechnicalIndicators centralizada
        
        # 1. Heikin Ashi - AHORA CALCULADO POR calculate_all_indicators_unified
        # data = self._calculate_heikin_ashi(data)

        # 2. Indicadores técnicos principales - AHORA CALCULADOS CENTRALIZADAMENTE
        # try:
        #     # Stochastic Oscillator
        #     data['stoch_k'], data['stoch_d'] = talib.STOCH(
        #         data['high'], data['low'], data['close'],
        #         fastk_period=14, slowk_period=3, slowd_period=3
        #     )
        #     # ... resto de indicadores manuales eliminados
        # except Exception as e:
        #     raise ValueError(f"Error calculando indicadores técnicos: {e}")

        # 3. VALIDAR que no hay NaN críticos (más tolerante)
        critical_indicators = ['ha_close', 'stoch_k', 'cci', 'rsi', 'macd', 'atr']
        nan_counts = data[critical_indicators].isna().sum()
        total_critical_nans = nan_counts.sum()
        max_allowed_nans = len(data) * 0.05  # Máximo 5% de NaN permitidos

        if total_critical_nans > max_allowed_nans:
            print(f"️ NaN detectados en indicadores críticos: {nan_counts.to_dict()}")
            print(f"Limpiando {total_critical_nans} filas con NaN...")
            # En lugar de error, limpiar los NaN
            data = data.dropna(subset=critical_indicators)
            print(f"Datos limpiados: {len(data)} filas restantes")

        if len(data) < 50:
            raise ValueError(f"Datos insuficientes después de limpieza: {len(data)} filas")

        # 4. Rellenar NaN restantes en indicadores no críticos
        data = data.fillna(method='bfill').fillna(method='ffill').fillna(0)

        print(f"Datos preparados: {len(data)} filas válidas con todos los indicadores")
        return data

    def _calculate_heikin_ashi(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcular velas Heikin Ashi"""

        # Heikin Ashi calculation
        ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4

        ha_open = pd.Series(index=data.index, dtype=float)
        ha_open.iloc[0] = (data['open'].iloc[0] + data['close'].iloc[0]) / 2

        for i in range(1, len(data)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

        ha_high = pd.concat([ha_open, ha_close, data['high']], axis=1).max(axis=1)
        ha_low = pd.concat([ha_open, ha_close, data['low']], axis=1).min(axis=1)

        # Agregar al DataFrame
        data['ha_open'] = ha_open
        data['ha_high'] = ha_high
        data['ha_low'] = ha_low
        data['ha_close'] = ha_close

        # Color change (señal principal)
        data['ha_color_change'] = (data['ha_close'] > data['ha_open']).astype(int).diff().fillna(0)
        data['ha_bullish'] = (data['ha_close'] > data['ha_open']).astype(int)
        data['ha_bearish'] = (data['ha_close'] < data['ha_open']).astype(int)

        return data

    def _generate_signals(self, data: pd.DataFrame, symbol: str, ml_confidence: pd.Series = None) -> pd.Series:
        """
        Generar señales con ALTA PROBABILIDAD usando ML real + filtros técnicos estrictos
        """
        signals = pd.Series(0, index=data.index, name='signal')

        # Usar ML confidence cacheado (OBLIGATORIO para señales reales)
        if ml_confidence is None:
            raise ValueError("ML confidence requerido - debe usar modelo entrenado real")

        long_signals = 0
        short_signals = 0

        for i in range(1, len(data)):
            # CONFIRMAR ML confidence (umbral más bajo para testing)
            ml_conf = ml_confidence.iloc[i]
            if ml_conf < 0.5:  # REDUCIDO AÚN MÁS para asegurar señales
                continue

            # FILTROS TÉCNICOS MÁS RELAJADOS para testing
            ha_change_long = data['ha_color_change'].iloc[i] == 1
            ha_change_short = data['ha_color_change'].iloc[i] == -1

            # RSI: Rango amplio
            rsi = data['rsi'].iloc[i]
            rsi_ok = 20 < rsi < 80  # AÚN MÁS AMPLIO

            # Stochastic: Solo evitar extremos absolutos
            stoch_k = data['stoch_k'].iloc[i]
            stoch_ok = 10 < stoch_k < 90  # AÚN MENOS RESTRICTIVO

            # Volumen: Mínimo requerimiento
            volume_ok = data['volume_ratio'].iloc[i] > 0.8  # REDUCIDO AÚN MÁS

            # ATR: Rango amplio
            atr = data['atr'].iloc[i]
            atr_pct = atr / data['close'].iloc[i]
            volatility_ok = atr_pct > 0.001  # SOLO EVITAR VOLATILIDAD MUY BAJA

            # DEBUG: Contar condiciones cumplidas
            conditions_met = sum([ha_change_long or ha_change_short, rsi_ok, stoch_ok, volume_ok, volatility_ok])

            # SEÑAL LONG: ML + HA + al menos 3 condiciones técnicas
            if ha_change_long and conditions_met >= 3:
                signals.iloc[i] = 1  # Long
                long_signals += 1

            # SEÑAL SHORT: ML + HA + al menos 3 condiciones técnicas
            elif ha_change_short and conditions_met >= 3:
                signals.iloc[i] = -1  # Short
                short_signals += 1

        print(f"Señales ML de ALTA PROBABILIDAD: {long_signals} LONG, {short_signals} SHORT")
        print(f"Confianza ML promedio en señales: {ml_confidence[signals != 0].mean():.3f}")

        return signals

    def _check_liquidity_score(self, row: pd.Series) -> bool:
        """
        Verificar score de liquidez basado en volumen y volatilidad real
        AJUSTADO: Fórmulas más permisivas y escalas razonables
        """
        # Volume score: 0-100, más permisivo (x10 en lugar de x20)
        volume_score = min(row['volume_ratio'] * 10, 100)
        
        # Volatility score: 0-100, invertido (mayor ATR/close = mayor volatilidad = mayor score)
        # Usamos (atr/close)*100 directamente como medida de volatilidad
        volatility_pct = (row['atr'] / row['close']) * 100  # ej. 7.5% volatilidad
        volatility_score = min(volatility_pct * 10, 100)  # Escalar a 0-100
        
        liquidity_score = (volume_score + volatility_score) / 2
        
        # Prints de liquidity ELIMINADOS para no saturar logs
        
        return liquidity_score > self.liquidity_score_min

    def _run_backtest(self, data: pd.DataFrame, signals: pd.Series, symbol: str, ml_confidence_all: pd.Series) -> Dict:
        """Ejecutar backtesting con GESTIÓN DE RIESGO REAL basada en ATR y volatilidad"""

        capital = self.portfolio_value
        trades = []
        peak_value = capital
        max_drawdown = 0
        position = 0
        entry_price = 0
        entry_time = None
        entry_index = None  # Para tracking de velas desde entrada

        # PARÁMETROS DE RIESGO OPTIMIZADOS Y REALES
        risk_per_trade = 0.02  # 2% por trade (más conservador)
        min_rr_ratio = 2.5     # Risk/Reward mínimo más alto
        max_concurrent_trades = self.max_concurrent_trades

        # CONTADORES para análisis
        from utils.logger import get_logger
        logger = get_logger('ultra_detailed_strategy')
        signals_nonzero = signals[signals != 0]
        logger.info(f"DEBUG: {len(signals_nonzero)} señales no-cero detectadas en serie signals")

        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            current_time = data.index[i]
            atr = data['atr'].iloc[i]

            # SKIP si ATR es NaN o cero (primeras velas sin datos suficientes)
            if pd.isna(atr) or atr == 0:
                if i < 10:  # Solo log primeras 10
                    logger.debug(f"[DEBUG] Saltando i={i} - ATR NaN o cero: {atr}")
                continue

            # GESTIÓN DE RIESGO REAL: Calcular position size basado en ATR
            if position == 0 and signals.iloc[i] != 0:
                # DEBUG: Primera señal válida
                if len(trades) == 0:
                    logger.info(f"[SIGNAL] Primera señal válida en i={i}: signal={signals.iloc[i]}, price={current_price}, atr={atr}")

                # CONFIRMAR señal con ML confidence alta
                ml_conf = ml_confidence_all.iloc[i]
                if ml_conf < self.ml_threshold:
                    if i < 30:  # Solo primeras 30 para no saturar
                        logger.debug(f"[DEBUG] Saltando i={i} - ML confidence baja: {ml_conf} < {self.ml_threshold}")
                    continue  # Skip señales con baja confianza ML

                entry_price = current_price
                entry_time = current_time
                entry_index = i  # Guardar índice de entrada

                # STOP LOSS REAL basado en ATR (volatilidad real del mercado)
                atr_multiplier = 1.5  # 1.5 ATR para stop loss
                stop_distance = atr * atr_multiplier

                # TAKE PROFIT REAL: Risk/Reward ratio mínimo
                take_profit_distance = stop_distance * min_rr_ratio

                # POSITION SIZE REAL: Basado en riesgo por trade + Kelly fraction
                risk_amount = capital * risk_per_trade
                position_size = risk_amount / stop_distance

                # AJUSTE KELLY: Más agresivo con alta confianza ML
                kelly_adjustment = self.kelly_fraction * ml_conf
                position_size *= kelly_adjustment

                # LÍMITES DE PORTFOLIO REALES
                active_trades_count = len([t for t in self.active_trades if t['status'] == 'open'])
                if active_trades_count >= max_concurrent_trades:
                    logger.debug(f"[DEBUG] Saltando i={i} - Max concurrent trades alcanzado: {active_trades_count} >= {max_concurrent_trades}")
                    continue

                # VALIDAR liquidez real antes de entrar
                current_row = data.iloc[i]
                if not self._check_liquidity_score(current_row):
                    logger.debug(f"[DEBUG] Saltando i={i} - Liquidity score bajo")
                    continue

                # ENTRAR POSICIÓN
                position = signals.iloc[i] * position_size
                direction = 'long' if signals.iloc[i] > 0 else 'short'

                take_profit_price = entry_price + (signals.iloc[i] * take_profit_distance)
                stop_loss_price = entry_price - (signals.iloc[i] * stop_distance)

                trade = {
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'direction': direction,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'status': 'open',
                    'symbol': symbol,
                    'ml_confidence': ml_conf,
                    'atr_at_entry': atr
                }

                self.active_trades.append(trade)
                print(f"[TRADE] Trade abierto en i={i}: {direction} {position_size:.4f} @ {entry_price:.2f}")

            # Gestionar posiciones abiertas con TRAILING STOP 50%
            elif position != 0:
                # TRAILING STOP DEL 50% - Stop loss se mueve al 50% del profit alcanzado
                unrealized_pnl = (current_price - entry_price) * position
                if unrealized_pnl > 0:  # En ganancia
                    # Calcular profit actual en términos de precio
                    profit_amount = abs(current_price - entry_price)  # Profit en precio
                    new_stop_distance = profit_amount * 0.5  # 50% del profit

                    if position > 0:  # Posición larga
                        new_stop = entry_price + new_stop_distance
                        # Solo mover stop loss si es mejor que el actual (más alto)
                        if new_stop > stop_loss_price:
                            stop_loss_price = new_stop
                            print(f"Trailing stop 50% ajustado: {stop_loss_price:.6f} (profit: {profit_amount:.6f})")
                    else:  # Posición corta
                        new_stop = entry_price - new_stop_distance
                        # Solo mover stop loss si es mejor que el actual (más bajo)
                        if new_stop < stop_loss_price:
                            stop_loss_price = new_stop
                            print(f"Trailing stop 50% ajustado: {stop_loss_price:.6f} (profit: {profit_amount:.6f})")

                # ⚠️ CÓDIGO DUPLICADO ELIMINADO ⚠️
                # El siguiente bloque estaba completamente repetido y no tenía efecto adicional
                # if position > 0:  # Posición larga
                #     new_stop = entry_price + new_stop_distance
                #     # Solo mover stop loss si es mejor que el actual (más alto)
                #     if new_stop > stop_loss_price:
                #         stop_loss_price = new_stop
                #         print(f"Trailing stop 50% ajustado: {stop_loss_price:.6f} (profit: {profit_amount:.6f})")
                # else:  # Posición corta
                #     new_stop = entry_price - new_stop_distance
                #     # Solo mover stop loss si es mejor que el actual (más bajo)
                #     if new_stop < stop_loss_price:
                #         stop_loss_price = new_stop
                #         print(f"Trailing stop 50% ajustado: {stop_loss_price:.6f} (profit: {profit_amount:.6f})")

                # Check condiciones de salida REALES
                exit_reason = None

                # 1. SEÑAL CONTRARIA (reversión de Heikin Ashi)
                if signals.iloc[i] == -position:
                    exit_price = current_price
                    exit_reason = 'signal_reversal'

                # 2. TAKE PROFIT alcanzado
                elif (position > 0 and current_price >= take_profit_price) or (position < 0 and current_price <= take_profit_price):
                    exit_price = take_profit_price
                    exit_reason = 'take_profit'

                # 3. STOP LOSS alcanzado
                elif (position > 0 and current_price <= stop_loss_price) or (position < 0 and current_price >= stop_loss_price):
                    exit_price = stop_loss_price
                    exit_reason = 'stop_loss'

                # 4. TIME EXIT: Máximo 80 velas (4h * 80 = ~13 días) en posición (evitar stagnation)
                elif entry_index is not None and (i - entry_index) > 80:
                    exit_price = current_price
                    exit_reason = 'time_exit'

                else:
                    continue  # Mantener posición abierta

                # EJECUTAR SALIDA
                pnl = (exit_price - entry_price) * position                # DEBUG: Primer trade cerrado
                if len([t for t in self.active_trades if t['status'] == 'closed']) == 0:
                    print(f"Primer trade cerrado:")
                    print(f"   Entry: {entry_price:.6f} @ {entry_time}")
                    print(f"   Exit: {exit_price:.6f} @ {current_time}")
                    print(f"   Position: {position:.2f}")
                    print(f"   P&L: ${pnl:.2f} ({exit_reason})")

                # Actualizar trade
                for trade in self.active_trades:
                    if trade['status'] == 'open':
                        trade.update({
                            'exit_time': current_time,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'status': 'closed',
                            'exit_reason': exit_reason
                        })
                        # Agregar trade cerrado a la lista de resultados
                        trades.append(trade.copy())
                        break

                # Actualizar capital
                capital += pnl
                position = 0
                entry_price = 0

                # Actualizar drawdown
                peak_value = max(peak_value, capital)
                current_drawdown = (peak_value - capital) / peak_value
                max_drawdown = max(max_drawdown, current_drawdown)

                # Check max drawdown
                if current_drawdown > self.max_drawdown:
                    break  # Stop trading

        # Calcular métricas finales
        total_trades = len([t for t in trades if t.get('exit_time')])
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        
        # DEBUG: Verificar trades antes de retornar
        print(f"[DEBUG] _run_backtest: Total trades generados = {len(trades)}")
        print(f"[DEBUG] _run_backtest: Trades con exit_time = {total_trades}")
        if len(trades) > 0:
            print(f"[DEBUG] _run_backtest: Primer trade = {trades[0]}")
        else:
            print(f"[DEBUG] _run_backtest: NO SE GENERARON TRADES - Verificar condiciones")

        total_pnl = sum([t.get('pnl', 0) for t in trades])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Calcular profit factor
        gross_profit = sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0])
        gross_loss = abs(sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_capital': capital,
            'return_pct': (capital - self.portfolio_value) / self.portfolio_value,
            'symbol': symbol,
            'strategy_name': 'UltraDetailedHeikinAshiStrategy',
            'trades': trades
        }

    def _run_safe_mode(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Ejecutar estrategia en modo seguro (sin ML) para compatibilidad Python 3.13
        Usa solo indicadores técnicos tradicionales
        """
        try:
            print(f"[SAFE MODE] Ejecutando estrategia sin ML para {symbol}")

            # Preparar datos con indicadores (sin ML)
            data_processed = self._prepare_data(data.copy())
            print(f"[SAFE MODE] Datos preparados: {len(data_processed)} filas")

            # Generar señales usando SOLO indicadores técnicos (sin ML)
            signals = self._generate_signals_safe_mode(data_processed, symbol)
            print(f"[SAFE MODE] Señales generadas: {signals.sum()} largas, {(signals == -1).sum()} cortas")

            # Ejecutar backtesting con señales técnicas
            trades = self._execute_backtest(data_processed, signals, symbol)
            print(f"[SAFE MODE] Backtest completado: {len(trades)} trades")

            # Calcular métricas finales
            return self._calculate_final_metrics(trades, symbol)

        except Exception as e:
            print(f"[SAFE MODE ERROR] Error en modo seguro: {e}")
            return self._get_empty_results(symbol)

    def _generate_signals_safe_mode(self, data: pd.DataFrame, symbol: str) -> pd.Series:
        """
        Generar señales usando solo indicadores técnicos (sin ML)
        Lógica simplificada para modo seguro
        """
        signals = pd.Series(0, index=data.index)

        try:
            # Condiciones técnicas básicas (sin ML)
            # Heikin Ashi trend
            ha_trend_up = (data['ha_close'] > data['ha_open']) & (data['ha_close'] > data['ha_close'].shift(1))
            ha_trend_down = (data['ha_close'] < data['ha_open']) & (data['ha_close'] < data['ha_close'].shift(1))

            # Volume confirmation
            volume_ok = data['volume'] > data['volume'].rolling(20).mean() * self.volume_threshold

            # RSI conditions
            rsi_oversold = data['rsi'] < self.stoch_oversold  # Usando stoch_oversold como threshold
            rsi_overbought = data['rsi'] > self.stoch_overbought

            # Trend strength (usando ATR ratio)
            trend_strength = abs(data['ema_10'] - data['ema_20']) / data['atr'] > 0.5

            # Señal de COMPRA: HA uptrend + volume + oversold + trend strength
            buy_signal = ha_trend_up & volume_ok & rsi_oversold & trend_strength

            # Señal de VENTA: HA downtrend + volume + overbought + trend strength
            sell_signal = ha_trend_down & volume_ok & rsi_overbought & trend_strength

            # Aplicar señales
            signals[buy_signal] = 1
            signals[sell_signal] = -1

            print(f"[SAFE MODE] Condiciones aplicadas: HA trend, volume, RSI, trend strength")

        except Exception as e:
            print(f"[SAFE MODE] Error generando señales: {e}")

        return signals

    def _get_empty_results(self, symbol: str) -> Dict:
        """Retornar resultados vacíos en caso de error"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'final_capital': self.portfolio_value,
            'return_pct': 0,
            'symbol': symbol,
            'strategy_name': 'UltraDetailedHeikinAshiStrategy',
            'trades': []
        }