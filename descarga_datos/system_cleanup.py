#!/usr/bin/env python3
"""
Script de Limpieza y Mantenimiento del Sistema - v2.8
Este script realiza tareas de limpieza y mantenimiento del sistema, siguiendo
la arquitectura centralizada y respetando las reglas de diseño del sistema.

Funcionalidades:
1. Elimina scripts innecesarios o duplicados
2. Limpia archivos de caché y temporales
3. Elimina archivos CSV temporales o duplicados
4. Resetea o limpia tablas de la base de datos SQLite
5. Elimina modelos antiguos o mal entrenados para permitir reentrenamiento

IMPORTANTE: Este script respeta la arquitectura centralizada y utiliza
los módulos principales del sistema para realizar las tareas.
"""
import os
import sys
import shutil
import sqlite3
import glob
import argparse
from pathlib import Path
from datetime import datetime

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar sistema de logging centralizado
from utils.logger import initialize_system_logging, get_logger

# Inicializar logging centralizado
initialize_system_logging({
    'level': 'INFO',
    'file': 'logs/system_cleanup.log'
})

# Obtener logger específico para este módulo
logger = get_logger('system_cleanup')

# Lista de scripts considerados innecesarios o duplicados
REDUNDANT_SCRIPTS = [
    'run_xrp_backtest_dashboard.py',  # Duplica funcionalidad de main.py
]

# Lista de archivos de validación, test y auditoría a eliminar
TEST_VALIDATION_FILES = [
    'audit_real_data.py',        # Auditoría de datos
    'clean_data.py',             # Limpieza de datos (ahora reemplazado por system_cleanup.py)
    'test_download_simple.py',   # Test simple de descarga
    'test_download_system.py',   # Test del sistema de descarga
    'test_symbol_classification.py', # Test de clasificación de símbolos
    'validate_fixes.py',         # Validación de arreglos
    'validate_modular_system.py', # Validación del sistema modular
    'validation_results.txt',    # Resultados de validación
    'verify_metrics.py',         # Verificación de métricas
]

# Lista de archivos de documentación temporal que ya no son necesarios
DOC_FILES = [
    'CORRECCIONES_IMPLEMENTADAS_v2.8.md',
    'DIAGNOSTICO_MT5_CCXT_FIXES.md',
    'INFORME_FINAL_CORRECCIONES_MT5_CCXT.md',
    'RESULTADOS_FIXES_MT5_CCXT_v2.8.1.md',
    'SELECTIVE_BACKTEST_README.md',
    'TEST_RESULTS_SUMMARY.md',
    'VERIFICACION_FINAL_FIXES_MT5_CCXT_v2.8.1.md',
]

# Lista de archivos temporales y de caché a eliminar
TEMP_FILE_PATTERNS = [
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyo',
    '**/*.pyd',
    '**/.pytest_cache',
    '**/*.log.?',
    '**/temp_*.csv',
]

