"""
Telegram State Manager - Tracks message state for inline expansion
"""

from typing import Dict, Any, Optional
from loguru import logger


class TelegramStateManager:
    """Manages state of Telegram messages for inline expansion."""
    
    def __init__(self):
        self.states: Dict[int, Dict[str, Any]] = {}  # message_id -> {original_card, current_section}
        logger.debug("TelegramStateManager initialized")
    
    def save_state(self, message_id: int, original_card: str, section: Optional[str] = None):
        """
        Save the original card and current section for a message.
        
        Args:
            message_id: Telegram message ID
            original_card: Original card content
            section: Currently expanded section (None = original state)
        """
        if message_id not in self.states:
            logger.debug(f"[STATE_MGR] Saving state for message_id={message_id}")
        
        self.states[message_id] = {
            'original': original_card,
            'section': section
        }
    
    def get_state(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the saved state for a message.
        
        Args:
            message_id: Telegram message ID
            
        Returns:
            State dict with 'original' and 'section', or None if not found
        """
        return self.states.get(message_id)
    
    def update_expansion(self, message_id: int, section: str):
        """
        Update the current expanded section for a message.
        
        Args:
            message_id: Telegram message ID
            section: Currently expanded section name
        """
        if message_id in self.states:
            self.states[message_id]['section'] = section
            logger.debug(f"[STATE_MGR] Updated expansion for message_id={message_id}, section={section}")
        else:
            logger.warning(f"[STATE_MGR] No state found for message_id={message_id}")
    
    def clear_state(self, message_id: int):
        """
        Clear state for a message.
        
        Args:
            message_id: Telegram message ID
        """
        if message_id in self.states:
            del self.states[message_id]
            logger.debug(f"[STATE_MGR] Cleared state for message_id={message_id}")


# Global singleton instance
_state_manager: Optional[TelegramStateManager] = None


def get_state_manager() -> TelegramStateManager:
    """Get the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = TelegramStateManager()
    return _state_manager

