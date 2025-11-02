"""
Telegram Callback Registry - Compresses callback data to stay under 64 bytes
Uses base62 encoding and key shortening (sym→s, act→a, page→p).
"""

import string
from typing import Dict, Optional
from loguru import logger


# Base62 alphabet: 0-9, a-z, A-Z
BASE62_ALPHABET = string.digits + string.ascii_letters


class CallbackRegistry:
    """Registry for mapping long callback data to short IDs."""
    
    # Key shortening map for common keys
    KEY_SHORTCUTS = {
        'sym': 's',
        'action': 'a',
        'act': 'a',
        'page': 'p',
        'view': 'v',
    }
    
    # Reverse map for decompression
    SHORTCUT_KEYS = {v: k for k, v in KEY_SHORTCUTS.items()}
    
    def __init__(self):
        self.registry: Dict[str, str] = {}  # short_id -> full_callback_data
        self.reverse_registry: Dict[str, str] = {}  # full_callback_data -> short_id
        self.counter = 0
        logger.debug("CallbackRegistry initialized")
    
    @staticmethod
    def _int_to_base62(num: int) -> str:
        """Convert integer to base62 string."""
        if num == 0:
            return BASE62_ALPHABET[0]
        
        result = []
        base = len(BASE62_ALPHABET)
        while num > 0:
            result.append(BASE62_ALPHABET[num % base])
            num //= base
        
        return ''.join(reversed(result))
    
    @staticmethod
    def _base62_to_int(s: str) -> int:
        """Convert base62 string to integer."""
        num = 0
        base = len(BASE62_ALPHABET)
        for char in s:
            num = num * base + BASE62_ALPHABET.index(char)
        return num
    
    def _compress_keys(self, callback_data: str) -> str:
        """
        Compress callback data by shortening common keys.
        
        Examples:
        - ai:sig|sym=BTC -> ai:sig|s=BTC
        - ai:ord|sym=BTC|page=next -> ai:ord|s=BTC|p=next
        
        Note: Only replaces keys in the pattern "key=value", not standalone key names.
        """
        result = callback_data
        for full_key, short_key in self.KEY_SHORTCUTS.items():
            # Replace in param format: |sym=value or sym=value (at start)
            result = result.replace(f"|{full_key}=", f"|{short_key}=")
            # Replace at start of callback (no | prefix)
            if result.startswith(f"{full_key}="):
                result = result.replace(f"{full_key}=", f"{short_key}=", 1)
        
        return result
    
    def _decompress_keys(self, callback_data: str) -> str:
        """
        Decompress callback data by expanding short keys.
        
        Examples:
        - ai:sig|s=BTC -> ai:sig|sym=BTC
        - ai:ord|s=BTC|p=next -> ai:ord|sym=BTC|page=next
        """
        result = callback_data
        for short_key, full_key in self.SHORTCUT_KEYS.items():
            result = result.replace(f"|{short_key}=", f"|{full_key}=")
            result = result.replace(f"{short_key}=", f"{full_key}=")
        
        return result
    
    def register(self, callback_data: str) -> str:
        """
        Register callback data and return compressed version if needed.
        
        Args:
            callback_data: Full callback data string (ai:* schema)
            
        Returns:
            Callback data (short ID if >64 bytes after compression, original if <=64 bytes)
        """
        # First, compress keys
        compressed = self._compress_keys(callback_data)
        
        # If already registered, return existing short ID
        if compressed in self.reverse_registry:
            return self.reverse_registry[compressed]
        
        # Check length after compression
        compressed_bytes = len(compressed.encode('utf-8'))
        
        # If <= 64 bytes after compression, return compressed version
        if compressed_bytes <= 64:
            return compressed
        
        # Otherwise, create short ID using base62
        short_id = f"cb{self._int_to_base62(self.counter)}"
        self.counter += 1
        
        # Store original (not compressed) in registry
        self.registry[short_id] = callback_data
        self.reverse_registry[compressed] = short_id
        
        logger.debug(f"[CALLBACK_REGISTRY] Registered: {callback_data[:50]}... -> {short_id} ({compressed_bytes}B)")
        
        return short_id
    
    def resolve(self, short_id: str) -> Optional[str]:
        """
        Resolve short ID to full callback data.
        
        Args:
            short_id: Short callback ID (e.g., "cb0") or compressed callback (e.g., "ai:sig|s=BTC")
        
        Returns:
            Full callback data (with keys expanded), or None if not found
        """
        # Check if it's a registered short ID (starts with "cb" followed by base62)
        if short_id.startswith("cb") and short_id[2:] and short_id in self.registry:
            full_callback = self.registry[short_id]
            # Expand keys before returning
            return self._decompress_keys(full_callback)
        
        # Not a registered short ID - assume it's already compressed or uncompressed
        # Try decompressing keys and return
        result = self._decompress_keys(short_id)
        
        logger.debug(f"[CALLBACK_REGISTRY] Resolved: {short_id} -> {result[:50]}...")
        
        return result
    
    def get_max_length(self, callback_data: str) -> int:
        """
        Get the actual byte length after compression.
        
        Args:
            callback_data: Full callback data string
            
        Returns:
            Byte length after compression
        """
        compressed = self._compress_keys(callback_data)
        return len(compressed.encode('utf-8'))


# Global singleton instance
_callback_registry: Optional[CallbackRegistry] = None


def get_callback_registry() -> CallbackRegistry:
    """Get the global callback registry instance."""
    global _callback_registry
    if _callback_registry is None:
        _callback_registry = CallbackRegistry()
    return _callback_registry

