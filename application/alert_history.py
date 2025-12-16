# application/alert_history.py
"""
In-memory alert/error history store for Telegram visualization.
Captures warnings and errors, resets on bot restart.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from collections import deque
from threading import Lock
from loguru import logger

# Maximum alerts stored
MAX_ALERTS = 100

# Thread-safe storage
_lock = Lock()
_alert_store: deque = deque(maxlen=MAX_ALERTS)

# Alert levels
AlertLevel = Literal['INFO', 'WARNING', 'ERROR', 'CRITICAL']


def record_alert(
    level: AlertLevel,
    message: str,
    source: str = 'system',
    symbol: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Record an alert/warning/error.
    
    Args:
        level: Alert level (INFO, WARNING, ERROR, CRITICAL)
        message: Alert message
        source: Source component (e.g., 'trading', 'exchange', 'risk')
        symbol: Optional related symbol
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    alert = {
        'time': timestamp,
        'level': level,
        'message': message[:200],  # Truncate long messages
        'source': source,
        'symbol': symbol
    }
    
    with _lock:
        _alert_store.appendleft(alert)  # Most recent first
    
    logger.debug(f"[ALERT_HIST] Recorded {level}: {message[:50]}...")


def get_alerts(
    level: Optional[AlertLevel] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Get recent alerts.
    
    Args:
        level: Filter by level, or None for all
        limit: Maximum number of alerts to return
    
    Returns:
        List of alert dictionaries (most recent first)
    """
    with _lock:
        if level:
            filtered = [a for a in _alert_store if a['level'] == level]
            return filtered[:limit]
        return list(_alert_store)[:limit]


def get_alert_counts() -> Dict[str, int]:
    """Get count of alerts by level."""
    with _lock:
        counts = {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
        for alert in _alert_store:
            lvl = alert.get('level', 'INFO')
            if lvl in counts:
                counts[lvl] += 1
        return counts


def clear_alerts() -> int:
    """Clear all alerts. Returns count cleared."""
    with _lock:
        count = len(_alert_store)
        _alert_store.clear()
        logger.info(f"[ALERT_HIST] Cleared {count} alerts")
        return count


def get_stats() -> Dict[str, Any]:
    """Get alert store statistics."""
    with _lock:
        return {
            'total': len(_alert_store),
            'counts': get_alert_counts()
        }


# Loguru sink to capture warnings and errors
class AlertHistorySink:
    """Loguru sink that captures warnings and errors to alert history."""
    
    def write(self, message):
        try:
            record = message.record
            level = record['level'].name
            
            # Only capture WARNING, ERROR, CRITICAL
            if level not in ['WARNING', 'ERROR', 'CRITICAL']:
                return
            
            # Extract source from logger name or module
            source = record.get('name', 'system')
            if '.' in source:
                source = source.split('.')[-1]
            
            # Get message text
            msg_text = record['message']
            
            # Skip some noisy messages
            skip_patterns = ['rate limit', 'deprecated', 'unclosed']
            if any(p in msg_text.lower() for p in skip_patterns):
                return
            
            record_alert(
                level=level,
                message=msg_text,
                source=source[:20],
                timestamp=record['time'].replace(tzinfo=timezone.utc)
            )
        except Exception:
            pass  # Don't break logging if sink fails


# Global sink instance
_sink_id = None


def install_loguru_sink():
    """Install the alert history sink into loguru."""
    global _sink_id
    if _sink_id is None:
        try:
            _sink_id = logger.add(
                AlertHistorySink(),
                level="WARNING",
                format="{message}"
            )
            logger.debug("[ALERT_HIST] Installed loguru sink")
        except Exception as e:
            logger.warning(f"Failed to install alert history sink: {e}")
