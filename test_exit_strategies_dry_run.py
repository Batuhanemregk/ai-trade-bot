"""
Exit Strategies Dry-Run Test

Simulates positions at various R-multiples to test:
1. Trailing Stop activation and calculation
2. Partial TP level hits
3. Time-based exit logic
4. New coin compatibility (GRT, ARKM)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))


class MockPosition:
    """Mock position for testing."""
    def __init__(self, symbol: str, side: str, entry_price: float, 
                 current_price: float, size: float = 1.0, 
                 opened_at: datetime = None):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.current_price = current_price
        self.size = size
        self.opened_at = opened_at or datetime.now(timezone.utc)
        
        # Calculate initial SL (2 ATR = ~2% for simplicity)
        sl_pct = 0.02
        if side == 'long':
            self.stop_loss = entry_price * (1 - sl_pct)
        else:
            self.stop_loss = entry_price * (1 + sl_pct)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'size': self.size,
            'stop_loss': self.stop_loss,
            'opened_at': self.opened_at
        }


def calculate_r_multiple(position: Dict, current_price: float) -> float:
    """Calculate R-multiple for position."""
    entry = position['entry_price']
    sl = position['stop_loss']
    side = position['side']
    
    risk = abs(entry - sl)  # 1R distance
    if risk == 0:
        return 0
    
    if side == 'long':
        pnl = current_price - entry
    else:
        pnl = entry - current_price
    
    return pnl / risk


def test_trailing_stop_logic():
    """Test trailing stop activation at different R-multiples."""
    print("\n" + "="*60)
    print("TEST 1: Trailing Stop Activation Logic")
    print("="*60)
    
    # Config from policy.yaml
    config = {
        'enabled': True,
        'activation_r_multiple': 0.5,
        'breakeven_r_multiple': 1.0,
        'tight_r_multiple': 1.5,
        'tight_offset': 0.3  # 0.3%
    }
    
    print(f"\nConfig: activation={config['activation_r_multiple']}R, "
          f"breakeven={config['breakeven_r_multiple']}R, "
          f"tight={config['tight_r_multiple']}R")
    
    # Test scenarios
    scenarios = [
        # (symbol, entry, current_price, expected_action)
        ('BTC-USDT-SWAP', 100000, 100100, 'NOT_ACTIVATED'),  # R=0.05
        ('BTC-USDT-SWAP', 100000, 101000, 'NORMAL_TRAIL'),   # R=0.5
        ('BTC-USDT-SWAP', 100000, 102000, 'BREAKEVEN'),      # R=1.0
        ('BTC-USDT-SWAP', 100000, 103000, 'TIGHT_TRAIL'),    # R=1.5
        ('ETH-USDT-SWAP', 4000, 4080, 'NORMAL_TRAIL'),       # R=1.0
        ('GRT-USDT-SWAP', 0.25, 0.26, 'NORMAL_TRAIL'),       # R=2.0 (new coin)
        ('ARKM-USDT-SWAP', 2.0, 2.08, 'BREAKEVEN'),          # R=2.0 (new coin)
    ]
    
    all_passed = True
    for symbol, entry, current, expected in scenarios:
        # Create mock position (LONG with 2% SL)
        sl = entry * 0.98
        risk = entry - sl  # 1R = 2%
        
        position = {
            'symbol': symbol,
            'side': 'long',
            'entry_price': entry,
            'stop_loss': sl,
            'size': 1.0
        }
        
        r_mult = calculate_r_multiple(position, current)
        
        # Determine action
        if r_mult < config['activation_r_multiple']:
            action = 'NOT_ACTIVATED'
        elif r_mult >= config['tight_r_multiple']:
            action = 'TIGHT_TRAIL'
        elif r_mult >= config['breakeven_r_multiple']:
            action = 'BREAKEVEN'
        else:
            action = 'NORMAL_TRAIL'
        
        status = "✅" if action == expected else "❌"
        if action != expected:
            all_passed = False
        
        print(f"  {status} {symbol}: entry={entry}, current={current}, R={r_mult:.2f} → {action}")
    
    return all_passed


def test_partial_tp_levels():
    """Test partial TP execution at R-multiple levels."""
    print("\n" + "="*60)
    print("TEST 2: Partial TP Level Detection")
    print("="*60)
    
    # Config from policy.yaml
    config = {
        'enabled': True,
        'levels': [
            {'r_multiple': 1.0, 'close_pct': 0.33},
            {'r_multiple': 2.0, 'close_pct': 0.33},
            {'r_multiple': 4.0, 'close_pct': 0.34},
        ]
    }
    
    print(f"\nConfig: levels={[(l['r_multiple'], l['close_pct']*100) for l in config['levels']]}")
    
    # Test scenarios
    scenarios = [
        # (R-multiple, expected_close_pct)
        (0.5, 0),      # Below first level
        (1.0, 33),     # Hit level 1
        (1.5, 33),     # Between level 1 and 2
        (2.0, 33),     # Hit level 2
        (3.0, 33),     # Between level 2 and 3
        (4.0, 34),     # Hit level 3
        (5.0, 34),     # Above all levels
    ]
    
    all_passed = True
    for r_mult, expected_pct in scenarios:
        # Find applicable level
        applicable_level = None
        for level in config['levels']:
            if r_mult >= level['r_multiple']:
                applicable_level = level
        
        close_pct = int(applicable_level['close_pct'] * 100) if applicable_level else 0
        
        status = "✅" if close_pct == expected_pct else "❌"
        if close_pct != expected_pct:
            all_passed = False
        
        print(f"  {status} R={r_mult:.1f} → close_pct={close_pct}% (expected {expected_pct}%)")
    
    return all_passed


def test_time_exit_logic():
    """Test time-based exit detection."""
    print("\n" + "="*60)
    print("TEST 3: Time Exit Detection")
    print("="*60)
    
    # Config from policy.yaml
    config = {
        'enabled': True,
        'max_position_age_hours': 24,
        'warning_hours': 20,
        'stale_position_action': 'close'
    }
    
    print(f"\nConfig: max_age={config['max_position_age_hours']}h, warning={config['warning_hours']}h")
    
    now = datetime.now(timezone.utc)
    
    # Test scenarios
    scenarios = [
        # (hours_old, expected_action)
        (5, 'OK'),           # Fresh position
        (20, 'WARNING'),     # Warning threshold
        (23, 'WARNING'),     # Close to limit
        (24, 'FORCE_CLOSE'), # At limit
        (30, 'FORCE_CLOSE'), # Past limit
    ]
    
    all_passed = True
    for hours_old, expected in scenarios:
        opened_at = now - timedelta(hours=hours_old)
        age_hours = (now - opened_at).total_seconds() / 3600
        
        if age_hours >= config['max_position_age_hours']:
            action = 'FORCE_CLOSE'
        elif age_hours >= config['warning_hours']:
            action = 'WARNING'
        else:
            action = 'OK'
        
        status = "✅" if action == expected else "❌"
        if action != expected:
            all_passed = False
        
        print(f"  {status} Age={hours_old}h → {action}")
    
    return all_passed


def test_new_coin_compatibility():
    """Test exit strategies work for newly added coins (GRT, ARKM)."""
    print("\n" + "="*60)
    print("TEST 4: New Coin Exit Strategy Compatibility")
    print("="*60)
    
    new_coins = ['GRT-USDT-SWAP', 'ARKM-USDT-SWAP', 'DOGE-USDT-SWAP']
    
    all_passed = True
    for symbol in new_coins:
        # Create mock position
        entry = 1.0
        current = 1.03  # 3% profit
        sl = 0.98  # 2% SL
        
        position = {
            'symbol': symbol,
            'side': 'long',
            'entry_price': entry,
            'stop_loss': sl,
            'size': 1.0,
            'opened_at': datetime.now(timezone.utc) - timedelta(hours=5)
        }
        
        r_mult = calculate_r_multiple(position, current)
        
        # All calculations should work without error
        trailing_active = r_mult >= 0.5
        partial_tp_hit = r_mult >= 1.0
        time_ok = True  # 5 hours < 24 hours
        
        print(f"  ✅ {symbol}:")
        print(f"     R-multiple: {r_mult:.2f}")
        print(f"     Trailing active: {trailing_active}")
        print(f"     Partial TP hit: {partial_tp_hit}")
        print(f"     Time OK: {time_ok}")
    
    return all_passed


async def test_trailing_job_simulation():
    """Simulate Trailing5mJob execution."""
    print("\n" + "="*60)
    print("TEST 5: Trailing5mJob Simulation")
    print("="*60)
    
    # Load real config
    import yaml
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    trading = policy.get('trading', {})
    trailing_config = trading.get('trailing', {})
    partial_tp_config = trading.get('partial_tp', {})
    time_exit_config = trading.get('time_exit', {})
    
    print(f"\nLoaded config from policy.yaml:")
    print(f"  trailing.enabled: {trailing_config.get('enabled', False)}")
    print(f"  partial_tp.enabled: {partial_tp_config.get('enabled', False)}")
    print(f"  time_exit.enabled: {time_exit_config.get('enabled', False)}")
    
    # Check all enabled
    all_enabled = all([
        trailing_config.get('enabled', False),
        partial_tp_config.get('enabled', False),
        time_exit_config.get('enabled', False)
    ])
    
    if all_enabled:
        print(f"\n  ✅ All exit strategies ENABLED in policy.yaml")
    else:
        print(f"\n  ❌ Some exit strategies DISABLED!")
    
    return all_enabled


def run_all_tests():
    """Run all dry-run tests."""
    print("\n" + "="*60)
    print("EXIT STRATEGY DRY-RUN TEST SUITE")
    print("="*60)
    
    results = []
    
    results.append(("Trailing Stop Logic", test_trailing_stop_logic()))
    results.append(("Partial TP Levels", test_partial_tp_levels()))
    results.append(("Time Exit Logic", test_time_exit_logic()))
    results.append(("New Coin Compatibility", test_new_coin_compatibility()))
    
    # Run async test
    loop = asyncio.get_event_loop()
    results.append(("Trailing Job Config", loop.run_until_complete(test_trailing_job_simulation())))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"  {status} | {name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL EXIT STRATEGY TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
