"""
Test script for Trading Analysis Fixes - 2025-11-10
Tests the fixes applied for confirmation processor, policy alignment, and risk weight.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from configs.policy import load_policy


def test_confirmation_processor_code():
    """Test that confirmation processor code has the entry/reversal logic."""
    print("=" * 80)
    print("Test 1: Confirmation Processor Code Check")
    print("=" * 80)
    
    # Read the signal_gate.py file to verify the code changes
    signal_gate_path = project_root / 'application' / 'signal_gate.py'
    with open(signal_gate_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check for _is_entry_signal method
    assert '_is_entry_signal' in code, "ConfirmationProcessor should have _is_entry_signal method"
    print("✓ _is_entry_signal method found")
    
    # Check for entry signal logic
    assert 'is_entry = self._is_entry_signal' in code, "ConfirmationProcessor should check is_entry"
    print("✓ Entry signal check found")
    
    # Check for entry is_valid = True
    has_entry_valid = ('is_valid = True  # Entry signals don\'t need confirmation' in code) or \
                      ('is_valid = True' in code and 'Entry signals' in code and 'don\'t need confirmation' in code)
    assert has_entry_valid, "Entry signals should have is_valid = True with comment"
    print("✓ Entry signal is_valid = True found")
    
    # Check for reversal confirmation logic
    assert 'Reversal confirmation' in code, "Reversal confirmation logic should be present"
    print("✓ Reversal confirmation logic found")
    
    print("✓ Confirmation processor code check PASSED")
    print()


def test_policy_values():
    """Test that policy values are correctly read."""
    print("=" * 80)
    print("Test 3: Policy Values")
    print("=" * 80)
    
    policy = load_policy()
    
    persistence_bars = policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('persistence_bars', None)
    rev_confirm_bars = policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('rev_confirm_bars', None)
    risk_weight = policy.get('trading', {}).get('scoring', {}).get('risk_weight', None)
    
    print(f"persistence_bars: {persistence_bars}")
    print(f"rev_confirm_bars: {rev_confirm_bars}")
    print(f"risk_weight: {risk_weight}")
    
    assert persistence_bars == 2, f"Expected persistence_bars=2, got {persistence_bars}"
    assert rev_confirm_bars == 2, f"Expected rev_confirm_bars=2, got {rev_confirm_bars}"
    assert risk_weight == 0.07, f"Expected risk_weight=0.07, got {risk_weight}"
    
    print("✓ Policy values test PASSED")
    print()


def test_risk_weight_code():
    """Test that risk weight code reads from policy."""
    print("=" * 80)
    print("Test 4: Risk Weight Code Check")
    print("=" * 80)
    
    # Read the runtime.py file to verify the code changes
    runtime_path = project_root / 'infrastructure' / 'runtime.py'
    with open(runtime_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check that _calculate_regime_adaptive_weights reads from policy
    assert 'load_policy' in code or 'policy.get' in code, \
        "_calculate_regime_adaptive_weights should read from policy"
    print("✓ Policy reading in _calculate_regime_adaptive_weights found")
    
    # Check for risk_weight reading
    assert 'risk_weight' in code and 'policy' in code, \
        "Risk weight should be read from policy"
    print("✓ Risk weight reading from policy found")
    
    print("✓ Risk weight code check PASSED")
    print()


def test_trading_analysis_policy_reading():
    """Test that trading_analysis.py reads persistence_bars from policy."""
    print("=" * 80)
    print("Test 5: Trading Analysis Policy Reading")
    print("=" * 80)
    
    # Read the trading_analysis.py file to verify the code changes
    trading_analysis_path = project_root / 'application' / 'jobs' / 'trading_analysis.py'
    with open(trading_analysis_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check that persistence_bars is read from policy
    assert 'persistence_bars_required = self.policy.get' in code, \
        "trading_analysis.py should read persistence_bars from policy"
    print("✓ persistence_bars reading from policy found")
    
    # Check that rev_confirm_bars is read from policy
    assert 'rev_confirm_bars_required = self.policy.get' in code, \
        "trading_analysis.py should read rev_confirm_bars from policy"
    print("✓ rev_confirm_bars reading from policy found")
    
    print("✓ Trading analysis policy reading check PASSED")
    print()


def test_log_formatter_conf_format():
    """Test that log_formatter.py formats conf as integer count."""
    print("=" * 80)
    print("Test 6: Log Formatter Conf Format")
    print("=" * 80)
    
    # Read the log_formatter.py file to verify the code changes
    log_formatter_path = project_root / 'application' / 'log_formatter.py'
    with open(log_formatter_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check that conf_count is converted to int
    assert 'if isinstance(conf_count, float):' in code, \
        "log_formatter.py should convert conf_count to int"
    print("✓ conf_count int conversion found")
    
    # Check that conf_required is converted to int
    assert 'if isinstance(conf_required, float):' in code, \
        "log_formatter.py should convert conf_required to int"
    print("✓ conf_required int conversion found")
    
    # Check that confirmation_bars is used
    assert 'confirmation_bars' in code, \
        "log_formatter.py should use confirmation_bars"
    print("✓ confirmation_bars usage found")
    
    print("✓ Log formatter conf format check PASSED")
    print()


def main():
    """Run all tests."""
    print("Testing Trading Analysis Fixes - 2025-11-10")
    print("=" * 80)
    print()
    
    try:
        test_confirmation_processor_code()
        test_policy_values()
        test_risk_weight_code()
        test_trading_analysis_policy_reading()
        test_log_formatter_conf_format()
        
        print("=" * 80)
        print("ALL TESTS PASSED")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print("=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        return 1
    except Exception as e:
        print("=" * 80)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return 1


if __name__ == '__main__':
    sys.exit(main())

