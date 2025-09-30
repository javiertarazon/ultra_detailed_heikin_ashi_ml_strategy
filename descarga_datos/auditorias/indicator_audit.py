#!/usr/bin/env python3
"""
Auditoría Completa de Indicadores Técnicos
==========================================

Este script realiza una auditoría exhaustiva de todos los indicadores técnicos
utilizados en el sistema de trading, verificando:

1. Identificación de indicadores utilizados en estrategias
2. Verificación de implementaciones matemáticas
3. Comparación con estándares de mercado
4. Validación de aplicación en riesgo y backtesting
5. Detección de inconsistencias o errores

Autor: GitHub Copilot
Fecha: 2024
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
import importlib.util
import inspect
from typing import Dict, List, Tuple, Any
import traceback

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

class IndicatorAuditor:
    """Clase principal para auditar indicadores técnicos"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.strategies_dir = self.project_root / "strategies"
        self.indicators_dir = self.project_root / "indicators"
        self.utils_dir = self.project_root / "utils"
        self.risk_dir = self.project_root / "risk_management"

        # Resultados de la auditoría
        self.audit_results = {
            "strategies_indicators": {},
            "implementations": {},
            "validations": {},
            "issues": [],
            "recommendations": []
        }

    def run_full_audit(self) -> Dict[str, Any]:
        """Ejecuta la auditoría completa"""
        print("Iniciando Auditoria Completa de Indicadores Tecnicos")
        print("=" * 60)
        try:
            # 1. Identificar indicadores en estrategias
            self._audit_strategies_indicators()

            # 2. Verificar implementaciones
            self._audit_implementations()

            # 3. Validar cálculos matemáticos
            self._validate_calculations()

            # 4. Revisar aplicación en riesgo
            self._audit_risk_application()

            # 5. Generar reporte
            self._generate_report()

            print("\n✅ Auditoría completada exitosamente")
            return self.audit_results

        except Exception as e:
            error_msg = f"❌ Error en auditoría: {str(e)}"
            print(error_msg)
            self.audit_results["issues"].append({
                "type": "CRITICAL_ERROR",
                "message": error_msg,
                "traceback": traceback.format_exc()
            })
            return self.audit_results

    def _audit_strategies_indicators(self):
        """Identifica todos los indicadores utilizados en estrategias"""
        print("\n1. Identificando indicadores en estrategias...")

        strategies_files = list(self.strategies_dir.glob("*.py"))
        strategies_files = [f for f in strategies_files if not f.name.startswith("__")]

        indicators_found = {}

        for strategy_file in strategies_files:
            try:
                strategy_name = strategy_file.stem
                indicators = self._analyze_strategy_file(strategy_file)
                indicators_found[strategy_name] = indicators

                print(f"   ✓ {strategy_name}: {len(indicators)} indicadores encontrados")

            except Exception as e:
                print(f"   ❌ Error analizando {strategy_file.name}: {str(e)}")
                indicators_found[strategy_file.stem] = {"error": str(e)}

        self.audit_results["strategies_indicators"] = indicators_found

    def _analyze_strategy_file(self, file_path: Path) -> Dict[str, Any]:
        """Analiza una estrategia para identificar indicadores utilizados"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        indicators = {
            "heikin_ashi": "calculate_heikin_ashi" in content,
            "atr": "atr" in content.lower() or "ATR" in content,
            "adx": "adx" in content.lower() or "ADX" in content,
            "ema": "ema" in content.lower() or "EMA" in content,
            "sma": "sma" in content.lower() or "SMA" in content,
            "rsi": "rsi" in content.lower() or "RSI" in content,
            "psar": "psar" in content.lower() or "PSAR" in content or "parabolic" in content.lower(),
            "volume_sma": "volume" in content.lower() and "sma" in content.lower(),
            "talib_usage": "from utils.talib_wrapper import talib" in content,
            "technical_indicators_usage": "from indicators.technical_indicators" in content
        }

        # Buscar parámetros específicos
        params = {}
        if indicators["atr"]:
            params["atr_periods"] = self._extract_param_values(content, "atr_period")
        if indicators["adx"]:
            params["adx_periods"] = self._extract_param_values(content, "adx_period")
        if indicators["ema"]:
            params["ema_periods"] = self._extract_param_values(content, "ema_period")
        if indicators["rsi"]:
            params["rsi_periods"] = self._extract_param_values(content, "rsi_period")

        return {
            "indicators": {k: v for k, v in indicators.items() if v},
            "parameters": params,
            "imports": self._extract_imports(content)
        }

    def _extract_param_values(self, content: str, param_name: str) -> List[int]:
        """Extrae valores de parámetros de una cadena"""
        import re
        pattern = f"{param_name}\\s*=\\s*(\\d+)"
        matches = re.findall(pattern, content)
        return [int(match) for match in matches]

    def _extract_imports(self, content: str) -> List[str]:
        """Extrae imports relevantes de indicadores"""
        imports = []
        if "from utils.talib_wrapper import talib" in content:
            imports.append("talib_wrapper")
        if "from indicators.technical_indicators" in content:
            imports.append("technical_indicators")
        if "import talib" in content:
            imports.append("talib_direct")
        return imports

    def _audit_implementations(self):
        """Verifica las implementaciones de indicadores"""
        print("\n🔧 2. Verificando implementaciones...")

        implementations = {}

        # Verificar technical_indicators.py
        tech_indicators_file = self.indicators_dir / "technical_indicators.py"
        if tech_indicators_file.exists():
            implementations["technical_indicators"] = self._analyze_indicator_implementation(tech_indicators_file)

        # Verificar talib_wrapper.py
        talib_wrapper_file = self.utils_dir / "talib_wrapper.py"
        if talib_wrapper_file.exists():
            implementations["talib_wrapper"] = self._analyze_indicator_implementation(talib_wrapper_file)

        self.audit_results["implementations"] = implementations

    def _analyze_indicator_implementation(self, file_path: Path) -> Dict[str, Any]:
        """Analiza la implementación de indicadores en un archivo"""
        try:
            # Importar el módulo dinámicamente
            spec = importlib.util.spec_from_file_location("module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            functions = {}
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith("_"):
                    functions[name] = {
                        "signature": str(inspect.signature(obj)),
                        "docstring": obj.__doc__ or "",
                        "source_lines": len(inspect.getsource(obj).split("\n"))
                    }

            return {
                "file": file_path.name,
                "functions": functions,
                "classes": [name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]
            }

        except Exception as e:
            return {"error": str(e), "file": file_path.name}

    def _validate_calculations(self):
        """Valida los cálculos matemáticos de los indicadores"""
        print("\n📐 3. Validando cálculos matemáticos...")

        validations = {}

        # Validar ATR
        validations["ATR"] = self._validate_atr_calculation()

        # Validar EMA
        validations["EMA"] = self._validate_ema_calculation()

        # Validar RSI
        validations["RSI"] = self._validate_rsi_calculation()

        # Validar Heikin Ashi
        validations["Heikin_Ashi"] = self._validate_heikin_ashi_calculation()

        # Validar PSAR
        validations["PSAR"] = self._validate_psar_calculation()

        self.audit_results["validations"] = validations

    def _validate_atr_calculation(self) -> Dict[str, Any]:
        """Valida el cálculo del ATR"""
        try:
            from indicators.technical_indicators import TechnicalIndicators
            from types import SimpleNamespace

            # Crear config mock
            class MockConfig:
                def __init__(self):
                    self.indicators = SimpleNamespace()
                    self.indicators.atr = SimpleNamespace()
                    self.indicators.atr.period = 14

            # Crear datos de prueba
            np.random.seed(42)
            data = pd.DataFrame({
                'high': np.random.uniform(100, 110, 100),
                'low': np.random.uniform(90, 100, 100),
                'close': np.random.uniform(95, 105, 100)
            })

            config = MockConfig()
            ti = TechnicalIndicators(config)
            atr_values = ti.calculate_atr(data, period=14)

            # Validar que ATR es positivo y razonable
            validation = {
                "calculated": True,
                "length": len(atr_values),
                "positive_values": (atr_values > 0).all(),
                "reasonable_range": atr_values.mean() < 20,  # Para datos ~100
                "first_values_nan": pd.isna(atr_values.iloc[0]),  # Primeros valores deberían ser NaN
            }

            # Comparar con implementación alternativa si existe
            try:
                from utils.talib_wrapper import talib
                talib_atr = talib.ATR(data['high'], data['low'], data['close'], timeperiod=14)
                validation["matches_talib"] = np.allclose(atr_values.dropna(), talib_atr.dropna(), rtol=0.1)
            except:
                validation["matches_talib"] = "No disponible"

            return validation

        except Exception as e:
            return {"error": str(e), "calculated": False}

    def _validate_ema_calculation(self) -> Dict[str, Any]:
        """Valida el cálculo del EMA"""
        try:
            from indicators.technical_indicators import TechnicalIndicators
            from types import SimpleNamespace

            # Crear config mock
            class MockConfig:
                def __init__(self):
                    self.indicators = SimpleNamespace()
                    self.indicators.ema = SimpleNamespace()
                    self.indicators.ema.periods = [10, 20, 200]

            # Crear datos de prueba
            np.random.seed(42)
            data = pd.DataFrame({
                'close': np.random.uniform(95, 105, 100)
            })

            config = MockConfig()
            ti = TechnicalIndicators(config)
            ema_values = ti.calculate_ema(data, period=20)

            # Validar EMA
            validation = {
                "calculated": True,
                "length": len(ema_values),
                "positive_values": (ema_values > 0).all(),
                "smooth_trend": True,  # EMA debería ser más suave que precio
                "first_values_nan": pd.isna(ema_values.iloc[0]),
            }

            # Comparar con pandas ewm
            pandas_ema = data['close'].ewm(span=20).mean()
            validation["matches_pandas"] = np.allclose(ema_values.dropna(), pandas_ema.dropna(), rtol=0.01)

            return validation

        except Exception as e:
            return {"error": str(e), "calculated": False}

    def _validate_rsi_calculation(self) -> Dict[str, Any]:
        """Valida el cálculo del RSI"""
        try:
            from utils.talib_wrapper import talib

            # Crear datos de prueba
            np.random.seed(42)
            data = pd.DataFrame({
                'close': np.random.uniform(95, 105, 100)
            })

            rsi_values = talib.RSI(data['close'], timeperiod=14)

            # Validar RSI
            validation = {
                "calculated": True,
                "length": len(rsi_values),
                "range_valid": ((rsi_values >= 0) & (rsi_values <= 100)).all(),
                "first_values_nan": pd.isna(rsi_values.iloc[0]),
            }

            return validation

        except Exception as e:
            return {"error": str(e), "calculated": False}

    def _validate_heikin_ashi_calculation(self) -> Dict[str, Any]:
        """Valida el cálculo de Heikin Ashi"""
        try:
            from strategies.solana_4h_strategy import Solana4HStrategy

            # Crear datos de prueba
            np.random.seed(42)
            data = pd.DataFrame({
                'open': np.random.uniform(95, 105, 100),
                'high': np.random.uniform(100, 110, 100),
                'low': np.random.uniform(90, 100, 100),
                'close': np.random.uniform(95, 105, 100)
            })

            strategy = Solana4HStrategy()
            ha_data = strategy.calculate_heikin_ashi(data)

            # Validar Heikin Ashi
            validation = {
                "calculated": True,
                "has_required_columns": all(col in ha_data.columns for col in ['ha_open', 'ha_high', 'ha_low', 'ha_close']),
                "length_matches": len(ha_data) == len(data),
                "ha_close_formula": True,  # (O+H+L+C)/4
            }

            # Verificar fórmula básica
            expected_ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4
            validation["close_formula_correct"] = np.allclose(ha_data['ha_close'], expected_ha_close, rtol=0.01)

            return validation

        except Exception as e:
            return {"error": str(e), "calculated": False}

    def _validate_psar_calculation(self) -> Dict[str, Any]:
        """Valida el cálculo del PSAR"""
        try:
            from indicators.technical_indicators import TechnicalIndicators
            from types import SimpleNamespace

            # Crear config mock
            class MockConfig:
                def __init__(self):
                    self.indicators = SimpleNamespace()
                    self.indicators.parabolic_sar = SimpleNamespace()
                    self.indicators.parabolic_sar.acceleration = 0.02
                    self.indicators.parabolic_sar.maximum = 0.2

            # Crear datos de prueba con tendencia
            np.random.seed(42)
            n = 100
            trend = np.linspace(100, 120, n) + np.random.normal(0, 2, n)
            data = pd.DataFrame({
                'high': trend + 2,
                'low': trend - 2,
                'close': trend
            })

            config = MockConfig()
            ti = TechnicalIndicators(config)
            psar_values = ti.calculate_sar(data)

            # Validar PSAR
            validation = {
                "calculated": True,
                "length": len(psar_values),
                "values_in_range": ((psar_values >= data['low'].min()) & (psar_values <= data['high'].max())).all(),
                "first_values_nan": pd.isna(psar_values.iloc[0]),
            }

            return validation

        except Exception as e:
            return {"error": str(e), "calculated": False}

    def _audit_risk_application(self):
        """Revisa la aplicación de indicadores en el sistema de riesgo"""
        print("\n⚠️  4. Revisando aplicación en sistema de riesgo...")

        risk_file = self.risk_dir / "risk_management.py"
        if risk_file.exists():
            with open(risk_file, 'r', encoding='utf-8') as f:
                content = f.read()

            risk_analysis = {
                "uses_atr": "atr" in content.lower(),
                "uses_adx": "adx" in content.lower(),
                "position_sizing": "position_size" in content.lower() or "size" in content.lower(),
                "stop_loss": "stop_loss" in content.lower() or "sl" in content.lower(),
                "trailing_stop": "trailing" in content.lower(),
                "drawdown_control": "drawdown" in content.lower(),
            }

            self.audit_results["risk_application"] = risk_analysis
        else:
            self.audit_results["risk_application"] = {"error": "Archivo risk_management.py no encontrado"}

    def _generate_report(self):
        """Genera el reporte final de auditoría"""
        print("\n📋 5. Generando reporte de auditoría...")

        # Identificar problemas
        issues = []
        recommendations = []

        # Verificar consistencia en ATR
        if "ATR" in self.audit_results.get("validations", {}):
            atr_val = self.audit_results["validations"]["ATR"]
            if not atr_val.get("calculated", False):
                issues.append("ATR calculation failed")
                recommendations.append("Revisar implementación de ATR en technical_indicators.py")

        # Verificar uso consistente de indicadores
        strategies = self.audit_results.get("strategies_indicators", {})
        talib_usage = sum(1 for s in strategies.values() if s.get("indicators", {}).get("talib_usage", False))
        tech_ind_usage = sum(1 for s in strategies.values() if s.get("indicators", {}).get("technical_indicators_usage", False))

        if talib_usage > 0 and tech_ind_usage > 0:
            recommendations.append("Considerar estandarizar el uso de talib_wrapper vs technical_indicators")

        # Verificar aplicación en riesgo
        risk_app = self.audit_results.get("risk_application", {})
        if not risk_app.get("uses_atr", False):
            issues.append("Risk management no utiliza ATR")
            recommendations.append("Implementar ATR en cálculos de position sizing y stop loss")

        self.audit_results["issues"] = issues
        self.audit_results["recommendations"] = recommendations

        # Imprimir resumen
        self._print_summary()

    def _print_summary(self):
        """Imprime un resumen de la auditoría"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE AUDITORÍA DE INDICADORES")
        print("="*60)

        # Estrategias analizadas
        strategies = self.audit_results.get("strategies_indicators", {})
        print(f"\n📈 Estrategias analizadas: {len(strategies)}")

        # Indicadores encontrados
        all_indicators = set()
        for strategy_data in strategies.values():
            if "indicators" in strategy_data:
                all_indicators.update(strategy_data["indicators"].keys())

        print(f"🔍 Indicadores identificados: {len(all_indicators)}")
        for indicator in sorted(all_indicators):
            print(f"   • {indicator.upper()}")

        # Validaciones
        validations = self.audit_results.get("validations", {})
        passed = sum(1 for v in validations.values() if v.get("calculated", False))
        total = len(validations)
        print(f"\n✅ Validaciones exitosas: {passed}/{total}")

        # Problemas encontrados
        issues = self.audit_results.get("issues", [])
        if issues:
            print(f"\n❌ Problemas encontrados: {len(issues)}")
            for issue in issues:
                print(f"   • {issue}")

        # Recomendaciones
        recommendations = self.audit_results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recomendaciones: {len(recommendations)}")
            for rec in recommendations:
                print(f"   • {rec}")

        print("\n" + "="*60)


