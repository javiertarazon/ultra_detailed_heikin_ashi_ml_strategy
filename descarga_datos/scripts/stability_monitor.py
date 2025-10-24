#!/usr/bin/env python3
"""
Monitor de Estabilidad 24/7 - Monitorea el sistema de trading en ejecución
Verifica salud, rendimiento y estabilidad durante operaciones extendidas
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
import logging
import os
import sys
from typing import Dict, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stability_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StabilityMonitor:
    """
    Monitor que verifica la estabilidad del sistema de trading 24/7.
    Monitorea recursos, rendimiento y salud del sistema.
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval  # segundos entre checks
        self.start_time = datetime.now()
        self.monitoring = False
        self.metrics_history: List[Dict] = []
        self.alerts_triggered = 0

        # Umbrales de alerta
        self.thresholds = {
            'memory_percent': 85.0,
            'cpu_percent': 90.0,
            'disk_usage_percent': 95.0,
            'max_consecutive_failures': 3
        }

    def start_monitoring(self):
        """Inicia el monitoreo en un hilo separado"""
        if self.monitoring:
            logger.warning("Monitoreo ya está activo")
            return

        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        logger.info("✅ Monitor de estabilidad iniciado")

    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.monitoring = False
        logger.info("🛑 Monitor de estabilidad detenido")

    def _monitoring_loop(self):
        """Bucle principal de monitoreo"""
        consecutive_failures = 0

        while self.monitoring:
            try:
                metrics = self._collect_metrics()

                # Verificar umbrales
                alerts = self._check_thresholds(metrics)

                if alerts:
                    consecutive_failures += 1
                    for alert in alerts:
                        logger.warning(f"🚨 ALERTA: {alert}")
                        self.alerts_triggered += 1
                else:
                    consecutive_failures = 0

                # Verificar salud del sistema de trading
                trading_health = self._check_trading_system_health()

                # Registrar métricas
                metrics.update({
                    'timestamp': datetime.now(),
                    'alerts': alerts,
                    'trading_health': trading_health,
                    'consecutive_failures': consecutive_failures
                })

                self.metrics_history.append(metrics)

                # Log periódico
                if len(self.metrics_history) % 10 == 0:  # Cada 10 minutos
                    self._log_periodic_report()

                # Verificar condición crítica
                if consecutive_failures >= self.thresholds['max_consecutive_failures']:
                    logger.critical("🚨 CONDICIÓN CRÍTICA: Múltiples fallos consecutivos detectados")
                    self._handle_critical_condition()

            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                consecutive_failures += 1

            time.sleep(self.check_interval)

    def _collect_metrics(self) -> Dict:
        """Recolecta métricas del sistema"""
        metrics = {}

        try:
            # Memoria
            memory = psutil.virtual_memory()
            metrics.update({
                'memory_total': memory.total,
                'memory_used': memory.used,
                'memory_percent': memory.percent,
                'memory_available': memory.available
            })

            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.update({
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True)
            })

            # Disco
            disk = psutil.disk_usage('/')
            metrics.update({
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'disk_percent': disk.percent
            })

            # Red
            net = psutil.net_io_counters()
            metrics.update({
                'net_bytes_sent': net.bytes_sent,
                'net_bytes_recv': net.bytes_recv,
                'net_packets_sent': net.packets_sent,
                'net_packets_recv': net.packets_recv
            })

            # Procesos Python
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if 'python' in proc.info['name'].lower():
                    python_processes.append(proc.info)

            metrics['python_processes'] = python_processes
            metrics['python_process_count'] = len(python_processes)

        except Exception as e:
            logger.error(f"Error recolectando métricas: {e}")

        return metrics

    def _check_thresholds(self, metrics: Dict) -> List[str]:
        """Verifica si las métricas exceden los umbrales"""
        alerts = []

        # Memoria
        if metrics.get('memory_percent', 0) > self.thresholds['memory_percent']:
            alerts.append(".1f"
        # CPU
        if metrics.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alerts.append(".1f"
        # Disco
        if metrics.get('disk_percent', 0) > self.thresholds['disk_usage_percent']:
            alerts.append(".1f"
        return alerts

    def _check_trading_system_health(self) -> Dict:
        """Verifica la salud del sistema de trading"""
        health = {
            'status': 'unknown',
            'details': {}
        }

        try:
            # Verificar que los módulos se pueden importar
            from core.ccxt_live_data import CCXTLiveDataProvider
            from core.ccxt_live_trading_orchestrator import CCXTLiveTradingOrchestrator

            health['imports_ok'] = True

            # Verificar archivos de log recientes
            log_files = [
                'logs/bot_trader.log',
                'logs/stability_monitor.log'
            ]

            recent_activity = {}
            for log_file in log_files:
                if os.path.exists(log_file):
                    mtime = os.path.getmtime(log_file)
                    age_hours = (time.time() - mtime) / 3600
                    recent_activity[log_file] = age_hours < 1  # Actividad en la última hora

            health['details']['log_activity'] = recent_activity

            # Verificar archivos de datos recientes
            data_dirs = [
                'data/dashboard_results',
                'data/live_data'
            ]

            data_activity = {}
            for data_dir in data_dirs:
                if os.path.exists(data_dir):
                    files = os.listdir(data_dir)
                    if files:
                        # Verificar si hay archivos modificados recientemente
                        recent_files = 0
                        for file in files[:10]:  # Revisar primeros 10 archivos
                            filepath = os.path.join(data_dir, file)
                            if os.path.isfile(filepath):
                                mtime = os.path.getmtime(filepath)
                                age_hours = (time.time() - mtime) / 3600
                                if age_hours < 24:  # Archivo modificado en las últimas 24h
                                    recent_files += 1
                        data_activity[data_dir] = recent_files > 0

            health['details']['data_activity'] = data_activity

            # Determinar estado general
            all_checks_ok = (
                health.get('imports_ok', False) and
                any(recent_activity.values()) and
                any(data_activity.values())
            )

            health['status'] = 'healthy' if all_checks_ok else 'warning'

        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
            logger.error(f"Error verificando salud del sistema de trading: {e}")

        return health

    def _log_periodic_report(self):
        """Genera un reporte periódico del estado del sistema"""
        if not self.metrics_history:
            return

        latest = self.metrics_history[-1]
        uptime = datetime.now() - self.start_time

        report = f"""
📊 Reporte Periódico - Monitor de Estabilidad
⏱️ Uptime: {uptime}
🔔 Alertas totales: {self.alerts_triggered}

💾 Memoria: {latest.get('memory_percent', 0):.1f}%
🖥️ CPU: {latest.get('cpu_percent', 0):.1f}%
💿 Disco: {latest.get('disk_percent', 0):.1f}%

🐍 Procesos Python: {latest.get('python_process_count', 0)}
🏥 Salud Trading: {latest.get('trading_health', {}).get('status', 'unknown')}
"""

        logger.info(report)

    def _handle_critical_condition(self):
        """Maneja condiciones críticas del sistema"""
        logger.critical("🚨 Manejando condición crítica - sistema potencialmente inestable")

        # En una implementación real, aquí se podrían enviar alertas por email/SMS
        # o ejecutar procedimientos de recuperación automática

        # Por ahora, solo loggeamos y continuamos monitoreando
        logger.critical("🔄 Continuando monitoreo - se recomienda intervención manual")

    def generate_final_report(self) -> str:
        """Genera un reporte final completo"""
        if not self.metrics_history:
            return "No hay datos de métricas disponibles"

        end_time = datetime.now()
        duration = end_time - self.start_time

        # Calcular estadísticas
        memory_usage = [m.get('memory_percent', 0) for m in self.metrics_history]
        cpu_usage = [m.get('cpu_percent', 0) for m in self.metrics_history]

        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0
        max_memory = max(memory_usage) if memory_usage else 0
        avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
        max_cpu = max(cpu_usage) if cpu_usage else 0

        # Salud del trading
        trading_status_counts = {}
        for m in self.metrics_history:
            status = m.get('trading_health', {}).get('status', 'unknown')
            trading_status_counts[status] = trading_status_counts.get(status, 0) + 1

        report = f"""
{'='*70}
📈 REPORTE FINAL - MONITOR DE ESTABILIDAD 24/7
{'='*70}

🕐 Período monitoreado: {duration}
🕐 Inicio: {self.start_time}
🕐 Fin: {end_time}

📊 Métricas de Rendimiento:
   • Memoria promedio: {avg_memory:.1f}%
   • Memoria máxima: {max_memory:.1f}%
   • CPU promedio: {avg_cpu:.1f}%
   • CPU máxima: {max_cpu:.1f}%

🚨 Alertas:
   • Total de alertas: {self.alerts_triggered}
   • Checks realizados: {len(self.metrics_history)}

🏥 Salud del Sistema de Trading:
"""

        for status, count in trading_status_counts.items():
            percentage = (count / len(self.metrics_history)) * 100
            report += f"   • {status.capitalize()}: {count} checks ({percentage:.1f}%)\n"

        report += f"""
✅ Estado Final: {'Estable' if self.alerts_triggered == 0 else 'Con alertas manejadas'}

{'='*70}
"""

        return report

def main():
    """Función principal"""
    print("🔍 Monitor de Estabilidad 24/7")
    print("Monitoreando salud y rendimiento del sistema de trading")
    print("Presione Ctrl+C para detener...")
    print("="*60)

    monitor = StabilityMonitor(check_interval=60)  # Check cada minuto

    try:
        monitor.start_monitoring()

        # Mantener vivo hasta interrupción
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo monitor...")

    finally:
        monitor.stop_monitoring()

        # Generar reporte final
        report = monitor.generate_final_report()
        print(report)

        # Guardar reporte
        with open('logs/stability_monitor_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)

        print("💾 Reporte guardado en: logs/stability_monitor_report.txt")

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">c:\Users\javie\copilot\botcopilot-sar\descarga_datos\scripts\stability_monitor.py