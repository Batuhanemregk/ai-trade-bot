"""
UTF-8 Configuration Module
Ensures proper Unicode/emoji support across all environments
"""

import os
import sys
from typing import Optional


def setup_utf8_environment():
    """Setup UTF-8 environment variables and stdout/stderr configuration."""
    
    # Set UTF-8 environment variables
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    os.environ.setdefault('LANG', 'C.UTF-8')
    
    # Configure stdout/stderr for UTF-8 (Python 3.7+)
    if sys.version_info >= (3, 7):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception as e:
            # Fallback if reconfigure fails
            print(f"Warning: Could not reconfigure stdout/stderr: {e}")


def get_emoji_setting() -> bool:
    """Get emoji usage setting from environment."""
    emoji_setting = os.environ.get('LOG_USE_EMOJI', 'true').lower()
    return emoji_setting in ('true', '1', 'yes', 'on')


def format_with_emoji(message: str, emoji: str = '') -> str:
    """Format message with emoji if enabled."""
    if get_emoji_setting() and emoji:
        return f"{emoji} {message}"
    return message


# Auto-setup when module is imported
setup_utf8_environment()

