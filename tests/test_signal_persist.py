"""
Test Signal Gate Persist Logic
Tests all scenarios where persist should reset or increment
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from application.signal_gate import (
    SignalGate, SignalHistory, PersistenceProcessor, RegimeInfo
)


def create_test_policy():
    """Create minimal test policy."""
    return {
        'trading': {
            'scoring': {
                'signal': {
                    'persistence_bars': 2,
                    'max_signal_age_bars': 6,  # Not used anymore but required
                    'rev_confirm_bars': 2,
                    'confirmation_margin': 2.0
                },
                'decision_thresholds': {
                    'enter_long': 62,
                    'exit_long': 45,
                    'enter_short': 38,
                    'exit_short': 55
                },
                'regime': {
                    'adx_1h_min': 22,
                    'low_adx_threshold': 20
                },
                'position_sizing': {
                    'regime_multiplier': 0.6
                }
            }
        }
    }


def get_bar_time(bar_index: int) -> datetime:
    """Generate distinct bar timestamps (15 min apart)."""
    base = datetime(2025, 12, 17, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(minutes=15 * bar_index)


def test_persist_increment_same_direction():
    """Test: Persist should increment when same direction signal continues."""
    print("\n" + "="*60)
    print("TEST 1: Persist Increment with Same Direction")
    print("="*60)
    
    policy = create_test_policy()
    gate = SignalGate(policy)
    symbol = "TEST-USDT-SWAP"
    
    # Bar 1: SHORT signal (score=30)
    result1 = gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(1)}, [], None)
    print(f"Bar 1: score=30 → persist={result1.persistence_bars}, valid={result1.is_valid}")
    assert result1.persistence_bars == 1, f"Expected persist=1, got {result1.persistence_bars}"
    assert result1.is_valid == False, "persist 1 < required 2"
    
    # Bar 2: SHORT signal (score=25)
    result2 = gate.process_signal(symbol, {'final_score': 25, 'bar_timestamp': get_bar_time(2)}, [], None)
    print(f"Bar 2: score=25 → persist={result2.persistence_bars}, valid={result2.is_valid}")
    assert result2.persistence_bars == 2, f"Expected persist=2, got {result2.persistence_bars}"
    assert result2.is_valid == True, "persist 2 >= required 2"
    
    # Bar 3: SHORT signal (score=20)
    result3 = gate.process_signal(symbol, {'final_score': 20, 'bar_timestamp': get_bar_time(3)}, [], None)
    print(f"Bar 3: score=20 → persist={result3.persistence_bars}, valid={result3.is_valid}")
    assert result3.persistence_bars == 3, f"Expected persist=3, got {result3.persistence_bars}"
    
    print("✅ TEST 1 PASSED")


def test_persist_reset_direction_change():
    """Test: Persist should reset when direction changes."""
    print("\n" + "="*60)
    print("TEST 2: Persist Reset on Direction Change")
    print("="*60)
    
    policy = create_test_policy()
    gate = SignalGate(policy)
    symbol = "TEST-USDT-SWAP"
    
    # Bar 1-2: SHORT signals
    gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(1)}, [], None)
    result1 = gate.process_signal(symbol, {'final_score': 25, 'bar_timestamp': get_bar_time(2)}, [], None)
    print(f"After 2 SHORT bars: persist={result1.persistence_bars}")
    assert result1.persistence_bars == 2
    
    # Bar 3: LONG signal (direction change!)
    result2 = gate.process_signal(symbol, {'final_score': 70, 'bar_timestamp': get_bar_time(3)}, [], None)
    print(f"After 1 LONG bar: persist={result2.persistence_bars}, direction={result2.direction}")
    assert result2.persistence_bars == 1, f"Expected persist=1 (reset), got {result2.persistence_bars}"
    assert result2.direction == 'long'
    
    print("✅ TEST 2 PASSED")


def test_persist_reset_score_below_threshold():
    """Test: Persist should reset when score drops below threshold (FLAT)."""
    print("\n" + "="*60)
    print("TEST 3: Persist Reset on Score Below Threshold (FLAT)")
    print("="*60)
    
    policy = create_test_policy()
    gate = SignalGate(policy)
    symbol = "TEST-USDT-SWAP"
    
    # Bar 1-2: SHORT signals
    gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(1)}, [], None)
    result1 = gate.process_signal(symbol, {'final_score': 25, 'bar_timestamp': get_bar_time(2)}, [], None)
    print(f"After 2 SHORT bars: persist={result1.persistence_bars}")
    
    # Bar 3: FLAT signal (score=50)
    result2 = gate.process_signal(symbol, {'final_score': 50, 'bar_timestamp': get_bar_time(3)}, [], None)
    print(f"After FLAT bar: persist={result2.persistence_bars}, direction={result2.direction}")
    assert result2.direction == 'flat'
    
    # Bar 4: SHORT again (should start from 1)
    result3 = gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(4)}, [], None)
    print(f"After SHORT again: persist={result3.persistence_bars}")
    assert result3.persistence_bars == 1, f"Should restart at 1, got {result3.persistence_bars}"
    
    print("✅ TEST 3 PASSED")


def test_persist_reset_on_history_clear():
    """Test: Persist should reset when signal history is cleared (position close)."""
    print("\n" + "="*60)
    print("TEST 4: Persist Reset on History Clear (Position Close)")
    print("="*60)
    
    policy = create_test_policy()
    gate = SignalGate(policy)
    symbol = "TEST-USDT-SWAP"
    
    # Build up persist count
    gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(1)}, [], None)
    gate.process_signal(symbol, {'final_score': 25, 'bar_timestamp': get_bar_time(2)}, [], None)
    result1 = gate.process_signal(symbol, {'final_score': 20, 'bar_timestamp': get_bar_time(3)}, [], None)
    print(f"Before clear: persist={result1.persistence_bars}")
    assert result1.persistence_bars == 3
    
    # Clear history (simulating position close by SL/TP)
    gate.clear_history(symbol)
    print("History cleared (simulating SL/TP hit)")
    
    # Next signal should start from 1
    result2 = gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(4)}, [], None)
    print(f"After clear: persist={result2.persistence_bars}")
    assert result2.persistence_bars == 1, f"Expected persist=1, got {result2.persistence_bars}"
    
    print("✅ TEST 4 PASSED")


def test_persist_long_sequence():
    """Test: Persist should keep incrementing even after 20+ bars (no age block)."""
    print("\n" + "="*60)
    print("TEST 5: Long Persist Sequence (Age Check Removed)")
    print("="*60)
    
    policy = create_test_policy()
    gate = SignalGate(policy)
    symbol = "TEST-USDT-SWAP"
    
    # Simulate 20 bars of same direction
    for i in range(20):
        result = gate.process_signal(symbol, {'final_score': 30, 'bar_timestamp': get_bar_time(i)}, [], None)
    
    print(f"After 20 bars: persist={result.persistence_bars}, valid={result.is_valid}")
    assert result.persistence_bars == 20, f"Expected persist=20, got {result.persistence_bars}"
    assert result.is_valid == True, "Should be valid (age check removed)"
    
    print("✅ TEST 5 PASSED")


def run_all_tests():
    """Run all persist logic tests."""
    print("\n" + "="*60)
    print("SIGNAL GATE PERSIST LOGIC TESTS")
    print("="*60)
    
    try:
        test_persist_increment_same_direction()
        test_persist_reset_direction_change()
        test_persist_reset_score_below_threshold()
        test_persist_reset_on_history_clear()
        test_persist_long_sequence()
        
        print("\n" + "="*60)
        print("✅ ALL 5 TESTS PASSED!")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
