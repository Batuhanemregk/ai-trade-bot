"""
Analysis Summary Logger
Enhanced logging for trading analysis with age tracking and detailed metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

from application.log_formatter import get_log_formatter
from application.market_data_service import get_market_data_cache
from application.jobs.base_job import BaseJob


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
        self._analysis_seen: Dict[Tuple[str, str], str] = {}
        self._batch_seen: Dict[str, str] = {}
        
        # Batch statistics
        self._batch_stats = {
            'total': 0,
            'success': 0,
            'fail': 0,
            'signals': {'LONG': 0, 'SHORT': 0, 'HOLD': 0},
            'scores': [],
            # Enhanced features tracking
            'enhanced_features': {
                'confidence_stats': {
                    'multipliers': [],
                    'high_confidence_count': 0
                },
                'regime_stats': {
                    'trend_regime_count': 0,
                    'sideways_regime_count': 0
                },
                'news_ttl_stats': {
                    'ttl_weights': [],
                    'fresh_news_count': 0,
                    'stale_news_count': 0
                },
                'ta_features_stats': {
                    'active_features_counts': [],
                    'max_features_used': 0
                }
            }
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
        timeframe = data.get('timeframe', '15m')
        bar_id = data.get('bar_id')
        bar_timestamp = data.get('bar_timestamp')
        
        if bar_id is None and bar_timestamp:
            if isinstance(bar_timestamp, str):
                try:
                    bar_dt = datetime.fromisoformat(bar_timestamp.replace('Z', '+00:00'))
                except ValueError:
                    bar_dt = datetime.now(timezone.utc)
            else:
                bar_dt = bar_timestamp
                if bar_dt.tzinfo is None:
                    bar_dt = bar_dt.replace(tzinfo=timezone.utc)
            bar_id = BaseJob.get_bar_id(bar_dt, timeframe)
            data['bar_id'] = bar_id
        elif bar_id is None:
            bar_id = BaseJob.get_bar_id(datetime.now(timezone.utc), timeframe)
            data['bar_id'] = bar_id
        
        cache_key = (symbol, timeframe)
        if bar_id and self._analysis_seen.get(cache_key) == bar_id:
            logger.info(f"[ANALYSIS] {symbol} tf={timeframe} bar={bar_id} skipped(idempotent)")
            return
        if bar_id:
            self._analysis_seen[cache_key] = bar_id
        
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
        cache_age = self.market_cache.get_age(symbol, timeframe)
        if cache_age:
            data['cache_age'] = cache_age
        
        # Format and log
        message = self.formatter.format_analysis_summary(data)
        logger.debug(message)
        
        # Update Prometheus metrics if available
        if self.prometheus_exporter:
            self._update_prometheus_metrics(data)
        
        # Update batch stats
        self._update_batch_stats(data)
        
        # Update last signal timestamp
        direction = data.get('direction', 'HOLD')
        if direction != 'HOLD':
            self._last_signals[symbol] = data.get('timestamp', datetime.now(timezone.utc))
    
    def log_batch_summary(self, timeframe: str, duration: float, bar_id: Optional[str] = None, run_id: Optional[str] = None):
        """
        Log batch analysis summary with enhanced features.
        
        Args:
            timeframe: Timeframe of analysis (e.g., '15m')
            duration: Duration in seconds
        """
        if bar_id is None:
            bar_id = BaseJob.get_bar_id(datetime.now(timezone.utc), timeframe)
        if bar_id and self._batch_seen.get(timeframe) == bar_id:
            logger.info(f"[BATCH] timeframe={timeframe} bar={bar_id} skipped(idempotent)")
            return
        if bar_id:
            self._batch_seen[timeframe] = bar_id
        
        # Calculate average score
        avg_score = 0.0
        if self._batch_stats['scores']:
            avg_score = sum(self._batch_stats['scores']) / len(self._batch_stats['scores'])
        
        # Calculate enhanced features statistics
        enhanced_features = self._calculate_enhanced_features_stats()
        
        summary_data = {
            'timeframe': timeframe,
            'total': self._batch_stats['total'],
            'success': self._batch_stats['success'],
            'fail': self._batch_stats['fail'],
            'signals': self._batch_stats['signals'].copy(),
            'avg_score': avg_score,
            'duration': duration,
            'enhanced_features': enhanced_features,
            'bar_id': bar_id,
            'run_id': run_id,
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
        """Update batch statistics with enhanced features."""
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
        
        # Track enhanced features
        self._track_enhanced_features(data)
    
    def _track_enhanced_features(self, data: Dict[str, Any]):
        """Track enhanced features statistics."""
        enhanced_features = self._batch_stats['enhanced_features']
        
        # Confidence-aware position sizing
        confidence_multiplier = data.get('confidence_multiplier')
        ml_confidence = data.get('ml_confidence')
        if confidence_multiplier is not None:
            enhanced_features['confidence_stats']['multipliers'].append(confidence_multiplier)
            if ml_confidence == 'high':
                enhanced_features['confidence_stats']['high_confidence_count'] += 1
        
        # Regime-adaptive weights
        regime = data.get('regime')
        if regime:
            if regime == 'trend_vol':
                enhanced_features['regime_stats']['trend_regime_count'] += 1
            elif regime == 'sideways_vol':
                enhanced_features['regime_stats']['sideways_regime_count'] += 1
        
        # News TTL dynamic weight
        ttl_weight = data.get('ttl_weight')
        news_age_hours = data.get('news_age_hours')
        if ttl_weight is not None:
            enhanced_features['news_ttl_stats']['ttl_weights'].append(ttl_weight)
            if news_age_hours and news_age_hours <= 2.0:
                enhanced_features['news_ttl_stats']['fresh_news_count'] += 1
            elif news_age_hours and news_age_hours >= 24.0:
                enhanced_features['news_ttl_stats']['stale_news_count'] += 1
        
        # TA active features
        ta_active_features = data.get('ta_active_features')
        if ta_active_features is not None:
            enhanced_features['ta_features_stats']['active_features_counts'].append(ta_active_features)
            enhanced_features['ta_features_stats']['max_features_used'] = max(
                enhanced_features['ta_features_stats']['max_features_used'], 
                ta_active_features
            )
    
    def _calculate_enhanced_features_stats(self) -> Dict[str, Any]:
        """Calculate enhanced features statistics."""
        enhanced_features = self._batch_stats['enhanced_features']
        
        # Confidence stats
        conf_multipliers = enhanced_features['confidence_stats']['multipliers']
        conf_stats = {
            'avg_multiplier': sum(conf_multipliers) / len(conf_multipliers) if conf_multipliers else 0.0,
            'high_confidence_count': enhanced_features['confidence_stats']['high_confidence_count']
        }
        
        # Regime stats
        regime_stats = {
            'trend_regime_count': enhanced_features['regime_stats']['trend_regime_count'],
            'sideways_regime_count': enhanced_features['regime_stats']['sideways_regime_count']
        }
        
        # News TTL stats
        ttl_weights = enhanced_features['news_ttl_stats']['ttl_weights']
        news_ttl_stats = {
            'avg_ttl_weight': sum(ttl_weights) / len(ttl_weights) if ttl_weights else 0.0,
            'fresh_news_count': enhanced_features['news_ttl_stats']['fresh_news_count'],
            'stale_news_count': enhanced_features['news_ttl_stats']['stale_news_count']
        }
        
        # TA features stats
        active_features_counts = enhanced_features['ta_features_stats']['active_features_counts']
        ta_features_stats = {
            'avg_active_features': sum(active_features_counts) / len(active_features_counts) if active_features_counts else 0.0,
            'max_features_used': enhanced_features['ta_features_stats']['max_features_used']
        }
        
        return {
            'confidence_stats': conf_stats,
            'regime_stats': regime_stats,
            'news_ttl_stats': news_ttl_stats,
            'ta_features_stats': ta_features_stats
        }
    
    def _reset_batch_stats(self):
        """Reset batch statistics for next batch."""
        self._batch_stats = {
            'total': 0,
            'success': 0,
            'fail': 0,
            'signals': {'LONG': 0, 'SHORT': 0, 'HOLD': 0},
            'scores': [],
            # Enhanced features tracking
            'enhanced_features': {
                'confidence_stats': {
                    'multipliers': [],
                    'high_confidence_count': 0
                },
                'regime_stats': {
                    'trend_regime_count': 0,
                    'sideways_regime_count': 0
                },
                'news_ttl_stats': {
                    'ttl_weights': [],
                    'fresh_news_count': 0,
                    'stale_news_count': 0
                },
                'ta_features_stats': {
                    'active_features_counts': [],
                    'max_features_used': 0
                }
            }
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

