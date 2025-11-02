"""
Telegram Formatter - Message formatting utilities
Handles footer generation, monospace columns, emoji toggling, and size validation.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger


class TelegramFormatter:
    """
    Formatter for Telegram messages.
    
    Features:
    - Footer generation with timestamp, timeframe, mode
    - Monospace column formatting
    - Emoji toggle support
    - Message size validation
    """
    
    # Emoji legend (optional)
    EMOJI_LEGEND = {
        'long': '📈',
        'short': '📉',
        'risk': '⚠',
        'age': '⏱',
        'score': '🎯',
        'flat': '➡',
        'up': '🟢',
        'down': '🔴',
        'neutral': '⚪',
    }
    
    def __init__(self, use_emojis: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_emojis: Whether to use emojis in formatting
        """
        self.use_emojis = use_emojis
        self.max_message_size = 3500  # Telegram limit with buffer
        self.logger = logger.bind(component="telegram_formatter")
    
    def format_footer(
        self,
        timeframe: str = "15m",
        mode: str = "paper",
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate footer string with last update time, timeframe, and mode.
        
        Args:
            timeframe: Trading timeframe (e.g., "15m", "1h", "4h")
            mode: Trading mode ("dry", "paper", "live")
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Footer string: "Last update: <hh:mm:ss> • TF: <tf> • Mode: <mode>"
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        time_str = timestamp.strftime('%H:%M:%S')
        
        footer = f"Last update: {time_str} • TF: {timeframe} • Mode: {mode}"
        return footer
    
    def format_monospace_column(
        self,
        rows: list[tuple],
        headers: Optional[list[str]] = None,
        col_sep: str = "  "
    ) -> str:
        """
        Format data as monospace columns.
        
        Args:
            rows: List of tuples, each tuple is a row of values
            headers: Optional list of header strings
            col_sep: Column separator string
        
        Returns:
            Formatted string with aligned columns
        """
        if not rows:
            return ""
        
        # Calculate max width for each column
        num_cols = len(rows[0])
        col_widths = [0] * num_cols
        
        # Include headers in width calculation
        all_rows = rows
        if headers:
            all_rows = [tuple(headers)] + rows
        
        for row in all_rows:
            for i, cell in enumerate(row):
                cell_str = str(cell)
                col_widths[i] = max(col_widths[i], len(cell_str))
        
        # Format rows
        formatted_lines = []
        
        if headers:
            header_line = col_sep.join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
            formatted_lines.append(header_line)
            formatted_lines.append("-" * len(header_line))
        
        for row in rows:
            row_line = col_sep.join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            formatted_lines.append(row_line)
        
        return "\n".join(formatted_lines)
    
    def format_emoji(self, key: str, fallback: str = "") -> str:
        """
        Get emoji for a key, or return fallback if emojis disabled.
        
        Args:
            key: Emoji key (e.g., 'long', 'short', 'risk')
            fallback: Fallback text if emojis disabled
        
        Returns:
            Emoji string or fallback
        """
        if not self.use_emojis:
            return fallback
        
        return self.EMOJI_LEGEND.get(key, "")
    
    def validate_message_size(self, text: str) -> tuple[bool, int]:
        """
        Validate message size and warn if too large.
        
        Args:
            text: Message text to validate
        
        Returns:
            Tuple of (is_valid, size_bytes)
        """
        size_bytes = len(text.encode('utf-8'))
        is_valid = size_bytes <= self.max_message_size
        
        if not is_valid:
            self.logger.warning(
                f"Message size {size_bytes}B exceeds limit {self.max_message_size}B"
            )
        
        return is_valid, size_bytes
    
    def truncate_message(self, text: str, max_size: Optional[int] = None) -> str:
        """
        Truncate message if exceeds size limit, appending "(+more...)".
        
        Args:
            text: Message text to truncate
            max_size: Optional max size (defaults to self.max_message_size)
        
        Returns:
            Truncated text with "(+more...)" appended if needed
        """
        if max_size is None:
            max_size = self.max_message_size
        
        # Reserve space for "(+more...)" footer
        truncate_marker = "\n(+more...)"
        reserved_bytes = len(truncate_marker.encode('utf-8'))
        max_content_bytes = max_size - reserved_bytes
        
        text_bytes = text.encode('utf-8')
        if len(text_bytes) <= max_size:
            return text
        
        # Truncate at character boundary (not byte boundary)
        truncated_bytes = text_bytes[:max_content_bytes]
        # Try to decode, removing incomplete characters
        try:
            truncated_text = truncated_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # If incomplete, remove last byte until valid
            while truncated_bytes:
                try:
                    truncated_text = truncated_bytes.decode('utf-8')
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
            else:
                truncated_text = ""
        
        return truncated_text + truncate_marker
    
    def add_footer(
        self,
        text: str,
        timeframe: str = "15m",
        mode: str = "paper",
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Add footer to message text.
        
        Args:
            text: Message text
            timeframe: Trading timeframe
            mode: Trading mode
            timestamp: Optional timestamp
        
        Returns:
            Text with footer appended
        """
        footer = self.format_footer(timeframe, mode, timestamp)
        
        if text:
            return f"{text}\n\n{footer}"
        else:
            return footer
    
    def format_number(self, value: float, decimals: int = 2, prefix: str = "") -> str:
        """
        Format a number with thousand separators.
        
        Args:
            value: Number to format
            decimals: Decimal places
            prefix: Optional prefix (e.g., "$")
        
        Returns:
            Formatted string (e.g., "$1,234.56")
        """
        if prefix:
            return f"{prefix}{value:,.{decimals}f}"
        else:
            return f"{value:,.{decimals}f}"
    
    def format_percentage(self, value: float, decimals: int = 1) -> str:
        """
        Format a percentage.
        
        Args:
            value: Value (0.0-1.0 for 0-100%)
            decimals: Decimal places
        
        Returns:
            Formatted string (e.g., "12.5%")
        """
        return f"{value * 100:.{decimals}f}%"


def get_formatter(use_emojis: bool = True) -> TelegramFormatter:
    """
    Get a Telegram formatter instance.
    
    Args:
        use_emojis: Whether to use emojis
    
    Returns:
        TelegramFormatter instance
    """
    return TelegramFormatter(use_emojis=use_emojis)

