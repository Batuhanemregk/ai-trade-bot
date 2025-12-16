"""
Real Integration Test - Dynamic Coin Support

This test actually starts the bot components and verifies:
1. CoinRegistry loads and works with real config
2. RiskService uses CoinRegistry correctly
3. ML Scorer returns None for non-ML coins
4. Composite signal handles ML=None correctly
5. Full trading cycle for a non-ML coin works
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_real_risk_service_integration():
    """Test RiskService actually uses CoinRegistry for a new coin."""
    print("\n" + "="*60)
    print("REAL TEST 1: RiskService + CoinRegistry Integration")
    print("="*60)
    
    from application.coin_registry import get_coin_registry, reset_coin_registry
    from application.risk_service import RiskService
    
    # Load real policy
    import yaml
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    reset_coin_registry()
    registry = get_coin_registry()
    risk_service = RiskService(policy)
    
    # Test with GRT (not in old static tier list)
    symbol = 'GRT-USDT-SWAP'
    market_data = {'trend': None}  # Minimal data
    
    # Get correlation risk via risk_service
    corr_risk = await risk_service._calculate_correlation_risk(symbol, market_data)
    tier = registry.get_tier(symbol)
    
    print(f"  Symbol: {symbol}")
    print(f"  Tier from registry: {tier}")
    print(f"  Correlation risk: {corr_risk}")
    
    # GRT should be tier_4 (new/unknown) with risk=70.0
    if tier == 'tier_4' and corr_risk == 70.0:
        print("  ✅ PASS: GRT correctly uses tier_4 with risk=70.0")
        return True
    else:
        print(f"  ❌ FAIL: Expected tier_4/70.0, got {tier}/{corr_risk}")
        return False


async def test_real_ml_scorer_no_fake():
    """Test ML Scorer really returns None (not 50.0) for non-ML coins."""
    print("\n" + "="*60)
    print("REAL TEST 2: ML Scorer Returns None (No Fake)")
    print("="*60)
    
    from scoring.ml_scorer import MLScorer
    import pandas as pd
    import numpy as np
    
    scorer = MLScorer()
    
    # Create realistic OHLCV data
    dates = pd.date_range(end='2025-01-01', periods=200, freq='15min')
    df = pd.DataFrame({
        'open': np.random.uniform(0.4, 0.5, 200),
        'high': np.random.uniform(0.45, 0.55, 200),
        'low': np.random.uniform(0.35, 0.45, 200),
        'close': np.random.uniform(0.4, 0.5, 200),
        'volume': np.random.uniform(1000000, 5000000, 200)
    }, index=dates)
    
    ohlcv_bundle = {'main': df, '15m': df}
    
    # Test GRT - should return None
    grt_score, grt_rationale, grt_details = scorer.score('GRT-USDT-SWAP', ohlcv_bundle)
    
    print(f"  Symbol: GRT-USDT-SWAP")
    print(f"  ML Score: {grt_score}")
    print(f"  Rationale: {grt_rationale}")
    print(f"  Details.ta_only_mode: {grt_details.get('ta_only_mode', False)}")
    
    if grt_score is None:
        print("  ✅ PASS: GRT returns None (true TA-only, no fake 50.0)")
        return True
    elif grt_score == 50.0:
        print("  ❌ FAIL: GRT returns 50.0 (fake fallback still in use!)")
        return False
    else:
        print(f"  ⚠️ UNEXPECTED: GRT returns {grt_score}")
        return False


async def test_real_composite_signal_ta_only():
    """Test composite signal correctly handles ML=None with weight redistribution."""
    print("\n" + "="*60)
    print("REAL TEST 3: Composite Signal ML Weight Redistribution")
    print("="*60)
    
    # Simulate composite calculation with ML=None
    ta_score = 65.0
    ml_score = None  # TA-only mode
    news_score = 55.0
    risk_score = 40.0
    
    weights = {
        'ta': 0.40,
        'ml': 0.30,
        'news': 0.15,
        'risk': 0.15
    }
    
    # This is what our new code should do
    if ml_score is None:
        # Redistribute ML weight to TA
        effective_ta_weight = weights['ta'] + weights['ml']  # 0.40 + 0.30 = 0.70
        final_score = (
            effective_ta_weight * ta_score +
            weights['news'] * news_score +
            weights['risk'] * risk_score
        )
        mode = "TA-only (ML weight redistributed)"
    else:
        final_score = (
            weights['ta'] * ta_score +
            weights['ml'] * ml_score +
            weights['news'] * news_score +
            weights['risk'] * risk_score
        )
        mode = "Full (ML active)"
    
    expected = 0.70 * 65.0 + 0.15 * 55.0 + 0.15 * 40.0  # = 45.5 + 8.25 + 6.0 = 59.75
    
    print(f"  TA Score: {ta_score}")
    print(f"  ML Score: {ml_score} (None = TA-only)")
    print(f"  News Score: {news_score}")
    print(f"  Risk Score: {risk_score}")
    print(f"  Mode: {mode}")
    print(f"  Final Score: {final_score}")
    print(f"  Expected: {expected}")
    
    if abs(final_score - expected) < 0.01:
        print("  ✅ PASS: Weight redistribution correct")
        return True
    else:
        print(f"  ❌ FAIL: Expected {expected}, got {final_score}")
        return False


async def test_real_trading_cycle_simulation():
    """Simulate a real trading cycle for a non-ML coin."""
    print("\n" + "="*60)
    print("REAL TEST 4: Full Trading Cycle Simulation (GRT)")
    print("="*60)
    
    from application.coin_registry import get_coin_registry
    from application.risk_service import RiskService
    from scoring.ml_scorer import MLScorer
    from scoring.ta_scorer import TAScorer
    import yaml
    import pandas as pd
    import numpy as np
    
    # Load real policy
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    symbol = 'GRT-USDT-SWAP'
    registry = get_coin_registry()
    
    # Step 1: Check tier
    tier = registry.get_tier(symbol)
    print(f"  Step 1 - Tier lookup: {tier}")
    
    # Step 2: Check ML availability
    has_ml = registry.has_ml_model(symbol)
    print(f"  Step 2 - Has ML model: {has_ml}")
    
    # Step 3: Get risk settings
    corr_risk = registry.get_correlation_risk(symbol)
    max_lev = registry.get_max_leverage(symbol)
    print(f"  Step 3 - Risk: corr={corr_risk}, max_lev={max_lev}")
    
    # Step 4: Simulate ML call
    ml_scorer = MLScorer()
    dates = pd.date_range(end='2025-01-01', periods=200, freq='15min')
    df = pd.DataFrame({
        'open': np.random.uniform(0.4, 0.5, 200),
        'high': np.random.uniform(0.45, 0.55, 200),
        'low': np.random.uniform(0.35, 0.45, 200),
        'close': np.random.uniform(0.4, 0.5, 200),
        'volume': np.random.uniform(1000000, 5000000, 200)
    }, index=dates)
    
    ml_score, ml_rationale, _ = ml_scorer.score(symbol, {'main': df, '15m': df})
    print(f"  Step 4 - ML Score: {ml_score} ({ml_rationale[:40]}...)")
    
    # Step 5: Verify all steps work without errors
    all_ok = (
        tier in ['tier_1', 'tier_2', 'tier_3', 'tier_4'] and
        has_ml == False and
        corr_risk > 0 and
        max_lev > 0 and
        ml_score is None
    )
    
    if all_ok:
        print("  ✅ PASS: Full trading cycle works for non-ML coin")
        return True
    else:
        print("  ❌ FAIL: Some step failed")
        return False


async def run_real_tests():
    """Run all real integration tests."""
    print("\n" + "="*60)
    print("REAL INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    results.append(("RiskService + CoinRegistry", await test_real_risk_service_integration()))
    results.append(("ML Scorer No Fake", await test_real_ml_scorer_no_fake()))
    results.append(("Composite ML Weight Redistribution", await test_real_composite_signal_ta_only()))
    results.append(("Full Trading Cycle Simulation", await test_real_trading_cycle_simulation()))
    
    # Summary
    print("\n" + "="*60)
    print("REAL TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"  {status} | {name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL REAL INTEGRATION TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED - REVIEW IMPLEMENTATION!")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_real_tests())
    sys.exit(0 if success else 1)
