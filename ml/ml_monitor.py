"""
ML Model Monitoring and Feedback System
Tracks model performance, detects drift, and provides feedback for retraining.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

class MLMonitor:
    """Monitors ML model performance and provides feedback."""

    def __init__(self, monitor_dir: str = "reports/ml_monitor"):
        self.monitor_dir = Path(monitor_dir)
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        self.performance_log_file = self.monitor_dir / "performance_log.jsonl"

    def log_performance(self, model_version: str, metrics: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Logs model performance metrics."""
        entry = {
            "timestamp": (timestamp or datetime.now()).isoformat(),
            "model_version": model_version,
            "metrics": metrics
        }
        with open(self.performance_log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        logger.info(f"📊 Logged performance for model '{model_version}': AUC={metrics.get('auc'):.3f}")

    def get_recent_performance(self, model_version: str, num_entries: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent performance logs for a given model."""
        if not self.performance_log_file.exists():
            return []
        
        recent_logs = []
        with open(self.performance_log_file, 'r') as f:
            for line in reversed(f.readlines()): # Read from end for recent
                entry = json.loads(line)
                if entry.get("model_version") == model_version:
                    recent_logs.append(entry)
                    if len(recent_logs) >= num_entries:
                        break
        return list(reversed(recent_logs)) # Return in chronological order

    def detect_drift(self, model_version: str, current_metrics: Dict[str, Any], threshold: float = 0.05) -> bool:
        """Detects performance drift compared to historical performance."""
        recent_performances = self.get_recent_performance(model_version, num_entries=5)
        if not recent_performances:
            return False

        avg_auc = np.mean([p['metrics'].get('auc', 0) for p in recent_performances])
        if current_metrics.get('auc', 0) < avg_auc * (1 - threshold):
            logger.warning(f"🚨 Performance drift detected for model '{model_version}'! "
                        f"Current AUC: {current_metrics.get('auc'):.3f}, Average AUC: {avg_auc:.3f}")
            return True
        return False

    def send_alert(self, message: str):
        """Sends an alert (e.g., to Telegram or email)."""
        logger.error(f"🔔 ML ALERT: {message}")
        # TODO: Integrate with Telegram/email notification system