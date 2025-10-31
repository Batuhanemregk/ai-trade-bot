"""
Dry-run test for TA scoring - validates score diversity and correctness
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '.')

from scoring.ta_scorer import TAScorer


def generate_synthetic_ohlcv(symbol, n_bars=200):
    """Generate synthetic OHLCV data with different characteristics per symbol."""
    np.random.seed(hash(symbol) % 10000)
    
    # Different price ranges per symbol
    if 'BTC' in symbol:
        base_price = 42000
        volatility = 0.02
        trend = 0.001
    elif 'ETH' in symbol:
        base_price = 2200
        volatility = 0.025
        trend = -0.0015
    elif 'SOL' in symbol:
        base_price = 95
        volatility = 0.03
        trend = 0.002
    else:
        base_price = 100
        volatility = 0.02
        trend = 0.0
    
    # Generate price series
    timestamps = [datetime.now() - timedelta(minutes=15 * (n_bars - i)) for i in range(n_bars)]
    
    prices = [base_price]
    for i in range(1, n_bars):
        change = np.random.normal(trend, volatility)
        prices.append(prices[-1] * (1 + change))
    
    # Create OHLCV
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        high = close * (1 + abs(np.random.normal(0, volatility / 2)))
        low = close * (1 - abs(np.random.normal(0, volatility / 2)))
        open_price = close * (1 + np.random.normal(0, volatility / 3))
        volume = np.random.uniform(1000000, 5000000)
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


def test_ta_scoring():
    """Test TA scoring with multiple symbols."""
    print("=" * 80)
    print("TA SCORING DRY-RUN TEST")
    print("=" * 80)
    
    scorer = TAScorer()
    symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
    results = []
    
    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"Testing: {symbol}")
        print(f"{'=' * 80}")
        
        # Generate data
        df = generate_synthetic_ohlcv(symbol)
        print(f"Generated {len(df)} bars")
        print(f"Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
        
        # Score
        score, rationale, flags = scorer.score(df, symbol)
        
        print(f"\n[RESULT] Score: {score:.1f}")
        print(f"[RESULT] Direction: {flags.get('dir_hint', 'UNKNOWN')}")
        # Encode rationale to ASCII to avoid Unicode errors
        rationale_ascii = rationale.encode('ascii', 'replace').decode('ascii')[:100]
        print(f"[RESULT] Rationale: {rationale_ascii}...")
        
        results.append({
            'symbol': symbol,
            'score': score,
            'direction': flags.get('dir_hint', 'UNKNOWN')
        })
    
    # Validation
    print(f"\n{'=' * 80}")
    print("VALIDATION")
    print(f"{'=' * 80}")
    
    scores = [r['score'] for r in results]
    variance = np.var(scores)
    
    print(f"\nScores: {scores}")
    print(f"Variance: {variance:.2f}")
    
    # Check 1: Not all 50.0
    all_fifty = all(abs(s - 50.0) < 0.1 for s in scores)
    print(f"\n[CHECK 1] Not all stuck at 50.0: {'PASS' if not all_fifty else 'FAIL'}")
    
    # Check 2: Scores differ
    differ = variance > 10
    print(f"[CHECK 2] Scores show variance (>10): {'PASS' if differ else 'FAIL'}")
    
    # Check 3: Valid range
    valid_range = all(0 <= s <= 100 for s in scores)
    print(f"[CHECK 3] Scores in valid range [0, 100]: {'PASS' if valid_range else 'FAIL'}")
    
    # Check 4: At least one strong signal
    has_signal = any(s >= 60 or s <= 40 for s in scores)
    print(f"[CHECK 4] At least one score shows clear signal: {'PASS' if has_signal else 'FAIL'}")
    
    if not all_fifty and differ and valid_range:
        print(f"\n{'=' * 80}")
        print("[PASS] ALL TESTS PASSED")
        print(f"{'=' * 80}")
        return 0
    else:
        print(f"\n{'=' * 80}")
        print("[FAIL] SOME TESTS FAILED")
        print(f"{'=' * 80}")
        return 1


if __name__ == '__main__':
    exit(test_ta_scoring())

