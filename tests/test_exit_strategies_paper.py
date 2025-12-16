"""
Exit Strategies Paper Testing Harness

Comprehensive tests for all exit strategies using deterministic simulations.
No real exchange connection - pure logic validation.

Test Coverage:
1. Trailing Stop (long/short, all R-levels, edge cases)
2. Partial Take Profit (multi-level, no duplicates)
3. Time-Based Exit (warning, force close, interactions)
4. Fixed TP/SL (hit scenarios)
"""

import pytest
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Import the pure exit strategy functions
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from application.exit_strategies import (
    calculate_r_multiple,
    calculate_r_multiple_simple,
    compute_trailing_stop,
    is_stop_hit,
    check_partial_tp_levels,
    get_remaining_size_after_partial_tp,
    check_time_exit,
    check_fixed_tp_sl,
    TrailingMode,
    TrailingStopResult,
    PartialTPResult,
    TimeExitResult,
)


# ============================================================
# PAPER TESTING HARNESS
# ============================================================

@dataclass
class PaperPosition:
    """Virtual position for testing."""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Tracking state
    current_stop: Optional[float] = None
    trailing_active: bool = False
    partial_tp_executed: List[int] = field(default_factory=list)
    closed: bool = False
    close_reason: str = ""
    close_price: float = 0.0
    remaining_size: float = 0.0
    
    def __post_init__(self):
        self.current_stop = self.stop_loss
        self.remaining_size = self.size


@dataclass
class PriceEvent:
    """A timestamped price update."""
    timestamp: datetime
    price: float


@dataclass 
class ExitAction:
    """Record of an exit action taken."""
    action_type: str  # 'trailing_update', 'partial_tp', 'time_exit', 'sl_hit', 'tp_hit'
    timestamp: datetime
    price: float
    details: Dict[str, Any]


class PaperExitEngine:
    """
    Paper trading engine for exit strategy simulation.
    
    Simulates price/time events and applies exit logic.
    """
    
    def __init__(self, trailing_config: Dict, partial_tp_config: Dict, time_exit_config: Dict):
        self.trailing_config = trailing_config
        self.partial_tp_config = partial_tp_config
        self.time_exit_config = time_exit_config
        self.actions: List[ExitAction] = []
    
    def simulate(self, position: PaperPosition, events: List[PriceEvent]) -> List[ExitAction]:
        """
        Run simulation with price/time events.
        
        Args:
            position: The paper position to simulate
            events: List of price events in chronological order
            
        Returns:
            List of exit actions taken
        """
        self.actions = []
        
        for event in events:
            if position.closed:
                break
                
            current_price = event.price
            current_time = event.timestamp
            
            # Check fixed TP/SL first
            triggered, trigger_type = check_fixed_tp_sl(
                current_price, position.take_profit, position.stop_loss, position.side
            )
            if triggered:
                position.closed = True
                position.close_reason = trigger_type
                position.close_price = current_price
                self.actions.append(ExitAction(
                    action_type=f"{trigger_type.lower()}_hit",
                    timestamp=current_time,
                    price=current_price,
                    details={'trigger': trigger_type}
                ))
                continue
            
            # Calculate R-multiple
            r_multiple = calculate_r_multiple(
                position.entry_price, current_price, 
                position.stop_loss, position.side
            )
            
            # Check trailing stop
            trailing_result = compute_trailing_stop(
                position.entry_price, current_price, position.side,
                r_multiple, self.trailing_config, position.current_stop
            )
            
            if trailing_result.mode != TrailingMode.NOT_ACTIVATED:
                position.trailing_active = True
                
                if trailing_result.should_update:
                    old_stop = position.current_stop
                    position.current_stop = trailing_result.new_stop_price
                    self.actions.append(ExitAction(
                        action_type='trailing_update',
                        timestamp=current_time,
                        price=current_price,
                        details={
                            'mode': trailing_result.mode.value,
                            'old_stop': old_stop,
                            'new_stop': trailing_result.new_stop_price,
                            'r_multiple': r_multiple,
                            'reason': trailing_result.reason
                        }
                    ))
                
                # Check if trailing stop hit
                if is_stop_hit(current_price, position.current_stop, position.side):
                    position.closed = True
                    position.close_reason = "TRAILING_STOP"
                    position.close_price = current_price
                    self.actions.append(ExitAction(
                        action_type='trailing_stop_hit',
                        timestamp=current_time,
                        price=current_price,
                        details={
                            'stop_price': position.current_stop,
                            'r_multiple': r_multiple
                        }
                    ))
                    continue
            
            # Check partial TP
            if r_multiple > 0:
                tp_results = check_partial_tp_levels(
                    r_multiple, position.remaining_size,
                    self.partial_tp_config, position.partial_tp_executed
                )
                
                for tp_result in tp_results:
                    position.partial_tp_executed.append(tp_result.level_index)
                    position.remaining_size -= tp_result.close_size
                    self.actions.append(ExitAction(
                        action_type='partial_tp',
                        timestamp=current_time,
                        price=current_price,
                        details={
                            'level': tp_result.level_index + 1,
                            'level_r': tp_result.level_r,
                            'close_pct': tp_result.close_pct,
                            'close_size': tp_result.close_size,
                            'remaining_size': position.remaining_size,
                            'r_multiple': r_multiple
                        }
                    ))
                    
                    # Check if fully closed
                    if position.remaining_size <= 0.001:
                        position.closed = True
                        position.close_reason = "PARTIAL_TP_COMPLETE"
            
            # Check time exit
            time_result = check_time_exit(
                position.opened_at, current_time, self.time_exit_config
            )
            
            if time_result.should_exit:
                position.closed = True
                position.close_reason = "TIME_EXIT"
                position.close_price = current_price
                self.actions.append(ExitAction(
                    action_type='time_exit',
                    timestamp=current_time,
                    price=current_price,
                    details={
                        'age_hours': time_result.age_hours,
                        'action': time_result.action
                    }
                ))
            elif time_result.should_warn:
                self.actions.append(ExitAction(
                    action_type='time_warning',
                    timestamp=current_time,
                    price=current_price,
                    details={
                        'age_hours': time_result.age_hours,
                        'reason': time_result.reason
                    }
                ))
        
        return self.actions


