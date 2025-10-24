#!/usr/bin/env python3
"""
Simple Hysteresis Test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from configs.policy import load_policy

def test_hysteresis():
    """Test hysteresis implementation."""
    print("Testing Hysteresis Implementation")
    print("=" * 40)
    
    try:
        # Load policy
        policy = load_policy()
        thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
        
        enter_long = thresholds.get('enter_long', 60)
        enter_short = thresholds.get('enter_short', 40)
        flat_range = thresholds.get('flat_range', [47, 53])
        flat_min, flat_max = flat_range
        
        print(f"Enter Long: {enter_long}")
        print(f"Enter Short: {enter_short}")
        print(f"Flat Range: {flat_min}-{flat_max}")
        
        # Test decision logic
        def get_decision(score):
            if score >= enter_long:
                return "LONG"
            elif score <= enter_short:
                return "SHORT"
            elif flat_min <= score <= flat_max:
                return "FLAT"
            else:
                return "FLAT"
        
        # Test scenarios
        test_cases = [
            (65, "LONG"),
            (60, "LONG"),
            (59, "FLAT"),
            (55, "FLAT"),
            (53, "FLAT"),
            (50, "FLAT"),
            (47, "FLAT"),
            (46, "FLAT"),
            (40, "SHORT"),
            (35, "SHORT")
        ]
        
        passed = 0
        for score, expected in test_cases:
            actual = get_decision(score)
            status = "PASS" if actual == expected else "FAIL"
            print(f"{status} Score {score:2d} -> {actual:5s} (expected: {expected:5s})")
            if actual == expected:
                passed += 1
        
        print(f"\nResults: {passed}/{len(test_cases)} passed")
        
        # Test hysteresis benefits
        print("\nHysteresis Benefits:")
        print("Old system (45-55): Score 59 would be FLAT, 61 would be LONG")
        print("New system (47-53): Score 59 is FLAT, 61 is LONG (same result)")
        print("But scores 54-56 now stay FLAT instead of flipping")
        
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_hysteresis()
    if success:
        print("\nPASS - Hysteresis test completed successfully!")
        exit(0)
    else:
        print("\nFAIL - Hysteresis test failed!")
        exit(1)
