"""
Telegram Callback Registry - Compresses callback data to stay under 64 bytes
"""

from typing import Dict, Optional
from loguru import logger


class CallbackRegistry:
    """Registry for mapping long callback data to short IDs."""
    
    def __init__(self):
        self.registry: Dict[str, str] = {}  # short_id -> full_callback_data
        self.reverse_registry: Dict[str, str] = {}  # full_callback_data -> short_id
        self.counter = 0
        logger.debug("CallbackRegistry initialized")
    
    def register(self, callback_data: str) -> str:
        """
        Register callback data and return compressed version if needed.
        
        Args:
            callback_data: Full callback data string
            
        Returns:
            Callback data (short ID if >64 bytes, original if <=64 bytes)
        """
        # If already registered, return existing short ID
        if callback_data in self.reverse_registry:
            return self.reverse_registry[callback_data]
        
        # If <= 64 bytes, return as-is
        if len(callback_data.encode('utf-8')) <= 64:
            return callback_data
        
        # Otherwise, create short ID
        short_id = f"cb_{self.counter}"
        self.counter += 1
        
        self.registry[short_id] = callback_data
        self.reverse_registry[callback_data] = short_id
        
        logger.debug(f"[CALLBACK_REGISTRY] Registered: {callback_data[:50]}... -> {short_id}")
        
        return short_id
    
    def resolve(self, short_id: str) -> Optional[str]:
        """
        Resolve short ID to full callback data.
        
        Args:
            short_id: Short callback ID
            
        Returns:
            Full callback data, or None if not found
        """
        result = self.registry.get(short_id, short_id)  # Return as-is if not in registry
        
        if result == short_id:
            logger.debug(f"[CALLBACK_REGISTRY] Resolved: {short_id} -> {result}")
        else:
            logger.debug(f"[CALLBACK_REGISTRY] Resolved: {short_id} -> {result[:50]}...")
        
        return result


# Global singleton instance
_callback_registry: Optional[CallbackRegistry] = None


def get_callback_registry() -> CallbackRegistry:
    """Get the global callback registry instance."""
    global _callback_registry
    if _callback_registry is None:
        _callback_registry = CallbackRegistry()
    return _callback_registry

