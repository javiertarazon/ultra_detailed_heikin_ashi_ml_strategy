"""
Sistema de monitoreo y métricas para el descargador de datos.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json

from utils.logger import get_logger
from utils.download_metrics import DownloadMetrics

class MonitoringManager:
    def __init__(self, metrics_dir):
        self.logger = get_logger(__name__)
        self.metrics_dir = metrics_dir
        self.current_metrics: Dict[str, DownloadMetrics] = {}

    def start_operation(self, symbol: str, exchange: str) -> str:
        """Inicia el seguimiento de una operación."""
        timestamp = int(time.time())
        operation_id = f"{exchange}_{symbol}_{timestamp}"
        metrics_dir = self.metrics_dir / exchange / symbol.replace('/', '_')
        metrics_dir.mkdir(parents=True, exist_ok=True)
        self.current_metrics[operation_id] = DownloadMetrics(symbol=symbol, exchange=exchange)
        return operation_id

    def update_metrics(self, operation_id: str, **updates):
        """Actualiza las métricas de una operación."""
        if operation_id in self.current_metrics:
            for key, value in updates.items():
                if hasattr(self.current_metrics[operation_id], key):
                    setattr(self.current_metrics[operation_id], key, value)

    def complete_operation(self, operation_id: str, success: bool = True):
        """Marca una operación como completada y guarda las métricas."""
        if operation_id in self.current_metrics:
            metrics = self.current_metrics[operation_id].complete(success)
            self._save_metrics(operation_id, metrics)
            self._check_performance_alerts(metrics)
            del self.current_metrics[operation_id]

    def _save_metrics(self, operation_id: str, metrics):
        """Guarda las métricas en un archivo JSON."""
        # Crear directorio para el exchange y símbolo
        metrics_subdir = self.metrics_dir / operation_id.split('_')[0] / operation_id.split('_')[1]
        metrics_subdir.mkdir(parents=True, exist_ok=True)

        # Guardar métricas
        metrics_file = metrics_subdir / f"{operation_id.split('_')[2]}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

    def _check_performance_alerts(self, metrics):
        """Verifica si hay problemas de rendimiento que requieran atención."""
        if metrics.duration > 300:  # 5 minutos
            self.logger.warning(
                f"Operación lenta detectada: {metrics.exchange}/{metrics.symbol} "
                f"tomó {metrics.duration:.2f} segundos"
            )
        if metrics.retry_count > 5:
            self.logger.warning(
                f"Alto número de reintentos: {metrics.exchange}/{metrics.symbol} "
                f"requirió {metrics.retry_count} reintentos"
            )
        if hasattr(metrics, 'errors') and len(metrics.errors) > 0:
            self.logger.error(
                f"Errores durante la descarga de {metrics.exchange}/{metrics.symbol}: "
                f"{', '.join(metrics.errors)}"
            )

    def get_performance_summary(self) -> dict:
        """Genera un resumen del rendimiento del sistema."""
        total_operations = 0
        total_errors = 0
        total_rows = 0
        total_duration = 0

        for metrics_file in self.metrics_dir.glob("*.json"):
            with open(metrics_file) as f:
                metrics = json.load(f)
                total_operations += 1
                total_errors += len(metrics['errors'])
                total_rows += metrics['rows_downloaded']
                total_duration += metrics['duration']

        return {
            'total_operations': total_operations,
            'total_errors': total_errors,
            'total_rows_downloaded': total_rows,
            'average_duration': total_duration / total_operations if total_operations > 0 else 0,
            'success_rate': (total_operations - total_errors) / total_operations if total_operations > 0 else 0
        }

    def alert_download_issue(self, symbol: str, timeframe: str, message: str):
        """
        Alerta sobre problemas de descarga que requieren atención.
        Args:
            symbol: Símbolo afectado
            timeframe: Timeframe solicitado
            message: Descripción del problema
        """
        alert_msg = f"🚨 ALERTA DE DESCARGA: {symbol} ({timeframe}) - {message}"
        self.logger.warning(alert_msg)
        # Podría enviar email/SMS en futuras versiones
        # self._send_alert_notification(alert_msg)