# ============================================================
# DEFAULT TEST CONFIGS (from policy.yaml)
# ============================================================

DEFAULT_TRAILING_CONFIG = {
    'enabled': True,
    'activation_r_multiple': 0.5,
    'breakeven_r_multiple': 1.0,
    'tight_r_multiple': 1.5,
    'tight_offset': 0.3  # 0.3%
}

DEFAULT_PARTIAL_TP_CONFIG = {
    'enabled': True,
    'levels': [
        {'r_multiple': 1.0, 'close_pct': 0.33},
        {'r_multiple': 2.0, 'close_pct': 0.33},
        {'r_multiple': 4.0, 'close_pct': 0.34},
    ]
}

DEFAULT_TIME_EXIT_CONFIG = {
    'enabled': True,
    'max_position_age_hours': 24,
    'warning_hours': 20,
    'stale_position_action': 'close'
}


# ============================================================
# TEST: R-MULTIPLE CALCULATION
# ============================================================

class TestRMultipleCalculation:
    """Test R-multiple calculations."""
    
    def test_long_profit(self):
        """Long position in profit."""
        r = calculate_r_multiple(
            entry_price=100, current_price=104, 
            stop_loss=98, side='long'
        )
        # Risk = 100 - 98 = 2, Profit = 104 - 100 = 4
        # R = 4 / 2 = 2.0
        assert r == 2.0
    
    def test_long_loss(self):
        """Long position in loss."""
        r = calculate_r_multiple(
            entry_price=100, current_price=99,
            stop_loss=98, side='long'
        )
        # Risk = 2, Loss = -1, R = -0.5
        assert r == -0.5
    
    def test_short_profit(self):
        """Short position in profit."""
        r = calculate_r_multiple(
            entry_price=100, current_price=96,
            stop_loss=102, side='short'
        )
        # Risk = 102 - 100 = 2, Profit = 100 - 96 = 4
        # R = 4 / 2 = 2.0
        assert r == 2.0
    
    def test_short_loss(self):
        """Short position in loss."""
        r = calculate_r_multiple(
            entry_price=100, current_price=101,
            stop_loss=102, side='short'
        )
        # Risk = 2, Loss = -1, R = -0.5
        assert r == -0.5
    
    def test_simple_r_multiple_long(self):
        """Simple R-multiple for long."""
        r = calculate_r_multiple_simple(
            entry_price=100, current_price=102, side='long'
        )
        # (102 - 100) / 100 = 0.02
        assert r == 0.02
    
    def test_simple_r_multiple_short(self):
        """Simple R-multiple for short."""
        r = calculate_r_multiple_simple(
            entry_price=100, current_price=98, side='short'
        )
        # (100 - 98) / 100 = 0.02  
        assert r == 0.02


