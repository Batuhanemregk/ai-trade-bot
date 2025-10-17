"""
Analysis Summary Logger
Enhanced logging for trading analysis with age tracking and detailed metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from application.log_formatter import get_log_formatter
from application.market_data_service import get_market_data_cache


class AnalysisSummaryLogger:
    """
    Enhanced logger for trading analysis with:
    - Age tracking (time since last signal)
    - Formatted output (line/block modes)
    - Batch summaries
    - Prometheus metrics integration
    """
    
    def __init__(self):
        self.formatter = get_log_formatter()
        self.market_cache = get_market_data_cache()
        
        # Track last signals for age calculation
        self._last_signals: Dict[str, datetime] = {}
        
        # Batch statistics
        self._batch_stats = {
            'total': 0,
            'success': 0,
            'fail': 0,
            'signals': {'LONG': 0, 'SHORT': 0, 'HOLD': 0},
            'scores': []
        }
        
        # Prometheus metrics (will be injected)
        self.prometheus_exporter = None
    
    def set_prometheus_exporter(self, exporter):
        """Set Prometheus exporter for metrics."""
        self.prometheus_exporter = exporter
    
    def log_analysis(self, data: Dict[str, Any]):
        """
        Log a single symbol analysis with enhanced formatting.
        
        Args:
            data: Analysis data containing all scores, signals, and metadata
        """
        symbol = data.get('symbol', 'UNKNOWN')
        
        # Age is already calculated in signal gate (counter format: 0/6, 3/6, etc.)
        # We use gate_details if available, otherwise calculate time-based age
        if 'age_bars' in data:
            # Already provided in counter format
            pass
        else:
            # Fallback: calculate time-based age (for compatibility)
            age = self._calculate_age(symbol, data.get('timestamp'))
            if age is not None:
                data['age'] = age
        
        # Get cache age for data freshness
        timeframe = data.get('timeframe', '15m')
        cache_age = self.market_cache.get_age(symbol, timeframe)
        if cache_age:
            data['cache_age'] = cache_age
        
        # Format and log
        message = self.formatter.format_analysis_summary(data)
        logger.info(message)
        
        # Update Prometheus metrics if available
        if self.prometheus_exporter:
            self._update_prometheus_metrics(data)
        
        # Update batch stats
        self._update_batch_stats(data)
        
        # Update last signal timestamp
        direction = data.get('direction', 'HOLD')
        if direction != 'HOLD':
            self._last_signals[symbol] = data.get('timestamp', datetime.now(timezone.utc))
    
    def log_batch_summary(self, timeframe: str, duration: float):
        """
        Log batch analysis summary.
        
        Args:
            timeframe: Timeframe of analysis (e.g., '15m')
            duration: Duration in seconds
        """
        # Calculate average score
        avg_score = 0.0
        if self._batch_stats['scores']:
            avg_score = sum(self._batch_stats['scores']) / len(self._batch_stats['scores'])
        
        summary_data = {
            'timeframe': timeframe,
            'total': self._batch_stats['total'],
            'success': self._batch_stats['success'],
            'fail': self._batch_stats['fail'],
            'signals': self._batch_stats['signals'].copy(),
            'avg_score': avg_score,
            'duration': duration
        }
        
        message = self.formatter.format_batch_summary(summary_data)
        logger.info(message)
        
        # Reset batch stats
        self._reset_batch_stats()
    
    def _calculate_age(self, symbol: str, current_timestamp: Optional[datetime] = None) -> Optional[float]:
        """Calculate hours since last signal for this symbol."""
        if symbol not in self._last_signals:
            return None
        
        last_signal = self._last_signals[symbol]
        current = current_timestamp or datetime.now(timezone.utc)
        
        # Ensure both are timezone-aware
        if last_signal.tzinfo is None:
            last_signal = last_signal.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        
        delta = current - last_signal
        return delta.total_seconds() / 3600.0  # Convert to hours
    
    def _update_prometheus_metrics(self, data: Dict[str, Any]):
        """Update Prometheus metrics with analysis data."""
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            direction = data.get('direction', 'HOLD')
            final_score = data.get('final_score', 0.0)
            
            # Update last signal gauge
            # This will be: aibot_last_signal{symbol="BTC-USDT", direction="LONG"} = score
            if hasattr(self.prometheus_exporter, 'set_last_signal'):
                self.prometheus_exporter.set_last_signal(symbol, direction, final_score)
            
            # Update analysis counters
            if hasattr(self.prometheus_exporter, 'inc_analysis_total'):
                self.prometheus_exporter.inc_analysis_total(symbol, direction)
            
        except Exception as e:
            logger.debug(f"Failed to update Prometheus metrics: {e}")
    
    def _update_batch_stats(self, data: Dict[str, Any]):
        """Update batch statistics."""
        self._batch_stats['total'] += 1
        
        # Success/fail (assuming success if we got this far)
        self._batch_stats['success'] += 1
        
        # Count signals
        direction = data.get('direction', 'HOLD')
        if direction in self._batch_stats['signals']:
            self._batch_stats['signals'][direction] += 1
        
        # Track scores
        final_score = data.get('final_score')
        if final_score is not None:
            self._batch_stats['scores'].append(final_score)
    
    def _reset_batch_stats(self):
        """Reset batch statistics for next batch."""
        self._batch_stats = {
            'total': 0,
            'success': 0,
            'fail': 0,
            'signals': {'LONG': 0, 'SHORT': 0, 'HOLD': 0},
            'scores': []
        }
    
    def record_failure(self, symbol: str, error: str):
        """Record a failed analysis."""
        self._batch_stats['total'] += 1
        self._batch_stats['fail'] += 1
        logger.error(f"❌ Analysis failed for {symbol}: {error}")


# Global singleton instance
_analysis_summary_logger = None


def get_analysis_summary_logger() -> AnalysisSummaryLogger:
    """Get the global analysis summary logger instance."""
    global _analysis_summary_logger
    if _analysis_summary_logger is None:
        _analysis_summary_logger = AnalysisSummaryLogger()
    return _analysis_summary_logger