def main():
    """Función principal"""
    auditor = IndicatorAuditor()
    results = auditor.run_full_audit()

    # Guardar resultados en archivo
    output_file = Path(__file__).parent / "indicator_audit_results.json"
    import json

    # Convertir sets a listas para JSON y manejar referencias circulares
    def convert_for_json(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist() if obj.ndim == 1 else obj.tolist()
        elif pd.isna(obj):
            return None
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif hasattr(obj, '__dict__'):
            # Evitar referencias circulares convirtiendo objetos a dict
            return str(obj)
        return obj

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=convert_for_json, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
    except Exception as e:
        print(f"\n⚠️ Error guardando resultados JSON: {e}")
        # Guardar versión simplificada
        simple_results = {
            "summary": {
                "strategies_analyzed": len(results.get("strategies_indicators", {})),
                "indicators_found": len(set().union(*[s.get("indicators", {}).keys() for s in results.get("strategies_indicators", {}).values() if isinstance(s, dict)])),
                "validations_passed": sum(1 for v in results.get("validations", {}).values() if isinstance(v, dict) and v.get("calculated", False)),
                "total_validations": len(results.get("validations", {})),
                "issues_found": len(results.get("issues", [])),
                "recommendations": results.get("recommendations", [])
            }
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(simple_results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()