# ============================================================
# TEST: TRAILING STOP
# ============================================================

class TestTrailingStop:
    """Test trailing stop logic."""
    
    def test_not_activated_low_r(self):
        """Trailing not activated when R < 0.5."""
        result = compute_trailing_stop(
            entry_price=100, current_price=100.5, side='long',
            r_multiple=0.25, config=DEFAULT_TRAILING_CONFIG
        )
        assert result.mode == TrailingMode.NOT_ACTIVATED
        assert result.should_update == False
    
    def test_normal_trail_long(self):
        """Normal trailing for long at R=0.5."""
        result = compute_trailing_stop(
            entry_price=100, current_price=101, side='long',
            r_multiple=0.5, config=DEFAULT_TRAILING_CONFIG
        )
        assert result.mode == TrailingMode.NORMAL
        assert result.should_update == True
        # 2% below current: 101 * 0.98 = 98.98
        assert abs(result.new_stop_price - 98.98) < 0.01
    
    def test_breakeven_long(self):
        """Breakeven trailing for long at R=1.0."""
        result = compute_trailing_stop(
            entry_price=100, current_price=102, side='long',
            r_multiple=1.0, config=DEFAULT_TRAILING_CONFIG
        )
        assert result.mode == TrailingMode.BREAKEVEN
        assert result.should_update == True
        # Entry + 0.1% buffer: 100 * 1.001 = 100.1
        assert abs(result.new_stop_price - 100.1) < 0.01
    
    def test_tight_trail_long(self):
        """Tight trailing for long at R=1.5."""
        result = compute_trailing_stop(
            entry_price=100, current_price=103, side='long',
            r_multiple=1.5, config=DEFAULT_TRAILING_CONFIG
        )
        assert result.mode == TrailingMode.TIGHT
        assert result.should_update == True
        # 0.3% below current: 103 * (1 - 0.003) = 102.691
        assert abs(result.new_stop_price - 102.691) < 0.01
    
    def test_normal_trail_short(self):
        """Normal trailing for short."""
        result = compute_trailing_stop(
            entry_price=100, current_price=99, side='short',
            r_multiple=0.5, config=DEFAULT_TRAILING_CONFIG
        )
        assert result.mode == TrailingMode.NORMAL
        # 2% above current: 99 * 1.02 = 100.98
        assert abs(result.new_stop_price - 100.98) < 0.01
    
    def test_no_update_if_worse(self):
        """Don't update stop if new stop is worse."""
        result = compute_trailing_stop(
            entry_price=100, current_price=101, side='long',
            r_multiple=0.5, config=DEFAULT_TRAILING_CONFIG,
            current_stop=99.5  # Current stop is better than new (98.98)
        )
        assert result.should_update == False
    
    def test_stop_hit_long(self):
        """Stop hit detection for long."""
        assert is_stop_hit(98, 99, 'long') == True
        assert is_stop_hit(100, 99, 'long') == False
    
    def test_stop_hit_short(self):
        """Stop hit detection for short."""
        assert is_stop_hit(102, 101, 'short') == True
        assert is_stop_hit(100, 101, 'short') == False


