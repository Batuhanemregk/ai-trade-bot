"""
ML Model Auto-Deployment System
Compares new model performance against active model and deploys if better.
"""

from typing import Dict, Any
from loguru import logger

from ml.model_version_manager import MLModelVersionManager
from ml.ml_monitor import MLMonitor

class MLAutoDeployer:
    """Automates ML model deployment based on performance."""

    def __init__(self, performance_threshold: float = 0.05):
        self.model_manager = MLModelVersionManager()
        self.ml_monitor = MLMonitor()
        self.performance_threshold = performance_threshold # e.g., 0.05 for 5% AUC improvement

    def compare_and_deploy(self, new_model_version: str, new_model_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares a new model's performance with the active model and deploys if significantly better.
        """
        active_version = self.model_manager.get_active_model_version()
        
        if not active_version:
            logger.info(f"No active model found. Deploying new model '{new_model_version}' as the first active model.")
            self.model_manager.set_active_model(new_model_version)
            self.ml_monitor.log_performance(new_model_version, new_model_metrics)
            return {"status": "DEPLOYED", "reason": "No active model, new model deployed."}

        active_model_metadata = self.model_manager.get_model_metadata(active_version)
        active_model_metrics = active_model_metadata.get("metrics", {})

        logger.info(f"Comparing new model '{new_model_version}' with active model '{active_version}'...")
        logger.info(f"  Active Model AUC: {active_model_metrics.get('auc', 0):.3f}")
        logger.info(f"  New Model AUC: {new_model_metrics.get('auc', 0):.3f}")

        # Compare AUC (Area Under Curve) as the primary metric
        active_auc = active_model_metrics.get('auc', 0)
        new_auc = new_model_metrics.get('auc', 0)

        if new_auc > active_auc * (1 + self.performance_threshold):
            logger.info(f"✅ New model '{new_model_version}' shows significant improvement (AUC +{((new_auc - active_auc)/active_auc)*100:.1f}%). Deploying...")
            self.model_manager.set_active_model(new_model_version)
            self.ml_monitor.log_performance(new_model_version, new_model_metrics)
            return {"status": "DEPLOYED", "reason": "New model significantly better."}
        elif new_auc > active_auc:
            logger.info(f"ℹ️ New model '{new_model_version}' is slightly better (AUC +{((new_auc - active_auc)/active_auc)*100:.1f}%), but not above threshold. Not deploying automatically.")
            self.ml_monitor.log_performance(new_model_version, new_model_metrics) # Log performance anyway
            return {"status": "NOT_DEPLOYED_SLIGHTLY_BETTER", "reason": "New model slightly better, but not above threshold."}
        else:
            logger.info(f"❌ New model '{new_model_version}' is not better than active model. Keeping '{active_version}'.")
            self.ml_monitor.log_performance(new_model_version, new_model_metrics) # Log performance anyway
            return {"status": "NOT_DEPLOYED_WORSE", "reason": "New model not better."}