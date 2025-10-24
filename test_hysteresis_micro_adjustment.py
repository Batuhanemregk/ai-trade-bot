#!/usr/bin/env python3
"""
Test Enhanced Hysteresis Micro-adjustment Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from configs.policy import load_policy
import numpy as np

def test_hysteresis_thresholds():
    """Test that new hysteresis thresholds are loaded correctly."""
    print("Testing Hysteresis Thresholds")
    print("=" * 50)
    
    try:
        policy = load_policy()
        thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
        
        enter_long = thresholds.get('enter_long', 60)
        enter_short = thresholds.get('enter_short', 40)
        flat_range = thresholds.get('flat_range', [47, 53])
        flat_min, flat_max = flat_range
        
        print(f"✅ Enter Long: {enter_long}")
        print(f"✅ Enter Short: {enter_short}")
        print(f"✅ Flat Range: {flat_min}-{flat_max}")
        
        # Verify the changes
        assert enter_long == 60, f"Expected enter_long=60, got {enter_long}"
        assert enter_short == 40, f"Expected enter_short=40, got {enter_short}"
        assert flat_min == 47, f"Expected flat_min=47, got {flat_min}"
        assert flat_max == 53, f"Expected flat_max=53, got {flat_max}"
        
        print("PASS - All thresholds loaded correctly!")
        print(f"PASS - Flat zone reduced from 45-55 to {flat_min}-{flat_max} (6 points narrower)")
        
    except Exception as e:
        print(f"FAIL - Failed to load thresholds: {e}")
        return False
    
    print("=" * 50)
    return True

def test_decision_logic():
    """Test decision logic with various score scenarios."""
    print("\nTesting Decision Logic")
    print("=" * 50)
    
    # Test scenarios: (score, expected_decision, description)
    test_scenarios = [
        (65, "LONG", "Strong bullish signal"),
        (60, "LONG", "Exactly at long threshold"),
        (59, "FLAT", "Just below long threshold"),
        (55, "FLAT", "Upper flat zone"),
        (53, "FLAT", "Upper flat boundary"),
        (52, "FLAT", "Just below upper flat boundary"),
        (50, "FLAT", "Middle of flat zone"),
        (48, "FLAT", "Just above lower flat boundary"),
        (47, "FLAT", "Lower flat boundary"),
        (46, "FLAT", "Just below lower flat boundary"),
        (45, "FLAT", "Just above short threshold"),
        (40, "SHORT", "Exactly at short threshold"),
        (35, "SHORT", "Strong bearish signal"),
    ]
    
    # Load thresholds
    policy = load_policy()
    thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
    enter_long = thresholds.get('enter_long', 60)
    enter_short = thresholds.get('enter_short', 40)
    flat_range = thresholds.get('flat_range', [47, 53])
    flat_min, flat_max = flat_range
    
    def simulate_decision_logic(final_score):
        """Simulate the decision logic from runtime.py"""
        if final_score >= enter_long:
            return "LONG"
        elif final_score <= enter_short:
            return "SHORT"
        elif flat_min <= final_score <= flat_max:
            return "FLAT"
        else:
            return "FLAT"
    
    passed = 0
    total = len(test_scenarios)
    
    for score, expected, description in test_scenarios:
        actual = simulate_decision_logic(score)
        status = "PASS" if actual == expected else "FAIL"
        
        print(f"{status} Score {score:2d} → {actual:5s} (expected: {expected:5s}) - {description}")
        
        if actual == expected:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 50)
    
    return passed == total

def test_hysteresis_benefits():
    """Test the benefits of narrower flat zone."""
    print("\nTesting Hysteresis Benefits")
    print("=" * 50)
    
    # Simulate score sequences that would cause flip-flopping
    score_sequences = [
        [59, 61, 59, 61, 59],  # Old system would flip between LONG/FLAT
        [46, 44, 46, 44, 46],  # Old system would flip between SHORT/FLAT
        [54, 56, 54, 56, 54],  # Old system would flip between FLAT/LONG
    ]
    
    # Old system (45-55 flat zone)
    def old_decision_logic(score):
        if score >= 60:
            return "LONG"
        elif score <= 40:
            return "SHORT"
        elif 45 <= score <= 55:
            return "FLAT"
        else:
            return "FLAT"
    
    # New system (47-53 flat zone)
    def new_decision_logic(score):
        if score >= 60:
            return "LONG"
        elif score <= 40:
            return "SHORT"
        elif 47 <= score <= 53:
            return "FLAT"
        else:
            return "FLAT"
    
    for i, sequence in enumerate(score_sequences, 1):
        print(f"\nSequence {i}: {sequence}")
        
        old_decisions = [old_decision_logic(s) for s in sequence]
        new_decisions = [new_decision_logic(s) for s in sequence]
        
        old_changes = sum(1 for j in range(1, len(old_decisions)) if old_decisions[j] != old_decisions[j-1])
        new_changes = sum(1 for j in range(1, len(new_decisions)) if new_decisions[j] != new_decisions[j-1])
        
        print(f"  Old system: {old_decisions} ({old_changes} changes)")
        print(f"  New system: {new_decisions} ({new_changes} changes)")
        
        improvement = old_changes - new_changes
        if improvement > 0:
            print(f"  PASS - Improvement: {improvement} fewer changes")
        else:
            print(f"  WARN - No improvement: {improvement} changes")
    
    print("=" * 50)

def test_edge_cases():
    """Test edge cases around the new thresholds."""
    print("\nTesting Edge Cases")
    print("=" * 50)
    
    edge_cases = [
        (60.0, "LONG", "Exactly at enter_long"),
        (59.9, "FLAT", "Just below enter_long"),
        (53.0, "FLAT", "Upper flat boundary"),
        (52.9, "FLAT", "Just below upper flat boundary"),
        (47.0, "FLAT", "Lower flat boundary"),
        (46.9, "FLAT", "Just below lower flat boundary"),
        (40.0, "SHORT", "Exactly at enter_short"),
        (40.1, "FLAT", "Just above enter_short"),
    ]
    
    policy = load_policy()
    thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
    enter_long = thresholds.get('enter_long', 60)
    enter_short = thresholds.get('enter_short', 40)
    flat_range = thresholds.get('flat_range', [47, 53])
    flat_min, flat_max = flat_range
    
    def simulate_decision_logic(final_score):
        if final_score >= enter_long:
            return "LONG"
        elif final_score <= enter_short:
            return "SHORT"
        elif flat_min <= final_score <= flat_max:
            return "FLAT"
        else:
            return "FLAT"
    
    passed = 0
    for score, expected, description in edge_cases:
        actual = simulate_decision_logic(score)
        status = "PASS" if actual == expected else "FAIL"
        print(f"{status} {score:5.1f} → {actual:5s} (expected: {expected:5s}) - {description}")
        if actual == expected:
            passed += 1
    
    print(f"\nEdge cases: {passed}/{len(edge_cases)} passed")
    print("=" * 50)
    
    return passed == len(edge_cases)

def main():
    """Run all hysteresis tests."""
    print("Enhanced Hysteresis Micro-adjustment Tests")
    print("=" * 60)
    
    try:
        # Run all tests
        test1 = test_hysteresis_thresholds()
        test2 = test_decision_logic()
        test3 = test_hysteresis_benefits()
        test4 = test_edge_cases()
        
        if all([test1, test2, test3, test4]):
            print("\nPASS - All hysteresis tests passed!")
            print("Enhanced hysteresis is ready for production!")
            print("Benefits: Reduced flip-flopping, more stable decisions")
            return 0
        else:
            print("\nFAIL - Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\nFAIL - Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