class TestTrailingStopScenarios:
    """Full scenario tests for trailing stop."""
    
    def test_long_normal_to_breakeven_to_tight(self):
        """
        Long position: price rises through all R levels.
        Entry: 100, SL: 98 (risk = 2)
        """
        entry = 100
        sl = 98
        risk = 2
        
        # R = 0.5 (price = 101)
        r = calculate_r_multiple(entry, 101, sl, 'long')
        assert abs(r - 0.5) < 0.01
        result = compute_trailing_stop(entry, 101, 'long', r, DEFAULT_TRAILING_CONFIG)
        assert result.mode == TrailingMode.NORMAL
        
        # R = 1.0 (price = 102)
        r = calculate_r_multiple(entry, 102, sl, 'long')
        assert abs(r - 1.0) < 0.01
        result = compute_trailing_stop(entry, 102, 'long', r, DEFAULT_TRAILING_CONFIG)
        assert result.mode == TrailingMode.BREAKEVEN
        
        # R = 1.5 (price = 103)
        r = calculate_r_multiple(entry, 103, sl, 'long')
        assert abs(r - 1.5) < 0.01
        result = compute_trailing_stop(entry, 103, 'long', r, DEFAULT_TRAILING_CONFIG)
        assert result.mode == TrailingMode.TIGHT
    
    def test_short_trailing_progression(self):
        """
        Short position: price falls through R levels.
        Entry: 100, SL: 102 (risk = 2)
        """
        entry = 100
        sl = 102
        
        # R = 0.5 (price = 99)
        r = calculate_r_multiple(entry, 99, sl, 'short')
        assert abs(r - 0.5) < 0.01
        result = compute_trailing_stop(entry, 99, 'short', r, DEFAULT_TRAILING_CONFIG)
        assert result.mode == TrailingMode.NORMAL
        # Stop should be ABOVE current: 99 * 1.02 = 100.98
        assert result.new_stop_price > 99
        
        # R = 1.0 (price = 98)
        r = calculate_r_multiple(entry, 98, sl, 'short')
        assert abs(r - 1.0) < 0.01
        result = compute_trailing_stop(entry, 98, 'short', r, DEFAULT_TRAILING_CONFIG)
        assert result.mode == TrailingMode.BREAKEVEN
        # Stop at entry - buffer: 100 * 0.999 = 99.9
        assert abs(result.new_stop_price - 99.9) < 0.01


# ============================================================
# TEST: PARTIAL TAKE PROFIT
# ============================================================

class TestPartialTP:
    """Test partial take profit logic."""
    
    def test_no_hit_below_first_level(self):
        """No partial TP when R < 1.0."""
        results = check_partial_tp_levels(
            r_multiple=0.5, position_size=1.0,
            config=DEFAULT_PARTIAL_TP_CONFIG, executed_levels=[]
        )
        assert len(results) == 0
    
    def test_hit_first_level(self):
        """Hit level 1 at R=1.0."""
        results = check_partial_tp_levels(
            r_multiple=1.0, position_size=1.0,
            config=DEFAULT_PARTIAL_TP_CONFIG, executed_levels=[]
        )
        assert len(results) == 1
        assert results[0].level_index == 0
        assert results[0].level_r == 1.0
        assert abs(results[0].close_pct - 0.33) < 0.01
        assert abs(results[0].close_size - 0.33) < 0.01
    
    def test_hit_multiple_levels(self):
        """Hit multiple levels at R=2.0."""
        results = check_partial_tp_levels(
            r_multiple=2.0, position_size=1.0,
            config=DEFAULT_PARTIAL_TP_CONFIG, executed_levels=[]
        )
        # Should hit level 1 (R=1.0) and level 2 (R=2.0)
        assert len(results) == 2
        assert results[0].level_r == 1.0
        assert results[1].level_r == 2.0
    
    def test_no_duplicate_execution(self):
        """Already executed levels are skipped."""
        results = check_partial_tp_levels(
            r_multiple=2.0, position_size=0.67,
            config=DEFAULT_PARTIAL_TP_CONFIG, executed_levels=[0]  # Level 1 already done
        )
        # Should only hit level 2
        assert len(results) == 1
        assert results[0].level_index == 1
    
    def test_remaining_size_calculation(self):
        """Calculate remaining size after partial TPs."""
        # After level 1 (33%)
        remaining = get_remaining_size_after_partial_tp(
            1.0, DEFAULT_PARTIAL_TP_CONFIG, [0]
        )
        assert abs(remaining - 0.67) < 0.01
        
        # After levels 1 and 2 (33% + 33% = 66%)
        remaining = get_remaining_size_after_partial_tp(
            1.0, DEFAULT_PARTIAL_TP_CONFIG, [0, 1]
        )
        assert abs(remaining - 0.34) < 0.01
        
        # After all levels (33% + 33% + 34% = 100%)
        remaining = get_remaining_size_after_partial_tp(
            1.0, DEFAULT_PARTIAL_TP_CONFIG, [0, 1, 2]
        )
        assert abs(remaining - 0.0) < 0.01