class SystemCleaner:
    """Clase centralizada para limpieza y mantenimiento del sistema"""
    
    def __init__(self, base_dir=None):
        """
        Inicializa el limpiador del sistema.
        
        Args:
            base_dir: Directorio base del sistema. Si es None, usa el directorio actual.
        """
        self.base_dir = Path(base_dir) if base_dir else Path(os.getcwd())
        self.data_dir = self.base_dir / 'data'
        self.models_dir = self.base_dir / 'models'  # Los modelos están en descarga_datos/models
        self.db_path = self.data_dir / 'data.db'
        self.csv_dir = self.data_dir / 'csv'
        self.dashboard_dir = self.data_dir / 'dashboard_results'
        self.optimization_results_dir = self.data_dir / 'optimization_results'
        self.optimization_pipeline_dir = self.data_dir / 'optimization_pipeline'
        
        # Verificar que estamos en el directorio correcto
        if not (self.base_dir / 'main.py').exists():
            logger.error("Este script debe ejecutarse desde el directorio 'descarga_datos'")
            sys.exit(1)
    
    def clean_redundant_scripts(self, dry_run=False):
        """
        Elimina scripts redundantes o innecesarios.
        
        Args:
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        for script in REDUNDANT_SCRIPTS:
            script_path = self.base_dir / script
            if script_path.exists():
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el script redundante: {script}")
                else:
                    try:
                        script_path.unlink()
                        logger.info(f"Script redundante eliminado: {script}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando {script}: {e}")
        return count
    
    def clean_temp_files(self, dry_run=False):
        """
        Elimina archivos temporales y de caché.
        
        Args:
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos y directorios eliminados o que se eliminarían.
        """
        count = 0
        for pattern in TEMP_FILE_PATTERNS:
            for path in self.base_dir.glob(pattern):
                if path.is_file():
                    if dry_run:
                        logger.info(f"[DRY RUN] Se eliminaría el archivo temporal: {path}")
                    else:
                        try:
                            path.unlink()
                            logger.info(f"Archivo temporal eliminado: {path}")
                            count += 1
                        except Exception as e:
                            logger.error(f"Error eliminando {path}: {e}")
                elif path.is_dir():
                    if dry_run:
                        logger.info(f"[DRY RUN] Se eliminaría el directorio temporal: {path}")
                    else:
                        try:
                            shutil.rmtree(path)
                            logger.info(f"Directorio temporal eliminado: {path}")
                            count += 1
                        except Exception as e:
                            logger.error(f"Error eliminando directorio {path}: {e}")
        return count
    
    def clean_csv_files(self, symbols=None, dry_run=False):
        """
        Elimina archivos CSV temporales o duplicados.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        if not self.csv_dir.exists():
            logger.warning(f"Directorio CSV no encontrado: {self.csv_dir}")
            return count
            
        # Si se especifican símbolos, construye la lista de archivos a eliminar
        if symbols:
            files_to_remove = []
            for symbol in symbols:
                # Normalizar el símbolo para el nombre de archivo
                normalized = symbol.replace('/', '_')
                pattern = f"{normalized}_*.csv"
                files_to_remove.extend(self.csv_dir.glob(pattern))
        else:
            # Si no se especifican símbolos, considerar todos los archivos CSV
            files_to_remove = list(self.csv_dir.glob("*.csv"))
            
        # Eliminar los archivos
        for file_path in files_to_remove:
            if dry_run:
                logger.info(f"[DRY RUN] Se eliminaría el archivo CSV: {file_path.name}")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"Archivo CSV eliminado: {file_path.name}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error eliminando {file_path.name}: {e}")
                    
        return count
    
    def clean_database(self, symbols=None, dry_run=False):
        """
        Limpia o resetea tablas de la base de datos SQLite.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra las tablas que se limpiarían sin limpiarlas.
        
        Returns:
            int: Número de tablas limpiadas o que se limpiarían.
        """
        count = 0
        if not self.db_path.exists():
            logger.warning(f"Base de datos no encontrada: {self.db_path}")
            return count
            
        # Conectar a la base de datos
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Listar las tablas existentes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Si se especifican símbolos, filtrar las tablas correspondientes
            tables_to_clean = []
            if symbols:
                for symbol in symbols:
                    # Normalizar el símbolo para el nombre de tabla
                    normalized = symbol.replace('/', '_')
                    for table in tables:
                        if normalized in table:
                            tables_to_clean.append(table)
            else:
                tables_to_clean = tables
                
            # Limpiar las tablas
            for table in tables_to_clean:
                if dry_run:
                    logger.info(f"[DRY RUN] Se limpiaría la tabla: {table}")
                else:
                    try:
                        cursor.execute(f"DELETE FROM {table};")
                        logger.info(f"Tabla limpiada: {table}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error limpiando tabla {table}: {e}")
            
            # Commit y cerrar conexión
            if not dry_run and count > 0:
                conn.commit()
            conn.close()
                    
        except Exception as e:
            logger.error(f"Error accediendo a la base de datos: {e}")
            
        return count
    
    def clean_models(self, symbols=None, dry_run=False):
        """
        Elimina modelos ML antiguos o mal entrenados.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra los modelos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de modelos eliminados o que se eliminarían.
        """
        count = 0
        # Crear el directorio de modelos si no existe (nueva estructura centralizada)
        if not self.models_dir.exists():
            if not dry_run:
                os.makedirs(self.models_dir, exist_ok=True)
                logger.info(f"Creado directorio de modelos: {self.models_dir}")
            else:
                logger.warning(f"Directorio de modelos no encontrado: {self.models_dir}")
                return count
            
        # Si se especifican símbolos, construye la lista de directorios a limpiar
        model_dirs = []
        if symbols:
            for symbol in symbols:
                # Separar el símbolo para identificar el directorio correspondiente
                parts = symbol.split('/')
                if len(parts) == 2:
                    base, quote = parts
                    # Comprobar ambas posibilidades (con y sin _)
                    possible_dirs = [
                        self.models_dir / base,
                        self.models_dir / f"{base}_{quote}"
                    ]
                    for dir_path in possible_dirs:
                        if dir_path.exists():
                            model_dirs.append(dir_path)
        else:
            # Si no se especifican símbolos, considerar todos los directorios de modelos
            model_dirs = [d for d in self.models_dir.iterdir() if d.is_dir()]
            
        # Eliminar los modelos en cada directorio
        for model_dir in model_dirs:
            model_files = list(model_dir.glob("*.pkl"))
            if not model_files:
                logger.info(f"No se encontraron modelos en {model_dir}")
                continue
                
            for model_file in model_files:
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el modelo: {model_file}")
                else:
                    try:
                        model_file.unlink()
                        logger.info(f"Modelo eliminado: {model_file}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando modelo {model_file}: {e}")
                    
        return count
    
    def clean_dashboard_results(self, symbols=None, dry_run=False):
        """
        Elimina resultados del dashboard para permitir una nueva ejecución limpia.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        if not self.dashboard_dir.exists():
            logger.warning(f"Directorio de resultados del dashboard no encontrado: {self.dashboard_dir}")
            return count
            
        # Si se especifican símbolos, construye la lista de archivos a eliminar
        if symbols:
            files_to_remove = []
            for symbol in symbols:
                # Normalizar el símbolo para el nombre de archivo
                normalized = symbol.replace('/', '_')
                pattern = f"{normalized}_*.json"
                files_to_remove.extend(self.dashboard_dir.glob(pattern))
        else:
            # Si no se especifican símbolos, considerar todos los archivos JSON
            files_to_remove = list(self.dashboard_dir.glob("*.json"))
            
        # Eliminar los archivos
        for file_path in files_to_remove:
            if dry_run:
                logger.info(f"[DRY RUN] Se eliminaría el resultado del dashboard: {file_path.name}")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"Resultado del dashboard eliminado: {file_path.name}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error eliminando {file_path.name}: {e}")
                    
        return count
        
    def clean_test_validation_files(self, dry_run=False):
        """
        Elimina los archivos de prueba, validación y auditoría.
        
        Args:
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        
        for file_name in TEST_VALIDATION_FILES:
            file_path = Path(file_name)
            if file_path.exists():
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el archivo de test/validación: {file_name}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Archivo de test/validación eliminado: {file_name}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando {file_name}: {e}")
                        
        return count
        
    def clean_doc_files(self, dry_run=False):
        """
        Elimina los archivos de documentación temporal.
        
        Args:
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
        
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        
        for file_name in DOC_FILES:
            file_path = Path(file_name)
            if file_path.exists():
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el archivo de documentación: {file_name}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Archivo de documentación eliminado: {file_name}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando {file_name}: {e}")
                        
        return count
        
    def clean_optimization_files(self, symbols=None, dry_run=False):
        """
        Limpia los archivos de resultados de optimización.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra los archivos que se eliminarían sin eliminarlos.
            
        Returns:
            int: Número de archivos eliminados o que se eliminarían.
        """
        count = 0
        
        # Crear directorios si no existen (nueva estructura centralizada)
        if not self.optimization_results_dir.exists():
            if not dry_run:
                os.makedirs(self.optimization_results_dir, exist_ok=True)
                logger.info(f"Creado directorio de resultados de optimización: {self.optimization_results_dir}")
            else:
                logger.warning(f"Directorio de resultados de optimización no encontrado: {self.optimization_results_dir}")
        
        if not self.optimization_pipeline_dir.exists():
            if not dry_run:
                os.makedirs(self.optimization_pipeline_dir, exist_ok=True)
                logger.info(f"Creado directorio de pipeline de optimización: {self.optimization_pipeline_dir}")
            else:
                logger.warning(f"Directorio de pipeline de optimización no encontrado: {self.optimization_pipeline_dir}")
        
        # Limpiar archivos en el directorio de resultados de optimización
        if self.optimization_results_dir.exists():
            files_to_remove = []
            if symbols:
                for symbol in symbols:
                    normalized = symbol.replace('/', '_')
                    pattern = f"*{normalized}*.json"
                    files_to_remove.extend(self.optimization_results_dir.glob(pattern))
                    pattern = f"*{normalized}*.csv"
                    files_to_remove.extend(self.optimization_results_dir.glob(pattern))
            else:
                files_to_remove = list(self.optimization_results_dir.glob("*.json"))
                files_to_remove.extend(self.optimization_results_dir.glob("*.csv"))
            
            for file_path in files_to_remove:
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el resultado de optimización: {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Resultado de optimización eliminado: {file_path.name}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando {file_path.name}: {e}")
        
        # Limpiar archivos en el directorio de pipeline de optimización
        if self.optimization_pipeline_dir.exists():
            files_to_remove = []
            if symbols:
                for symbol in symbols:
                    normalized = symbol.replace('/', '_')
                    pattern = f"*{normalized}*.json"
                    files_to_remove.extend(self.optimization_pipeline_dir.glob(pattern))
                    pattern = f"*{normalized}*.csv"
                    files_to_remove.extend(self.optimization_pipeline_dir.glob(pattern))
            else:
                files_to_remove = list(self.optimization_pipeline_dir.glob("*.json"))
                files_to_remove.extend(self.optimization_pipeline_dir.glob("*.csv"))
            
            for file_path in files_to_remove:
                if dry_run:
                    logger.info(f"[DRY RUN] Se eliminaría el archivo de pipeline: {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Archivo de pipeline eliminado: {file_path.name}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando {file_path.name}: {e}")
        
        return count
        
    def run_full_cleanup(self, symbols=None, dry_run=False, skip_scripts=False):
        """
        Ejecuta todas las tareas de limpieza.
        
        Args:
            symbols: Lista de símbolos para limpiar. Si es None, limpia todos.
            dry_run: Si es True, solo muestra los cambios sin realizarlos.
            skip_scripts: Si es True, no elimina scripts redundantes.
            
        Returns:
            dict: Diccionario con los resultados de cada tarea.
        """
        logger.info("=== INICIANDO LIMPIEZA COMPLETA DEL SISTEMA ===")
        logger.info(f"Modo: {'Simulación (dry-run)' if dry_run else 'Ejecución real'}")
        if symbols:
            logger.info(f"Símbolos a limpiar: {', '.join(symbols)}")
        else:
            logger.info("Limpiando todos los símbolos")
            
        results = {}
        
        # 1. Limpiar scripts redundantes
        if not skip_scripts:
            logger.info("\n=== LIMPIANDO SCRIPTS REDUNDANTES ===")
            count = self.clean_redundant_scripts(dry_run)
            results['scripts_redundantes'] = count
            logger.info(f"Total scripts redundantes {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # 2. Limpiar archivos temporales
        logger.info("\n=== LIMPIANDO ARCHIVOS TEMPORALES Y CACHÉ ===")
        count = self.clean_temp_files(dry_run)
        results['archivos_temporales'] = count
        logger.info(f"Total archivos temporales {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # 3. Limpiar archivos CSV
        logger.info("\n=== LIMPIANDO ARCHIVOS CSV ===")
        count = self.clean_csv_files(symbols, dry_run)
        results['archivos_csv'] = count
        logger.info(f"Total archivos CSV {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # 4. Limpiar base de datos
        logger.info("\n=== LIMPIANDO BASE DE DATOS ===")
        count = self.clean_database(symbols, dry_run)
        results['tablas_db'] = count
        logger.info(f"Total tablas {('que se limpiarían' if dry_run else 'limpiadas')}: {count}")
        
        # 5. Limpiar modelos
        logger.info("\n=== LIMPIANDO MODELOS ML ===")
        count = self.clean_models(symbols, dry_run)
        results['modelos'] = count
        logger.info(f"Total modelos {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # 6. Limpiar resultados del dashboard
        logger.info("\n=== LIMPIANDO RESULTADOS DEL DASHBOARD ===")
        count = self.clean_dashboard_results(symbols, dry_run)
        results['dashboard_results'] = count
        logger.info(f"Total resultados dashboard {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # 7. Limpiar archivos de test y validación
        count = self.clean_test_validation_files(dry_run)
        results['archivos_test_validacion'] = count
        
        # 8. Limpiar archivos de documentación
        count = self.clean_doc_files(dry_run)
        results['archivos_documentacion'] = count
        
        # 9. Limpiar archivos de optimización
        logger.info("\n=== LIMPIANDO ARCHIVOS DE OPTIMIZACIÓN ===")
        count = self.clean_optimization_files(symbols, dry_run)
        results['archivos_optimizacion'] = count
        logger.info(f"Total archivos de optimización {('que se eliminarían' if dry_run else 'eliminados')}: {count}")
        
        # Resumen
        total = sum(results.values())
        logger.info("\n=== RESUMEN DE LIMPIEZA ===")
        logger.info(f"Total de elementos {('que se eliminarían/limpiarían' if dry_run else 'eliminados/limpiados')}: {total}")
        for category, count in results.items():
            logger.info(f"  - {category}: {count}")
            
        if dry_run:
            logger.info("\nEste fue un dry-run. Ningún cambio fue realizado.")
            logger.info("Para ejecutar la limpieza real, elimine el parámetro --dry-run")
        else:
            logger.info("\nLimpieza completa realizada exitosamente")
            
        return results


def main():
    """Función principal de la utilidad de limpieza"""
    parser = argparse.ArgumentParser(
        description='Herramienta de limpieza y mantenimiento del sistema de trading'
    )
    parser.add_argument('--symbols', nargs='+', help='Símbolos específicos para limpiar (ej: BTC/USDT XRP/USDT)')
    parser.add_argument('--dry-run', action='store_true', help='Ejecutar en modo simulación (no realizar cambios)')
    parser.add_argument('--skip-scripts', action='store_true', help='No eliminar scripts redundantes')
    parser.add_argument('--csv-only', action='store_true', help='Limpiar solo archivos CSV')
    parser.add_argument('--db-only', action='store_true', help='Limpiar solo base de datos')
    parser.add_argument('--models-only', action='store_true', help='Limpiar solo modelos')
    parser.add_argument('--temp-only', action='store_true', help='Limpiar solo archivos temporales')
    parser.add_argument('--dashboard-only', action='store_true', help='Limpiar solo resultados del dashboard')
    parser.add_argument('--test-files-only', action='store_true', help='Limpiar solo archivos de test y validación')
    parser.add_argument('--doc-files-only', action='store_true', help='Limpiar solo archivos de documentación temporal')
    parser.add_argument('--optimization-only', action='store_true', help='Limpiar solo archivos de optimización')
    
    args = parser.parse_args()
    
    cleaner = SystemCleaner()
    
    # Determinar si se debe realizar una limpieza específica o completa
    if args.csv_only:
        count = cleaner.clean_csv_files(args.symbols, args.dry_run)
        logger.info(f"Total archivos CSV {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.db_only:
        count = cleaner.clean_database(args.symbols, args.dry_run)
        logger.info(f"Total tablas {('que se limpiarían' if args.dry_run else 'limpiadas')}: {count}")
    elif args.models_only:
        count = cleaner.clean_models(args.symbols, args.dry_run)
        logger.info(f"Total modelos {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.temp_only:
        count = cleaner.clean_temp_files(args.dry_run)
        logger.info(f"Total archivos temporales {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.dashboard_only:
        count = cleaner.clean_dashboard_results(args.symbols, args.dry_run)
        logger.info(f"Total resultados dashboard {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.test_files_only:
        count = cleaner.clean_test_validation_files(args.dry_run)
        logger.info(f"Total archivos de test/validación {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.doc_files_only:
        count = cleaner.clean_doc_files(args.dry_run)
        logger.info(f"Total archivos de documentación {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    elif args.optimization_only:
        count = cleaner.clean_optimization_files(args.symbols, args.dry_run)
        logger.info(f"Total archivos de optimización {('que se eliminarían' if args.dry_run else 'eliminados')}: {count}")
    else:
        # Limpieza completa
        cleaner.run_full_cleanup(args.symbols, args.dry_run, args.skip_scripts)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nOperación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        sys.exit(1)