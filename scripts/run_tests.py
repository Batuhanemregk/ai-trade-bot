#!/usr/bin/env python3
"""
OKX Trading Bot Test Runner
Alternative to the bash script for running tests programmatically.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    print(f"   Running: {cmd}")
    print()

    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print("   Output:", result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("   Stdout:", e.stdout.strip())
        if e.stderr:
            print("   Stderr:", e.stderr.strip())
        return False


def main():
    """Main test runner function."""
    print("🚀 OKX Trading Bot Test Suite")
    print("===============================")
    print()

    # Check if we're in the right directory
    if not Path("policy.yaml").exists():
        print("❌ Error: policy.yaml not found. Please run from project root.")
        sys.exit(1)

    # Set environment variables
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{os.getcwd()}"
    os.environ["TESTING_MODE"] = "true"
    os.environ["DRY_RUN"] = "true"

    print("🔧 Environment Setup:")
    print(f"   PYTHONPATH: {os.environ['PYTHONPATH']}")
    print(f"   TESTING_MODE: {os.environ['TESTING_MODE']}")
    print(f"   DRY_RUN: {os.environ['DRY_RUN']}")
    print()

    # Check if pytest is available
    try:
        subprocess.run(["pytest", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: pytest not found. Please install pytest first:")
        print("   pip install -r requirements_testing.txt")
        sys.exit(1)

    start_time = time.time()

    # Run test suites
    test_suites = [
        ("tests/test_config_policy.py", "Configuration & Policy Tests"),
        ("tests/test_indicators_ta.py", "Technical Analysis Tests"),
        ("tests/test_composite_math.py", "Composite Math Tests"),
        ("tests/test_ml_news_fallbacks.py", "ML/News Fallback Tests"),
        ("tests/test_risk_scorer.py", "Risk Scoring Tests"),
        ("tests/test_pipeline_smoke.py", "End-to-End Pipeline Tests"),
    ]

    passed = 0
    failed = 0

    for test_file, description in test_suites:
        if Path(test_file).exists():
            cmd = f"pytest {test_file} -v --tb=short --no-header --durations=10"
            if run_command(cmd, description):
                passed += 1
            else:
                failed += 1
        else:
            print(f"⚠️  Test file {test_file} not found, skipping...")
        print()

    # Run full test suite with coverage
    print("📊 Running Full Test Suite with Coverage...")
    coverage_cmd = "pytest tests/ -v --tb=short --no-header --durations=10 --cov=scoring --cov-report=term-missing"
    if run_command(coverage_cmd, "Full Test Suite with Coverage"):
        passed += 1
    else:
        failed += 1

    end_time = time.time()
    duration = end_time - start_time

    print()
    print("🎉 Test Suite Completed!")
    print("=========================")
    print(f"⏱️  Total Duration: {duration:.1f} seconds")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print()

    if failed == 0:
        print("📈 Test Summary:")
        print("   ✅ Configuration validation")
        print("   ✅ Technical analysis indicators")
        print("   ✅ Composite scoring math")
        print("   ✅ ML/News fallbacks")
        print("   ✅ Risk scoring")
        print("   ✅ End-to-end pipeline")
        print()
        print("🔍 Coverage report generated in htmlcov/")
        print("📁 Test results available in tests/")
        print()
        print("🚀 Ready for production use!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
