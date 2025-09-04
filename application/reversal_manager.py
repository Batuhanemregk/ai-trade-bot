"""
Reversal Manager - SOLID Compliant Reversal Logic
Handles hybrid reversal policy with strength, confirmation, and edge checks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
from loguru import logger


@dataclass
class ReversalCheck:
    """Reversal eligibility check result."""
    is_eligible: bool
    strength: float
    confirmation_bars: int
    edge_cost_ratio: float
    expected_move: float
    total_cost: float
    holding_bars: int
    min_hold_met: bool
    reason: str


@dataclass
class ReversalSignal:
    """Reversal signal with all required information."""
    symbol: str
    from_direction: str  # 'long' or 'short'
    to_direction: str    # 'long' or 'short'
    strength: float
    confirmation_bars: int
    expected_move: float
    total_cost: float
    edge_cost_ratio: float
    is_valid: bool
    reason: str


class ReversalStrengthCalculator(ABC):
    """Abstract base for reversal strength calculation."""
    
    @abstractmethod
    def calculate_strength(self, ohlcv_data: Dict, signal: Dict, current_direction: str) -> float:
        """Calculate reversal strength (0-1)."""
        pass


class TechnicalReversalStrength(ReversalStrengthCalculator):
    """Calculate reversal strength from technical indicators."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.rev_strength_min = policy['trading']['scoring']['signal']['rev_strength_min']
    
    def calculate_strength(self, ohlcv_data: Dict, signal: Dict, current_direction: str) -> float:
        """Calculate technical reversal strength."""
        try:
            # Get OHLCV data for different timeframes
            ohlcv_15m = ohlcv_data.get('15m', [])
            ohlcv_5m = ohlcv_data.get('5m', [])
            
            if not ohlcv_15m or len(ohlcv_15m) < 20:
                return 0.0
            
            # Calculate multiple strength components
            supertrend_strength = self._calculate_supertrend_strength(ohlcv_15m, current_direction)
            rsi_strength = self._calculate_rsi_strength(ohlcv_15m, current_direction)
            momentum_strength = self._calculate_momentum_strength(ohlcv_15m, current_direction)
            volume_strength = self._calculate_volume_strength(ohlcv_15m)
            
            # Weighted combination
            weights = {
                'supertrend': 0.3,
                'rsi': 0.25,
                'momentum': 0.25,
                'volume': 0.2
            }
            
            total_strength = (
                weights['supertrend'] * supertrend_strength +
                weights['rsi'] * rsi_strength +
                weights['momentum'] * momentum_strength +
                weights['volume'] * volume_strength
            )
            
            return min(max(total_strength, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"Technical reversal strength calculation failed: {e}")
            return 0.0
    
    def _calculate_supertrend_strength(self, ohlcv: List[List], current_direction: str) -> float:
        """Calculate Supertrend reversal strength."""
        if len(ohlcv) < 20:
            return 0.0
        
        try:
            high = np.array([bar[2] for bar in ohlcv])
            low = np.array([bar[3] for bar in ohlcv])
            close = np.array([bar[4] for bar in ohlcv])
            
            # Calculate ATR
            atr = self._calculate_atr(high, low, close, 10)
            
            # Calculate Supertrend
            hl2 = (high + low) / 2
            upper_band = hl2 + (2 * atr)
            lower_band = hl2 - (2 * atr)
            
            supertrend = np.zeros_like(close)
            direction = np.ones_like(close)
            
            for i in range(1, len(close)):
                if close[i] <= lower_band[i-1]:
                    direction[i] = -1
                elif close[i] >= upper_band[i-1]:
                    direction[i] = 1
                else:
                    direction[i] = direction[i-1]
                
                if direction[i] == 1:
                    supertrend[i] = lower_band[i]
                else:
                    supertrend[i] = upper_band[i]
            
            # Check for direction change
            if len(direction) >= 2:
                current_dir = direction[-1]
                prev_dir = direction[-2]
                
                if current_dir != prev_dir:
                    # Direction change detected
                    if current_direction == 'long' and current_dir == -1:
                        return 0.8  # Long to short reversal
                    elif current_direction == 'short' and current_dir == 1:
                        return 0.8  # Short to long reversal
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Supertrend calculation failed: {e}")
            return 0.0
    
    def _calculate_rsi_strength(self, ohlcv: List[List], current_direction: str) -> float:
        """Calculate RSI reversal strength."""
        if len(ohlcv) < 14:
            return 0.0
        
        try:
            close = np.array([bar[4] for bar in ohlcv])
            rsi = self._calculate_rsi(close, 14)
            
            if len(rsi) < 2:
                return 0.0
            
            current_rsi = rsi[-1]
            prev_rsi = rsi[-2]
            
            # Check for RSI divergence
            if current_direction == 'long':
                # Long position - look for bearish divergence
                if current_rsi < 70 and prev_rsi >= 70:
                    return 0.7  # RSI overbought to neutral
                elif current_rsi < 50 and prev_rsi >= 50:
                    return 0.5  # RSI bullish to bearish
            else:
                # Short position - look for bullish divergence
                if current_rsi > 30 and prev_rsi <= 30:
                    return 0.7  # RSI oversold to neutral
                elif current_rsi > 50 and prev_rsi <= 50:
                    return 0.5  # RSI bearish to bullish
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"RSI strength calculation failed: {e}")
            return 0.0
    
    def _calculate_momentum_strength(self, ohlcv: List[List], current_direction: str) -> float:
        """Calculate momentum reversal strength."""
        if len(ohlcv) < 10:
            return 0.0
        
        try:
            close = np.array([bar[4] for bar in ohlcv])
            
            # Calculate momentum (rate of change)
            momentum_5 = (close[-1] - close[-6]) / close[-6] if len(close) >= 6 else 0
            momentum_10 = (close[-1] - close[-11]) / close[-11] if len(close) >= 11 else 0
            
            # Check for momentum reversal
            if current_direction == 'long':
                # Long position - look for negative momentum
                if momentum_5 < -0.02 and momentum_10 < -0.01:
                    return 0.8  # Strong negative momentum
                elif momentum_5 < 0:
                    return 0.4  # Weak negative momentum
            else:
                # Short position - look for positive momentum
                if momentum_5 > 0.02 and momentum_10 > 0.01:
                    return 0.8  # Strong positive momentum
                elif momentum_5 > 0:
                    return 0.4  # Weak positive momentum
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Momentum strength calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_strength(self, ohlcv: List[List]) -> float:
        """Calculate volume confirmation strength."""
        if len(ohlcv) < 5:
            return 0.0
        
        try:
            volume = np.array([bar[5] for bar in ohlcv])
            
            # Calculate volume moving average
            vol_ma = np.mean(volume[-5:])
            current_vol = volume[-1]
            
            # Volume spike indicates strong reversal
            if current_vol > vol_ma * 1.5:
                return 0.8  # High volume confirmation
            elif current_vol > vol_ma * 1.2:
                return 0.5  # Moderate volume confirmation
            else:
                return 0.2  # Low volume confirmation
            
        except Exception as e:
            logger.warning(f"Volume strength calculation failed: {e}")
            return 0.0
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        atr = np.zeros_like(tr)
        atr[period-1] = np.mean(tr[:period])
        
        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _calculate_rsi(self, close: np.ndarray, period: int) -> np.ndarray:
        """Calculate RSI."""
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.zeros_like(close)
        avg_loss = np.zeros_like(close)
        
        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])
        
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i-1]) / period
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class EdgeCostCalculator:
    """Calculate edge vs cost for reversal decisions."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.edge_cost_ratio_min = policy['trading']['scoring']['reversal']['edge_cost_ratio_min']
        self.atr_coefficient = policy['trading']['scoring']['reversal']['atr_coefficient']
        self.score_distance_coefficient = policy['trading']['scoring']['reversal']['score_distance_coefficient']
        self.fees_bps = policy['trading']['scoring']['reversal']['fees_bps']
        self.slippage_bps = policy['trading']['scoring']['reversal']['slippage_bps']
    
    def calculate_edge_cost_ratio(self, ohlcv_data: Dict, signal: Dict, current_price: float) -> Tuple[float, float, float]:
        """Calculate edge vs cost ratio for reversal."""
        try:
            # Calculate expected move
            expected_move = self._calculate_expected_move(ohlcv_data, signal, current_price)
            
            # Calculate total cost
            total_cost = self._calculate_total_cost(current_price)
            
            # Calculate ratio
            edge_cost_ratio = expected_move / total_cost if total_cost > 0 else 0
            
            return edge_cost_ratio, expected_move, total_cost
            
        except Exception as e:
            logger.warning(f"Edge cost calculation failed: {e}")
            return 0.0, 0.0, 0.0
    
    def _calculate_expected_move(self, ohlcv_data: Dict, signal: Dict, current_price: float) -> float:
        """Calculate expected price move."""
        try:
            # Get 15m data for ATR calculation
            ohlcv_15m = ohlcv_data.get('15m', [])
            if not ohlcv_15m or len(ohlcv_15m) < 14:
                return 0.0
            
            high = np.array([bar[2] for bar in ohlcv_15m])
            low = np.array([bar[3] for bar in ohlcv_15m])
            close = np.array([bar[4] for bar in ohlcv_15m])
            
            # Calculate ATR
            atr = self._calculate_atr(high, low, close, 14)
            current_atr = atr[-1] if len(atr) > 0 else 0
            
            # ATR component
            atr_component = current_atr * self.atr_coefficient
            
            # Score distance component
            final_score = signal.get('final_score', 50)
            score_distance = abs(final_score - 50) / 50  # Normalize to 0-1
            score_component = score_distance * self.score_distance_coefficient * current_price
            
            # Combine components
            expected_move = atr_component + score_component
            
            return expected_move
            
        except Exception as e:
            logger.warning(f"Expected move calculation failed: {e}")
            return 0.0
    
    def _calculate_total_cost(self, current_price: float) -> float:
        """Calculate total trading cost."""
        # Fees (round trip)
        fees = current_price * (self.fees_bps / 10000) * 2  # 2x for round trip
        
        # Slippage
        slippage = current_price * (self.slippage_bps / 10000)
        
        return fees + slippage
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        atr = np.zeros_like(tr)
        atr[period-1] = np.mean(tr[:period])
        
        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr


class ReversalManager:
    """Main reversal manager with SOLID principles."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.strength_calculator = TechnicalReversalStrength(policy)
        self.edge_cost_calculator = EdgeCostCalculator(policy)
        
        # Reversal parameters
        self.rev_strength_min = policy['trading']['scoring']['signal']['rev_strength_min']
        self.rev_confirm_bars = policy['trading']['scoring']['signal']['rev_confirm_bars']
        self.min_hold_bars = policy['trading']['scoring']['position_management']['min_hold_bars']
        self.edge_cost_ratio_min = policy['trading']['scoring']['reversal']['edge_cost_ratio_min']
        
        logger.info("ReversalManager initialized with technical strength calculator and edge cost calculator")
    
    def check_reversal_eligibility(self, symbol: str, signal: Dict, ohlcv_data: Dict, 
                                 current_direction: str, holding_bars: int, current_price: float) -> ReversalCheck:
        """Check if reversal is eligible based on all criteria."""
        try:
            # Calculate reversal strength
            strength = self.strength_calculator.calculate_strength(ohlcv_data, signal, current_direction)
            
            # Calculate edge vs cost ratio
            edge_cost_ratio, expected_move, total_cost = self.edge_cost_calculator.calculate_edge_cost_ratio(
                ohlcv_data, signal, current_price
            )
            
            # Check confirmation bars (simplified - would need signal history)
            confirmation_bars = 2  # TODO: Implement proper confirmation tracking
            
            # Check minimum holding period
            min_hold_met = holding_bars >= self.min_hold_bars
            
            # Check all criteria
            strength_ok = strength >= self.rev_strength_min
            confirmation_ok = confirmation_bars >= self.rev_confirm_bars
            edge_ok = edge_cost_ratio >= self.edge_cost_ratio_min
            holding_ok = min_hold_met
            
            is_eligible = strength_ok and confirmation_ok and edge_ok and holding_ok
            
            # Build reason
            reasons = []
            if not strength_ok:
                reasons.append(f"strength={strength:.2f}<{self.rev_strength_min}")
            if not confirmation_ok:
                reasons.append(f"confirm={confirmation_bars}<{self.rev_confirm_bars}")
            if not edge_ok:
                reasons.append(f"edge={edge_cost_ratio:.2f}<{self.edge_cost_ratio_min}")
            if not holding_ok:
                reasons.append(f"holding={holding_bars}<{self.min_hold_bars}")
            
            reason = "PASS" if is_eligible else f"FAIL: {', '.join(reasons)}"
            
            return ReversalCheck(
                is_eligible=is_eligible,
                strength=strength,
                confirmation_bars=confirmation_bars,
                edge_cost_ratio=edge_cost_ratio,
                expected_move=expected_move,
                total_cost=total_cost,
                holding_bars=holding_bars,
                min_hold_met=min_hold_met,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Reversal eligibility check failed for {symbol}: {e}")
            return ReversalCheck(
                is_eligible=False,
                strength=0.0,
                confirmation_bars=0,
                edge_cost_ratio=0.0,
                expected_move=0.0,
                total_cost=0.0,
                holding_bars=holding_bars,
                min_hold_met=False,
                reason=f"ERROR: {str(e)}"
            )
    
    def create_reversal_signal(self, symbol: str, signal: Dict, reversal_check: ReversalCheck, 
                             current_direction: str) -> ReversalSignal:
        """Create reversal signal if eligible."""
        final_score = signal.get('final_score', 0)
        
        # Determine new direction
        if current_direction == 'long':
            to_direction = 'short'
        else:
            to_direction = 'long'
        
        return ReversalSignal(
            symbol=symbol,
            from_direction=current_direction,
            to_direction=to_direction,
            strength=reversal_check.strength,
            confirmation_bars=reversal_check.confirmation_bars,
            expected_move=reversal_check.expected_move,
            total_cost=reversal_check.total_cost,
            edge_cost_ratio=reversal_check.edge_cost_ratio,
            is_valid=reversal_check.is_eligible,
            reason=reversal_check.reason
        )
    
    def should_activate_trailing(self, current_direction: str, r_multiple: float) -> bool:
        """Check if trailing stop should be activated."""
        activation_r = self.policy['trading']['scoring']['trailing']['activation_r_multiple']
        return r_multiple >= activation_r
    
    def get_trailing_stop_price(self, current_direction: str, entry_price: float, 
                               current_price: float, r_multiple: float) -> float:
        """Calculate trailing stop price based on R-multiple."""
        breakeven_r = self.policy['trading']['scoring']['trailing']['breakeven_r_multiple']
        tight_r = self.policy['trading']['scoring']['trailing']['tight_r_multiple']
        tight_offset = self.policy['trading']['scoring']['trailing']['tight_offset']
        
        if current_direction == 'long':
            if r_multiple >= tight_r:
                # Tight trailing stop
                return current_price * (1 - tight_offset)
            elif r_multiple >= breakeven_r:
                # Breakeven stop
                return entry_price
            else:
                # Normal trailing stop
                return current_price * 0.98  # 2% trailing
        else:
            if r_multiple >= tight_r:
                # Tight trailing stop
                return current_price * (1 + tight_offset)
            elif r_multiple >= breakeven_r:
                # Breakeven stop
                return entry_price
            else:
                # Normal trailing stop
                return current_price * 1.02  # 2% trailing
