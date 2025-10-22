# 🔄 DOWNGRADE PYTHON 3.13.7 → 3.11.x

## 🚨 Problema Identificado
Python 3.13.7 tiene **problemas de compatibilidad** con las bibliotecas del proyecto:
- `joblib` (estrategias ML)
- `sklearn/scipy` (normalización de datos)
- `aiohttp/ccxt` (trading en vivo)

## ✅ Solución: Downgrade a Python 3.11

### 📋 INSTRUCCIONES PASO A PASO

#### PASO 1: Descargar Python 3.11.9
1. Ve a: https://www.python.org/downloads/release/python-3119/
2. Descarga: `python-3.11.9-amd64.exe` (versión Windows 64-bit)
3. **IMPORTANTE**: Guarda el instalador, lo necesitarás

#### PASO 2: Instalar Python 3.11
1. **Ejecuta como Administrador** el instalador descargado
2. ✅ Marca: `Add Python 3.11 to PATH`
3. Selecciona: `Customize installation`
4. En **Optional Features**: marca todo
5. En **Advanced Options**:
   - ✅ Install for all users
   - ✅ Associate files with Python
   - ✅ Create shortcuts
   - ✅ Add Python to environment variables
   - ✅ Precompile standard library
6. Instala en la ubicación por defecto

#### PASO 3: Ejecutar Script Automático
```batch
# Desde el directorio raíz del proyecto:
downgrade_python.bat
```

Este script:
- ✅ Verifica instalación de Python 3.11
- ✅ Respaldá el entorno virtual actual (.venv → .venv_backup_313)
- ✅ Crea nuevo entorno virtual con Python 3.11
- ✅ Instala todas las dependencias

#### PASO 4: Verificar Downgrade
```batch
# CIERRA la terminal actual completamente
# ABRE una nueva terminal PowerShell

cd C:\Users\javie\copilot\botcopilot-sar
.venv\Scripts\Activate.ps1
python verify_downgrade.py
```

#### PASO 5: Probar el Sistema
```batch
python descarga_datos/main.py --live-ccxt
```

## 🔍 Verificación Manual

Si el script automático falla, verifica manualmente:

```batch
# Verificar versión
python --version
# Debe mostrar: Python 3.11.9

# Verificar entorno virtual
.venv\Scripts\Activate.ps1

# Verificar imports críticos
python -c "import ccxt, sklearn, joblib, pandas; print('✅ Todos los imports OK')"

# Verificar proyecto
python -c "from config.config_loader import load_config_from_yaml; print('✅ Proyecto OK')"
```

## 🛠️ Solución de Problemas

### ❌ "Python 3.11 no encontrado"
- Verifica que esté en PATH: `where python311`
- Reinicia la terminal
- Reinstala Python 3.11 con la opción "Add to PATH"

### ❌ "Error instalando dependencias"
```batch
pip install --upgrade setuptools wheel
pip install -r requirements.txt
```

### ❌ "sklearn no funciona"
```batch
pip uninstall scikit-learn
pip install scikit-learn==1.3.2
```

### ❌ "joblib no funciona"
```batch
pip install joblib==1.3.2
```

## 🔄 Restaurar si algo falla

Si necesitas volver a Python 3.13:
```batch
# Restaurar entorno anterior
move .venv .venv_311
move .venv_backup_313 .venv
```

## ✅ Resultado Esperado

Después del downgrade exitoso:
- ✅ `python --version` → Python 3.11.9
- ✅ Sistema de trading funciona sin errores de compatibilidad
- ✅ Posiciones fantasma eliminadas
- ✅ Cálculo de riesgo corregido
- ✅ Operaciones de trading ejecutadas correctamente

## 📞 Soporte

Si encuentras problemas:
1. Ejecuta: `python verify_downgrade.py`
2. Comparte la salida del script
3. Incluye logs de error específicos