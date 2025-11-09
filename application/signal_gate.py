"""
Signal Gate - SOLID Compliant Signal Processing
Handles signal persistence, confirmation, hysteresis, and regime filtering.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from loguru import logger

from application.jobs.base_job import BaseJob


def round_to_bar(ts, bar_minutes=15):
    """Round timestamp to bar boundary (15-minute default)."""
    if ts is None:
        return None
    
    # Handle pandas Timestamp
    if hasattr(ts, 'to_pydatetime'):
        ts = ts.to_pydatetime()
    
    # Ensure timezone aware
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    
    # Round to bar boundary
    epoch = int(ts.timestamp())
    bar_seconds = bar_minutes * 60
    rounded = (epoch // bar_seconds) * bar_seconds
    return datetime.fromtimestamp(rounded, tz=timezone.utc)


@dataclass
class SignalHistory:
    """Signal history for persistence tracking."""
    timestamp: datetime
    final_score: float
    direction: str  # 'long', 'short', 'flat'
    strength: float
    age_bars: int = 0


@dataclass
class RegimeInfo:
    """Market regime information."""
    adx_1h: float
    regime: str  # 'trend', 'sideways', 'mean_reversion'
    confidence_multiplier: float
    trend_throttle: bool


@dataclass
class GatedSignal:
    """Processed signal with gating applied."""
    original_score: float
    gated_score: float
    direction: str
    strength: float
    is_valid: bool
    reason: str
    regime_info: RegimeInfo
    persistence_bars: int
    confirmation_bars: int
    details: Dict[str, Any] = field(default_factory=dict)


class SignalProcessor(ABC):
    """Abstract base for signal processing components."""
    
    @abstractmethod
    def process(self, signal: Dict, history: List[SignalHistory], regime: RegimeInfo) -> GatedSignal:
        """Process signal with gating logic."""
        pass


class PersistenceProcessor(SignalProcessor):
    """Handles signal persistence requirements."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.persistence_bars = policy['trading']['scoring']['signal']['persistence_bars']
        self.max_signal_age = policy['trading']['scoring']['signal']['max_signal_age_bars']
    
    def process(
        self,
        signal: Dict,
        history: List[SignalHistory],
        regime: RegimeInfo,
        current_bar_id: Optional[str] = None,
    ) -> GatedSignal:
        """Check signal persistence requirements."""
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        direction = self._get_direction(final_score)
        
        # Check if signal has persisted for required bars
        persistence_count = self._count_persistence(history, direction, current_bar_id)
        
        # Check signal age
        signal_age = len(history) if history else 0
        
        is_valid = persistence_count >= self.persistence_bars and signal_age <= self.max_signal_age
        
        reason = f"Persistence: {persistence_count}/{self.persistence_bars}, Age: {signal_age}/{self.max_signal_age}"
        
        return GatedSignal(
            original_score=final_score,
            gated_score=final_score,
            direction=direction,
            strength=self._calculate_strength(final_score),
            is_valid=is_valid,
            reason=reason,
            regime_info=regime,
            persistence_bars=persistence_count,
            confirmation_bars=0
        )
    
    def _get_direction(self, score: float) -> str:
        """Get signal direction from score."""
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        if score >= enter_long:
            return 'long'
        elif score <= enter_short:
            return 'short'
        else:
            return 'flat'
    
    def _count_persistence(
        self,
        history: List[SignalHistory],
        direction: str,
        current_bar_id: Optional[str] = None,
    ) -> int:
        """Count consecutive bars with same direction and threshold met."""
        if not history:
            return 0
        
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        count = 0
        for signal in reversed(history):
            # Check if direction matches AND threshold met
            if current_bar_id and getattr(signal, 'bar_id', None) == current_bar_id:
                continue
            if signal.direction == direction:
                # Verify score meets threshold
                score_meets_threshold = (
                    (direction == 'long' and signal.final_score >= enter_long) or
                    (direction == 'short' and signal.final_score <= enter_short)
                )
                if score_meets_threshold:
                    count += 1
                else:
                    # Score dropped below threshold, reset
                    break
            else:
                # Direction changed, reset
                break
        
        return count
    
    def _calculate_strength(self, score: float) -> float:
        """Calculate signal strength (0-1)."""
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        if score >= enter_long:
            return min((score - enter_long) / (100 - enter_long), 1.0)
        elif score <= enter_short:
            return min((enter_short - score) / enter_short, 1.0)
        else:
            return 0.0


