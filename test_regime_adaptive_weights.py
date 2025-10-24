#!/usr/bin/env python3
"""
Test Regime-Adaptive Weights Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infrastructure.runtime import _calculate_regime_adaptive_weights

def test_regime_detection():
    """Test regime detection logic."""
    print("Testing Regime Detection")
    print("=" * 40)
    
    # Test scenarios: (ta_score, risk_score, expected_regime, description)
    test_scenarios = [
        # Trend↑/Vol↓ regime
        (80, 20, "trend_vol", "Strong trend, low risk"),
        (70, 30, "trend_vol", "Good trend, low risk"),
        (65, 25, "trend_vol", "Moderate trend, low risk"),
        
        # Yanal/Vol↑ regime
        (50, 50, "sideways_vol", "Neutral trend, medium risk"),
        (40, 60, "sideways_vol", "Weak trend, high risk"),
        (30, 70, "sideways_vol", "Poor trend, high risk"),
        (60, 40, "sideways_vol", "Good trend but high risk"),
    ]
    
    passed = 0
    for ta_score, risk_score, expected_regime, description in test_scenarios:
        weights = _calculate_regime_adaptive_weights(ta_score, risk_score)
        
        # Determine actual regime based on weights
        if weights['ta'] > 0.4:  # High TA weight indicates trend regime
            actual_regime = "trend_vol"
        else:  # Low TA weight indicates sideways regime
            actual_regime = "sideways_vol"
        
        status = "PASS" if actual_regime == expected_regime else "FAIL"
        print(f"{status} TA:{ta_score:2d} Risk:{risk_score:2d} -> {actual_regime:12s} ({description})")
        print(f"      Weights: TA={weights['ta']:.2f} ML={weights['ml']:.2f} News={weights['news']:.2f} Risk={weights['risk']:.2f}")
        
        if actual_regime == expected_regime:
            passed += 1
    
    print(f"\nResults: {passed}/{len(test_scenarios)} passed")
    return passed == len(test_scenarios)

def test_weight_adaptation():
    """Test weight adaptation in different regimes."""
    print("\nTesting Weight Adaptation")
    print("=" * 40)
    
    # Test trend regime (should emphasize TA)
    trend_weights = _calculate_regime_adaptive_weights(80, 20)
    print("Trend Regime (TA:80, Risk:20):")
    print(f"  TA: {trend_weights['ta']:.2f} (should be > 0.4)")
    print(f"  ML: {trend_weights['ml']:.2f} (should be < 0.3)")
    print(f"  News: {trend_weights['news']:.2f}")
    print(f"  Risk: {trend_weights['risk']:.2f}")
    
    trend_ta_ok = trend_weights['ta'] > 0.4
    trend_ml_ok = trend_weights['ml'] < 0.3
    print(f"  Trend regime check: {'PASS' if trend_ta_ok and trend_ml_ok else 'FAIL'}")
    
    # Test sideways regime (should emphasize ML and Risk)
    sideways_weights = _calculate_regime_adaptive_weights(50, 60)
    print("\nSideways Regime (TA:50, Risk:60):")
    print(f"  TA: {sideways_weights['ta']:.2f} (should be < 0.4)")
    print(f"  ML: {sideways_weights['ml']:.2f} (should be > 0.3)")
    print(f"  News: {sideways_weights['news']:.2f}")
    print(f"  Risk: {sideways_weights['risk']:.2f}")
    
    sideways_ta_ok = sideways_weights['ta'] < 0.4
    sideways_ml_ok = sideways_weights['ml'] > 0.3
    print(f"  Sideways regime check: {'PASS' if sideways_ta_ok and sideways_ml_ok else 'FAIL'}")
    
    return trend_ta_ok and trend_ml_ok and sideways_ta_ok and sideways_ml_ok

def test_weight_sum():
    """Test that weights sum to 1.0."""
    print("\nTesting Weight Sum")
    print("=" * 40)
    
    test_cases = [
        (90, 10),  # Strong trend, low risk
        (70, 30),  # Good trend, low risk
        (50, 50),  # Neutral
        (30, 70),  # Weak trend, high risk
        (10, 90),  # Poor trend, high risk
    ]
    
    passed = 0
    for ta_score, risk_score in test_cases:
        weights = _calculate_regime_adaptive_weights(ta_score, risk_score)
        weight_sum = sum(weights.values())
        
        status = "PASS" if abs(weight_sum - 1.0) < 0.001 else "FAIL"
        print(f"{status} TA:{ta_score:2d} Risk:{risk_score:2d} -> Sum: {weight_sum:.3f}")
        
        if abs(weight_sum - 1.0) < 0.001:
            passed += 1
    
    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_edge_cases():
    """Test edge cases."""
    print("\nTesting Edge Cases")
    print("=" * 40)
    
    edge_cases = [
        (100, 0),   # Maximum trend, minimum risk
        (0, 100),   # Minimum trend, maximum risk
        (60, 30),   # Boundary case for trend regime
        (59, 31),   # Just below trend threshold
    ]
    
    passed = 0
    for ta_score, risk_score in edge_cases:
        try:
            weights = _calculate_regime_adaptive_weights(ta_score, risk_score)
            weight_sum = sum(weights.values())
            
            # Check if weights are valid
            valid = (
                0 <= weights['ta'] <= 1 and
                0 <= weights['ml'] <= 1 and
                0 <= weights['news'] <= 1 and
                0 <= weights['risk'] <= 1 and
                abs(weight_sum - 1.0) < 0.001
            )
            
            status = "PASS" if valid else "FAIL"
            print(f"{status} TA:{ta_score:3d} Risk:{risk_score:3d} -> Valid: {valid}")
            
            if valid:
                passed += 1
                
        except Exception as e:
            print(f"FAIL TA:{ta_score:3d} Risk:{risk_score:3d} -> Exception: {e}")
    
    print(f"\nResults: {passed}/{len(edge_cases)} passed")
    return passed == len(edge_cases)

def test_performance():
    """Test performance impact."""
    print("\nTesting Performance")
    print("=" * 40)
    
    import time
    
    iterations = 10000
    test_scores = [(80, 20), (50, 50), (30, 70)]
    
    start_time = time.time()
    for _ in range(iterations):
        for ta_score, risk_score in test_scores:
            _calculate_regime_adaptive_weights(ta_score, risk_score)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / (iterations * len(test_scores))
    
    print(f"Iterations: {iterations:,}")
    print(f"Total time: {total_time:.4f}s")
    print(f"Average time per call: {avg_time*1000:.4f}ms")
    print(f"Performance: {'PASS' if avg_time < 0.001 else 'FAIL'} (< 1ms per call)")
    
    return avg_time < 0.001

def main():
    """Run all regime-adaptive weight tests."""
    print("Regime-Adaptive Weights Tests")
    print("=" * 50)
    
    try:
        test1 = test_regime_detection()
        test2 = test_weight_adaptation()
        test3 = test_weight_sum()
        test4 = test_edge_cases()
        test5 = test_performance()
        
        if all([test1, test2, test3, test4, test5]):
            print("\nPASS - All regime-adaptive weight tests passed!")
            print("Regime-adaptive weights are ready for production!")
            print("Benefits: Adaptive to market conditions, better signal quality")
            return 0
        else:
            print("\nFAIL - Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\nFAIL - Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
