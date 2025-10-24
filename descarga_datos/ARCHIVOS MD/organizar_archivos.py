#!/usr/bin/env python3
"""
Script para organizar archivos MD en descarga_datos/ARCHIVOS MD
Clasifica archivos por categoría
"""

import os
import shutil
from pathlib import Path

# Definir clasificación de archivos
CLASIFICACION = {
    "_00_INDICE_MAESTRO": [
        "00_INDICE_MAESTRO.md",
        "00_INDICE_MAESTRO_v4.md",
        "INDICE_DOCUMENTOS_ANALISIS.md",
        "INDICE_DOCUMENTOS_LIVE_ANALYSIS.md",
        "INDICE_ARCHIVOS.md",
    ],
    "_01_GUIAS_RAPIDAS": [
        "GUIA_RAPIDA_v47.md",
        "REFERENCIA_RAPIDA.txt",
        "GUIA_SOLUCION_BALANCE_SANDBOX.md",
        "LOGGING_GUIDE.md",
        "LIVE_TRADING_SANDBOX_GUIDE.md",
        "OPTIMIZATION_PROCESS_GUIDE.md",
        "MIGRATION_GUIDE_v2.8.md",
        "QUICK_REFERENCE_LIMITE_POSICIONES.md",
    ],
    "_02_ARQUITECTURA_SISTEMA": [
        "ESTRUCTURA_DEPURADA.md",
        "01_SISTEMA_MODULAR_COMPLETO.md",
        "ARCHIVOS_PROTEGIDOS.md",
        "SYSTEM_DIAGRAM.md",
        "MULTI_MARKET_STRATEGY_README.md",
        "CONTRIBUTING.md",
    ],
    "_03_OPERACION_LIVE": [
        "24_7_OPERATION_GUIDE.md",
        "LIVE_TRADING_READY.md",
        "LIVE_TRADING_SYSTEM_COMPLETED.md",
        "OPERACIONES_REALES_TESTNET.md",
        "ANALISIS_OPERACIONES_LIVE_21OCT2025.md",
        "ANALISIS_OPERACIONES_REALES_TESTNET.md",
        "CORRECCIONES_LIVE_TRADING.md",
        "CORRECCIONES_SISTEMA_LIVE_TRADING.md",
        "LIVE_TRADING_NO_SIGNALS_ANALYSIS.md",
        "METRICAS_OPERACIONES_LIVE_RESUMEN.md",
        "RESUMEN_OPERACIONES_LIVE_SIMPLE.md",
        "TRADING_VIVO_VS_SIMULACION.md",
        "IMPLEMENTACION_COMPLETADA_OPERACIONES_REALES.md",
    ],
    "_04_BACKTESTING_OPTIMIZACION": [
        "02_OPTIMIZACION_ML_COMPLETO.md",
        "OPTIMIZATION_RESULTS_ANALYSIS.md",
        "OPTIMIZATION_RESULTS_SOL_USDT.md",
        "OPTIMIZATION_QUICK_SUMMARY.md",
        "optimization_report.md",
        "BACKTEST_RESULTS_REPORT.md",
        "ANALISIS_BACKTEST_VS_LIVE_PROFUNDO.md",
        "03_TESTING_Y_VALIDACION.md",
        "TRAINING_VALIDATION_REPORT.md",
    ],
    "_05_BUGS_FIXES": [
        "FIX_SIGNAL2_RESOLUTION.md",
        "BUG_FIX_REPORT_PNL_CALCULATION.md",
        "CORRECCIONES_V4.0.md",
        "CORRECCIONES_Y_MEJORAS.md",
        "CORRECCION_LIMITE_POSICIONES_v4.6.md",
        "05_CORRECCIONES_Y_MEJORAS.md",
        "FIX_SIZE_ERROR_AND_TRAILING_STOP.md",
        "POSITION_RESET_FIX.md",
        "TRAILING_STOP_IMPLEMENTATION.md",
        "ATR_FILTER_ADJUSTMENT.md",
        "IDENTIFICACION_BUG_CALCULO_PNL_CRITICO.md",
        "SOLUCIÓN_ERROR_SALDO_INSUFICIENTE.md",
        "GUIA_PRUEBAS_SIN_LIMITE.md",
    ],
    "_06_ANALISIS_RESULTADOS": [
        "ANALISIS_TESTNET_OCT21.md",
        "02_ANALISIS_TESTNET_OCT21.md",
        "RESUMEN_DEPURACION_v47.md",
        "RESUMEN_CONSOLIDACION_v4.5.txt",
        "RESUMEN_CORRECCIONES_SISTEMA_LIVE.md",
        "RESUMEN_EJECUTIVO_FINAL_ANALISIS.md",
        "RESUMEN_INVESTIGACION_APALANCAMIENTO.txt",
        "RESUMEN_LANZAMIENTO_v4.5.txt",
        "RESUMEN_UNA_PAGINA.txt",
        "RESPUESTA_FINAL_APALANCAMIENTO_ANALISIS.md",
        "RESPUESTAS_DIRECTAS_PREGUNTAS.md",
        "ACLARACION_TU_PREGUNTA_FUE_VALIDA.md",
        "CALCULO_CORRECTO_PNL_BTC_USDT.md",
        "PNL_FINAL_BTC_USDT_TABLA_COMPLETA.md",
        "PNL_RESUMEN_TEXTO_SIMPLE.txt",
        "TABLA_MAESTRA_PNL_BTC_USDT.md",
        "RESUMEN_EJECUTIVO_LIMITE_POSICIONES.txt",
        "RESPUESTA_ESTADISTICAS_OPERACIONES.txt",
        "RESUMEN_OPERACIONES_24OCT2025.txt",
        "CONTEXTO_ESTADO_ACTUAL.txt",
        "VERIFICACION_FINAL_v4.5.txt",
        "SYSTEM_ANALYSIS_REPORT.md",
        "SYSTEM_CLEANUP_SUMMARY.md",
        "VERIFICATION_FINAL_TRADING_LISTO.txt",
    ],
    "_07_HISTORICO_VERSIONES": [
        "CHANGELOG.md",
        "CHANGELOG_v47.md",
        "04_HISTORIAL_VERSIONES.md",
        "08_VERSION_3.5_DOCS.md",
        "VERSION_4.5_RELEASE.md",
        "RELEASE_4.5_ANNOUNCEMENT.txt",
        "07_SYSTEM_LOCKDOWN_STATUS.md",
        "CONSOLIDATION_LOGS_v4.5.md",
        "CONSOLIDATION_v4.5_COMPLETE.md",
        "LOGGING_SYSTEM_UPDATE.md",
        "04_PYTHON_DOWNGRADE_GUIDE.md",
        "05_KRAKEN_DEMO_SETUP.md",
        "01_ROADMAP_FUTUROS.md",
    ],
    "_MISC_OTROS": [
        "LICENSE.md",
        "README.md",
        "copilot-instructions.md",
        "copilot-checkpoint-sep2025.md",
        "CONCLUSION_FINAL.txt",
        "LIMPIEZA_COMPLETADA.txt",
        "LIVE_TRADING_READY.md",
        "LIVE_TRADING_READY.md",
        "06_BALANCE_REPORT_OCT21.md",
        "03_DASHBOARD_FIXES.md",
        "CONTEXTO_ESTADO_ACTUAL.txt",
    ],
}

