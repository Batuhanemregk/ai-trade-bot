#!/usr/bin/env python3
"""
Comprehensive Test Runner for AiBotBS
Executes all test categories with detailed reporting and analysis.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import argparse
from dataclasses import dataclass, asdict

from loguru import logger


@dataclass
class TestResult:
    """Test result data structure."""
    category: str
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP", "ERROR"
    duration: float
    coverage: Optional[float] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = None


@dataclass
class TestSuite:
    """Test suite configuration."""
    name: str
    path: str
    command: str
    timeout: int = 300
    required: bool = True
    environment: str = "test"


class ComprehensiveTestRunner:
    """Comprehensive test runner for AiBotBS system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results: List[TestResult] = []
        self.start_time = time.time()
        self.test_suites = self._initialize_test_suites()
        
        # Setup logging
        self._setup_logging()
        
        # Setup test environment
        self._setup_test_environment()
    
    def _setup_logging(self):
        """Setup test logging."""
        log_level = self.config.get('log_level', 'INFO')
        log_file = f"logs/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)
        
        logger.remove()
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> → <level>{message}</level>"
        )
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days"
        )
    
    def _setup_test_environment(self):
        """Setup test environment variables."""
        test_env = {
            'APP_ENV': 'test',
            'LOG_LEVEL': 'DEBUG',
            'OKX_SANDBOX': 'true',
            'OKX_TESTNET': 'true',
            'NEWS_VERBOSITY': 'full',
            'PYTHONPATH': str(Path.cwd()),
            'PYTHONUNBUFFERED': '1'
        }
        
        for key, value in test_env.items():
            os.environ[key] = value
        
        logger.info("✅ Test environment configured")
    
    def _initialize_test_suites(self) -> List[TestSuite]:
        """Initialize test suite configurations."""
        return [
            # Unit Tests
            TestSuite(
                name="Unit Tests - Scoring Services",
                path="tests/unit/test_scoring_services.py",
                command="python -m pytest tests/unit/test_scoring_services.py -v --cov=scoring --cov-report=term-missing",
                timeout=300
            ),
            TestSuite(
                name="Unit Tests - Data Services",
                path="tests/unit/test_data_services.py",
                command="python -m pytest tests/unit/test_data_services.py -v --cov=application --cov-report=term-missing",
                timeout=300
            ),
            TestSuite(
                name="Unit Tests - Log Services",
                path="tests/unit/test_log_services.py",
                command="python -m pytest tests/unit/test_log_services.py -v --cov=application --cov-report=term-missing",
                timeout=300
            ),
            
            # Integration Tests
            TestSuite(
                name="Integration Tests - Exchange APIs",
                path="tests/integration/test_exchange_integration.py",
                command="python -m pytest tests/integration/test_exchange_integration.py -v --env=testnet",
                timeout=600,
                environment="testnet"
            ),
            TestSuite(
                name="Integration Tests - News APIs",
                path="tests/integration/test_news_integration.py",
                command="python -m pytest tests/integration/test_news_integration.py -v --env=test",
                timeout=300
            ),
            TestSuite(
                name="Integration Tests - Telegram",
                path="tests/integration/test_telegram_integration.py",
                command="python -m pytest tests/integration/test_telegram_integration.py -v --env=test",
                timeout=300
            ),
            
            # Job Tests
            TestSuite(
                name="Job Tests - Trading Analysis",
                path="tests/jobs/test_trading_analysis_job.py",
                command="python -m pytest tests/jobs/test_trading_analysis_job.py -v --env=testnet",
                timeout=600,
                environment="testnet"
            ),
            TestSuite(
                name="Job Tests - Risk Monitor",
                path="tests/jobs/test_risk_monitor_job.py",
                command="python -m pytest tests/jobs/test_risk_monitor_job.py -v --env=testnet",
                timeout=300,
                environment="testnet"
            ),
            TestSuite(
                name="Job Tests - Scheduler",
                path="tests/jobs/test_scheduler.py",
                command="python -m pytest tests/jobs/test_scheduler.py -v --env=test",
                timeout=300
            ),
            
            # End-to-End Tests
            TestSuite(
                name="E2E Tests - Complete Trading Cycle",
                path="tests/e2e/test_complete_trading_cycle.py",
                command="python -m pytest tests/e2e/test_complete_trading_cycle.py -v --env=testnet",
                timeout=900,
                environment="testnet"
            ),
            TestSuite(
                name="E2E Tests - Multi-Symbol Processing",
                path="tests/e2e/test_multi_symbol_processing.py",
                command="python -m pytest tests/e2e/test_multi_symbol_processing.py -v --env=testnet",
                timeout=600,
                environment="testnet"
            ),
            
            # Performance Tests
            TestSuite(
                name="Performance Tests - Load Testing",
                path="tests/performance/test_load.py",
                command="python -m pytest tests/performance/test_load.py -v --env=testnet",
                timeout=1200,
                environment="testnet"
            ),
            TestSuite(
                name="Performance Tests - Memory Management",
                path="tests/performance/test_memory.py",
                command="python -m pytest tests/performance/test_memory.py -v --env=test",
                timeout=600
            ),
            
            # Security Tests
            TestSuite(
                name="Security Tests - API Keys",
                path="tests/security/test_api_security.py",
                command="python -m pytest tests/security/test_api_security.py -v --env=test",
                timeout=300
            ),
            TestSuite(
                name="Security Tests - Data Validation",
                path="tests/security/test_data_validation.py",
                command="python -m pytest tests/security/test_data_validation.py -v --env=test",
                timeout=300
            ),
            
            # Configuration Tests
            TestSuite(
                name="Config Tests - Policy Validation",
                path="tests/config/test_policy_validation.py",
                command="python -m pytest tests/config/test_policy_validation.py -v --env=test",
                timeout=300
            ),
            TestSuite(
                name="Config Tests - Environment",
                path="tests/config/test_environment.py",
                command="python -m pytest tests/config/test_environment.py -v --env=test",
                timeout=300
            )
        ]
    
    async def run_test_suite(self, suite: TestSuite) -> TestResult:
        """Run a single test suite."""
        logger.info(f"🧪 Running {suite.name}...")
        
        start_time = time.time()
        status = "PASS"
        error_message = None
        coverage = None
        
        try:
            # Check if test file exists
            if not Path(suite.path).exists():
                logger.warning(f"⚠️ Test file not found: {suite.path}")
                return TestResult(
                    category=suite.name,
                    test_name=suite.name,
                    status="SKIP",
                    duration=0.0,
                    error_message=f"Test file not found: {suite.path}"
                )
            
            # Run the test command
            result = subprocess.run(
                suite.command.split(),
                capture_output=True,
                text=True,
                timeout=suite.timeout,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ {suite.name} PASSED ({duration:.2f}s)")
                status = "PASS"
                
                # Extract coverage if available
                if "--cov" in suite.command and "TOTAL" in result.stdout:
                    for line in result.stdout.split('\n'):
                        if "TOTAL" in line and "%" in line:
                            try:
                                coverage = float(line.split()[-1].replace('%', ''))
                                break
                            except (ValueError, IndexError):
                                pass
            else:
                logger.error(f"❌ {suite.name} FAILED ({duration:.2f}s)")
                status = "FAIL"
                error_message = result.stderr or result.stdout
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"⏰ {suite.name} TIMEOUT ({duration:.2f}s)")
            status = "ERROR"
            error_message = f"Test timeout after {suite.timeout}s"
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 {suite.name} ERROR ({duration:.2f}s): {e}")
            status = "ERROR"
            error_message = str(e)
        
        return TestResult(
            category=suite.name,
            test_name=suite.name,
            status=status,
            duration=duration,
            coverage=coverage,
            error_message=error_message
        )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites."""
        logger.info("🚀 Starting comprehensive test suite...")
        
        total_suites = len(self.test_suites)
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        
        for i, suite in enumerate(self.test_suites, 1):
            logger.info(f"📊 Progress: {i}/{total_suites} - {suite.name}")
            
            result = await self.run_test_suite(suite)
            self.results.append(result)
            
            if result.status == "PASS":
                passed += 1
            elif result.status == "FAIL":
                failed += 1
            elif result.status == "SKIP":
                skipped += 1
            else:
                errors += 1
            
            # Small delay between test suites
            await asyncio.sleep(1)
        
        total_duration = time.time() - self.start_time
        
        # Generate summary
        summary = {
            "total_suites": total_suites,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "total_duration": total_duration,
            "success_rate": (passed / total_suites) * 100 if total_suites > 0 else 0,
            "results": [asdict(result) for result in self.results]
        }
        
        return summary
    
    def generate_report(self, summary: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("# AiBotBS Comprehensive Test Report")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## 📊 Test Summary")
        report.append(f"- **Total Suites:** {summary['total_suites']}")
        report.append(f"- **Passed:** {summary['passed']} ✅")
        report.append(f"- **Failed:** {summary['failed']} ❌")
        report.append(f"- **Skipped:** {summary['skipped']} ⏭️")
        report.append(f"- **Errors:** {summary['errors']} 💥")
        report.append(f"- **Success Rate:** {summary['success_rate']:.1f}%")
        report.append(f"- **Total Duration:** {summary['total_duration']:.2f}s")
        report.append("")
        
        # Detailed Results
        report.append("## 📋 Detailed Results")
        report.append("")
        
        for result in self.results:
            status_emoji = {
                "PASS": "✅",
                "FAIL": "❌",
                "SKIP": "⏭️",
                "ERROR": "💥"
            }.get(result.status, "❓")
            
            report.append(f"### {status_emoji} {result.category}")
            report.append(f"- **Status:** {result.status}")
            report.append(f"- **Duration:** {result.duration:.2f}s")
            if result.coverage:
                report.append(f"- **Coverage:** {result.coverage:.1f}%")
            if result.error_message:
                report.append(f"- **Error:** {result.error_message}")
            report.append("")
        
        # Recommendations
        report.append("## 🎯 Recommendations")
        report.append("")
        
        if summary['failed'] > 0 or summary['errors'] > 0:
            report.append("### Issues Found:")
            for result in self.results:
                if result.status in ["FAIL", "ERROR"]:
                    report.append(f"- **{result.category}:** {result.error_message}")
            report.append("")
        
        if summary['success_rate'] >= 90:
            report.append("🎉 **Excellent!** System is production-ready.")
        elif summary['success_rate'] >= 80:
            report.append("✅ **Good!** Minor issues need attention.")
        elif summary['success_rate'] >= 70:
            report.append("⚠️ **Fair.** Several issues need fixing.")
        else:
            report.append("❌ **Poor.** Major issues require immediate attention.")
        
        return "\n".join(report)
    
    def save_results(self, summary: Dict[str, Any], report: str):
        """Save test results to files."""
        # Save JSON results
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save markdown report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Results saved to {results_file}")
        logger.info(f"📄 Report saved to {report_file}")


async def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Comprehensive Test Runner for AiBotBS")
    parser.add_argument("--config", type=str, default="test_config.json", help="Test configuration file")
    parser.add_argument("--suite", type=str, help="Run specific test suite")
    parser.add_argument("--category", type=str, help="Run specific test category")
    parser.add_argument("--env", type=str, default="test", help="Test environment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        "log_level": "DEBUG" if args.verbose else "INFO",
        "environment": args.env,
        "timeout_multiplier": 1.0
    }
    
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            config.update(json.load(f))
    
    # Initialize test runner
    runner = ComprehensiveTestRunner(config)
    
    try:
        # Run tests
        summary = await runner.run_all_tests()
        
        # Generate report
        report = runner.generate_report(summary)
        
        # Save results
        runner.save_results(summary, report)
        
        # Print summary
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        # Exit with appropriate code
        if summary['failed'] > 0 or summary['errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

