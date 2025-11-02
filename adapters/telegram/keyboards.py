"""
Telegram Keyboards Builder
Builds inline keyboards from button specs and registers callbacks through registry.
"""

from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from adapters.telegram.callback_registry import CallbackRegistry, get_callback_registry
from loguru import logger


class KeyboardBuilder:
    """
    Builder for Telegram inline keyboards.
    
    Features:
    - Validates button count (max 8 rows, 3-5 buttons per row)
    - Registers callbacks through callback registry
    - Ensures callbacks ≤64 bytes
    """
    
    MAX_ROWS = 8
    MAX_BUTTONS_PER_ROW = 5
    MIN_BUTTONS_PER_ROW = 1
    
    def __init__(self, callback_registry: Optional[CallbackRegistry] = None):
        """
        Initialize keyboard builder.
        
        Args:
            callback_registry: Optional callback registry (uses global if None)
        """
        self.callback_registry = callback_registry or get_callback_registry()
        self.logger = logger.bind(component="keyboard_builder")
    
    def build_keyboard(
        self,
        buttons: List[List[Dict[str, str]]],
        validate: bool = True
    ) -> InlineKeyboardMarkup:
        """
        Build inline keyboard from button specs.
        
        Args:
            buttons: List of rows, each row is a list of button dicts
                     Each button dict has: {'text': str, 'callback_data': str}
            validate: Whether to validate button count
        
        Returns:
            InlineKeyboardMarkup instance
        
        Raises:
            ValueError: If validation fails
        """
        if validate:
            self._validate_buttons(buttons)
        
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                text = button.get('text', '')
                callback_data = button.get('callback_data', '')
                
                # Register callback through registry
                registered_callback = self.callback_registry.register(callback_data)
                
                # Verify callback length
                callback_bytes = len(registered_callback.encode('utf-8'))
                if callback_bytes > 64:
                    self.logger.warning(
                        f"Callback still >64B after registration: {callback_data} ({callback_bytes}B)"
                    )
                
                keyboard_row.append(
                    InlineKeyboardButton(text=text, callback_data=registered_callback)
                )
            
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def _validate_buttons(self, buttons: List[List[Dict[str, str]]]):
        """
        Validate button layout.
        
        Args:
            buttons: Button layout
        
        Raises:
            ValueError: If validation fails
        """
        num_rows = len(buttons)
        
        if num_rows > self.MAX_ROWS:
            raise ValueError(
                f"Too many rows: {num_rows} > {self.MAX_ROWS}"
            )
        
        for i, row in enumerate(buttons):
            num_buttons = len(row)
            
            if num_buttons < self.MIN_BUTTONS_PER_ROW:
                raise ValueError(
                    f"Row {i} has too few buttons: {num_buttons} < {self.MIN_BUTTONS_PER_ROW}"
                )
            
            if num_buttons > self.MAX_BUTTONS_PER_ROW:
                raise ValueError(
                    f"Row {i} has too many buttons: {num_buttons} > {self.MAX_BUTTONS_PER_ROW}"
                )
            
            # Validate button structure
            for j, button in enumerate(row):
                if not isinstance(button, dict):
                    raise ValueError(f"Row {i}, button {j} is not a dict")
                
                if 'text' not in button:
                    raise ValueError(f"Row {i}, button {j} missing 'text' key")
                
                if 'callback_data' not in button:
                    raise ValueError(f"Row {i}, button {j} missing 'callback_data' key")
    
    def build_single_button(self, text: str, callback_data: str) -> InlineKeyboardMarkup:
        """
        Build keyboard with a single button.
        
        Args:
            text: Button text
            callback_data: Callback data
        
        Returns:
            InlineKeyboardMarkup with single button
        """
        return self.build_keyboard([[{'text': text, 'callback_data': callback_data}]])
    
    def build_back_button(self, callback_data: str = "ai:main") -> InlineKeyboardMarkup:
        """
        Build keyboard with a back button.
        
        Args:
            callback_data: Back callback data (default: ai:main)
        
        Returns:
            InlineKeyboardMarkup with back button
        """
        return self.build_single_button("⬅️ Back", callback_data)


# Global instance
_keyboard_builder: Optional[KeyboardBuilder] = None


def get_keyboard_builder() -> KeyboardBuilder:
    """Get the global keyboard builder instance."""
    global _keyboard_builder
    if _keyboard_builder is None:
        _keyboard_builder = KeyboardBuilder()
    return _keyboard_builder


def build_keyboard(
    buttons: List[List[Dict[str, str]]],
    validate: bool = True
) -> InlineKeyboardMarkup:
    """
    Convenience function to build keyboard.
    
    Args:
        buttons: Button layout
        validate: Whether to validate
    
    Returns:
        InlineKeyboardMarkup instance
    """
    builder = get_keyboard_builder()
    return builder.build_keyboard(buttons, validate=validate)

