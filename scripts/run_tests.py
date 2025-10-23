#!/usr/bin/env python3
"""
Simple Test Runner for AiBotBS
Executes tests with basic reporting.
"""

import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"Running {description}...")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{description} passed")
            return True
        else:
            print(f"{description} failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"{description} crashed: {e}")
        return False


def check_prerequisites():
    """Check if required tools are available."""
    print("Checking prerequisites...")
    
    # Check Python
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"Python found: {result.stdout.strip()}")
    except Exception as e:
        print(f"Python not found: {e}")
        return False
    
    # Check pytest
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"], capture_output=True, text=True)
        print(f"pytest found: {result.stdout.strip()}")
    except Exception as e:
        print("pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-cov", "pytest-mock"])
    
    return True


def setup_environment():
    """Setup test environment."""
    print("Setting up test environment...")
    
    # Create directories
    directories = ["logs", "test_reports"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Set environment variables
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["OKX_SANDBOX"] = "true"
    os.environ["OKX_TESTNET"] = "true"
    os.environ["NEWS_VERBOSITY"] = "full"
    os.environ["PYTHONPATH"] = str(Path.cwd())
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    print("Test environment setup complete")


def run_unit_tests():
    """Run unit tests (now real integration tests)."""
    print("Note: Unit tests are now real integration tests with actual data")
    cmd = f"{sys.executable} -m pytest tests/unit/ -v --tb=short --html=test_reports/unit_test_report.html --self-contained-html"
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run integration tests with real APIs and data."""
    print("Running real integration tests with live APIs...")
    cmd = f"{sys.executable} -m pytest tests/integration/ -v --tb=short --html=test_reports/integration_test_report.html --self-contained-html"
    return run_command(cmd, "Integration Tests")


def run_e2e_tests():
    """Run end-to-end tests with complete trading cycle."""
    print("Running real end-to-end trading cycle tests...")
    cmd = f"{sys.executable} -m pytest tests/e2e/ -v --tb=short --html=test_reports/e2e_test_report.html --self-contained-html"
    return run_command(cmd, "E2E Tests")


def run_performance_tests():
    """Run performance tests with real data loads."""
    print("Running performance tests with real data...")
    cmd = f"{sys.executable} -m pytest tests/performance/ -v --tb=short --html=test_reports/performance_test_report.html --self-contained-html"
    return run_command(cmd, "Performance Tests")


def generate_report(results):
    """Generate test report."""
    print("Generating test report...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"test_reports/test_summary_{timestamp}.md"
    
    report = f"""# AiBotBS Real Data Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Environment:** test
**Test Type:** Real data integration tests (no mocks)

## Test Summary

**Note:** All tests use real APIs and real market data. Tests may be skipped if APIs are unavailable.

"""
    
    total_passed = 0
    total_failed = 0
    
    for category, result in results.items():
        status = "PASS" if result["passed"] else "FAIL"
        duration = result["duration"]
        report += f"- **{category}**: {status} ({duration:.2f}s)\n"
        
        if result["passed"]:
            total_passed += 1
        else:
            total_failed += 1
    
    report += f"""
## Overall Results

- **Total Categories:** {len(results)}
- **Passed:** {total_passed}
- **Failed:** {total_failed}
- **Success Rate:** {(total_passed / len(results) * 100):.1f}%

## Generated Reports

- Unit Tests: test_reports/unit_test_report.html
- Integration Tests: test_reports/integration_test_report.html
- E2E Tests: test_reports/e2e_test_report.html
- Performance Tests: test_reports/performance_test_report.html

## Recommendations

"""
    
    if total_failed == 0:
        report += "**Excellent!** All real data tests passed. System is production-ready.\n"
    elif total_failed <= 2:
        report += "**Good!** Minor issues need attention. Some tests may have been skipped due to API unavailability.\n"
    else:
        report += "**Attention Required.** Several issues need fixing. Check API connectivity and configuration.\n"
    
    report += """
## Test Categories

- **Unit Tests**: Real integration tests with actual market data
- **Integration Tests**: Real API connectivity tests (OKX, News APIs)
- **E2E Tests**: Complete trading cycle with real data
- **Performance Tests**: Real data load and performance tests

## API Requirements

Tests require:
- OKX API keys (for exchange tests)
- OpenAI API key (for LLM tests)
- Internet connectivity (for news APIs)

Tests will be skipped if APIs are unavailable.
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Test report saved to: {report_file}")


def main():
    """Main test runner function."""
    print("AiBotBS Real Data Test Runner")
    print("=============================")
    print("Testing with real APIs and real market data (no mocks)")
    
    start_time = time.time()
    results = {}
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Setup environment
        setup_environment()
        
        # Run tests
        test_start = time.time()
        results["Unit Tests"] = {
            "passed": run_unit_tests(),
            "duration": time.time() - test_start
        }
        
        test_start = time.time()
        results["Integration Tests"] = {
            "passed": run_integration_tests(),
            "duration": time.time() - test_start
        }
        
        test_start = time.time()
        results["E2E Tests"] = {
            "passed": run_e2e_tests(),
            "duration": time.time() - test_start
        }
        
        test_start = time.time()
        results["Performance Tests"] = {
            "passed": run_performance_tests(),
            "duration": time.time() - test_start
        }
        
        # Generate report
        generate_report(results)
        
        # Final summary
        total_duration = time.time() - start_time
        passed_count = sum(1 for r in results.values() if r["passed"])
        total_count = len(results)
        
        print(f"\nTest Execution Complete!")
        print(f"========================")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Tests Passed: {passed_count}/{total_count}")
        print(f"Success Rate: {(passed_count / total_count * 100):.1f}%")
        
        if passed_count == total_count:
            print("All real data tests passed! System is ready for production.")
            sys.exit(0)
        else:
            print("Some tests failed or were skipped. Please review the reports.")
            print("Note: Tests may be skipped if APIs are unavailable.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()