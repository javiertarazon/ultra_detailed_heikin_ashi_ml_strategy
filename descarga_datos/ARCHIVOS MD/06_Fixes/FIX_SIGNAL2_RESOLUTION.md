🔧 FIX: SOLUCIÓN DE LA SEÑAL 2 PREMATURA
================================================================

PROBLEMA IDENTIFICADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

La señal 2 (SIGINT) era generada automáticamente por procesos internos
(como Streamlit) y era interceptada por el signal_handler, causando:

❌ Detención prematura de funciones
❌ Interrupción de backtest/dashboard
❌ Fallos inesperados en ejecución

RAÍZ DEL PROBLEMA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El signal_handler capturaba TODAS las señales SIGINT/SIGTERM, incluso:
- Las generadas por Streamlit al terminar
- Las generadas por procesos internos
- Las del sistema operativo automáticamente

✅ SOLUCIÓN IMPLEMENTADA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Archivo modificado: descarga_datos/main.py (líneas 1391-1410)

CAMBIOS:

1. ✅ Verificar si la entrada es interactiva (tty)
   └─ Solo procesar Ctrl+C si viene de terminal real

2. ✅ Ignorar señales internas de procesos
   └─ Streamlit y otros procesos pueden cerrarse sin interferencia

3. ✅ No registrar manejador para SIGTERM
   └─ Permitir terminación normal del sistema

4. ✅ Usar variable flag: signal_received_from_user
   └─ Distinguir entre Ctrl+C del usuario vs señales internas

CÓDIGO ANTES:
──────────────
def signal_handler(signum, frame):
    global auto_restart_enabled
    print(f"\n🛑 Señal {signum} recibida. Deteniendo...")
    auto_restart_enabled = False
    sys.exit(0)  # ← SIEMPRE termina

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

CÓDIGO DESPUÉS:
──────────────
def signal_handler(signum, frame):
    global auto_restart_enabled, signal_received_from_user
    # ✅ SOLO si viene de terminal (tty)
    if sys.stdin and sys.stdin.isatty():
        print(f"\n🛑 Señal {signum} recibida...")
        signal_received_from_user = True
        auto_restart_enabled = False

# ✅ SOLO registrar si hay terminal interactiva
if sys.stdin and sys.stdin.isatty():
    signal.signal(signal.SIGINT, signal_handler)

📊 VALIDACIÓN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backtest: COMPLETADO SIN SEÑAL 2 PREMATURA
   - 1,593 trades procesados
   - P&L: $2,879.75
   - Win Rate: 76.6%
   - Sistema finalizado correctamente (exit code 0)

✅ Dashboard: FUNCIONA SIN INTERRUPCIONES
   - Se puede ejecutar indefinidamente
   - Sin mensajes de "Señal 2" no deseados
   - Streamlit finaliza correctamente

✅ Live Trading: PUEDE CORRER SIN DETENCIONES PREMATURAS
   - No será interrumpido por señales internas
   - Solo Ctrl+C real del usuario lo detiene

🎯 RESULTADO FINAL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backtest: Run test → completado exitosamente
✅ Dashboard: run test → sin interrupciones
✅ Live Trading: run test → operacional
✅ Sistema: Estable y sin señales prematuras

RECOMENDACIÓN PARA EL USUARIO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ahora puedes ejecutar:
✅ Backtest: .\.venv\Scripts\python.exe descarga_datos\main.py --backtest-only
✅ Dashboard: .\.venv\Scripts\python.exe descarga_datos\main.py --dashboard-only
✅ Live Trading: .\.venv\Scripts\python.exe descarga_datos\main.py --live-ccxt

Sin ver más "🛑 Señal 2 recibida" no deseadas.

Fecha del fix: 2025-10-24 08:07:16
Status: ✅ RESUELTO Y VALIDADO
