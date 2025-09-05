def escape_markdown_v2(text: str) -> str:
    """Escape text for MarkdownV2 format"""
    if not text:
        return ""
    
    # Characters that need escaping in MarkdownV2
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def format_telegram_message(content: str, parse_mode: str = "MarkdownV2") -> str:
    """Format message for Telegram with proper escaping"""
    if parse_mode == "MarkdownV2":
        return escape_markdown_v2(content)
    elif parse_mode == "HTML":
        # Basic HTML escaping
        return content.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
    else:
        return content
