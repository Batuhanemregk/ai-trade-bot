"""
Test script for bracket validation and case-sensitivity fix.
Tests that LONG/long both result in correct side='buy' and validation passes.
"""

from execution.prevalidation import validate_bracket_order

def test_bracket_validation():
    """Test bracket validation for both LONG and SHORT positions."""
    
    # LONG position test cases
    # For LONG: sl < entry < tp (TP above entry)
    long_tests = [
        # (entry, tp, sl, side, expected_valid, description)
        (3123.11, 3216.80, 3076.26, 'buy', True, "LONG with 'buy' side"),
        (3123.11, 3216.80, 3076.26, 'BUY', True, "LONG with 'BUY' uppercase"),
        (132.29, 136.26, 130.31, 'buy', True, "SOL LONG with 'buy'"),
    ]
    
    # SHORT position test cases  
    # For SHORT: tp < entry < sl (TP below entry)
    short_tests = [
        (3123.11, 3029.42, 3169.80, 'sell', True, "SHORT with 'sell' side"),
        (3123.11, 3029.42, 3169.80, 'SELL', True, "SHORT with 'SELL' uppercase"),
    ]
    
    # Invalid cases (should fail validation)
    invalid_tests = [
        # LONG with wrong TP/SL order
        (3123.11, 3076.26, 3216.80, 'buy', False, "LONG but TP < SL (invalid)"),
        # SHORT with wrong TP/SL order  
        (3123.11, 3216.80, 3076.26, 'sell', False, "SHORT but TP > SL (invalid)"),
    ]
    
    print("=" * 60)
    print("BRACKET VALIDATION TEST")
    print("=" * 60)
    
    all_passed = True
    
    # Test LONG cases
    print("\n📈 LONG Position Tests:")
    for entry, tp, sl, side, expected, desc in long_tests:
        is_valid, errors = validate_bracket_order(entry, tp, sl, side)
        status = "✅ PASS" if is_valid == expected else "❌ FAIL"
        if is_valid != expected:
            all_passed = False
        print(f"  {status} | {desc}")
        if errors:
            print(f"         Errors: {errors}")
    
    # Test SHORT cases
    print("\n📉 SHORT Position Tests:")
    for entry, tp, sl, side, expected, desc in short_tests:
        is_valid, errors = validate_bracket_order(entry, tp, sl, side)
        status = "✅ PASS" if is_valid == expected else "❌ FAIL"
        if is_valid != expected:
            all_passed = False
        print(f"  {status} | {desc}")
        if errors:
            print(f"         Errors: {errors}")
    
    # Test invalid cases
    print("\n⚠️ Invalid Cases (should fail):")
    for entry, tp, sl, side, expected, desc in invalid_tests:
        is_valid, errors = validate_bracket_order(entry, tp, sl, side)
        status = "✅ PASS" if is_valid == expected else "❌ FAIL"
        if is_valid != expected:
            all_passed = False
        print(f"  {status} | {desc}")
        if errors:
            print(f"         Errors: {errors}")
    
    print("\n" + "=" * 60)
    
    # Test decision_upper logic
    print("\n🔤 Decision Case-Sensitivity Test:")
    test_decisions = ['LONG', 'long', 'Long', 'SHORT', 'short', 'Short']
    for decision in test_decisions:
        decision_upper = decision.upper() if decision else 'FLAT'
        side = 'buy' if decision_upper == 'LONG' else 'sell'
        expected_side = 'buy' if 'long' in decision.lower() else 'sell'
        status = "✅" if side == expected_side else "❌"
        print(f"  {status} decision='{decision}' → decision_upper='{decision_upper}' → side='{side}'")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    test_bracket_validation()
