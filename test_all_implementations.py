#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Implementations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import subprocess
import time
from datetime import datetime

def run_test_script(script_name, description):
    """Run a test script and return results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"PASS - {description}")
            print(f"Duration: {duration:.2f}s")
            return True, duration
        else:
            print(f"FAIL - {description}")
            print(f"Return code: {result.returncode}")
            print(f"Duration: {duration:.2f}s")
            if result.stderr:
                print(f"Error output: {result.stderr[:500]}...")
            return False, duration
            
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT - {description} (60s timeout)")
        return False, 60.0
    except Exception as e:
        print(f"ERROR - {description}: {e}")
        return False, 0.0

def main():
    """Run comprehensive test suite."""
    print("Comprehensive Test Suite for All Implementations")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Test scripts and descriptions
    test_suite = [
        ("test_confidence_position_sizing.py", "Confidence-aware Position Sizing"),
        ("test_hysteresis_simple.py", "Enhanced Hysteresis Micro-adjustment"),
        ("test_regime_adaptive_weights.py", "Regime-Adaptive Weights"),
        ("test_news_ttl_dynamic_weight.py", "News TTL Dynamic Weight"),
        ("test_ta_active_features_expansion.py", "TA Active Features Expansion"),
    ]
    
    # Results tracking
    results = []
    total_tests = len(test_suite)
    passed_tests = 0
    total_duration = 0.0
    
    print(f"\nRunning {total_tests} test suites...")
    
    for script_name, description in test_suite:
        # Check if script exists
        if not os.path.exists(script_name):
            print(f"WARNING - Script not found: {script_name}")
            results.append((description, False, 0.0, "Script not found"))
            continue
        
        # Run the test
        success, duration = run_test_script(script_name, description)
        results.append((description, success, duration, ""))
        
        if success:
            passed_tests += 1
        total_duration += duration
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUITE SUMMARY")
    print(f"{'='*80}")
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Average Duration: {total_duration/total_tests:.2f}s per test")
    
    print(f"\nDETAILED RESULTS:")
    print(f"{'='*80}")
    
    for i, (description, success, duration, error) in enumerate(results, 1):
        status = "PASS" if success else "FAIL"
        print(f"{i:2d}. {status} {description:35s} ({duration:6.2f}s)")
        if error:
            print(f"     Error: {error}")
    
    # Final assessment
    print(f"\n{'='*80}")
    if passed_tests == total_tests:
        print("ALL TESTS PASSED! All implementations are working correctly.")
        print("System is ready for production deployment!")
        return 0
    else:
        print(f"{total_tests - passed_tests} test(s) failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    exit(main())
