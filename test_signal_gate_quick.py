"""
Signal Gate Quick Test
Tests signal gate persistence logic without connecting to exchange.
Run: python test_signal_gate_quick.py
"""

import asyncio
from datetime import datetime, timezone, timedelta
from application.signal_gate import SignalGate
import yaml


def load_policy():
    """Load policy from file."""
    with open('configs/policy.yaml', 'r') as f:
        return yaml.safe_load(f)


def test_persistence_counting():
    """Test that persistence counter increments correctly."""
    print("\n" + "="*60)
    print("TEST 1: Persistence Counter")
    print("="*60)
    
    policy = load_policy()
    gate = SignalGate(policy)
    
    # Get thresholds
    enter_long = policy['trading']['scoring']['decision_thresholds']['enter_long']
    persistence_required = policy['trading']['scoring']['signal']['persistence_bars']
    
    print(f"\nThresholds: enter_long={enter_long}, persistence_required={persistence_required}")
    print("-"*60)
    
    # Simulate consecutive bars with score > enter_long
    symbol = "BTC-USDT-TEST"
    
    for i in range(persistence_required + 1):
        # Create signal with score above long threshold
        bar_time = datetime.now(timezone.utc) + timedelta(minutes=15*i)
        signal = {
            'final_score': 65,  # Above enter_long (60)
            'bar_timestamp': bar_time
        }
        
        # Empty OHLCV for regime detection
        ohlcv = [[1, 100, 101, 99, 100, 1000] for _ in range(20)]
        
        result = gate.process_signal(symbol, signal, ohlcv)
        
        status = "✅ PASS" if result.is_valid else "⏳ PENDING"
        print(f"Bar {i+1}: score={signal['final_score']:.1f} | persist={result.persistence_bars}/{persistence_required} | {status}")
    
    # Final check
    history = gate.get_signal_history(symbol)
    print(f"\nHistory length: {len(history)}")
    print(f"Expected: persist >= {persistence_required} → Gate should PASS")
    
    return result.is_valid


def test_direction_change_resets():
    """Test that direction change resets persistence."""
    print("\n" + "="*60)
    print("TEST 2: Direction Change Resets Counter")
    print("="*60)
    
    policy = load_policy()
    gate = SignalGate(policy)
    
    symbol = "ETH-USDT-TEST"
    ohlcv = [[1, 100, 101, 99, 100, 1000] for _ in range(20)]
    
    # Bar 1: Long signal (score=65)
    signal1 = {'final_score': 65, 'bar_timestamp': datetime.now(timezone.utc)}
    result1 = gate.process_signal(symbol, signal1, ohlcv)
    print(f"Bar 1: score=65 (LONG) | persist={result1.persistence_bars}")
    
    # Bar 2: Short signal (score=35) - should reset
    signal2 = {'final_score': 35, 'bar_timestamp': datetime.now(timezone.utc) + timedelta(minutes=15)}
    result2 = gate.process_signal(symbol, signal2, ohlcv)
    print(f"Bar 2: score=35 (SHORT) | persist={result2.persistence_bars} ← Reset expected")
    
    # Bar 3: Short again
    signal3 = {'final_score': 35, 'bar_timestamp': datetime.now(timezone.utc) + timedelta(minutes=30)}
    result3 = gate.process_signal(symbol, signal3, ohlcv)
    print(f"Bar 3: score=35 (SHORT) | persist={result3.persistence_bars}")
    
    return result2.persistence_bars == 1  # Should reset to 1 on direction change


def test_flat_signal():
    """Test that flat signals don't pass gate."""
    print("\n" + "="*60)
    print("TEST 3: Flat Signals Stay Pending")
    print("="*60)
    
    policy = load_policy()
    gate = SignalGate(policy)
    
    enter_long = policy['trading']['scoring']['decision_thresholds']['enter_long']
    enter_short = policy['trading']['scoring']['decision_thresholds']['enter_short']
    
    symbol = "SOL-USDT-TEST"
    ohlcv = [[1, 100, 101, 99, 100, 1000] for _ in range(20)]
    
    # Simulate flat signals (between thresholds)
    for i in range(5):
        signal = {
            'final_score': 50,  # Flat (between 40-60)
            'bar_timestamp': datetime.now(timezone.utc) + timedelta(minutes=15*i)
        }
        result = gate.process_signal(symbol, signal, ohlcv)
        print(f"Bar {i+1}: score=50 (FLAT) | persist={result.persistence_bars} | is_valid={result.is_valid}")
    
    print(f"\nFlat signals should NEVER pass gate (is_valid should stay False)")
    return not result.is_valid


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 SIGNAL GATE QUICK TEST")
    print("="*60)
    
    results = []
    
    # Test 1
    try:
        passed = test_persistence_counting()
        results.append(("Persistence Counter", passed))
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results.append(("Persistence Counter", False))
    
    # Test 2
    try:
        passed = test_direction_change_resets()
        results.append(("Direction Change Reset", passed))
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results.append(("Direction Change Reset", False))
    
    # Test 3
    try:
        passed = test_flat_signal()
        results.append(("Flat Signals Pending", passed))
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        results.append(("Flat Signals Pending", False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {name}")
    
    all_passed = all(p for _, p in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))
    
    return all_passed


if __name__ == "__main__":
    main()
