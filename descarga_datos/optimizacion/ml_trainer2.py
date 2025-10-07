#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML TRAINER 2 - Entrenador Avanzado para Redes Neuronales ML2
============================================================

Entrenador especializado para las redes neuronales avanzadas de la estrategia
UltraDetailedHeikinAshiML2. Optimizado para arquitecturas MLP eficientes
con bajo consumo de recursos.

CARACTERÍSTICAS v2:
- Redes Neuronales MLP avanzadas (128→64→32 neuronas)
- Arquitecturas optimizadas para recursos limitados
- Early stopping y regularización avanzada
- Entrenamiento estable con learning rate adaptativo
- Modelos duales: avanzado y ligero

MODELOS SOPORTADOS:
- neural_network_advanced: Arquitectura completa para máxima precisión
- neural_network_light: Versión ligera para recursos limitados

COMPATIBLE CON: UltraDetailedHeikinAshiML2Strategy
"""

import sys
import os
# Añadir el directorio padre (descarga_datos) al path para importar módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import joblib
import json
# Importaciones lazy de sklearn para compatibilidad Python 3.13
# from sklearn.neural_network import MLPClassifier
# from sklearn.model_selection import TimeSeriesSplit, cross_val_score
# from sklearn.metrics import confusion_matrix, roc_auc_score
from config.config_loader import load_config
# Importación lazy para evitar KeyboardInterrupt en Python 3.13
# from core.downloader import AdvancedDataDownloader  # Importado solo cuando se necesita
from indicators.technical_indicators import TechnicalIndicators
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MLTrainer2:
    def __init__(self, symbol, timeframe='4h'):
        self.symbol = symbol
        self.timeframe = timeframe
        # Usar load_config_from_yaml que retorna un objeto Config
        from config.config_loader import load_config_from_yaml
        self.config = load_config_from_yaml()

        # Configuración de modelos ML activados/desactivados
        ml_config_dict = self.config.ml_training.training if hasattr(self.config, 'ml_training') else {}
        self.ml_config = ml_config_dict if isinstance(ml_config_dict, dict) else {}
        enabled_models_dict = self.config.ml_training.enabled_models if hasattr(self.config, 'ml_training') else {}
        self.enabled_models = enabled_models_dict if isinstance(enabled_models_dict, dict) else {
            'neural_network_advanced': True,  # Red neuronal avanzada para ML2
            'neural_network_light': True      # Red neuronal ligera para ML2
        }

        # Ajustar períodos según datos disponibles de SOL/USDT (2024-2025)
        self.train_start = '2024-12-26'
        self.train_end = '2025-06-30'
        self.val_start = '2025-07-01'
        self.val_end = '2025-10-06'
            
        self.models_dir = Path('models') / symbol.replace('/', '_')
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f'MLTrainer inicializado para {symbol} {timeframe}')
        logger.info(f'Modelos activados: {self.enabled_models}')
        logger.info(f'Período entrenamiento: {self.train_start} → {self.train_end}')
        logger.info(f'Período validación: {self.val_start} → {self.val_end}')

    async def download_data(self):
        """Carga datos locales para el símbolo (VPN disponible pero usamos locales por estabilidad)"""
        try:
            # Usar datos locales para estabilidad
            data = self._load_local_data()
            if data is None or data.empty:
                raise ValueError(f"No hay datos locales disponibles para {self.symbol}")

            logger.info(f"Datos locales cargados: {len(data)} velas")
            return data

        except Exception as e:
            logger.error(f"Error cargando datos locales: {e}")
            raise

    def prepare_features(self, df):
        # Usar el objeto Config correctamente
        from indicators.technical_indicators import TechnicalIndicators
        indicator = TechnicalIndicators(self.config)
        df = indicator.calculate_all_indicators(df)
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
        return df

    def create_labels(self, df):
        future_returns = df['close'].shift(-5) / df['close'] - 1
        labels = pd.Series(index=df.index, dtype=float)
        labels[future_returns > 0.005] = 1
        labels[future_returns < -0.005] = 0
        return labels

    def select_features(self):
        return ['ha_close', 'ha_open', 'ha_high', 'ha_low', 'ema_10', 'ema_20', 'ema_200', 'macd', 'macd_signal', 'adx', 'sar', 'atr', 'volatility', 'bb_upper', 'bb_lower', 'rsi', 'momentum_5', 'momentum_10', 'volume_ratio', 'price_position', 'trend_strength', 'returns', 'log_returns']

    def train_models(self, X_train, y_train, X_val, y_val):
        logger.info('Entrenando modelos ML...')
        logger.info(f'Modelos activados: {self.enabled_models}')
        
        # VALIDACIÓN CRÍTICA: Verificar que hay datos suficientes
        if len(X_train) == 0:
            raise RuntimeError(f'❌ Período de entrenamiento vacío. Train: {self.train_start} → {self.train_end}. Verificar datos disponibles.')
        
        if len(X_train) < 100:
            raise RuntimeError(f'❌ Datos de entrenamiento insuficientes: {len(X_train)} samples. Mínimo requerido: 100')
        
        if len(X_val) == 0:
            raise RuntimeError(f'❌ Período de validación vacío. Val: {self.val_start} → {self.val_end}. Verificar datos disponibles.')
        
        logger.info(f'✅ Datos válidos - Train: {len(X_train)} samples, Val: {len(X_val)} samples')

        # Importaciones lazy de sklearn para compatibilidad Python 3.13 - SOLO REDES NEURONALES
        try:
            from sklearn.neural_network import MLPClassifier
            from sklearn.model_selection import TimeSeriesSplit, cross_val_score
            from sklearn.metrics import confusion_matrix, roc_auc_score
            logger.info('Importaciones sklearn para redes neuronales exitosas')
        except KeyboardInterrupt:
            logger.error('KeyboardInterrupt durante importación sklearn - abortando entrenamiento')
            return {}, None
        except Exception as e:
            logger.error(f'Error importando sklearn: {e}')
            return {}, None

        models = {}

        # Configuración de parámetros de modelos desde Config
        models_config = {}
        if hasattr(self.config, 'ml_training') and hasattr(self.config.ml_training, 'models'):
            models_config = self.config.ml_training.models if isinstance(self.config.ml_training.models, dict) else {}

        # RED NEURONAL AVANZADA - Arquitectura completa para máxima precisión
        if self.enabled_models.get('neural_network_advanced', True):
            nn_advanced_config = models_config.get('neural_network_advanced', {}) if models_config else {}
            models['neural_network_advanced'] = MLPClassifier(
                hidden_layer_sizes=(128, 64, 32),  # Arquitectura profunda pero eficiente
                activation='relu',                   # ReLU para gradientes estables
                solver='adam',                      # Adam optimizer eficiente
                alpha=nn_advanced_config.get('alpha', 0.001),  # Regularización L2
                batch_size=nn_advanced_config.get('batch_size', 64),  # Batch size optimizado
                learning_rate='adaptive',           # Learning rate adaptativo
                learning_rate_init=nn_advanced_config.get('learning_rate_init', 0.001),
                max_iter=nn_advanced_config.get('max_iter', 500),  # Iteraciones suficientes
                early_stopping=True,                # Early stopping para evitar overfitting
                validation_fraction=0.2,            # Validación interna
                n_iter_no_change=20,                # Paciencia para early stopping
                random_state=42,
                verbose=False
            )
            logger.info('Red Neuronal Avanzada activada')

        # RED NEURONAL LIGERA - Arquitectura simplificada para recursos limitados
        if self.enabled_models.get('neural_network_light', True):
            nn_light_config = models_config.get('neural_network_light', {}) if models_config else {}
            models['neural_network_light'] = MLPClassifier(
                hidden_layer_sizes=(64, 32),        # Arquitectura ligera
                activation='relu',
                solver='adam',
                alpha=nn_light_config.get('alpha', 0.01),  # Regularización más fuerte
                batch_size=nn_light_config.get('batch_size', 128),  # Batch size mayor
                learning_rate='adaptive',
                learning_rate_init=nn_light_config.get('learning_rate_init', 0.01),  # LR inicial más alto
                max_iter=nn_light_config.get('max_iter', 300),  # Menos iteraciones
                early_stopping=True,
                validation_fraction=0.2,
                n_iter_no_change=15,                # Menos paciencia
                random_state=42,
                verbose=False
            )
            logger.info('Red Neuronal Ligera activada')

        results = {}
        best_model, best_score = None, 0
        tscv = TimeSeriesSplit(n_splits=3)

        for name, model in models.items():
            logger.info(f'Entrenando {name}...')
            try:
                cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='roc_auc', n_jobs=1)
                logger.info(f'{name} - CV Mean: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})')

                model.fit(X_train, y_train)
                y_val_pred = model.predict(X_val)
                y_val_proba = model.predict_proba(X_val)[:, 1]
                val_auc = roc_auc_score(y_val, y_val_proba)
                val_accuracy = (y_val_pred == y_val).mean()

                logger.info(f'{name} - Validation AUC: {val_auc:.4f}, Accuracy: {val_accuracy:.4f}')

                results[name] = {
                    'model': model,
                    'cv_scores': cv_scores.tolist(),
                    'cv_mean': float(cv_scores.mean()),
                    'cv_std': float(cv_scores.std()),
                    'val_auc': float(val_auc),
                    'val_accuracy': float(val_accuracy),
                    'confusion_matrix': confusion_matrix(y_val, y_val_pred).tolist()
                }

                if val_auc > best_score:
                    best_score, best_model = val_auc, name

            except Exception as e:
                logger.error(f'Error entrenando {name}: {e}')
                continue

        if not results:
            raise RuntimeError('No se pudo entrenar ningún modelo ML')

        logger.info(f'Mejor modelo: {best_model} (AUC: {best_score:.4f})')
        return results, best_model

    def save_models(self, results, feature_names):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for name, data in results.items():
            model_path = self.models_dir / f'{name}_{timestamp}.joblib'
            joblib.dump(data['model'], model_path)
            metadata = {'symbol': self.symbol, 'timeframe': self.timeframe, 'model_type': name, 'features': feature_names, 'cv_mean': data['cv_mean'], 'val_auc': data['val_auc'], 'timestamp': timestamp}
            with open(self.models_dir / f'{name}_{timestamp}_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

    async def run(self):
        logger.info('INICIANDO ENTRENAMIENTO ML')
        df = await self.download_data()
        df = self.prepare_features(df)
        labels = self.create_labels(df)
        feature_cols = [col for col in self.select_features() if col in df.columns]
        train_mask = (df.index >= self.train_start) & (df.index <= self.train_end)
        val_mask = (df.index >= self.val_start) & (df.index <= self.val_end)
        X_train = df.loc[train_mask, feature_cols].fillna(0)
        y_train = labels.loc[train_mask].dropna()
        X_val = df.loc[val_mask, feature_cols].fillna(0)
        y_val = labels.loc[val_mask].dropna()
        common_train = X_train.index.intersection(y_train.index)
        X_train, y_train = X_train.loc[common_train], y_train.loc[common_train]
        common_val = X_val.index.intersection(y_val.index)
        X_val, y_val = X_val.loc[common_val], y_val.loc[common_val]
        logger.info(f'Train: {len(X_train)}, Val: {len(X_val)}')
        results, best_model = self.train_models(X_train, y_train, X_val, y_val)
        self.save_models(results, feature_cols)
        logger.info('ENTRENAMIENTO COMPLETADO')
        return results, best_model

    def _load_local_data(self):
        """Cargar datos locales desde CSV si existen"""
        from pathlib import Path
        
        symbol_clean = self.symbol.replace('/', '_')
        csv_path = Path('data/csv') / f'{symbol_clean}_{self.timeframe}.csv'
        
        if not csv_path.exists():
            logger.warning(f'No se encontró archivo CSV local: {csv_path}')
            return None
        
        try:
            df = pd.read_csv(csv_path)
            logger.info(f'Datos locales cargados desde {csv_path}: {len(df)} registros')
            
            # CRÍTICO: Asegurar timestamp como índice
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
            elif 'Unnamed: 0' in df.columns:
                # Algunas veces timestamp está en Unnamed: 0
                df['timestamp'] = pd.to_datetime(df['Unnamed: 0'])
                df = df.set_index('timestamp')
                df = df.drop('Unnamed: 0', axis=1, errors='ignore')
            else:
                # Si no hay columna timestamp, asumir que el índice ya es timestamp
                df.index = pd.to_datetime(df.index)
                df.index.name = 'timestamp'
            
            # Verificar columnas OHLCV básicas
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f'Faltan columnas requeridas: {missing_cols}')
                return None
            
            return df
        except Exception as e:
            logger.error(f'Error leyendo CSV local: {e}')
            return None

    def download_training_data(self):
        """Método síncrono para descargar datos de entrenamiento"""
        try:
            import asyncio
            # Crear un nuevo event loop si no hay uno corriendo
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si hay un loop corriendo, necesitamos usar asyncio.run_in_executor o similar
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.download_data())
                        return future.result()
                else:
                    return asyncio.run(self.download_data())
            except RuntimeError:
                # No hay event loop, crear uno nuevo
                return asyncio.run(self.download_data())
        except Exception as e:
            logger.error(f"Error en download_training_data: {e}")
            raise

    def train_all_models(self):
        """Método síncrono para entrenar todos los modelos"""
        import asyncio
        return asyncio.run(self.run())

async def main():
    # SOL/USDT con VPN - sin restricciones geográficas
    symbol = 'SOL/USDT'
    logger.info(f'═══════════════════════════════════════════════════')
    logger.info(f'🚀 ENTRENAMIENTO ML - {symbol}')
    logger.info(f'═══════════════════════════════════════════════════')
    trainer = MLTrainer2(symbol, '4h')
    await trainer.run()
    logger.info(f'✅ Entrenamiento completado para {symbol}')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
