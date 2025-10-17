"""
Model Manager - Gestor centralizado de modelos de machine learning
"""
import os
import pickle
import joblib
from typing import Dict, Any, Optional
from utils.logger import get_logger

class ModelManager:
    """
    Gestor centralizado para modelos de machine learning
    """

    def __init__(self, base_dir: str = None):
        """
        Inicializa el ModelManager

        Args:
            base_dir: Directorio base para almacenar modelos
        """
        if base_dir is None:
            base_dir = os.path.join(os.getcwd(), 'models')

        self.base_dir = base_dir
        self.model_dir = base_dir  # Agregar atributo model_dir para compatibilidad
        self.logger = get_logger(__name__)

        # Crear directorio si no existe
        os.makedirs(self.base_dir, exist_ok=True)

        self.logger.info(f"ModelManager inicializado en {self.base_dir}")

    def ensure_model_dir(self):
        """Crear directorio de modelos si no existe"""
        os.makedirs(self.base_dir, exist_ok=True)

    def get_model_path(self, symbol: str, model_name: str) -> str:
        """Obtener ruta del modelo para un símbolo específico"""
        symbol_dir = os.path.join(self.base_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{model_name}.pkl")

    def get_scaler_path(self, symbol: str, model_name: str) -> str:
        """Obtener ruta del scaler para un símbolo específico"""
        symbol_dir = os.path.join(self.base_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{model_name}_scaler.pkl")

    def save_model(self, model: Any, model_name: str, symbol: str = None, metadata: Optional[Dict] = None) -> bool:
        """
        Guarda un modelo en disco

        Args:
            model: Modelo a guardar
            model_name: Nombre del modelo
            symbol: Símbolo (opcional, para organizar en subdirectorios)
            metadata: Metadatos opcionales

        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if symbol:
                model_path = self.get_model_path(symbol, model_name)
            else:
                model_path = os.path.join(self.base_dir, f"{model_name}.pkl")

            # Guardar modelo y metadatos
            data = {
                'model': model,
                'metadata': metadata or {},
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }

            with open(model_path, 'wb') as f:
                pickle.dump(data, f)

            self.logger.info(f"Modelo {model_name} guardado en {model_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error guardando modelo {model_name}: {e}")
            return False

    def load_model(self, model_name: str, symbol: str = None) -> Optional[Any]:
        """
        Carga un modelo desde disco

        Args:
            model_name: Nombre del modelo
            symbol: Símbolo (opcional, para organizar en subdirectorios)

        Returns:
            Modelo cargado o None si no existe
        """
        try:
            if symbol:
                model_path = self.get_model_path(symbol, model_name)
            else:
                model_path = os.path.join(self.base_dir, f"{model_name}.pkl")

            if not os.path.exists(model_path):
                self.logger.warning(f"Modelo {model_name} no encontrado en {model_path}")
                return None

            with open(model_path, 'rb') as f:
                data = pickle.load(f)

            model = data.get('model')
            metadata = data.get('metadata', {})

            self.logger.info(f"Modelo {model_name} cargado desde {model_path}")
            return model

        except Exception as e:
            self.logger.error(f"Error cargando modelo {model_name}: {e}")
            return None

    def list_models(self) -> list:
        """
        Lista todos los modelos disponibles

        Returns:
            Lista de nombres de modelos
        """
        try:
            files = os.listdir(self.base_dir)
            models = [f.replace('.pkl', '') for f in files if f.endswith('.pkl')]
            return models
        except Exception as e:
            self.logger.error(f"Error listando modelos: {e}")
            return []

    def delete_model(self, model_name: str) -> bool:
        """
        Elimina un modelo

        Args:
            model_name: Nombre del modelo

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            model_path = os.path.join(self.base_dir, f"{model_name}.pkl")

            if os.path.exists(model_path):
                os.remove(model_path)
                self.logger.info(f"Modelo {model_name} eliminado")
                return True
            else:
                self.logger.warning(f"Modelo {model_name} no encontrado")
                return False

        except Exception as e:
            self.logger.error(f"Error eliminando modelo {model_name}: {e}")
            return False