class ConfirmationProcessor(SignalProcessor):
    """Handles signal confirmation requirements."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.confirm_bars = policy['trading']['scoring']['signal']['rev_confirm_bars']
    
    def process(
        self,
        signal: Dict,
        history: List[SignalHistory],
        regime: RegimeInfo,
        current_bar_id: Optional[str] = None,
    ) -> GatedSignal:
        """Check signal confirmation requirements."""
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        direction = self._get_direction(final_score)
        
        # Count confirmation bars
        confirmation_count = self._count_confirmation(history, direction, current_bar_id)
        
        is_valid = confirmation_count >= self.confirm_bars
        
        reason = f"Confirmation: {confirmation_count}/{self.confirm_bars}"
        
        return GatedSignal(
            original_score=final_score,
            gated_score=final_score,
            direction=direction,
            strength=self._calculate_strength(final_score),
            is_valid=is_valid,
            reason=reason,
            regime_info=regime,
            persistence_bars=0,
            confirmation_bars=confirmation_count
        )
    
    def _get_direction(self, score: float) -> str:
        """Get signal direction from score."""
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        if score >= enter_long:
            return 'long'
        elif score <= enter_short:
            return 'short'
        else:
            return 'flat'
    
    def _count_confirmation(
        self,
        history: List[SignalHistory],
        direction: str,
        current_bar_id: Optional[str] = None,
    ) -> int:
        """Count confirmation bars for direction with threshold + margin check."""
        if not history:
            return 0
        
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        margin = self.policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('confirmation_margin', 2.0)
        
        count = 0
        for signal in reversed(history):
            # Check if direction matches AND score meets threshold + margin
            if current_bar_id and getattr(signal, 'bar_id', None) == current_bar_id:
                continue
            if signal.direction == direction:
                # Verify score meets threshold + margin for confirmation
                score_meets_threshold_margin = (
                    (direction == 'long' and signal.final_score >= (enter_long + margin)) or
                    (direction == 'short' and signal.final_score <= (enter_short - margin))
                )
                if score_meets_threshold_margin:
                    count += 1
                else:
                    # Score dropped below threshold + margin, reset
                    break
            else:
                # Direction changed, reset
                break
        
        return count
    
    def _calculate_strength(self, score: float) -> float:
        """Calculate signal strength (0-1)."""
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        if score >= enter_long:
            return min((score - enter_long) / (100 - enter_long), 1.0)
        elif score <= enter_short:
            return min((enter_short - score) / enter_short, 1.0)
        else:
            return 0.0


class RegimeProcessor:
    """Handles market regime detection and filtering."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.adx_min = policy['trading']['scoring']['regime']['adx_1h_min']
        self.low_adx_threshold = policy['trading']['scoring']['regime']['low_adx_threshold']
        self.regime_multiplier = policy['trading']['scoring']['position_sizing']['regime_multiplier']
    
    def detect_regime(self, ohlcv_1h: List[List]) -> RegimeInfo:
        """Detect market regime from 1H OHLCV data."""
        if not ohlcv_1h or len(ohlcv_1h) < 14:
            return RegimeInfo(
                adx_1h=0.0,
                regime='unknown',
                confidence_multiplier=1.0,
                trend_throttle=False
            )
        
        # Calculate ADX from 1H data
        adx = self._calculate_adx(ohlcv_1h)
        
        if adx >= self.adx_min:
            regime = 'trend'
            confidence_multiplier = 1.0
            trend_throttle = False
        elif adx >= self.low_adx_threshold:
            regime = 'sideways'
            confidence_multiplier = 0.8
            trend_throttle = False
        else:
            regime = 'mean_reversion'
            confidence_multiplier = self.regime_multiplier
            trend_throttle = True
        
        return RegimeInfo(
            adx_1h=adx,
            regime=regime,
            confidence_multiplier=confidence_multiplier,
            trend_throttle=trend_throttle
        )
    
    def _calculate_adx(self, ohlcv: List[List]) -> float:
        """Calculate ADX from OHLCV data."""
        if len(ohlcv) < 14:
            return 0.0
        
        try:
            # Convert to numpy arrays
            high = np.array([bar[2] for bar in ohlcv])
            low = np.array([bar[3] for bar in ohlcv])
            close = np.array([bar[4] for bar in ohlcv])
            
            # Calculate True Range
            tr1 = high - low
            tr2 = np.abs(high - np.roll(close, 1))
            tr3 = np.abs(low - np.roll(close, 1))
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            
            # Calculate Directional Movement
            dm_plus = high - np.roll(high, 1)
            dm_minus = np.roll(low, 1) - low
            
            dm_plus = np.where((dm_plus > dm_minus) & (dm_plus > 0), dm_plus, 0)
            dm_minus = np.where((dm_minus > dm_plus) & (dm_minus > 0), dm_minus, 0)
            
            # Smooth with 14-period Wilder's smoothing
            period = 14
            atr = self._wilders_smooth(tr, period)
            
            # Avoid division by zero - replace zeros with small values
            atr = np.where(atr == 0, 1e-8, atr)
            if len(atr) == 0:
                return 0.0
                
            di_plus = self._wilders_smooth(dm_plus, period) / atr * 100
            di_minus = self._wilders_smooth(dm_minus, period) / atr * 100
            
            # Calculate ADX - avoid division by zero
            denominator = di_plus + di_minus
            denominator = np.where(denominator == 0, 1e-8, denominator)
            dx = np.abs(di_plus - di_minus) / denominator * 100
            adx = self._wilders_smooth(dx, period)
            
            return float(adx[-1]) if len(adx) > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"ADX calculation failed: {e}")
            return 0.0
    
    def _wilders_smooth(self, data: np.ndarray, period: int) -> np.ndarray:
        """Apply Wilder's smoothing."""
        if len(data) < period:
            return data
        
        smoothed = np.zeros_like(data)
        smoothed[period-1] = np.mean(data[:period])
        
        for i in range(period, len(data)):
            smoothed[i] = (smoothed[i-1] * (period - 1) + data[i]) / period
        
        return smoothed