def organizar_archivos():
    """Organiza archivos MD en subcarpetas"""
    base_path = Path(".")
    
    # Archivos movidos
    movidos = 0
    no_encontrados = []
    
    for categoria, archivos in CLASIFICACION.items():
        categoria_path = base_path / categoria
        
        for archivo in archivos:
            archivo_path = base_path / archivo
            
            if archivo_path.exists():
                # Si es un archivo (no es directorio)
                if archivo_path.is_file():
                    # Copiar en vez de mover para preservar en CONSOLIDADOS
                    destino = categoria_path / archivo
                    
                    if not destino.exists():
                        try:
                            shutil.copy2(archivo_path, destino)
                            print(f"✅ {archivo} → {categoria}/")
                            movidos += 1
                        except Exception as e:
                            print(f"❌ Error moviendo {archivo}: {e}")
            else:
                no_encontrados.append(archivo)
    
    print(f"\n✅ {movidos} archivos organizados")
    if no_encontrados:
        print(f"⚠️  {len(no_encontrados)} archivos no encontrados")
        for f in no_encontrados[:5]:
            print(f"   - {f}")
        if len(no_encontrados) > 5:
            print(f"   ... y {len(no_encontrados)-5} más")

if __name__ == "__main__":
    print("\n📁 Organizando archivos MD en categorías...\n")
    organizar_archivos()
    print("\n✅ Organización completada\n")
