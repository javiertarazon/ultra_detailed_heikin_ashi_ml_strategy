#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
# from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
# from sklearn.model_selection import TimeSeriesSplit, cross_val_score
# from sklearn.metrics import confusion_matrix, roc_auc_score
# try:
#     from xgboost import XGBClassifier
#     XGBOOST_AVAILABLE = True
# except ImportError:
#     XGBOOST_AVAILABLE = False
from config.config_loader import load_config
# Importación lazy para evitar KeyboardInterrupt en Python 3.13
# from core.downloader import AdvancedDataDownloader  # Importado solo cuando se necesita
from indicators.technical_indicators import TechnicalIndicators
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MLTrainer:
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
            'random_forest': True,
            'gradient_boosting': False,
            'neural_network': False
        }

        # Configuración de períodos de entrenamiento desde objeto Config
        if hasattr(self.config, 'ml_training'):
            training_config = self.config.ml_training.training
            self.train_start = training_config.get('train_start', '2023-01-01')
            self.train_end = training_config.get('train_end', '2023-12-31')
            self.val_start = training_config.get('val_start', '2024-01-01')
            self.val_end = training_config.get('val_end', '2025-10-06')
        else:
            self.train_start = '2023-01-01'
            self.train_end = '2023-12-31'
            self.val_start = '2024-01-01'
            self.val_end = '2025-10-06'
            
        self.models_dir = Path('models') / symbol.replace('/', '_')
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f'MLTrainer inicializado para {symbol} {timeframe}')
        logger.info(f'Modelos activados: {self.enabled_models}')
        logger.info(f'Período entrenamiento: {self.train_start} → {self.train_end}')
        logger.info(f'Período validación: {self.val_start} → {self.val_end}')

    async def download_data(self):
        logger.info('Descargando datos historicos...')
        
        # Primero intentar cargar datos locales
        local_data = None
        try:
            local_data = self._load_local_data()
            if local_data is not None and len(local_data) > 0:
                logger.info(f'Datos locales encontrados: {len(local_data)} velas')
                
                # Verificar si cubren el período completo requerido
                data_start = local_data.index.min()
                data_end = local_data.index.max()
                required_start = pd.Timestamp(self.train_start)
                required_end = pd.Timestamp(self.val_end)
                
                logger.info(f'Datos locales período: {data_start} → {data_end}')
                logger.info(f'Período requerido: {required_start} → {required_end}')
                
                # Si cubren el período, usar datos locales
                if data_start <= required_start and data_end >= required_end:
                    logger.info('✅ Datos locales cubren período completo')
                    return local_data
                else:
                    logger.warning('⚠️ Datos locales no cubren período completo. Se requiere descarga.')
        except Exception as e:
            logger.warning(f'Error cargando datos locales: {e}, intentando descarga...')
        
        # Si no hay datos locales suficientes, descargar
        logger.info('📥 Descargando datos desde exchange...')
        try:
            from core.downloader import AdvancedDataDownloader
            logger.info('AdvancedDataDownloader importado correctamente')
        except KeyboardInterrupt:
            logger.error('KeyboardInterrupt durante importación de AdvancedDataDownloader')
            raise RuntimeError('No se puede importar AdvancedDataDownloader')

        # CRÍTICO: Forzar descarga limpiando cache primero
        symbol_clean = self.symbol.replace('/', '_')
        csv_path = Path('data/csv') / f'{symbol_clean}_{self.timeframe}.csv'
        if csv_path.exists():
            logger.info(f'🗑️ Eliminando cache antiguo: {csv_path}')
            csv_path.unlink()
        
        # Crear config temporal para downloader con fechas correctas
        temp_config = self.config
        if hasattr(temp_config, 'backtesting'):
            # Temporalmente sobrescribir fechas de backtesting
            original_start = temp_config.backtesting.start_date
            original_end = temp_config.backtesting.end_date
            temp_config.backtesting.start_date = self.train_start
            temp_config.backtesting.end_date = self.val_end
            logger.info(f'🔧 Config temporal: {self.train_start} → {self.val_end}')

        downloader = AdvancedDataDownloader(temp_config)
        await downloader.initialize()
        try:
            # CRÍTICO: Usar fechas correctas para descargar
            logger.info(f'📥 Solicitando descarga: {self.train_start} → {self.val_end}')
            
            data = await downloader.download_multiple_symbols(
                [self.symbol], 
                self.timeframe, 
                start_date=self.train_start,  # DEBE usar train_start
                end_date=self.val_end          # DEBE usar val_end
            )
            
            if self.symbol not in data or data[self.symbol].empty:
                raise ValueError(f'No se descargaron datos para {self.symbol}')
            
            df = data[self.symbol]
            
            # CRÍTICO: Asegurar que timestamp esté como índice
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
            elif df.index.name != 'timestamp':
                # Si el índice no tiene nombre, asumirlo como timestamp
                df.index = pd.to_datetime(df.index)
                df.index.name = 'timestamp'
            
            logger.info(f'✅ Datos descargados: {len(df)} velas desde {df.index.min()} hasta {df.index.max()}')
            
            # VALIDAR que los datos cubren el período requerido
            if df.index.min() > pd.Timestamp(self.train_start):
                logger.error(f'❌ Datos descargados comienzan en {df.index.min()} pero necesitamos desde {self.train_start}')
                raise ValueError(f'Datos insuficientes: comienzan en {df.index.min()}, necesario desde {self.train_start}')
            
            return df
        finally:
            # Restaurar config original
            if hasattr(temp_config, 'backtesting'):
                temp_config.backtesting.start_date = original_start
                temp_config.backtesting.end_date = original_end
            await downloader.shutdown()

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

        # Importaciones lazy de sklearn para compatibilidad Python 3.13
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.model_selection import TimeSeriesSplit, cross_val_score
            from sklearn.metrics import confusion_matrix, roc_auc_score
            try:
                from xgboost import XGBClassifier  # type: ignore
                XGBOOST_AVAILABLE = True
            except ImportError:
                XGBOOST_AVAILABLE = False
            logger.info('Importaciones sklearn exitosas')
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

        # RandomForest - Siempre disponible
        if self.enabled_models.get('random_forest', True):
            rf_config = models_config.get('random_forest', {}) if models_config else {}
            models['RandomForest'] = RandomForestClassifier(
                n_estimators=rf_config.get('n_estimators', 100),
                max_depth=rf_config.get('max_depth', 10),
                random_state=rf_config.get('random_state', 42),
                n_jobs=rf_config.get('n_jobs', 1)  # Usar configuración del YAML, default 1 para Python 3.13
            )
            logger.info('RandomForest activado')

        # GradientBoosting - Activado/desactivado por configuración
        if self.enabled_models.get('gradient_boosting', False):
            gb_config = models_config.get('gradient_boosting', {}) if models_config else {}
            models['GradientBoosting'] = GradientBoostingClassifier(
                n_estimators=gb_config.get('n_estimators', 100),
                max_depth=gb_config.get('max_depth', 3),
                learning_rate=gb_config.get('learning_rate', 0.1),
                random_state=gb_config.get('random_state', 42)
            )
            logger.info('GradientBoosting activado')

        # Neural Network (XGBoost) - Activado/desactivado por configuración
        if self.enabled_models.get('neural_network', False) and XGBOOST_AVAILABLE:
            nn_config = models_config.get('neural_network', {}) if models_config else {}
            models['XGBoost'] = XGBClassifier(
                n_estimators=nn_config.get('n_estimators', 100),
                max_depth=nn_config.get('max_depth', 4),
                learning_rate=nn_config.get('learning_rate', 0.1),
                random_state=nn_config.get('random_state', 42),
                n_jobs=-1,
                eval_metric=nn_config.get('eval_metric', 'logloss')
            )
            logger.info('XGBoost (Neural Network) activado')
        elif self.enabled_models.get('neural_network', False) and not XGBOOST_AVAILABLE:
            logger.warning('XGBoost no está disponible. Instale con: pip install xgboost')

        if not models:
            raise ValueError('No hay modelos ML activados. Verifique la configuración enabled_models')

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
    # SOLO BTC/USDT con período ampliado (2020-2024)
    symbol = 'BTC/USDT'
    logger.info(f'═══════════════════════════════════════════════════')
    logger.info(f'🚀 ENTRENAMIENTO ML - {symbol}')
    logger.info(f'═══════════════════════════════════════════════════')
    trainer = MLTrainer(symbol, '4h')
    await trainer.run()
    logger.info(f'✅ Entrenamiento completado para {symbol}')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