class HysteresisProcessor(SignalProcessor):
    """Handles signal hysteresis (different entry/exit thresholds)."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.enter_long = policy['trading']['scoring']['decision_thresholds']['enter_long']
        self.exit_long = policy['trading']['scoring']['decision_thresholds']['exit_long']
        self.enter_short = policy['trading']['scoring']['decision_thresholds']['enter_short']
        self.exit_short = policy['trading']['scoring']['decision_thresholds']['exit_short']
    
    def process(self, signal: Dict, history: List[SignalHistory], regime: RegimeInfo) -> GatedSignal:
        """Apply hysteresis logic."""
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        
        # Determine if this is an entry or exit signal based on history
        is_entry = self._is_entry_signal(history, final_score)
        
        if is_entry:
            direction = self._get_entry_direction(final_score)
            is_valid = self._is_valid_entry(final_score)
            reason = f"Entry signal: {direction}"
        else:
            direction = self._get_exit_direction(history, final_score)
            is_valid = self._is_valid_exit(history, final_score)
            reason = f"Exit signal: {direction}"
        
        return GatedSignal(
            original_score=final_score,
            gated_score=final_score,
            direction=direction,
            strength=self._calculate_strength(final_score),
            is_valid=is_valid,
            reason=reason,
            regime_info=regime,
            persistence_bars=0,
            confirmation_bars=0
        )
    
    def _is_entry_signal(self, history: List[SignalHistory], score: float) -> bool:
        """Determine if this is an entry signal."""
        if not history:
            return True  # First signal is always entry
        
        # Check if we're in a position
        last_direction = history[-1].direction
        return last_direction == 'flat'
    
    def _get_entry_direction(self, score: float) -> str:
        """Get entry direction."""
        if score >= self.enter_long:
            return 'long'
        elif score <= self.enter_short:
            return 'short'
        else:
            return 'flat'
    
    def _get_exit_direction(self, history: List[SignalHistory], score: float) -> str:
        """Get exit direction based on current position."""
        if not history:
            return 'flat'
        
        last_direction = history[-1].direction
        
        if last_direction == 'long' and score <= self.exit_long:
            return 'short'  # Long to short reversal
        elif last_direction == 'short' and score >= self.exit_short:
            return 'long'   # Short to long reversal
        else:
            return last_direction  # Maintain current direction
    
    def _is_valid_entry(self, score: float) -> bool:
        """Check if entry signal is valid."""
        return score >= self.enter_long or score <= self.enter_short
    
    def _is_valid_exit(self, history: List[SignalHistory], score: float) -> bool:
        """Check if exit signal is valid."""
        if not history:
            return False
        
        last_direction = history[-1].direction
        
        if last_direction == 'long':
            return score <= self.exit_long
        elif last_direction == 'short':
            return score >= self.exit_short
        
        return False
    
    def _calculate_strength(self, score: float) -> float:
        """Calculate signal strength (0-1)."""
        if score >= self.enter_long:
            return min((score - self.enter_long) / (100 - self.enter_long), 1.0)
        elif score <= self.enter_short:
            return min((self.enter_short - score) / self.enter_short, 1.0)
        else:
            return 0.0


class SignalGate:
    """Main signal gate orchestrator."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.signal_history: Dict[str, List[SignalHistory]] = {}
        self._last_bar_for_symbol: Dict[str, str] = {}
        self._duplicate_counts: Dict[str, int] = {}
        
        # Initialize processors
        self.persistence_processor = PersistenceProcessor(policy)
        self.confirmation_processor = ConfirmationProcessor(policy)
        self.hysteresis_processor = HysteresisProcessor(policy)
        self.regime_processor = RegimeProcessor(policy)
        
        logger.info("SignalGate initialized with persistence, confirmation, and hysteresis processors")
    
    def process_signal(self, symbol: str, signal: Dict, ohlcv_1h: List[List]) -> GatedSignal:
        """Process signal with all gating logic."""
        bar_timestamp = signal.get('bar_timestamp')
        if isinstance(bar_timestamp, str):
            try:
                bar_timestamp = datetime.fromisoformat(bar_timestamp.replace('Z', '+00:00'))
            except ValueError:
                bar_timestamp = datetime.now(timezone.utc)
        elif bar_timestamp is None:
            bar_timestamp = datetime.now(timezone.utc)
        elif hasattr(bar_timestamp, "to_pydatetime"):
            bar_timestamp = bar_timestamp.to_pydatetime()
        
        if bar_timestamp.tzinfo is None:
            bar_timestamp = bar_timestamp.replace(tzinfo=timezone.utc)
        
        timeframe = signal.get('timeframe', '15m')
        bar_id = BaseJob.get_bar_id(bar_timestamp, timeframe)
        signal['bar_timestamp'] = bar_timestamp
        signal['bar_id'] = bar_id
        
        duplicate_bar = self._last_bar_for_symbol.get(symbol) == bar_id
        
        # Detect market regime
        regime = self.regime_processor.detect_regime(ohlcv_1h)
        
        # Get signal history
        history = self.signal_history.get(symbol, [])
        
        # Apply persistence check
        persistence_result = self.persistence_processor.process(signal, history, regime, current_bar_id=bar_id)
        
        # Apply confirmation check
        confirmation_result = self.confirmation_processor.process(signal, history, regime, current_bar_id=bar_id)
        
        # Apply hysteresis check
        hysteresis_result = self.hysteresis_processor.process(signal, history, regime)
        
        # Combine results
        final_result = self._combine_results(persistence_result, confirmation_result, hysteresis_result, regime)
        final_result.details.setdefault('bar_id', bar_id)
        if signal.get('run_id'):
            final_result.details.setdefault('run_id', signal['run_id'])
        
        if duplicate_bar:
            final_result.details['duplicate_bar'] = True
            final_result.details['duplicate_count'] = self._duplicate_counts.get(symbol, 0) + 1
            logger.debug(f"[GATE] {symbol} duplicate bar detected id={bar_id} count={final_result.details['duplicate_count']}")
            self._duplicate_counts[symbol] = final_result.details['duplicate_count']
        else:
            self._duplicate_counts[symbol] = 0
        
        # Update signal history
        self._update_history(symbol, signal, final_result, bar_id)
        self._last_bar_for_symbol[symbol] = bar_id
        
        # Log regime information
        if regime.trend_throttle:
            logger.info(f"[REGIME] {symbol} ADX(1H)={regime.adx_1h:.1f} → {regime.regime} mode, confidence_mult={regime.confidence_multiplier}")
        
        return final_result
    
    def _combine_results(self, persistence: GatedSignal, confirmation: GatedSignal, 
                        hysteresis: GatedSignal, regime: RegimeInfo) -> GatedSignal:
        """Combine all processing results."""
        # Check if hysteresis is disabled for testing
        import os
        hysteresis_enabled = os.environ.get('HYSTERESIS_ENABLE', 'true').lower() != 'false'
        
        if hysteresis_enabled:
            # Signal is valid if all processors agree
            is_valid = (persistence.is_valid and confirmation.is_valid and hysteresis.is_valid)
        else:
            # Skip hysteresis check for testing
            is_valid = (persistence.is_valid and confirmation.is_valid)
        
        # Apply regime multiplier to score
        gated_score = hysteresis.gated_score * regime.confidence_multiplier
        
        # Determine final direction
        direction = hysteresis.direction
        
        # Calculate combined strength
        strength = min(persistence.strength, confirmation.strength, hysteresis.strength)
        
        # Combine reasons
        reason = f"Persistence: {persistence.reason}, Confirmation: {confirmation.reason}, Hysteresis: {hysteresis.reason}"
        
        return GatedSignal(
            original_score=persistence.original_score,
            gated_score=gated_score,
            direction=direction,
            strength=strength,
            is_valid=is_valid,
            reason=reason,
            regime_info=regime,
            persistence_bars=persistence.persistence_bars,
            confirmation_bars=confirmation.confirmation_bars
        )
    
    def _update_history(self, symbol: str, signal: Dict, gated_signal: GatedSignal, bar_id: str):
        """Update signal history with bar-based deduplication."""
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        
        # Extract bar_timestamp for deduplication
        bar_timestamp = signal.get('bar_timestamp') or datetime.now(timezone.utc)
        
        # Check if this bar already processed (deduplication)
        history = self.signal_history[symbol]
        existing_entry_idx = None
        
        if history:
            # Find entry with same bar_id
            for idx, hist_entry in enumerate(reversed(history)):
                if hasattr(hist_entry, 'bar_id') and hist_entry.bar_id == bar_id:
                    existing_entry_idx = len(history) - 1 - idx
                    break
        
        if existing_entry_idx is not None:
            # Update existing entry for this bar
            logger.debug(f"[COUNTER] {symbol} Updating existing bar_id={bar_id} entry")
            history[existing_entry_idx].final_score = signal.get('final_score', 0)
            history[existing_entry_idx].direction = gated_signal.direction
            history[existing_entry_idx].strength = gated_signal.strength
        else:
            # Add new signal to history
            new_signal = SignalHistory(
                timestamp=bar_timestamp if bar_timestamp else datetime.now(),
                final_score=signal.get('final_score', 0),
                direction=gated_signal.direction,
                strength=gated_signal.strength,
                age_bars=0
            )
            # Add bar_id for deduplication
            new_signal.bar_id = bar_id
            history.append(new_signal)
        
        # Calculate and log counters
        persist_count = self.persistence_processor._count_persistence(history, gated_signal.direction, bar_id)
        conf_count = self.confirmation_processor._count_confirmation(history, gated_signal.direction, bar_id)
        age_count = len(history)
        
        logger.debug(f"[COUNTER] {symbol} bar_id={bar_id} persist={persist_count} conf={conf_count} age={age_count}")
        
        # Keep only recent history (last 20 bars)
        max_history = 20
        if len(history) > max_history:
            self.signal_history[symbol] = history[-max_history:]
    
    def get_signal_history(self, symbol: str) -> List[SignalHistory]:
        """Get signal history for symbol."""
        return self.signal_history.get(symbol, [])
    
    def clear_history(self, symbol: str):
        """Clear signal history for symbol."""
        if symbol in self.signal_history:
            del self.signal_history[symbol]
