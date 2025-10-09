#!/usr/bin/env python3
"""
Script para estandarizar el sistema de logging.
Este script busca y reemplaza referencias a logging directo por el sistema centralizado.
"""
import os
import re
import argparse
from pathlib import Path

# Lista de patrones a buscar y reemplazar
PATTERNS = [
    # Patrón 1: import logging -> from utils.logger import get_logger
    {
        'search': r'import\s+logging\s*$',
        'replace': 'from utils.logger import get_logger',
        'single_line': True
    },
    # Patrón 2: logging.getLogger -> get_logger
    {
        'search': r'self\.logger\s*=\s*logging\.getLogger\(["\']?([^"\']*)["\']?\)',
        'replace': 'self.logger = get_logger({name})',
        'single_line': True
    },
    # Patrón 5: logging.basicConfig
    {
        'search': r'logging\.basicConfig\(.*\)',
        'replace': '# Reemplazado por sistema de logging centralizado\n# Para inicializar el logging, use: from utils.logger import initialize_system_logging',
        'single_line': False
    }
]

# Lista de archivos a ignorar
IGNORE_FILES = [
    'utils/logger.py',
    'utils/logger_metrics.py'
]

def standardize_logging_in_file(file_path, dry_run=True):
    """
    Estandariza el sistema de logging en un archivo.
    
    Args:
        file_path: Ruta del archivo a estandarizar
        dry_run: Si True, solo muestra cambios sin aplicarlos
    """
    # Comprobar si el archivo debe ser ignorado
    rel_path = os.path.relpath(file_path, Path(__file__).parent.parent)
    if any(rel_path.endswith(ignore) for ignore in IGNORE_FILES):
        print(f"Ignorando archivo: {rel_path}")
        return False, 0
    
    # Leer el contenido del archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Aplicar patrones
    for pattern in PATTERNS:
        if pattern['single_line']:
            # Reemplazo línea por línea
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                match = re.search(pattern['search'], line)
                if match:
                    if len(match.groups()) > 0:
                        name = f'"{match.group(1)}"' if match.group(1) else '__name__'
                        replacement = pattern['replace'].format(name=name)
                    else:
                        replacement = pattern['replace']
                    
                    new_lines.append(re.sub(pattern['search'], replacement, line))
                    changes_made += 1
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            # Reemplazo en contenido completo
            matches = re.finditer(pattern['search'], content, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match.groups()) > 0:
                    name = f'"{match.group(1)}"' if match.group(1) else '__name__'
                    replacement = pattern['replace'].format(name=name)
                else:
                    replacement = pattern['replace']
                
                content = content[:match.start()] + replacement + content[match.end():]
                changes_made += 1
    
    # Si hay cambios y no es dry run, escribir archivo
    if content != original_content and not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Actualizado: {rel_path} ({changes_made} cambios)")
        return True, changes_made
    elif content != original_content:
        print(f"🔍 Cambios pendientes: {rel_path} ({changes_made} cambios)")
        return False, changes_made
    else:
        return False, 0

def standardize_logging(root_dir, dry_run=True):
    """
    Estandariza el sistema de logging en todos los archivos Python del directorio.
    
    Args:
        root_dir: Directorio raíz
        dry_run: Si True, solo muestra cambios sin aplicarlos
    """
    python_files = list(Path(root_dir).glob('**/*.py'))
    
    print(f"Encontrados {len(python_files)} archivos Python")
    print(f"Modo: {'Vista previa' if dry_run else 'Aplicar cambios'}")
    
    total_files_changed = 0
    total_changes = 0
    
    for file_path in python_files:
        changed, changes = standardize_logging_in_file(file_path, dry_run)
        if changed:
            total_files_changed += 1
        total_changes += changes
    
    print("\nResumen:")
    print(f"Total de archivos procesados: {len(python_files)}")
    print(f"Archivos con cambios: {total_files_changed}")
    print(f"Total de cambios: {total_changes}")
    
    if dry_run and total_changes > 0:
        print("\nEste fue un dry run. Para aplicar los cambios, ejecute:")
        print(f"python {os.path.basename(__file__)} --apply")

def main():
    parser = argparse.ArgumentParser(description='Estandarizar sistema de logging')
    parser.add_argument('--apply', action='store_true', help='Aplicar cambios (sin este flag, solo muestra cambios)')
    parser.add_argument('--dir', type=str, default='.', help='Directorio a procesar (default: directorio actual)')
    
    args = parser.parse_args()
    
    # Determinar directorio base
    base_dir = os.path.abspath(args.dir)
    
    print("=" * 50)
    print("Estandarizando Sistema de Logging")
    print("=" * 50)
    
    standardize_logging(base_dir, not args.apply)

if __name__ == "__main__":
    main()