# application/signal_history.py
"""
In-memory signal history store for Telegram visualization.
Stores recent signals per symbol, resets on bot restart.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque
from threading import Lock
from loguru import logger

# Maximum signals per symbol
MAX_SIGNALS_PER_SYMBOL = 100

# Thread-safe storage
_lock = Lock()
_signal_store: Dict[str, deque] = {}
_store_id = id(_signal_store)
logger.info(f"[SIGNAL_STORE] Initialized with id={_store_id}")


def record_signal(
    symbol: str,
    ta_score: float,
    ml_score: float,
    news_score: float,
    risk_score: float,
    final_score: float,
    direction: str,
    gate_status: str,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Record a signal for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
        ta_score: Technical analysis score
        ml_score: Machine learning score
        news_score: News sentiment score
        risk_score: Risk score
        final_score: Final composite score
        direction: Signal direction ('long', 'short', 'flat')
        gate_status: Gate status ('PASS', 'PENDING', 'REJECT')
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    signal = {
        'time': timestamp,
        'ta': round(ta_score, 1),
        'ml': round(ml_score, 1),
        'news': round(news_score, 1),
        'risk': round(risk_score, 1),
        'final': round(final_score, 1),
        'dir': direction,
        'gate': gate_status
    }
    
    with _lock:
        if symbol not in _signal_store:
            _signal_store[symbol] = deque(maxlen=MAX_SIGNALS_PER_SYMBOL)
        _signal_store[symbol].appendleft(signal)  # Most recent first
    
    logger.debug(f"[SIGNAL_HIST] Recorded signal for {symbol}: {direction} {final_score:.1f}")


def get_signals(symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent signals for a symbol.
    
    Args:
        symbol: Trading symbol
        limit: Maximum number of signals to return
    
    Returns:
        List of signal dictionaries (most recent first)
    """
    with _lock:
        if symbol not in _signal_store:
            return []
        return list(_signal_store[symbol])[:limit]


def get_all_symbols() -> List[str]:
    """Get list of symbols with recorded signals."""
    with _lock:
        return sorted(_signal_store.keys())


def get_signal_count(symbol: str) -> int:
    """Get number of recorded signals for a symbol."""
    with _lock:
        if symbol not in _signal_store:
            return 0
        return len(_signal_store[symbol])


def clear_signals(symbol: Optional[str] = None) -> int:
    """
    Clear signal history.
    
    Args:
        symbol: Symbol to clear, or None to clear all
    
    Returns:
        Number of signals cleared
    """
    with _lock:
        if symbol:
            if symbol in _signal_store:
                count = len(_signal_store[symbol])
                _signal_store[symbol].clear()
                logger.info(f"[SIGNAL_HIST] Cleared {count} signals for {symbol}")
                return count
            return 0
        else:
            count = sum(len(q) for q in _signal_store.values())
            _signal_store.clear()
            logger.info(f"[SIGNAL_HIST] Cleared all signals ({count} total)")
            return count


def get_stats() -> Dict[str, Any]:
    """Get signal store statistics."""
    with _lock:
        total = sum(len(q) for q in _signal_store.values())
        logger.debug(f"[SIGNAL_STORE] get_stats called, store_id={id(_signal_store)}, symbols={list(_signal_store.keys())}, total={total}")
        return {
            'symbols': len(_signal_store),
            'total_signals': total,
            'per_symbol': {s: len(q) for s, q in _signal_store.items()}
        }


# Singleton getter for external access
def get_signal_history():
    """Get module reference (for consistent API)."""
    return {
        'record': record_signal,
        'get': get_signals,
        'symbols': get_all_symbols,
        'count': get_signal_count,
        'clear': clear_signals,
        'stats': get_stats
    }
