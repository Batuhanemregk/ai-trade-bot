"""
Telegram Inline Expander - Accordion-style inline content expansion
"""

from typing import List, Dict, Any
from loguru import logger


class InlineExpander:
    """Handles accordion-style inline expansion of Telegram card content."""
    
    def __init__(self):
        logger.debug("InlineExpander initialized")
    
    def expand_section(self, original_card: str, section_name: str, section_data: str) -> tuple[str, List[List[Dict[str, str]]]]:
        """
        Expand a section inline by appending to the original card.
        
        Args:
            original_card: Original card content
            section_name: Name of the section being expanded
            section_data: Data to show in the expanded section
            
        Returns:
            Tuple of (expanded_content, buttons)
        """
        expanded = f"{original_card}\n\n{'=' * 40}\n**{section_name}**\n{section_data}"
        
        # Add Back button
        buttons = [[{"text": "⬅️ Back", "callback_data": "back"}]]
        
        logger.debug(f"[INLINE_EXPAND] Expanded section: {section_name}")
        
        return expanded, buttons
    
    def collapse_section(self, original_card: str) -> tuple[str, List[List[Dict[str, str]]]]:
        """
        Collapse to original card (remove expanded section).
        
        Args:
            original_card: Original card content
            
        Returns:
            Tuple of (original_content, empty_buttons)
        """
        logger.debug("[INLINE_EXPAND] Collapsed to original card")
        return original_card, []


# Global singleton instance
_inline_expander: 'InlineExpander | None' = None


def get_inline_expander() -> InlineExpander:
    """Get the global inline expander instance."""
    global _inline_expander
    if _inline_expander is None:
        _inline_expander = InlineExpander()
    return _inline_expander

