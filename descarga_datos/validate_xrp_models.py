#!/usr/bin/env python3
"""
Script para validar que los modelos ML de XRP/USDT se pueden cargar correctamente
"""

import sys
import os
from pathlib import Path
import joblib

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger

logger = get_logger(__name__)

def validate_xrp_models():
    """Valida que los modelos de XRP/USDT se pueden cargar correctamente"""

    logger.info("=== VALIDACION DE MODELOS XRP/USDT ===")

    # Directorio de modelos XRP/USDT
    models_dir = Path(__file__).parent / "models" / "XRP_USDT"

    if not models_dir.exists():
        logger.error(f"Directorio de modelos no existe: {models_dir}")
        return False

    # Buscar archivos de modelos
    model_files = list(models_dir.glob("RandomForest_*.joblib"))

    if not model_files:
        logger.error("No se encontraron archivos de modelo RandomForest")
        return False

    logger.info(f"Encontrados {len(model_files)} archivos de modelo")

    # Intentar cargar cada modelo
    loaded_models = []
    for model_file in model_files:
        model_name = model_file.stem  # Sin extension
        logger.info(f"Intentando cargar modelo: {model_name}")

        try:
            model = joblib.load(model_file)
            loaded_models.append((model_name, model))
            logger.info(f"Modelo {model_name} cargado exitosamente")

        except Exception as e:
            logger.error(f"Error cargando modelo {model_name}: {e}")
            continue

    if not loaded_models:
        logger.error("No se pudo cargar ningun modelo")
        return False

    logger.info(f"Validacion exitosa: {len(loaded_models)} modelos cargados correctamente")

    # Mostrar informacion de los modelos cargados
    for name, model in loaded_models[:5]:  # Mostrar solo los primeros 5
        logger.info(f"Modelo: {name}")
        logger.info(f"  Tipo: {type(model)}")
        if hasattr(model, 'n_estimators'):
            logger.info(f"  Estimadores: {model.n_estimators}")
        if hasattr(model, 'max_depth'):
            logger.info(f"  Max depth: {model.max_depth}")

    return True

if __name__ == "__main__":
    success = validate_xrp_models()
    sys.exit(0 if success else 1)