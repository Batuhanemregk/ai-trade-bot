"""
ML Model Version Manager
Manages loading, saving, and tracking different versions of ML models.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

class MLModelVersionManager:
    """Manages different versions of ML models."""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.active_model_path = self.models_dir / "active_model.json"
        self.available_versions = self._scan_available_versions()

    def _scan_available_versions(self) -> Dict[str, Path]:
        """Scans the models directory for available model versions."""
        versions = {}
        for model_file in self.models_dir.glob("*.pkl"):
            version_name = model_file.stem.replace("_model", "")
            versions[version_name] = model_file
        logger.info(f"Available model versions: {list(versions.keys())}")
        return versions

    def save_model(self, model: Any, metadata: Dict[str, Any], version_name: str):
        """Saves a trained model and its metadata."""
        model_path = self.models_dir / f"{version_name}_model.pkl"
        metadata_path = self.models_dir / f"{version_name}_version.json"

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.available_versions[version_name] = model_path
        logger.info(f"✅ Model '{version_name}' saved to {model_path}")

    def load_model(self, version_name: str) -> Optional[Any]:
        """Loads a specific model version."""
        model_path = self.available_versions.get(version_name)
        if not model_path or not model_path.exists():
            logger.warning(f"⚠️ Model '{version_name}' not found.")
            return None

        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        logger.info(f"✅ Model '{version_name}' loaded from {model_path}")
        return model

    def get_model_metadata(self, version_name: str) -> Dict[str, Any]:
        """Loads metadata for a specific model version."""
        metadata_path = self.models_dir / f"{version_name}_version.json"
        if not metadata_path.exists():
            return {}
        with open(metadata_path, 'r') as f:
            return json.load(f)

    def set_active_model(self, version_name: str):
        """Sets a model as the active model for inference."""
        if version_name not in self.available_versions:
            logger.error(f"❌ Cannot set '{version_name}' as active: version not found.")
            return

        active_info = {
            "active_version": version_name,
            "path": str(self.available_versions[version_name]),
            "timestamp": datetime.now().isoformat()
        }
        with open(self.active_model_path, 'w') as f:
            json.dump(active_info, f, indent=2)
        logger.info(f"✅ Model '{version_name}' set as active.")

    def get_active_model_version(self) -> Optional[str]:
        """Returns the name of the currently active model version."""
        if not self.active_model_path.exists():
            return None
        with open(self.active_model_path, 'r') as f:
            active_info = json.load(f)
            return active_info.get("active_version")

    def get_active_model(self) -> Optional[Any]:
        """Loads and returns the currently active model."""
        active_version = self.get_active_model_version()
        if active_version:
            return self.load_model(active_version)
        return None