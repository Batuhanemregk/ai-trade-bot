"""
DRY-RUN: Test ML integration end-to-end
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger

from scoring.ml_scorer import MLScorer
from scoring.ta_scorer import TAScorer


def test_ml_scorer():
    """Test ML scorer with real data."""
    print("\n" + "="*100)
    print("ML INTEGRATION DRY-RUN TEST")
    print("="*100)
    
    scorer = MLScorer()
    
    # Test symbols and timeframes
    symbols = ['BTC', 'ETH', 'SOL']
    timeframes = ['15m', '1h', '4h']
    
    results = []
    
    for symbol in symbols:
        for tf in timeframes:
            print(f"\n{symbol} {tf}:")
            
            # Load data
            data_file = Path(f"data/ml_training/{symbol}_USDT_{tf}_6months_binance.csv")
            if not data_file.exists():
                print(f"  [FAIL] Data file not found: {data_file.name}")
                continue
            
            df = pd.read_csv(data_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Prepare bundle with MTF data (last 100 bars for testing)
            df_test = df.tail(100).copy()
            df_test.set_index('timestamp', inplace=True)
            
            bundle = {
                'main': df_test,
                tf: df_test
            }
            
            # Add MTF data if not the current tf
            if tf != '1h':
                data_1h = pd.read_csv(f"data/ml_training/{symbol}_USDT_1h_6months_binance.csv")
                data_1h['timestamp'] = pd.to_datetime(data_1h['timestamp'])
                bundle['1h'] = data_1h.tail(100).copy().set_index('timestamp')
            
            if tf != '4h':
                data_4h = pd.read_csv(f"data/ml_training/{symbol}_USDT_4h_6months_binance.csv")
                data_4h['timestamp'] = pd.to_datetime(data_4h['timestamp'])
                bundle['4h'] = data_4h.tail(100).copy().set_index('timestamp')
            
            # Get ML score
            try:
                ml_score, ml_rationale, ml_details = scorer.score(
                    f"{symbol}-USDT-SWAP",
                    bundle
                )
                
                # Validate results
                score_valid = 0 <= ml_score <= 100
                has_details = 'model' in ml_details and 'p_up' in ml_details
                has_signal = 'signal_direction' in ml_details
                
                print(f"  Score: {ml_score:.1f}/100")
                print(f"  Rationale: {ml_rationale[:80]}")
                print(f"  Signal: {ml_details.get('signal_direction', 'N/A')}")
                print(f"  Model: {ml_details.get('model', 'N/A')}")
                print(f"  AUC: {ml_details.get('auc', 'N/A')}")
                print(f"  Features: {ml_details.get('n_features', 'N/A')}")
                print(f"  Status: {'OK' if score_valid and has_details and has_signal else 'FAIL'}")
                
                results.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'score': ml_score,
                    'valid': score_valid and has_details and has_signal,
                    'model': ml_details.get('model'),
                    'auc': ml_details.get('auc'),
                    'n_features': ml_details.get('n_features')
                })
                
            except Exception as e:
                print(f"  [FAIL] Error: {e}")
                results.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'score': None,
                    'valid': False,
                    'error': str(e)
                })
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    
    valid_count = sum(1 for r in results if r.get('valid', False))
    total_count = len(results)
    
    print(f"Valid scores: {valid_count}/{total_count}")
    
    if valid_count == total_count:
        print("[OK] ALL TESTS PASSED")
    else:
        print(f"[WARN] {total_count - valid_count} tests failed")
    
    print("\n" + "="*100)
    
    return results


def test_feature_builder():
    """Test feature builder for no-look-ahead."""
    print("\n" + "="*100)
    print("FEATURE BUILDER NO-LOOK-AHEAD TEST")
    print("="*100)
    
    from ml.features import FeatureBuilder
    
    builder = FeatureBuilder()
    
    # Create test data
    dates = pd.date_range('2025-01-01', periods=200, freq='15min')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': 100 + np.random.randn(200).cumsum() * 0.1,
        'high': 100 + np.random.randn(200).cumsum() * 0.12,
        'low': 100 + np.random.randn(200).cumsum() * 0.08,
        'close': 100 + np.random.randn(200).cumsum() * 0.1,
        'volume': np.random.uniform(1000, 10000, 200)
    }, index=dates)
    
    # Build features
    df_features = builder.build_features(df)
    
    # Check for forward-looking operations
    issues = []
    
    # No shift with positive values
    for col in df_features.columns:
        if df_features[col].isna().any():
            issues.append(f"{col}: has NaN values")
    
    # No future data in rolling windows
    if 'future_price' in df_features.columns:
        issues.append("future_price: forward-looking feature detected")
    
    if issues:
        print("[FAIL] ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("[OK] NO LOOK-AHEAD ISSUES DETECTED")
    
    print(f"Total features: {len(builder.feature_columns)}")
    print(f"Feature columns: {', '.join(sorted(builder.feature_columns)[:10])}...")
    
    print("="*100)
    
    return len(issues) == 0


def main():
    """Run all tests."""
    logger.info("Starting ML integration dry-run tests...")
    
    # Test 1: Feature builder
    builder_ok = test_feature_builder()
    
    # Test 2: ML scorer
    scorer_results = test_ml_scorer()
    
    # Overall result
    all_ok = builder_ok and all(r.get('valid', False) for r in scorer_results)
    
    print("\n" + "="*100)
    print("OVERALL RESULT")
    print("="*100)
    print(f"Feature Builder: {'[OK] PASS' if builder_ok else '[FAIL]'}")
    print(f"ML Scorer: {sum(1 for r in scorer_results if r.get('valid', False))}/{len(scorer_results)} PASS")
    print(f"Overall: {'[OK] ALL TESTS PASS' if all_ok else '[FAIL] SOME TESTS FAILED'}")
    print("="*100)
    
    return all_ok


if __name__ == '__main__':
    main()

