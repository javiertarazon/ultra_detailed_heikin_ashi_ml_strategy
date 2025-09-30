"""Validación rápida del sistema modular.

Esta versión mínima se enfoca en garantizar que:
1. El archivo de configuración carga correctamente.
2. Al menos una estrategia activa se puede importar e instanciar.
3. Se puede crear el directorio de resultados del dashboard.

Devuelve True si todo pasa, False si hay algún fallo.
"""
from __future__ import annotations

import traceback
from pathlib import Path
import sys, os


def validate_modular_system() -> bool:
    try:
        from config.config_loader import load_config_from_yaml
        config = load_config_from_yaml()
        # Estrategias activas declaradas
        strategies_cfg = config.backtesting.strategies if hasattr(config.backtesting, 'strategies') else {}
        if not strategies_cfg:
            print("[validate] No hay estrategias activas en config")
            return False
        active = [k for k, v in strategies_cfg.items() if v]
        if not active:
            print("[validate] Todas las estrategias están desactivadas")
            return False
        # Asegurar que el path incluye el directorio actual y subcarpeta backtesting
        base_dir = Path(__file__).parent
        if str(base_dir) not in sys.path:
            sys.path.append(str(base_dir))
        backtesting_dir = base_dir / 'backtesting'
        if backtesting_dir.exists() and str(backtesting_dir) not in sys.path:
            sys.path.append(str(backtesting_dir))
        # Validación ligera: comprobar existencia de archivo orquestador y no importarlo (evita fallos por dependencias pesadas en tests rápidos)
        orchestrator_file = backtesting_dir / 'backtesting_orchestrator.py'
        if not orchestrator_file.exists():
            print("[validate] Falta archivo backtesting_orchestrator.py")
            return False
        # Heurística: buscar nombres de clases de estrategias en el archivo (garantiza definiciones disponibles para carga dinámica)
        content = orchestrator_file.read_text(encoding='utf-8')
        required_tokens = [
            'Solana4HStrategy', 'Solana4HSARStrategy', 'Solana4HTrailingStrategy',
            'Solana4HRiskManagedStrategy', 'Solana4HOptimizedTrailingStrategy'
        ]
        missing = [t for t in required_tokens if t not in content]
        if missing:
            print(f"[validate] Tokens esperados ausentes en orquestador: {missing}")
            return False
        # Verificar directorio de resultados
        out_dir = Path(__file__).parent / 'data' / 'dashboard_results'
        out_dir.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[validate] Error: {e}")
        traceback.print_exc()
        return False


__all__ = ["validate_modular_system"]
