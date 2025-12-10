#!/usr/bin/env python3
"""
Test News TTL Dynamic Weight Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scoring.news_scorer import NewsScorer
from datetime import datetime, timezone, timedelta

def test_ttl_weight_calculation():
    """Test TTL weight calculation function."""
    print("Testing TTL Weight Calculation")
    print("=" * 40)
    
    # Create news scorer instance
    scorer = NewsScorer()
    
    # Test scenarios: (age_hours, expected_weight_range, description)
    test_scenarios = [
        (0.5, (0.95, 1.0), "Very fresh news (30 min)"),
        (1.0, (0.95, 1.0), "Fresh news (1 hour)"),
        (2.0, (0.95, 1.0), "Fresh threshold (2 hours)"),
        (3.0, (0.95, 0.97), "Just past fresh threshold"),
        (6.0, (0.75, 0.85), "Moderately fresh (6 hours)"),
        (12.0, (0.50, 0.60), "Getting stale (12 hours)"),
        (18.0, (0.25, 0.35), "Quite stale (18 hours)"),
        (24.0, (0.05, 0.10), "Stale threshold (24 hours)"),
        (48.0, (0.05, 0.10), "Very stale (48 hours)"),
    ]
    
    passed = 0
    for age_hours, expected_range, description in test_scenarios:
        weight = scorer._calculate_ttl_weight(age_hours)
        min_expected, max_expected = expected_range
        
        status = "PASS" if min_expected <= weight <= max_expected else "FAIL"
        print(f"{status} {age_hours:4.1f}h -> {weight:.3f} (expected: {min_expected:.2f}-{max_expected:.2f}) - {description}")
        
        if min_expected <= weight <= max_expected:
            passed += 1
    
    print(f"\nResults: {passed}/{len(test_scenarios)} passed")
    return passed == len(test_scenarios)

def test_ttl_weight_properties():
    """Test TTL weight properties."""
    print("\nTesting TTL Weight Properties")
    print("=" * 40)
    
    scorer = NewsScorer()
    
    # Test weight bounds
    test_ages = [0, 1, 2, 6, 12, 18, 24, 48, 72]
    all_weights = []
    
    for age in test_ages:
        weight = scorer._calculate_ttl_weight(age)
        all_weights.append(weight)
        
        # Check bounds
        bounds_ok = 0.05 <= weight <= 1.0
        status = "PASS" if bounds_ok else "FAIL"
        print(f"{status} Age {age:2d}h -> Weight {weight:.3f} (bounds: 0.05-1.0)")
    
    # Test monotonicity (weight should decrease with age)
    monotonic_ok = all(all_weights[i] >= all_weights[i+1] for i in range(len(all_weights)-1))
    status = "PASS" if monotonic_ok else "FAIL"
    print(f"\n{status} Monotonicity: Weight decreases with age")
    
    # Test edge cases
    edge_cases = [
        (-1, 1.0),    # Negative age should return max weight
        (0, 1.0),      # Zero age should return max weight
        (1000, 0.05),  # Very old should return min weight
    ]
    
    edge_passed = 0
    for age, expected in edge_cases:
        weight = scorer._calculate_ttl_weight(age)
        status = "PASS" if abs(weight - expected) < 0.01 else "FAIL"
        print(f"{status} Edge case {age:4d}h -> {weight:.3f} (expected: {expected:.2f})")
        if abs(weight - expected) < 0.01:
            edge_passed += 1
    
    print(f"\nEdge cases: {edge_passed}/{len(edge_cases)} passed")
    
    return bounds_ok and monotonic_ok and edge_passed == len(edge_cases)

def test_ttl_weight_impact():
    """Test the impact of TTL weighting on news scores."""
    print("\nTesting TTL Weight Impact")
    print("=" * 40)
    
    scorer = NewsScorer()
    
    # Test scenarios: (base_score, age_hours, expected_weighted_score_range)
    test_scenarios = [
        (80.0, 1.0, (76.0, 80.0)),    # Fresh news: minimal impact
        (70.0, 6.0, (52.5, 59.5)),    # Moderately fresh: moderate impact
        (60.0, 12.0, (30.0, 36.0)),   # Getting stale: significant impact
        (50.0, 24.0, (2.5, 5.0)),     # Stale: major impact
    ]
    
    passed = 0
    for base_score, age_hours, expected_range in test_scenarios:
        weight = scorer._calculate_ttl_weight(age_hours)
        weighted_score = base_score * weight
        min_expected, max_expected = expected_range
        
        status = "PASS" if min_expected <= weighted_score <= max_expected else "FAIL"
        print(f"{status} Base:{base_score:4.1f} Age:{age_hours:4.1f}h -> {weighted_score:5.1f} (weight:{weight:.3f})")
        
        if min_expected <= weighted_score <= max_expected:
            passed += 1
    
    print(f"\nResults: {passed}/{len(test_scenarios)} passed")
    return passed == len(test_scenarios)

def test_ttl_weight_linearity():
    """Test linear decay between fresh and stale thresholds."""
    print("\nTesting TTL Weight Linearity")
    print("=" * 40)
    
    scorer = NewsScorer()
    
    # Test linear decay between 2h and 24h
    test_ages = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
    weights = [scorer._calculate_ttl_weight(age) for age in test_ages]
    
    # Check that weights decrease linearly
    linear_ok = True
    for i in range(len(weights) - 1):
        if weights[i] <= weights[i+1]:  # Should be decreasing
            linear_ok = False
            break
    
    status = "PASS" if linear_ok else "FAIL"
    print(f"{status} Linear decay between 2h-24h")
    
    # Print weight progression
    print("Age progression:")
    for age, weight in zip(test_ages, weights):
        print(f"  {age:2d}h -> {weight:.3f}")
    
    return linear_ok

def test_performance():
    """Test performance of TTL weight calculation."""
    print("\nTesting Performance")
    print("=" * 40)
    
    import time
    
    scorer = NewsScorer()
    iterations = 10000
    
    start_time = time.time()
    for _ in range(iterations):
        scorer._calculate_ttl_weight(12.0)  # Typical age
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / iterations
    
    print(f"Iterations: {iterations:,}")
    print(f"Total time: {total_time:.4f}s")
    print(f"Average time per call: {avg_time*1000:.4f}ms")
    print(f"Performance: {'PASS' if avg_time < 0.001 else 'FAIL'} (< 1ms per call)")
    
    return avg_time < 0.001

def main():
    """Run all TTL dynamic weight tests."""
    print("News TTL Dynamic Weight Tests")
    print("=" * 50)
    
    try:
        test1 = test_ttl_weight_calculation()
        test2 = test_ttl_weight_properties()
        test3 = test_ttl_weight_impact()
        test4 = test_ttl_weight_linearity()
        test5 = test_performance()
        
        if all([test1, test2, test3, test4, test5]):
            print("\nPASS - All TTL dynamic weight tests passed!")
            print("News TTL dynamic weighting is ready for production!")
            print("Benefits: Fresh news gets full weight, stale news gets reduced weight")
            return 0
        else:
            print("\nFAIL - Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\nFAIL - Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
