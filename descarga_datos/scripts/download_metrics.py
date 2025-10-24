from dataclasses import dataclass, field
from typing import List

@dataclass
class DownloadMetrics:
    symbol: str
    exchange: str
    start_time: float = field(default_factory=lambda: 0.0)
    end_time: float = field(default_factory=lambda: 0.0)
    duration: float = 0.0
    retry_count: int = 0
    errors: List[str] = field(default_factory=list)
    rows_downloaded: int = 0
    success: bool = True

    def complete(self, success: bool = True):
        self.end_time = self.end_time or 0.0
        self.duration = self.end_time - self.start_time if self.end_time and self.start_time else self.duration
        self.success = success
        return self

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'retry_count': self.retry_count,
            'errors': self.errors,
            'rows_downloaded': self.rows_downloaded,
            'success': self.success
        }
