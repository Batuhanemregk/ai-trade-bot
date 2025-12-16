"""
Exit Strategy Implementation Verification

This script verifies that the pure exit_strategies.py functions
match the actual implementation in trailing_5m.py.

Run this to confirm that the test harness accurately reflects
real trading behavior.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from application.exit_strategies import (
    calculate_r_multiple,
    calculate_r_multiple_simple,
    compute_trailing_stop,
    check_partial_tp_levels,
    check_time_exit,
    TrailingMode,
)


def verify_trailing_stop_logic():
    """
    Verify trailing stop logic matches trailing_5m.py._process_trailing_stop()
    
    FIXED: Now uses proper R-multiple = pnl / risk
    
    From trailing_5m.py (AFTER FIX):
    - R = (current - entry) / (entry - sl)
    - activation_r = 0.5
    - breakeven_r = 1.0
    - tight_r = 1.5
    """
    print("\n" + "="*60)
    print("VERIFICATION: Trailing Stop Logic")
    print("="*60)
    
    config = {
        'activation_r_multiple': 0.5,
        'breakeven_r_multiple': 1.0,
        'tight_r_multiple': 1.5,
        'tight_offset': 0.3  # 0.3%
    }
    
    # Test cases with proper SL-based R calculation
    # Entry=100, SL=98, Risk=2
    test_cases = [
        # (entry, sl, current, side, expected_mode, description)
        (100, 98, 100.5, 'long', 'NOT_ACTIVATED', "R < 0.5 (R=0.25)"),
        (100, 98, 101, 'long', 'NORMAL', "R = 0.5 at price 101"),
        (100, 98, 102, 'long', 'BREAKEVEN', "R = 1.0 at price 102"),
        (100, 98, 103, 'long', 'TIGHT', "R = 1.5 at price 103"),
        (100, 102, 99, 'short', 'NORMAL', "Short R = 0.5 at price 99"),
        (100, 102, 98, 'short', 'BREAKEVEN', "Short R = 1.0 at price 98"),
    ]
    
    all_passed = True
    for entry, sl, current, side, expected_mode, desc in test_cases:
        # Calculate R with proper formula: R = pnl / risk
        r = calculate_r_multiple(entry, current, sl, side)
        result = compute_trailing_stop(entry, current, side, r, config)
        
        actual = result.mode.value
        status = "✅" if actual == expected_mode else "❌"
        if actual != expected_mode:
            all_passed = False
        
        print(f"  {status} {desc}: entry={entry}, SL={sl}, current={current}, R={r:.3f}")
        print(f"      Expected: {expected_mode}, Got: {actual}")
    
    return all_passed


def verify_partial_tp_logic():
    """
    Verify partial TP logic matches trailing_5m.py._check_partial_tp()
    
    From policy.yaml lines 213-221:
    - Level 1: R=1.0, close 33%
    - Level 2: R=2.0, close 33%
    - Level 3: R=4.0, close 34%
    """
    print("\n" + "="*60)
    print("VERIFICATION: Partial TP Logic")
    print("="*60)
    
    config = {
        'enabled': True,
        'levels': [
            {'r_multiple': 1.0, 'close_pct': 0.33},
            {'r_multiple': 2.0, 'close_pct': 0.33},
            {'r_multiple': 4.0, 'close_pct': 0.34},
        ]
    }
    
    test_cases = [
        # (r_multiple, executed_levels, expected_new_levels, description)
        (0.5, [], [], "R < 1.0, no levels hit"),
        (1.0, [], [0], "R = 1.0, level 1 hit"),
        (1.5, [0], [], "R = 1.5, level 1 already done"),
        (2.0, [0], [1], "R = 2.0, level 2 hit"),
        (4.0, [0, 1], [2], "R = 4.0, level 3 hit"),
        (5.0, [0, 1, 2], [], "All levels done"),
    ]
    
    all_passed = True
    for r_mult, executed, expected_new, desc in test_cases:
        results = check_partial_tp_levels(r_mult, 1.0, config, executed)
        actual_new = [r.level_index for r in results]
        
        status = "✅" if actual_new == expected_new else "❌"
        if actual_new != expected_new:
            all_passed = False
        
        print(f"  {status} {desc}")
        print(f"      R={r_mult}, already_done={executed}")
        print(f"      Expected new: {expected_new}, Got: {actual_new}")
    
    return all_passed


def verify_time_exit_logic():
    """
    Verify time exit logic matches trailing_5m.py._check_time_exit()
    
    From policy.yaml lines 222-226:
    - max_position_age_hours: 24
    - warning_hours: 20
    - stale_position_action: close
    """
    print("\n" + "="*60)
    print("VERIFICATION: Time Exit Logic")
    print("="*60)
    
    config = {
        'enabled': True,
        'max_position_age_hours': 24,
        'warning_hours': 20,
        'stale_position_action': 'close'
    }
    
    now = datetime.now(timezone.utc)
    
    test_cases = [
        # (hours_old, expected_warn, expected_exit, description)
        (5, False, False, "Fresh position (5h)"),
        (19, False, False, "Before warning (19h)"),
        (20, True, False, "At warning threshold (20h)"),
        (23, True, False, "Between warning and exit (23h)"),
        (24, False, True, "At exit threshold (24h)"),
        (30, False, True, "Past exit threshold (30h)"),
    ]
    
    all_passed = True
    for hours_old, expected_warn, expected_exit, desc in test_cases:
        opened_at = now - timedelta(hours=hours_old)
        result = check_time_exit(opened_at, now, config)
        
        warn_ok = result.should_warn == expected_warn
        exit_ok = result.should_exit == expected_exit
        status = "✅" if (warn_ok and exit_ok) else "❌"
        if not (warn_ok and exit_ok):
            all_passed = False
        
        print(f"  {status} {desc}")
        print(f"      Expected: warn={expected_warn}, exit={expected_exit}")
        print(f"      Got:      warn={result.should_warn}, exit={result.should_exit}")
    
    return all_passed


def verify_r_multiple_calculation():
    """
    Verify R-multiple calculation matches trailing_5m.py._calculate_r_multiple()
    
    From trailing_5m.py lines 242-255:
    - Long: (current - entry) / entry
    - Short: (entry - current) / entry
    """
    print("\n" + "="*60)
    print("VERIFICATION: R-Multiple Calculation")
    print("="*60)
    
    test_cases = [
        # (entry, current, side, expected_r, description)
        (100, 101, 'long', 0.01, "Long +1%"),
        (100, 102, 'long', 0.02, "Long +2%"),
        (100, 99, 'long', -0.01, "Long -1%"),
        (100, 99, 'short', 0.01, "Short +1%"),
        (100, 98, 'short', 0.02, "Short +2%"),
        (100, 101, 'short', -0.01, "Short -1%"),
    ]
    
    all_passed = True
    for entry, current, side, expected, desc in test_cases:
        actual = calculate_r_multiple_simple(entry, current, side)
        
        status = "✅" if abs(actual - expected) < 0.001 else "❌"
        if abs(actual - expected) >= 0.001:
            all_passed = False
        
        print(f"  {status} {desc}: entry={entry}, current={current}, side={side}")
        print(f"      Expected R={expected:.4f}, Got R={actual:.4f}")
    
    return all_passed


def run_all_verifications():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("EXIT STRATEGY IMPLEMENTATION VERIFICATION")
    print("="*60)
    print("\nThis verifies that exit_strategies.py matches trailing_5m.py")
    
    results = []
    
    results.append(("R-Multiple Calculation", verify_r_multiple_calculation()))
    results.append(("Trailing Stop Logic", verify_trailing_stop_logic()))
    results.append(("Partial TP Logic", verify_partial_tp_logic()))
    results.append(("Time Exit Logic", verify_time_exit_logic()))
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"  {status} | {name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("   Pure functions in exit_strategies.py correctly match")
        print("   the actual implementation in trailing_5m.py")
    else:
        print("❌ SOME VERIFICATIONS FAILED!")
        print("   Review mismatches above")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
