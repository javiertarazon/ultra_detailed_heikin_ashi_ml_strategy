"""Wrapper utilitario para mantener compatibilidad con tests que importan
utils.validate_modular_system.validate_modular_system.

Delegamos al módulo raíz `validate_modular_system.py` que reside en la carpeta
principal `descarga_datos/`.
"""
from importlib import import_module


def validate_modular_system():
    """Delegar a la función real ubicada en `descarga_datos/validate_modular_system.py`.

    Returns:
        bool: True si la validación del sistema modular pasa, False en caso contrario.
    """
    try:
        mod = import_module('validate_modular_system')
        if hasattr(mod, 'validate_modular_system'):
            return mod.validate_modular_system()
        print("[compat] El módulo raíz no expone validate_modular_system")
        return False
    except Exception as e:
        print(f"[compat] Error delegando validación modular: {e}")
        return False

__all__ = ["validate_modular_system"]
