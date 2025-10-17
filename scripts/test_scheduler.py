#!/usr/bin/env python3
"""
Scheduler Test Utility
Quick tests for scheduler components
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from infrastructure.scheduler_runner import SchedulerRunner


async def test_initialization():
    """Test scheduler initialization."""
    print("\n[TEST] 1: Scheduler Initialization")
    print("=" * 60)
    
    try:
        runner = SchedulerRunner()
        await runner.initialize()
        
        print("[OK] Scheduler initialized successfully")
        print(f"   - Jobs loaded: {len(runner.jobs)}")
        print(f"   - State file: {runner.state_file}")
        print(f"   - Semaphore limit: {runner.semaphore._value}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        return False


async def test_jobs():
    """Test individual job loading."""
    print("\n[TEST] 2: Job Loading")
    print("=" * 60)
    
    try:
        runner = SchedulerRunner()
        await runner.initialize()
        
        expected_jobs = [
            'trading_analysis',
            'trailing_5m',
            'regime_1h',
            'risk_monitor',
            'market_overview',
            'news_incremental_5m',
            'telegram_summary_15m'
        ]
        
        for job_name in expected_jobs:
            if job_name in runner.jobs:
                print(f"   [OK] {job_name}")
            else:
                print(f"   [ERROR] {job_name} - MISSING!")
                return False
        
        print(f"\n[OK] All {len(expected_jobs)} jobs loaded successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Job loading failed: {e}")
        return False


async def test_single_job(job_name: str = 'market_overview'):
    """Test running a single job."""
    print(f"\n[TEST] 3: Single Job Execution ({job_name})")
    print("=" * 60)
    
    try:
        runner = SchedulerRunner()
        await runner.initialize()
        
        job = runner.jobs.get(job_name)
        if not job:
            print(f"[ERROR] Job '{job_name}' not found")
            return False
        
        print(f"   Executing {job_name}...")
        await job.execute()
        
        print(f"[OK] Job '{job_name}' executed successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Job execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_configuration():
    """Test policy configuration."""
    print("\n[TEST] 4: Configuration")
    print("=" * 60)
    
    try:
        from infrastructure.bootstrap import load_policy
        
        policy = load_policy()
        
        # Check essential keys
        checks = [
            ('schedule' in policy, "Schedule configuration"),
            ('scheduler' in policy, "Scheduler settings"),
            ('exchange' in policy, "Exchange configuration"),
            ('telegram' in policy, "Telegram configuration"),
            ('trading' in policy, "Trading configuration"),
        ]
        
        all_passed = True
        for check, description in checks:
            if check:
                print(f"   [OK] {description}")
            else:
                print(f"   [ERROR] {description} - MISSING!")
                all_passed = False
        
        # Check mode
        mode = policy.get('exchange', {}).get('mode', 'unknown')
        print(f"\n   [INFO] Exchange mode: {mode}")
        if mode == 'dry-run':
            print(f"   [SAFE] Running in DRY-RUN mode")
        elif mode == 'live':
            print(f"   [WARNING] Running in LIVE mode (real trading!)")
        
        if all_passed:
            print(f"\n[OK] Configuration valid")
        return all_passed
    except Exception as e:
        print(f"[ERROR] Configuration test failed: {e}")
        return False


async def test_state_persistence():
    """Test state save/load."""
    print("\n[TEST] 5: State Persistence")
    print("=" * 60)
    
    try:
        runner = SchedulerRunner()
        await runner.initialize()
        
        # Test state save
        runner.runtime_state['test_key'] = 'test_value'
        await runner._save_runtime_state()
        print("   [OK] State saved")
        
        # Test state load
        runner.runtime_state = {}
        await runner._load_runtime_state()
        
        if runner.runtime_state.get('test_key') == 'test_value':
            print("   [OK] State loaded correctly")
            return True
        else:
            print("   [ERROR] State not loaded correctly")
            return False
    except Exception as e:
        print(f"[ERROR] State persistence test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SCHEDULER TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Initialization", test_initialization),
        ("Job Loading", test_jobs),
        ("Configuration", test_configuration),
        ("State Persistence", test_state_persistence),
        ("Single Job", lambda: test_single_job('market_overview')),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"   {status}: {test_name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED! Scheduler is ready to run.")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} test(s) failed. Please fix issues before running.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

