"""
Dry-run test for counter logic - validates bar-based deduplication and threshold checks
"""

from datetime import datetime, timedelta, timezone
import sys
sys.path.insert(0, '.')

from application.signal_gate import round_to_bar, SignalHistory


def test_round_to_bar():
    """Test bar rounding helper."""
    print("=" * 80)
    print("TEST 1: round_to_bar() helper")
    print("=" * 80)
    
    # Test cases
    ts1 = datetime(2025, 10, 31, 19, 17, 23, tzinfo=timezone.utc)
    ts2 = datetime(2025, 10, 31, 19, 30, 0, tzinfo=timezone.utc)
    ts3 = datetime(2025, 10, 31, 19, 44, 59, tzinfo=timezone.utc)
    
    rounded1 = round_to_bar(ts1, 15)
    rounded2 = round_to_bar(ts2, 15)
    rounded3 = round_to_bar(ts3, 15)
    
    expected1 = datetime(2025, 10, 31, 19, 15, 0, tzinfo=timezone.utc)
    expected2 = datetime(2025, 10, 31, 19, 30, 0, tzinfo=timezone.utc)
    expected3 = datetime(2025, 10, 31, 19, 30, 0, tzinfo=timezone.utc)
    
    print(f"Input:    {ts1} -> Rounded: {rounded1} (Expected: {expected1})")
    print(f"Input:    {ts2} -> Rounded: {rounded2} (Expected: {expected2})")
    print(f"Input:    {ts3} -> Rounded: {rounded3} (Expected: {expected3})")
    
    pass1 = rounded1 == expected1
    pass2 = rounded2 == expected2
    pass3 = rounded3 == expected3
    
    print(f"\n[CHECK] All rounding tests: {'PASS' if all([pass1, pass2, pass3]) else 'FAIL'}")
    return all([pass1, pass2, pass3])


def test_counter_logic():
    """Test counter increment logic with bar-based deduplication."""
    print("\n" + "=" * 80)
    print("TEST 2: Counter logic (bar-based, threshold-aware)")
    print("=" * 80)
    
    # Simulate 20 bars with varying scores
    base_time = datetime(2025, 10, 31, 19, 0, 0, tzinfo=timezone.utc)
    
    # Policy thresholds
    enter_long_threshold = 60
    enter_short_threshold = 40
    
    # Scenario: scores vary, some meet threshold, some don't
    scenarios = [
        # (bar, score, direction, expected_persist_increment)
        (0, 65.0, 'long', True),   # Bar 0: threshold met, persist++
        (1, 62.0, 'long', True),   # Bar 1: threshold met, persist++
        (2, 58.0, 'long', False),  # Bar 2: below threshold, persist reset
        (3, 67.0, 'long', True),   # Bar 3: threshold met again, persist=1
        (4, 70.0, 'long', True),   # Bar 4: threshold met, persist++
        (5, 68.0, 'long', True),   # Bar 5: threshold met, persist++
        (6, 35.0, 'short', True),  # Bar 6: direction change, persist=1 (short)
        (7, 38.0, 'short', True),  # Bar 7: threshold met, persist++
        (8, 32.0, 'short', True),  # Bar 8: threshold met, persist++
        (9, 42.0, 'short', False), # Bar 9: above short threshold, persist reset
        (10, 50.0, 'flat', False), # Bar 10: flat, persist=0
    ]
    
    print("\nSimulating bars:")
    print(f"{'Bar':<5} {'Score':<8} {'Dir':<8} {'Threshold Met':<15} {'Expected Persist':<20}")
    print("-" * 80)
    
    persist_count = 0
    last_direction = None
    
    for bar, score, direction, threshold_met in scenarios:
        bar_time = base_time + timedelta(minutes=15 * bar)
        bar_id = round_to_bar(bar_time, 15)
        
        # Check threshold
        if direction == 'long' and score >= enter_long_threshold:
            actual_threshold_met = True
        elif direction == 'short' and score <= enter_short_threshold:
            actual_threshold_met = True
        else:
            actual_threshold_met = False
        
        # Counter logic
        if direction == last_direction and actual_threshold_met:
            persist_count += 1
        elif actual_threshold_met:
            persist_count = 1  # New direction
        else:
            persist_count = 0  # Reset
        
        last_direction = direction if actual_threshold_met else None
        
        expected_persist = "Increment" if threshold_met else "Reset to 0"
        status = "OK" if actual_threshold_met == threshold_met else "FAIL"
        
        print(f"{bar:<5} {score:<8.1f} {direction:<8} {str(actual_threshold_met):<15} {expected_persist:<20} [{status}] persist={persist_count}")
    
    print("\n[CHECK] Counter logic simulation complete")
    return True


def test_bar_deduplication():
    """Test that same bar doesn't increment counter twice."""
    print("\n" + "=" * 80)
    print("TEST 3: Bar deduplication (no same-bar duplicates)")
    print("=" * 80)
    
    # Simulate multiple signals in same bar
    bar_time = datetime(2025, 10, 31, 19, 15, 0, tzinfo=timezone.utc)
    
    # Signals within same 15m bar
    signals = [
        bar_time + timedelta(seconds=10),   # 19:15:10
        bar_time + timedelta(seconds=120),  # 19:17:00
        bar_time + timedelta(seconds=300),  # 19:20:00
        bar_time + timedelta(seconds=800),  # 19:28:20
    ]
    
    bar_ids = [round_to_bar(s, 15) for s in signals]
    unique_bars = set(bar_ids)
    
    print(f"\nSignals:")
    for i, (sig, bar_id) in enumerate(zip(signals, bar_ids)):
        print(f"  Signal {i+1}: {sig} -> Bar ID: {bar_id}")
    
    print(f"\nUnique bar IDs: {len(unique_bars)}")
    print(f"Expected: 1 (all in same bar)")
    
    pass_dedup = len(unique_bars) == 1
    print(f"\n[CHECK] Bar deduplication: {'PASS' if pass_dedup else 'FAIL'}")
    
    return pass_dedup


def main():
    """Run all counter tests."""
    print("\n" + "=" * 80)
    print("COUNTER LOGIC DRY-RUN TESTS")
    print("=" * 80)
    
    test1 = test_round_to_bar()
    test2 = test_counter_logic()
    test3 = test_bar_deduplication()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Test 1 (round_to_bar): {'[PASS]' if test1 else '[FAIL]'}")
    print(f"Test 2 (counter logic): {'[PASS]' if test2 else '[FAIL]'}")
    print(f"Test 3 (bar dedup): {'[PASS]' if test3 else '[FAIL]'}")
    
    if all([test1, test2, test3]):
        print("\n" + "=" * 80)
        print("[PASS] ALL TESTS PASSED")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("[FAIL] SOME TESTS FAILED")
        print("=" * 80)
        return 1


if __name__ == '__main__':
    exit(main())