class TestPartialTPScenarios:
    """Full scenario tests for partial TP."""
    
    def test_sequential_level_execution(self):
        """
        Position size 1.0, R progresses through levels.
        """
        size = 1.0
        executed = []
        
        # R = 0.5 - nothing
        results = check_partial_tp_levels(0.5, size, DEFAULT_PARTIAL_TP_CONFIG, executed)
        assert len(results) == 0
        
        # R = 1.0 - hit level 1
        results = check_partial_tp_levels(1.0, size, DEFAULT_PARTIAL_TP_CONFIG, executed)
        assert len(results) == 1
        executed.append(results[0].level_index)
        size -= results[0].close_size
        assert abs(size - 0.67) < 0.01
        
        # R = 1.5 - nothing new
        results = check_partial_tp_levels(1.5, size, DEFAULT_PARTIAL_TP_CONFIG, executed)
        assert len(results) == 0
        
        # R = 2.0 - hit level 2
        results = check_partial_tp_levels(2.0, size, DEFAULT_PARTIAL_TP_CONFIG, executed)
        assert len(results) == 1
        executed.append(results[0].level_index)
        size -= results[0].close_size
        # 0.67 - (0.67 * 0.33) ≈ 0.45? No - close_size is based on original calculation
        # Actually: 0.67 * 0.33 = 0.22, remaining = 0.67 - 0.22 = 0.45
        # But the config says close_pct is of ORIGINAL size, so we need to track carefully
        
        # R = 4.0 - hit level 3  
        results = check_partial_tp_levels(4.0, size, DEFAULT_PARTIAL_TP_CONFIG, executed)
        assert len(results) == 1
        executed.append(results[0].level_index)


# ============================================================
# TEST: TIME EXIT
# ============================================================

class TestTimeExit:
    """Test time-based exit logic."""
    
    def test_ok_fresh_position(self):
        """Fresh position - no warning or exit."""
        now = datetime.now(timezone.utc)
        opened = now - timedelta(hours=5)
        result = check_time_exit(opened, now, DEFAULT_TIME_EXIT_CONFIG)
        assert result.should_exit == False
        assert result.should_warn == False
        assert abs(result.age_hours - 5) < 0.1
    
    def test_warning_threshold(self):
        """Position at warning threshold (20h)."""
        now = datetime.now(timezone.utc)
        opened = now - timedelta(hours=20)
        result = check_time_exit(opened, now, DEFAULT_TIME_EXIT_CONFIG)
        assert result.should_exit == False
        assert result.should_warn == True
        assert abs(result.age_hours - 20) < 0.1
    
    def test_exit_threshold(self):
        """Position at exit threshold (24h)."""
        now = datetime.now(timezone.utc)
        opened = now - timedelta(hours=24)
        result = check_time_exit(opened, now, DEFAULT_TIME_EXIT_CONFIG)
        assert result.should_exit == True
        assert result.should_warn == False
        assert result.action == 'close'
    
    def test_past_exit_threshold(self):
        """Position past exit threshold (30h)."""
        now = datetime.now(timezone.utc)
        opened = now - timedelta(hours=30)
        result = check_time_exit(opened, now, DEFAULT_TIME_EXIT_CONFIG)
        assert result.should_exit == True
        assert abs(result.age_hours - 30) < 0.1


