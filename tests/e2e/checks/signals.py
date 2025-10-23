"""
Signal Gating Checker
====================

Signal gating kontrolleri:
- Composite signal üretimi (TA/ML/News/Risk)
- Gating kuralları (persist/age/conf/hysteresis)
- Signal strength ve direction
- Regime filtering
- Signal history tracking
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class SignalEvent:
    """Signal event for tracking."""
    timestamp: datetime
    symbol: str
    timeframe: str
    ta_score: float
    ml_score: float
    news_score: float
    risk_score: float
    composite_score: float
    direction: str  # LONG, SHORT, HOLD
    strength: float
    is_valid: bool
    gating_reason: str
    regime: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class GatingMetrics:
    """Gating metrics for analysis."""
    persistence_bars: int
    confirmation_bars: int
    signal_age: int
    hysteresis_threshold: float
    regime_multiplier: float
    final_score: float


class SignalGatingChecker:
    """Checks signal generation and gating logic."""
    
    def __init__(self):
        self.signal_events: List[SignalEvent] = []
        self.gating_metrics: List[GatingMetrics] = []
        self.signal_history: Dict[str, List[SignalEvent]] = {}
        
    async def check_composite_signal_generation(self, symbol: str, timeframe: str) -> Tuple[bool, str]:
        """
        Check composite signal generation.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            (success, message)
        """
        try:
            # This would integrate with the actual signal generation system
            # For now, we'll simulate the check
            
            # Simulate signal scores
            ta_score = 65.0
            ml_score = 70.0
            news_score = 60.0
            risk_score = 55.0
            
            # Calculate composite score (weighted average)
            weights = {'ta': 0.4, 'ml': 0.25, 'news': 0.2, 'risk': 0.15}
            composite_score = (
                ta_score * weights['ta'] +
                ml_score * weights['ml'] +
                news_score * weights['news'] +
                risk_score * weights['risk']
            )
            
            # Determine direction
            if composite_score >= 60:
                direction = "LONG"
            elif composite_score <= 40:
                direction = "SHORT"
            else:
                direction = "HOLD"
            
            # Create signal event
            event = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                timeframe=timeframe,
                ta_score=ta_score,
                ml_score=ml_score,
                news_score=news_score,
                risk_score=risk_score,
                composite_score=composite_score,
                direction=direction,
                strength=abs(composite_score - 50) / 50,  # 0-1 strength
                is_valid=False,  # Will be determined by gating
                gating_reason="",
                regime="trending"
            )
            
            self.signal_events.append(event)
            
            # Add to history
            key = f"{symbol}_{timeframe}"
            if key not in self.signal_history:
                self.signal_history[key] = []
            self.signal_history[key].append(event)
            
            logger.info(f"✅ Signal generated: {symbol} {timeframe} {direction} {composite_score:.1f}")
            return True, f"Signal generated: {direction} {composite_score:.1f}"
            
        except Exception as e:
            logger.error(f"❌ Signal generation failed: {e}")
            return False, f"Signal generation failed: {e}"
    
    async def check_persistence_gating(self, symbol: str, timeframe: str, 
                                     required_bars: int = 2) -> Tuple[bool, str]:
        """
        Check signal persistence gating.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            required_bars: Required persistence bars
            
        Returns:
            (success, message)
        """
        try:
            key = f"{symbol}_{timeframe}"
            history = self.signal_history.get(key, [])
            
            if len(history) < required_bars:
                return False, f"Insufficient history: {len(history)} < {required_bars}"
            
            # Check if last N signals have same direction
            recent_signals = history[-required_bars:]
            directions = [s.direction for s in recent_signals]
            
            if len(set(directions)) == 1 and directions[0] != "HOLD":
                persistence_count = len([d for d in directions if d == directions[0]])
                
                logger.info(f"✅ Persistence check passed: {persistence_count}/{required_bars}")
                return True, f"Persistence: {persistence_count}/{required_bars} bars"
            else:
                return False, f"Persistence failed: {directions}"
                
        except Exception as e:
            logger.error(f"❌ Persistence check failed: {e}")
            return False, f"Persistence check failed: {e}"
    
    async def check_age_gating(self, symbol: str, timeframe: str, 
                             max_age: int = 6) -> Tuple[bool, str]:
        """
        Check signal age gating.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            max_age: Maximum signal age in bars
            
        Returns:
            (success, message)
        """
        try:
            key = f"{symbol}_{timeframe}"
            history = self.signal_history.get(key, [])
            
            if not history:
                return False, "No signal history"
            
            # Check age of current signal
            current_signal = history[-1]
            signal_age = len(history)
            
            if signal_age <= max_age:
                logger.info(f"✅ Age check passed: {signal_age}/{max_age}")
                return True, f"Signal age: {signal_age}/{max_age} bars"
            else:
                return False, f"Signal too old: {signal_age} > {max_age}"
                
        except Exception as e:
            logger.error(f"❌ Age check failed: {e}")
            return False, f"Age check failed: {e}"
    
    async def check_confirmation_gating(self, symbol: str, timeframe: str, 
                                      required_bars: int = 2) -> Tuple[bool, str]:
        """
        Check signal confirmation gating.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            required_bars: Required confirmation bars
            
        Returns:
            (success, message)
        """
        try:
            key = f"{symbol}_{timeframe}"
            history = self.signal_history.get(key, [])
            
            if len(history) < required_bars:
                return False, f"Insufficient history: {len(history)} < {required_bars}"
            
            # Check if last N signals confirm the direction
            recent_signals = history[-required_bars:]
            directions = [s.direction for s in recent_signals]
            
            # Count confirmation for each direction
            long_count = len([d for d in directions if d == "LONG"])
            short_count = len([d for d in directions if d == "SHORT"])
            
            if long_count >= required_bars:
                logger.info(f"✅ Confirmation check passed: LONG {long_count}/{required_bars}")
                return True, f"LONG confirmation: {long_count}/{required_bars}"
            elif short_count >= required_bars:
                logger.info(f"✅ Confirmation check passed: SHORT {short_count}/{required_bars}")
                return True, f"SHORT confirmation: {short_count}/{required_bars}"
            else:
                return False, f"Insufficient confirmation: LONG {long_count}, SHORT {short_count}"
                
        except Exception as e:
            logger.error(f"❌ Confirmation check failed: {e}")
            return False, f"Confirmation check failed: {e}"
    
    async def check_hysteresis_gating(self, symbol: str, timeframe: str, 
                                    enter_long: float = 60, exit_long: float = 45,
                                    enter_short: float = 40, exit_short: float = 55) -> Tuple[bool, str]:
        """
        Check hysteresis gating (different entry/exit thresholds).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            enter_long: Long entry threshold
            exit_long: Long exit threshold
            enter_short: Short entry threshold
            exit_short: Short exit threshold
            
        Returns:
            (success, message)
        """
        try:
            key = f"{symbol}_{timeframe}"
            history = self.signal_history.get(key, [])
            
            if not history:
                return False, "No signal history"
            
            current_signal = history[-1]
            score = current_signal.composite_score
            
            # Determine if this is entry or exit based on history
            if len(history) > 1:
                prev_signal = history[-2]
                if prev_signal.direction == "LONG":
                    # Check for LONG exit
                    if score <= exit_long:
                        logger.info(f"✅ Hysteresis check passed: LONG exit {score:.1f} <= {exit_long}")
                        return True, f"LONG exit: {score:.1f} <= {exit_long}"
                elif prev_signal.direction == "SHORT":
                    # Check for SHORT exit
                    if score >= exit_short:
                        logger.info(f"✅ Hysteresis check passed: SHORT exit {score:.1f} >= {exit_short}")
                        return True, f"SHORT exit: {score:.1f} >= {exit_short}"
            
            # Check for entry signals
            if score >= enter_long:
                logger.info(f"✅ Hysteresis check passed: LONG entry {score:.1f} >= {enter_long}")
                return True, f"LONG entry: {score:.1f} >= {enter_long}"
            elif score <= enter_short:
                logger.info(f"✅ Hysteresis check passed: SHORT entry {score:.1f} <= {enter_short}")
                return True, f"SHORT entry: {score:.1f} <= {enter_short}"
            else:
                return False, f"No hysteresis trigger: {score:.1f} not in entry/exit ranges"
                
        except Exception as e:
            logger.error(f"❌ Hysteresis check failed: {e}")
            return False, f"Hysteresis check failed: {e}"
    
    async def check_regime_filtering(self, symbol: str, timeframe: str, 
                                   adx_threshold: float = 22) -> Tuple[bool, str]:
        """
        Check regime filtering (trending vs mean reversion).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            adx_threshold: ADX threshold for trend mode
            
        Returns:
            (success, message)
        """
        try:
            # This would integrate with actual regime detection
            # For now, we'll simulate the check
            
            # Simulate ADX value
            adx_value = 25.0  # Above threshold = trending
            
            if adx_value >= adx_threshold:
                regime = "trending"
                confidence_multiplier = 1.0
            else:
                regime = "mean_reversion"
                confidence_multiplier = 0.6
            
            logger.info(f"✅ Regime check passed: {regime} (ADX: {adx_value:.1f})")
            return True, f"Regime: {regime} (ADX: {adx_value:.1f}, multiplier: {confidence_multiplier})"
            
        except Exception as e:
            logger.error(f"❌ Regime check failed: {e}")
            return False, f"Regime check failed: {e}"
    
    async def check_signal_strength(self, symbol: str, timeframe: str, 
                                  min_strength: float = 0.6) -> Tuple[bool, str]:
        """
        Check signal strength.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            min_strength: Minimum signal strength (0-1)
            
        Returns:
            (success, message)
        """
        try:
            key = f"{symbol}_{timeframe}"
            history = self.signal_history.get(key, [])
            
            if not history:
                return False, "No signal history"
            
            current_signal = history[-1]
            strength = current_signal.strength
            
            if strength >= min_strength:
                logger.info(f"✅ Signal strength check passed: {strength:.2f} >= {min_strength}")
                return True, f"Signal strength: {strength:.2f} >= {min_strength}"
            else:
                return False, f"Signal too weak: {strength:.2f} < {min_strength}"
                
        except Exception as e:
            logger.error(f"❌ Signal strength check failed: {e}")
            return False, f"Signal strength check failed: {e}"
    
    async def check_gating_combination(self, symbol: str, timeframe: str) -> Tuple[bool, str]:
        """
        Check all gating rules combined.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            (success, message)
        """
        try:
            gating_results = []
            
            # Check all gating rules
            persistence_ok, persistence_msg = await self.check_persistence_gating(symbol, timeframe)
            gating_results.append(("persistence", persistence_ok, persistence_msg))
            
            age_ok, age_msg = await self.check_age_gating(symbol, timeframe)
            gating_results.append(("age", age_ok, age_msg))
            
            confirmation_ok, confirmation_msg = await self.check_confirmation_gating(symbol, timeframe)
            gating_results.append(("confirmation", confirmation_ok, confirmation_msg))
            
            hysteresis_ok, hysteresis_msg = await self.check_hysteresis_gating(symbol, timeframe)
            gating_results.append(("hysteresis", hysteresis_ok, hysteresis_msg))
            
            regime_ok, regime_msg = await self.check_regime_filtering(symbol, timeframe)
            gating_results.append(("regime", regime_ok, regime_msg))
            
            strength_ok, strength_msg = await self.check_signal_strength(symbol, timeframe)
            gating_results.append(("strength", strength_ok, strength_msg))
            
            # Count passed checks
            passed_checks = [name for name, ok, _ in gating_results if ok]
            failed_checks = [name for name, ok, _ in gating_results if not ok]
            
            # Signal is valid if all checks pass
            is_valid = len(failed_checks) == 0
            
            # Update latest signal
            key = f"{symbol}_{timeframe}"
            if key in self.signal_history and self.signal_history[key]:
                latest_signal = self.signal_history[key][-1]
                latest_signal.is_valid = is_valid
                latest_signal.gating_reason = f"Passed: {passed_checks}, Failed: {failed_checks}"
            
            if is_valid:
                logger.info(f"✅ All gating checks passed: {passed_checks}")
                return True, f"All gating checks passed: {passed_checks}"
            else:
                logger.warning(f"⚠️ Some gating checks failed: {failed_checks}")
                return False, f"Gating failed: {failed_checks}"
                
        except Exception as e:
            logger.error(f"❌ Gating combination check failed: {e}")
            return False, f"Gating combination check failed: {e}"
    
    def get_signal_summary(self) -> Dict[str, Any]:
        """Get summary of all signals."""
        return {
            'total_signals': len(self.signal_events),
            'valid_signals': len([s for s in self.signal_events if s.is_valid]),
            'invalid_signals': len([s for s in self.signal_events if not s.is_valid]),
            'signals_by_direction': {
                direction: len([s for s in self.signal_events if s.direction == direction])
                for direction in ['LONG', 'SHORT', 'HOLD']
            },
            'signals_by_symbol': {
                symbol: len([s for s in self.signal_events if s.symbol == symbol])
                for symbol in set(s.symbol for s in self.signal_events)
            },
            'average_scores': {
                'ta': sum(s.ta_score for s in self.signal_events) / len(self.signal_events) if self.signal_events else 0,
                'ml': sum(s.ml_score for s in self.signal_events) / len(self.signal_events) if self.signal_events else 0,
                'news': sum(s.news_score for s in self.signal_events) / len(self.signal_events) if self.signal_events else 0,
                'risk': sum(s.risk_score for s in self.signal_events) / len(self.signal_events) if self.signal_events else 0,
                'composite': sum(s.composite_score for s in self.signal_events) / len(self.signal_events) if self.signal_events else 0
            }
        }
    
    def get_gating_metrics(self) -> List[Dict]:
        """Get gating metrics for analysis."""
        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'symbol': s.symbol,
                'timeframe': s.timeframe,
                'composite_score': s.composite_score,
                'direction': s.direction,
                'is_valid': s.is_valid,
                'gating_reason': s.gating_reason,
                'regime': s.regime
            }
            for s in self.signal_events
        ]

