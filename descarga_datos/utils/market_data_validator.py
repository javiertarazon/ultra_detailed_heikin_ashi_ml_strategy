#!/usr/bin/env python3
"""
Market Data Validator - Sistema de verificación de autenticidad de datos
Implementa validaciones estadísticas y heurísticas para confirmar que los datos
son del mercado real y no sintéticos/generados artificialmente.
"""
import numpy as np
import pandas as pd
import hashlib
from utils.logger import get_logger

logger = get_logger("__name__")

class MarketDataValidator:
    """
    Validador de autenticidad de datos de mercado financiero.
    Implementa métodos estadísticos para detectar datos sintéticos.
    """
    
    def __init__(self, db_path: str = "data/data.db"):
        """
        Inicializa el validador con la conexión a la base de datos.
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        import os
        # Normalizar ruta: si comienza con "data/", cambiar a descarga_datos/data/
        if db_path.startswith("data/"):
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        self.db_path = db_path
        self._init_audit_table()
    
    def _init_audit_table(self):
        """Inicializa la tabla de auditoría de datos en SQLite"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS data_audit_log (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    rows INTEGER,
                    hash_value TEXT,
                    normality_p_value REAL,
                    kurtosis REAL,
                    volatility_clusters REAL, 
                    is_real_data INTEGER,
                    timestamp INTEGER DEFAULT (strftime('%s','now'))
                )
                """)
            logger.info("Tabla de auditoría de datos inicializada")
        except Exception as e:
            logger.error(f"Error inicializando tabla de auditoría: {e}")
    
    def detect_synthetic_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detecta patrones específicos de datos sintéticos o generados artificialmente.
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            Dict con resultados de la detección
        """
        patterns = {
            'uniform_gaps': False,
            'perfect_patterns': False,
            'repeated_sequences': False,
            'abnormal_precision': False,
            'unrealistic_patterns': False
        }
        
        try:
            # 1. Detectar espaciado uniforme anormal
            if 'timestamp' in df.columns:
                # Convertir timestamp a datetime si es necesario
                if isinstance(df['timestamp'].iloc[0], (int, float, str)):
                    timestamps = pd.to_datetime(df['timestamp'])
                else:
                    timestamps = df['timestamp']
                
                # Calcular diferencias de tiempo
                time_diffs = timestamps.diff().dropna()
                
                # En datos reales, las diferencias de tiempo no son perfectamente uniformes
                # incluso en marcos de tiempo regulares debido a fines de semana, días festivos, etc.
                unique_diffs = time_diffs.unique()
                
                # Si hay muy pocas diferencias únicas (< 3) es sospechoso
                patterns['uniform_gaps'] = len(unique_diffs) < 3
            
            # 2. Buscar patrones perfectos o repetitivos
            if 'close' in df.columns and 'open' in df.columns:
                # Calcular retornos
                returns = df['close'].pct_change().dropna()
                
                # En datos reales, rara vez hay secuencias largas idénticas
                # Buscar secuencias repetidas de retornos (ventanas de 5)
                patterns['repeated_sequences'] = self._detect_repeated_sequences(returns, window=5)
                
                # 3. Buscar precisión anormal
                # Los datos reales suelen tener precisión variable
                price_precisions = set([len(str(p).split('.')[-1]) for p in df['close'] if '.' in str(p)])
                patterns['abnormal_precision'] = len(price_precisions) < 2
                
                # 4. Buscar patrones irreales
                # En datos reales, high-low nunca es cero y no hay patrones perfectos
                zero_range_count = ((df['high'] - df['low']) == 0).sum()
                patterns['unrealistic_patterns'] = zero_range_count > len(df) * 0.05  # >5% es sospechoso
            
            # Determinar si hay sospecha de datos sintéticos
            synthetic_score = sum(1 for p in patterns.values() if p)
            is_suspicious = synthetic_score >= 2  # Si 2 o más patrones son sospechosos
            
            return {
                'is_suspicious': is_suspicious,
                'synthetic_score': synthetic_score,
                'detected_patterns': patterns
            }
            
        except Exception as e:
            logger.error(f"Error detectando patrones sintéticos: {e}")
            return {'is_suspicious': False, 'error': str(e), 'patterns': patterns}
    
    def _detect_repeated_sequences(self, series, window=5):
        """Detecta secuencias repetidas en una serie temporal"""
        if len(series) < window * 2:
            return False
            
        # Convertir a cadenas con precisión limitada para evitar problemas de punto flotante
        str_values = [f"{x:.6f}" for x in series]
        
        # Crear ventanas como cadenas
        windows = []
        for i in range(len(str_values) - window + 1):
            windows.append(','.join(str_values[i:i+window]))
            
        # Contar ocurrencias
        from collections import Counter
        counts = Counter(windows)
        
        # Verificar si alguna secuencia se repite más de lo esperado
        max_repeats = max(counts.values()) if counts else 0
        return max_repeats > 3  # Más de 3 repeticiones exactas es sospechoso
        
    def validate_real_market_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Valida que los datos tengan características estadísticas de mercados reales
        
        Args:
            df: DataFrame con datos OHLCV (debe incluir columna 'close')
            
        Returns:
            Dict con resultado de validación y métricas estadísticas
        """
        try:
            # Verificar que el dataframe tiene los datos necesarios
            if 'close' not in df.columns or len(df) < 100:
                return {
                    'is_real_data': False,
                    'error': f"Datos insuficientes o formato incorrecto: {len(df)} filas",
                    'metrics': {}
                }
            
            # Calcular retornos logarítmicos (característica fundamental de datos financieros)
            log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
            
            # Si no hay suficientes retornos para análisis estadístico
            if len(log_returns) < 50:
                return {
                    'is_real_data': False, 
                    'error': f"Insuficientes puntos de datos para análisis: {len(log_returns)}",
                    'metrics': {}
                }
                
            try:
                # 1. Verificar distribución de retornos (no perfectamente normal)
                from scipy import stats
                _, normality_p_value = stats.normaltest(log_returns)
                
                # 2. Verificar presencia de leptocurtosis (característica de mercados reales)
                kurtosis = stats.kurtosis(log_returns)
                
                # 3. Verificar volatilidad no uniforme (clusters de volatilidad)
                volatility_clusters = np.abs(log_returns).rolling(20).std().std() / np.abs(log_returns).std()
                
                # Validar todas las métricas
                is_real_data = (
                    normality_p_value < 0.05 and  # No perfectamente normal (p-valor bajo)
                    kurtosis > 1.0 and            # Leptocurtosis presente
                    volatility_clusters > 0.2     # Presencia de clusters de volatilidad
                )
                
                # Validación adicional con detector de datos sintéticos
                synthetic_check = self.detect_synthetic_patterns(df)
                
                # Combinar todos los criterios
                is_real_data = (
                    is_real_data and 
                    not synthetic_check['is_suspicious']
                )
                
                return {
                    'is_real_data': bool(is_real_data),
                    'metrics': {
                        'normality_p_value': float(normality_p_value),
                        'kurtosis': float(kurtosis),
                        'volatility_clusters': float(volatility_clusters)
                    },
                    'synthetic_check': synthetic_check
                }
            except ImportError:
                logger.warning("No se pudo importar scipy para análisis estadístico")
                # Validación alternativa básica si no está disponible scipy
                # Verificar distribución de retornos usando estadísticas básicas
                abs_returns = np.abs(log_returns)
                skew = np.mean(log_returns**3) / (np.std(log_returns)**3)
                kurt = np.mean(log_returns**4) / (np.std(log_returns)**4) - 3
                
                # Volatilidad por periodos 
                vol_periods = []
                for i in range(0, len(log_returns), 20):
                    if i + 20 <= len(log_returns):
                        vol_periods.append(np.std(log_returns[i:i+20]))
                
                vol_of_vol = np.std(vol_periods) if vol_periods else 0
                
                # Criterios básicos
                is_real_data = (
                    abs(skew) > 0.1 and    # Asimetría no nula
                    kurt > 1.0 and         # Leptocurtosis presente
                    vol_of_vol > 0.0001    # Variación en la volatilidad
                )
                
                return {
                    'is_real_data': bool(is_real_data),
                    'metrics': {
                        'skew': float(skew),
                        'kurtosis': float(kurt),
                        'volatility_variation': float(vol_of_vol)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error validando características del mercado: {e}")
            import traceback
            traceback.print_exc()
            return {
                'is_real_data': False,
                'error': str(e),
                'metrics': {}
            }
    
    def create_data_hash(self, df: pd.DataFrame) -> str:
        """
        Crea un hash único de los datos para verificar integridad
        
        Args:
            df: DataFrame con los datos
            
        Returns:
            Hash SHA-256 de los datos
        """
        try:
            # Convertir los valores numéricos a una representación estable
            if df.empty:
                return ""
                
            # Asegurarse de que solo usamos columnas numéricas
            numeric_df = df.select_dtypes(include=['number'])
            if numeric_df.empty:
                logger.warning("No hay columnas numéricas para hash")
                # Usar todo el dataframe como string
                data_str = df.to_string()
            else:
                # Usar estadísticas sobre columnas numéricas
                values = numeric_df.describe().round(6).values.flatten()
                # Crear string único y determinístico
                data_str = f"{len(df)}_{numeric_df.columns.tolist()}_{values.tolist()}"
            
            # Generar hash
            return hashlib.sha256(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error creando hash de datos: {e}")
            return ""
    
    def register_data_audit(self, symbol: str, timeframe: str, origin: str, 
                            df: pd.DataFrame, validation_result: Dict[str, Any]) -> bool:
        """
        Registra una entrada de auditoría para los datos
        
        Args:
            symbol: Símbolo del instrumento
            timeframe: Timeframe de los datos
            origin: Origen de los datos (sqlite, csv, download)
            df: DataFrame con los datos
            validation_result: Resultado de la validación
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            # Crear hash de los datos
            hash_value = self.create_data_hash(df)
            
            # Extraer métricas de validación
            metrics = validation_result.get('metrics', {})
            is_real_data = int(validation_result.get('is_real_data', False))
            
            # Valores para la base de datos
            normality = metrics.get('normality_p_value', None)
            kurtosis = metrics.get('kurtosis', None)
            vol_clusters = metrics.get('volatility_clusters', None)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT INTO data_audit_log(
                    symbol, timeframe, origin, rows, hash_value, 
                    normality_p_value, kurtosis, volatility_clusters, is_real_data
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, timeframe, origin, len(df), hash_value,
                    normality, kurtosis, vol_clusters, is_real_data
                ))
                
            logger.info(f"✅ Auditoría: Datos {symbol} {timeframe} registrados (origen: {origin}, filas: {len(df)})")
            return True
        except Exception as e:
            logger.error(f"Error registrando auditoría: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_data_origin(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Devuelve el origen de los datos y sus metadatos desde la tabla de metadatos
        
        Args:
            symbol: Símbolo del instrumento
            timeframe: Timeframe de los datos
            
        Returns:
            Dict con información de origen y metadatos
        """
        try:
            table_name = f"data_metadata"
            
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT * FROM data_metadata 
                WHERE symbol = ? AND timeframe = ?
                """
                
                cursor = conn.execute(query, (symbol, timeframe))
                row = cursor.fetchone()
                
                if row:
                    # Convertir a dict usando descripción de columnas
                    col_names = [desc[0] for desc in cursor.description]
                    metadata = dict(zip(col_names, row))
                    
                    return {
                        'source': metadata.get('source_exchange', 'unknown'),
                        'origin': 'sqlite',
                        'start_ts': metadata.get('start_ts'),
                        'end_ts': metadata.get('end_ts'),
                        'records': metadata.get('records', 0),
                        'coverage_pct': metadata.get('coverage_pct', 0)
                    }
                
                return {'origin': 'unknown', 'records': 0}
        except Exception as e:
            logger.error(f"Error obteniendo origen de datos: {e}")
            return {'origin': 'error', 'error': str(e)}
    
    def check_data_integrity(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Verificación completa de integridad de datos:
        1. Validación estadística (características de mercado)
        2. Creación de hash para verificación
        3. Registro en log de auditoría
        
        Args:
            symbol: Símbolo del instrumento
            timeframe: Timeframe de los datos
            df: DataFrame con los datos
            
        Returns:
            Dict con resultado de verificación
        """
        # 1. Validar características estadísticas
        validation = self.validate_real_market_data(df)
        is_real_data = validation.get('is_real_data', False)
        
        # 2. Crear hash de los datos
        data_hash = self.create_data_hash(df)
        
        # 3. Verificar si tenemos registro previo de estos datos
        origin = self._get_data_history(symbol, timeframe, data_hash)
        
        # 4. Registrar esta verificación en el log de auditoría
        self.register_data_audit(
            symbol=symbol,
            timeframe=timeframe, 
            origin=origin.get('origin', 'new_verification'),
            df=df,
            validation_result=validation
        )
        
        return {
            'is_real_data': is_real_data,
            'origin': origin.get('origin', 'unknown'),
            'hash': data_hash,
            'validation': validation,
            'rows': len(df),
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_data_history(self, symbol: str, timeframe: str, hash_value: str) -> Dict[str, Any]:
        """
        Busca en el historial de auditoría si estos datos han sido verificados antes
        
        Args:
            symbol: Símbolo del instrumento 
            timeframe: Timeframe de los datos
            hash_value: Hash de los datos a verificar
            
        Returns:
            Dict con información del historial
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT * FROM data_audit_log
                WHERE symbol = ? AND timeframe = ? AND hash_value = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """
                
                cursor = conn.execute(query, (symbol, timeframe, hash_value))
                row = cursor.fetchone()
                
                if row:
                    # Convertir a dict usando descripción de columnas
                    col_names = [desc[0] for desc in cursor.description]
                    audit_record = dict(zip(col_names, row))
                    
                    return {
                        'origin': audit_record.get('origin', 'unknown'),
                        'timestamp': audit_record.get('timestamp'),
                        'is_real_data': bool(audit_record.get('is_real_data', 0)),
                        'found': True
                    }
                
                return {'origin': 'new', 'found': False}
        except Exception as e:
            logger.error(f"Error buscando historial de datos: {e}")
            return {'origin': 'error', 'error': str(e), 'found': False}


# Función auxiliar para usar directamente
def validate_dataframe(df: pd.DataFrame, symbol: str = "", timeframe: str = "") -> Dict[str, Any]:
    """
    Función de conveniencia para validar un DataFrame directamente
    
    Args:
        df: DataFrame con datos OHLCV
        symbol: Símbolo opcional para registrar
        timeframe: Timeframe opcional para registrar
        
    Returns:
        Dict con resultado de validación
    """
    validator = MarketDataValidator()
    validation = validator.validate_real_market_data(df)
    
    # Si se proporcionó símbolo y timeframe, registrar en auditoría
    if symbol and timeframe:
        validator.register_data_audit(symbol, timeframe, "direct_validation", df, validation)
        
    return validation