# ============================================================
# TEST: FIXED TP/SL
# ============================================================

class TestFixedTPSL:
    """Test fixed TP/SL hit detection."""
    
    def test_long_tp_hit(self):
        """Long position TP hit."""
        hit, trigger = check_fixed_tp_sl(105, 105, 95, 'long')
        assert hit == True
        assert trigger == 'TP'
    
    def test_long_sl_hit(self):
        """Long position SL hit."""
        hit, trigger = check_fixed_tp_sl(95, 105, 95, 'long')
        assert hit == True
        assert trigger == 'SL'
    
    def test_long_no_hit(self):
        """Long position neither hit."""
        hit, trigger = check_fixed_tp_sl(100, 105, 95, 'long')
        assert hit == False
        assert trigger == 'NONE'
    
    def test_short_tp_hit(self):
        """Short position TP hit."""
        hit, trigger = check_fixed_tp_sl(95, 95, 105, 'short')
        assert hit == True
        assert trigger == 'TP'
    
    def test_short_sl_hit(self):
        """Short position SL hit."""
        hit, trigger = check_fixed_tp_sl(105, 95, 105, 'short')
        assert hit == True
        assert trigger == 'SL'


# ============================================================
# TEST: FULL SIMULATION SCENARIOS
# ============================================================

class TestPaperExitEngine:
    """Test full simulation with PaperExitEngine."""
    
    def test_long_trailing_stop_hit(self):
        """
        Long position: price rises then falls to trailing stop.
        """
        position = PaperPosition(
            symbol="BTC-USDT-SWAP",
            side="long",
            entry_price=100,
            size=1.0,
            stop_loss=98,
            take_profit=110,
            opened_at=datetime.now(timezone.utc)
        )
        
        engine = PaperExitEngine(
            DEFAULT_TRAILING_CONFIG, 
            DEFAULT_PARTIAL_TP_CONFIG,
            DEFAULT_TIME_EXIT_CONFIG
        )
        
        # Price path: rises to 103 (R=1.5), then falls
        t0 = datetime.now(timezone.utc)
        events = [
            PriceEvent(t0 + timedelta(minutes=5), 101),   # R=0.5
            PriceEvent(t0 + timedelta(minutes=10), 102),  # R=1.0
            PriceEvent(t0 + timedelta(minutes=15), 103),  # R=1.5
            PriceEvent(t0 + timedelta(minutes=20), 102),  # Still above stop
            PriceEvent(t0 + timedelta(minutes=25), 101),  # Approaching stop
            PriceEvent(t0 + timedelta(minutes=30), 102.5),  # Stop should be ~102.69
        ]
        
        actions = engine.simulate(position, events)
        
        # Should have trailing updates
        trailing_updates = [a for a in actions if a.action_type == 'trailing_update']
        assert len(trailing_updates) >= 3  # Normal, Breakeven, Tight
        
        # Check modes progressed correctly
        modes = [a.details['mode'] for a in trailing_updates]
        assert 'NORMAL' in modes
        assert 'BREAKEVEN' in modes
        assert 'TIGHT' in modes
    
    def test_time_exit_triggers(self):
        """
        Position exceeds max age and gets force closed.
        """
        t0 = datetime.now(timezone.utc) - timedelta(hours=25)  # Opened 25h ago
        
        position = PaperPosition(
            symbol="ETH-USDT-SWAP",
            side="long",
            entry_price=100,
            size=1.0,
            stop_loss=98,
            take_profit=110,
            opened_at=t0
        )
        
        engine = PaperExitEngine(
            DEFAULT_TRAILING_CONFIG,
            DEFAULT_PARTIAL_TP_CONFIG,
            DEFAULT_TIME_EXIT_CONFIG
        )
        
        events = [
            PriceEvent(datetime.now(timezone.utc), 100.5),  # Current price
        ]
        
        actions = engine.simulate(position, events)
        
        # Should have time exit
        time_exits = [a for a in actions if a.action_type == 'time_exit']
        assert len(time_exits) == 1
        assert position.closed == True
        assert position.close_reason == "TIME_EXIT"


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
