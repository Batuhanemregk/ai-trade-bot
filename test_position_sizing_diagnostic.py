"""
Position Size Diagnostic Script
Shows exactly where position size gets clipped at each step.
"""

import asyncio
import yaml
from pathlib import Path

def load_policy():
    """Load policy.yaml"""
    policy_path = Path("configs/policy.yaml")
    with open(policy_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def simulate_position_sizing(
    balance: float = 340.0,
    composite_score: float = 42.5,
    ml_score: float = 37.9,
    regime: str = "TRENDING"
):
    """
    Simulate the exact position sizing calculation from runtime.py
    with step-by-step output to find where clipping happens.
    """
    print("=" * 60)
    print("POSITION SIZE DIAGNOSTIC")
    print("=" * 60)
    print(f"\nInputs:")
    print(f"  Balance: ${balance:.2f}")
    print(f"  Composite Score: {composite_score}")
    print(f"  ML Score: {ml_score}")
    print(f"  Regime: {regime}")
    print()
    
    policy = load_policy()
    scoring = policy.get('trading', {}).get('scoring', {})
    sizing_config = scoring.get('position_sizing', {})
    scalable_config = scoring.get('scalable_sizing', {})
    
    # ============ STEP 1: SIGNAL STRENGTH ============
    print("-" * 60)
    print("STEP 1: Signal Strength Calculation")
    print("-" * 60)
    
    # Direction determination
    composite_dir = "SHORT" if composite_score < 48 else ("LONG" if composite_score > 52 else "NEUTRAL")
    ml_dir = "SHORT" if ml_score < 45 else ("LONG" if ml_score > 55 else "NEUTRAL")
    
    print(f"  Composite direction: {composite_dir} (score={composite_score})")
    print(f"  ML direction: {ml_dir} (score={ml_score})")
    
    # Strength calculation
    composite_strength = abs(composite_score - 50) / 50
    ml_strength = abs(ml_score - 50) / 50
    
    print(f"  Composite strength: {composite_strength:.3f}")
    print(f"  ML strength: {ml_strength:.3f}")
    
    # Agreement
    if composite_dir == ml_dir and composite_dir != "NEUTRAL":
        signal_strength = (composite_strength + ml_strength) / 2
        agreement = "AGREE"
    elif composite_dir == "NEUTRAL" or ml_dir == "NEUTRAL":
        signal_strength = max(composite_strength, ml_strength) * 0.7
        agreement = "PARTIAL"
    else:
        signal_strength = 0.15
        agreement = "CONFLICT"
    
    print(f"  Agreement: {agreement}")
    print(f"  >>> Final Signal Strength: {signal_strength:.3f}")
    
    # ============ STEP 2: TIER SELECTION ============
    print()
    print("-" * 60)
    print("STEP 2: Tier Selection")
    print("-" * 60)
    
    tiers = sizing_config.get('tiers', {})
    print(f"  Available tiers from policy.yaml:")
    for name, tier in tiers.items():
        print(f"    {name}: strength {tier.get('min_strength')}-{tier.get('max_strength')} → {tier.get('position_pct')*100:.1f}%")
    
    # Find matching tier
    position_pct = 0.02
    tier_name = "weak"
    
    for name, tier in tiers.items():
        min_s = tier.get('min_strength', 0)
        max_s = tier.get('max_strength', 1)
        if min_s <= signal_strength < max_s:
            position_pct = tier.get('position_pct', 0.02)
            tier_name = name
            break
    
    print(f"\n  Signal strength {signal_strength:.3f} matches: {tier_name}")
    print(f"  >>> Tier Position %: {position_pct*100:.1f}%")
    print(f"  >>> Position before clipping: ${balance * position_pct:.2f}")
    
    # ============ STEP 3: REGIME MULTIPLIER ============
    print()
    print("-" * 60)
    print("STEP 3: Regime Multiplier")
    print("-" * 60)
    
    regime_multiplier = sizing_config.get('regime_multiplier', 1.0)
    print(f"  Regime multiplier from policy: {regime_multiplier}")
    print(f"  Current regime: {regime}")
    
    # Apply regime multiplier only if not trending
    if regime != "TRENDING":
        position_pct_after_regime = position_pct * regime_multiplier
        print(f"  >>> Applied! {position_pct*100:.1f}% × {regime_multiplier} = {position_pct_after_regime*100:.1f}%")
        position_pct = position_pct_after_regime
    else:
        print(f"  >>> NOT applied (regime is TRENDING)")
    
    print(f"  >>> Position after regime: ${balance * position_pct:.2f}")
    
    # ============ STEP 4: SCALABLE SIZING ============
    print()
    print("-" * 60)
    print("STEP 4: Scalable Sizing (Dynamic Max)")
    print("-" * 60)
    
    enabled = scalable_config.get('enabled', True)
    dynamic = scalable_config.get('dynamic_sizing', True)
    max_portfolio_alloc = scalable_config.get('max_portfolio_allocation', 0.60)
    per_position_max = scalable_config.get('per_position_max', 0.10)
    
    trading_pairs = policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
    num_symbols = len(trading_pairs) if trading_pairs else 10
    
    print(f"  Scalable sizing enabled: {enabled}")
    print(f"  Dynamic sizing: {dynamic}")
    print(f"  Max portfolio allocation: {max_portfolio_alloc*100:.0f}%")
    print(f"  Per position max: {per_position_max*100:.0f}%")
    print(f"  Number of trading pairs: {num_symbols}")
    
    if enabled and dynamic:
        dynamic_max = min(per_position_max, max_portfolio_alloc / num_symbols)
        print(f"\n  Calculation: min({per_position_max*100:.0f}%, {max_portfolio_alloc*100:.0f}% / {num_symbols}) = {dynamic_max*100:.1f}%")
        
        if position_pct > dynamic_max:
            print(f"  >>> CLIPPED! {position_pct*100:.1f}% → {dynamic_max*100:.1f}%")
            position_pct = dynamic_max
        else:
            print(f"  >>> NOT clipped ({position_pct*100:.1f}% <= {dynamic_max*100:.1f}%)")
    
    print(f"  >>> Position after scalable: ${balance * position_pct:.2f}")
    
    # ============ STEP 5: MIN/MAX PERCENTAGE ============
    print()
    print("-" * 60)
    print("STEP 5: Min/Max Percentage Limits")
    print("-" * 60)
    
    min_pct = sizing_config.get('min_percentage', 0.02)
    max_pct = sizing_config.get('max_percentage', 0.15)
    
    print(f"  Min percentage: {min_pct*100:.1f}%")
    print(f"  Max percentage: {max_pct*100:.1f}%")
    
    if position_pct < min_pct:
        print(f"  >>> RAISED to minimum! {position_pct*100:.1f}% → {min_pct*100:.1f}%")
        position_pct = min_pct
    elif position_pct > max_pct:
        print(f"  >>> CAPPED to maximum! {position_pct*100:.1f}% → {max_pct*100:.1f}%")
        position_pct = max_pct
    else:
        print(f"  >>> No change needed")
    
    print(f"  >>> Position after min/max: ${balance * position_pct:.2f}")
    
    # ============ STEP 6: 90% BALANCE CAP ============
    print()
    print("-" * 60)
    print("STEP 6: 90% Balance Safety Cap")
    print("-" * 60)
    
    position_usdt = balance * position_pct
    max_balance_cap = balance * 0.90
    
    print(f"  Position USDT: ${position_usdt:.2f}")
    print(f"  90% of balance: ${max_balance_cap:.2f}")
    
    if position_usdt > max_balance_cap:
        print(f"  >>> CAPPED to 90%! ${position_usdt:.2f} → ${max_balance_cap:.2f}")
        position_usdt = max_balance_cap
    else:
        print(f"  >>> No change needed")
    
    # ============ FINAL RESULT ============
    print()
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"  Balance: ${balance:.2f}")
    print(f"  Final percentage: {position_pct*100:.2f}%")
    print(f"  >>> FINAL POSITION SIZE: ${position_usdt:.2f}")
    print("=" * 60)
    
    return position_usdt


if __name__ == "__main__":
    print("\n\n")
    print("TEST 1: Your current scenario (TA/ML around neutral)")
    print("=" * 60)
    simulate_position_sizing(
        balance=340.0,
        composite_score=42.5,
        ml_score=37.9,
        regime="RANGING"  # Not trending
    )
    
    print("\n\n")
    print("TEST 2: Same but with TRENDING regime")
    print("=" * 60)
    simulate_position_sizing(
        balance=340.0,
        composite_score=42.5,
        ml_score=37.9,
        regime="TRENDING"
    )
    
    print("\n\n")
    print("TEST 3: Strong signal (composite=70, ml=75)")
    print("=" * 60)
    simulate_position_sizing(
        balance=340.0,
        composite_score=70.0,
        ml_score=75.0,
        regime="TRENDING"
    )
