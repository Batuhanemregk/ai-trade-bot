"""
Telegram User Settings - Persists user preferences to file.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class UserSettings:
    """
    Manages user-specific settings for Telegram interface.
    
    Settings are stored in data/telegram_user_settings.json
    
    Available Settings:
    - show_emojis: bool (default: True)
    - compact_mode: bool (default: False)
    - confirmations: bool (default: True)
    - auto_refresh: bool (default: False)
    - notification_level: str (all|important|critical)
    - default_timeframe: str (15m)
    """
    
    DEFAULTS = {
        'show_emojis': True,
        'compact_mode': False,
        'confirmations': True,
        'auto_refresh': False,
        'notification_level': 'all',
        'default_timeframe': '15m',
        'leverage': 5,  # Default leverage (1-10)
    }
    
    def __init__(self, file_path: str = None):
        self.logger = logger.bind(component="user_settings")
        
        if file_path is None:
            # Default path
            base_dir = Path(__file__).parent.parent.parent
            file_path = base_dir / "data" / "telegram_user_settings.json"
        
        self.file_path = Path(file_path)
        self._settings: Dict[str, Dict[str, Any]] = {}
        self._last_modified = None
        
        self._load()
    
    def _load(self):
        """Load settings from file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    self._settings = json.load(f)
                self._last_modified = datetime.fromtimestamp(self.file_path.stat().st_mtime)
                self.logger.debug(f"Loaded settings from {self.file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load settings: {e}")
                self._settings = {}
        else:
            self._settings = {}
    
    def _save(self):
        """Save settings to file."""
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w') as f:
                json.dump(self._settings, f, indent=2, default=str)
            
            self._last_modified = datetime.now()
            self.logger.debug(f"Saved settings to {self.file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
    
    def _get_user_key(self, user_id: Optional[int]) -> str:
        """Get settings key for user."""
        if user_id is None:
            return "default"
        return str(user_id)
    
    def get(self, user_id: Optional[int], key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            user_id: Telegram user ID (or None for global)
            key: Setting key
            default: Default value if not set
            
        Returns:
            Setting value
        """
        user_key = self._get_user_key(user_id)
        
        # Check user-specific settings first
        if user_key in self._settings and key in self._settings[user_key]:
            return self._settings[user_key][key]
        
        # Fall back to defaults
        if default is not None:
            return default
        
        return self.DEFAULTS.get(key)
    
    def set(self, user_id: Optional[int], key: str, value: Any):
        """
        Set a setting value.
        
        Args:
            user_id: Telegram user ID (or None for global)
            key: Setting key
            value: Setting value
        """
        user_key = self._get_user_key(user_id)
        
        if user_key not in self._settings:
            self._settings[user_key] = {}
        
        self._settings[user_key][key] = value
        self._settings[user_key]['_updated_at'] = datetime.now().isoformat()
        
        self._save()
        self.logger.info(f"Set {key}={value} for user {user_key}")
    
    def get_all(self, user_id: Optional[int]) -> Dict[str, Any]:
        """
        Get all settings for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict of all settings with defaults applied
        """
        user_key = self._get_user_key(user_id)
        user_settings = self._settings.get(user_key, {})
        
        # Merge with defaults
        result = {**self.DEFAULTS}
        for key, value in user_settings.items():
            if not key.startswith('_'):
                result[key] = value
        
        return result
    
    def reset(self, user_id: Optional[int], key: Optional[str] = None):
        """
        Reset settings to defaults.
        
        Args:
            user_id: Telegram user ID
            key: Specific key to reset (or None for all)
        """
        user_key = self._get_user_key(user_id)
        
        if user_key not in self._settings:
            return
        
        if key:
            # Reset specific key
            if key in self._settings[user_key]:
                del self._settings[user_key][key]
        else:
            # Reset all
            del self._settings[user_key]
        
        self._save()
        self.logger.info(f"Reset settings for user {user_key}")
    
    def toggle(self, user_id: Optional[int], key: str) -> bool:
        """
        Toggle a boolean setting.
        
        Args:
            user_id: Telegram user ID
            key: Setting key
            
        Returns:
            New value after toggle
        """
        current = self.get(user_id, key, default=False)
        new_value = not current
        self.set(user_id, key, new_value)
        return new_value


# Global instance
_user_settings: Optional[UserSettings] = None


def get_user_settings() -> UserSettings:
    """Get the global user settings instance."""
    global _user_settings
    if _user_settings is None:
        _user_settings = UserSettings()
    return _user_settings
