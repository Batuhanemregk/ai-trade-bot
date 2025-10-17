"""
Log Redaction Filter - Prevents sensitive data from appearing in logs
Follows Single Responsibility: Only handles log sanitization
"""

import re
from typing import Dict, Pattern
from loguru import logger as base_logger


class LogRedactionFilter:
    """
    Filters sensitive information from log messages.
    
    Responsibilities:
    - Detect sensitive patterns (API keys, tokens, secrets)
    - Replace with masked versions
    - Maintain readability while protecting data
    """
    
    # Sensitive patterns to redact
    REDACTION_PATTERNS: Dict[str, Pattern] = {
        # API Keys (various formats)
        'api_key': re.compile(
            r'(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{8,})["\']?',
            re.IGNORECASE
        ),
        
        # Secrets (various formats)
        'secret': re.compile(
            r'(?:secret|api[_-]?secret)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{8,})["\']?',
            re.IGNORECASE
        ),
        
        # Passphrases
        'passphrase': re.compile(
            r'(?:passphrase|pass[_-]?phrase)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{4,})["\']?',
            re.IGNORECASE
        ),
        
        # Tokens (Bot tokens, Bearer tokens)
        'token': re.compile(
            r'(?:token|bot[_-]?token|bearer)["\']?\s*[:=]\s*["\']?([A-Za-z0-9:_-]{10,})["\']?',
            re.IGNORECASE
        ),
        
        # Passwords
        'password': re.compile(
            r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([A-Za-z0-9!@#$%^&*()_+-=]{4,})["\']?',
            re.IGNORECASE
        ),
        
        # Private keys
        'private_key': re.compile(
            r'(?:private[_-]?key|priv[_-]?key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{20,})["\']?',
            re.IGNORECASE
        ),
        
        # Email addresses (partial redaction)
        'email': re.compile(
            r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
        ),
        
        # IP addresses in auth contexts
        'ip_auth': re.compile(
            r'(?:IP|ip)["\']?\s*[:=]\s*["\']?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})["\']?'
        ),
    }
    
    def __init__(self, show_prefix: int = 4, show_suffix: int = 0):
        """
        Initialize redaction filter.
        
        Args:
            show_prefix: Number of chars to show at start (default: 4)
            show_suffix: Number of chars to show at end (default: 0)
        """
        self.show_prefix = show_prefix
        self.show_suffix = show_suffix
    
    def filter(self, record: Dict) -> Dict:
        """
        Filter log record to redact sensitive information.
        
        Args:
            record: Loguru record dict
            
        Returns:
            Modified record with redacted message
        """
        try:
            message = record.get('message', '')
            
            if not message:
                return record
            
            # Apply all redaction patterns
            redacted_message = message
            
            for pattern_name, pattern in self.REDACTION_PATTERNS.items():
                if pattern_name == 'email':
                    # Special handling for emails
                    redacted_message = self._redact_emails(redacted_message, pattern)
                else:
                    # Standard redaction
                    redacted_message = self._redact_pattern(redacted_message, pattern, pattern_name)
            
            record['message'] = redacted_message
            return record
            
        except Exception as e:
            # If redaction fails, don't break logging
            base_logger.error(f"Log redaction failed: {e}")
            return record
    
    def _redact_pattern(self, text: str, pattern: Pattern, pattern_name: str) -> str:
        """Redact a specific pattern."""
        def replace_match(match):
            # Get the captured group (the sensitive part)
            if len(match.groups()) < 1:
                return match.group(0)
            
            sensitive_value = match.group(1)
            masked_value = self._mask_value(sensitive_value)
            
            # Replace the sensitive part while keeping the context
            full_match = match.group(0)
            return full_match.replace(sensitive_value, masked_value)
        
        return pattern.sub(replace_match, text)
    
    def _redact_emails(self, text: str, pattern: Pattern) -> str:
        """Redact email addresses partially."""
        def replace_email(match):
            username = match.group(1)
            domain = match.group(2)
            
            # Show first 2 chars of username
            if len(username) > 3:
                masked_username = username[:2] + '***'
            else:
                masked_username = '***'
            
            return f"{masked_username}@{domain}"
        
        return pattern.sub(replace_email, text)
    
    def _mask_value(self, value: str) -> str:
        """
        Mask a sensitive value.
        
        Args:
            value: Value to mask
            
        Returns:
            Masked value (e.g., "abc1***")
        """
        if len(value) <= self.show_prefix:
            return '*' * len(value)
        
        if self.show_suffix > 0:
            prefix = value[:self.show_prefix]
            suffix = value[-self.show_suffix:]
            middle_length = len(value) - self.show_prefix - self.show_suffix
            return f"{prefix}{'*' * min(middle_length, 10)}{suffix}"
        else:
            prefix = value[:self.show_prefix]
            return f"{prefix}***"


def create_redaction_filter(show_prefix: int = 4, show_suffix: int = 0):
    """
    Create a redaction filter for loguru.
    
    Usage:
        from infrastructure.log_redaction import create_redaction_filter
        
        logger.add(
            "logs/main.log",
            filter=create_redaction_filter(show_prefix=4)
        )
    
    Args:
        show_prefix: Number of chars to show at start
        show_suffix: Number of chars to show at end
        
    Returns:
        Filter function for loguru
    """
    redactor = LogRedactionFilter(show_prefix, show_suffix)
    return redactor.filter


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret for safe display.
    
    Args:
        secret: Secret string to mask
        visible_chars: Number of visible characters
        
    Returns:
        Masked string (e.g., "abc1...")
    """
    if not secret or len(secret) <= visible_chars:
        return '*' * len(secret) if secret else ''
    
    return f"{secret[:visible_chars]}..."


# Test function
if __name__ == "__main__":
    test_messages = [
        "API Key: abc123defg456",
        "api_key=1234567890abcdef",
        "secret='my-super-secret-key'",
        "token: 123456:ABCdefGHI-jklMNO",
        "passphrase=MySecretPhrase123",
        "email: test@example.com",
        "Initializing with API key: bafb2c4b-e9a1-41e1-90e0-5c918cc7491f"
    ]
    
    filter_instance = LogRedactionFilter()
    
    print("Testing Log Redaction:")
    print("=" * 60)
    
    for msg in test_messages:
        record = {'message': msg}
        filtered = filter_instance.filter(record)
        
        print(f"\nOriginal: {msg}")
        print(f"Redacted: {filtered['message']}")

