"""
Data Audit Script
Audits 6-month Binance data quality for ML training.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import glob

def audit_file(filepath: str) -> Dict:
    """Audit a single CSV file."""
    df = pd.read_csv(filepath)
    
    # Parse timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    elif 'time' in df.columns:
        df['timestamp'] = pd.to_datetime(df['time'])
    else:
        # Assume first column is timestamp
        df['timestamp'] = pd.to_datetime(df.iloc[:, 0])
    
    df = df.sort_values('timestamp')
    
    # Extract symbol and timeframe from filename
    filename = Path(filepath).stem
    parts = filename.split('_')
    symbol = parts[0]
    tf = parts[2] if len(parts) > 2 else 'unknown'
    
    # Calculate expected bars
    time_delta = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
    days = time_delta.total_seconds() / (24 * 3600)
    
    tf_minutes = {'15m': 15, '1h': 60, '4h': 240}[tf]
    expected_bars = int(days * 24 * 60 / tf_minutes)
    
    # Detect gaps
    expected_interval = pd.Timedelta(minutes=tf_minutes)
    time_diffs = df['timestamp'].diff().dropna()
    
    # Gaps are intervals > 1.5x expected
    gaps = time_diffs > (expected_interval * 1.5)
    n_gaps = gaps.sum()
    
    # Missing bars estimate
    missing_estimate = expected_bars - len(df)
    missing_pct = (missing_estimate / expected_bars * 100) if expected_bars > 0 else 0
    
    # Check OHLCV columns
    has_ohlcv = all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
    
    # Check for NaN
    n_nan = df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum()
    
    return {
        'file': filename,
        'symbol': symbol,
        'timeframe': tf,
        'bars': len(df),
        'expected_bars': expected_bars,
        'missing_estimate': missing_estimate,
        'missing_pct': round(missing_pct, 2),
        'gaps': int(n_gaps),
        'start': df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M'),
        'end': df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M'),
        'days': round(days, 1),
        'has_ohlcv': has_ohlcv,
        'n_nan': int(n_nan),
        'quality': 'PASS' if missing_pct < 5 and n_nan == 0 else 'FAIL'
    }

def audit_all():
    """Audit all binance CSV files."""
    files = glob.glob('data/ml_training/*_binance.csv')
    files = sorted(files)
    
    results = []
    for filepath in files:
        result = audit_file(filepath)
        results.append(result)
        print(f"Processed: {result['file']}")
    
    # Create summary
    print("\n" + "="*80)
    print("DATA AUDIT REPORT")
    print("="*80)
    
    df_results = pd.DataFrame(results)
    print(f"\nTotal files: {len(results)}")
    print(f"Symbols: {df_results['symbol'].nunique()}")
    print(f"Timeframes: {', '.join(df_results['timeframe'].unique())}")
    
    print("\nDetailed Results:")
    print("-"*80)
    print(f"{'Symbol':<8} {'TF':<4} {'Bars':<8} {'Expected':<8} {'Missing':<8} {'Missing%':<8} {'Gaps':<6} {'Quality':<8}")
    print("-"*80)
    
    for r in results:
        print(f"{r['symbol']:<8} {r['timeframe']:<4} {r['bars']:<8} {r['expected_bars']:<8} "
              f"{r['missing_estimate']:<8} {r['missing_pct']:<8.2f} {r['gaps']:<6} {r['quality']:<8}")
    
    # Overall quality
    n_pass = sum(1 for r in results if r['quality'] == 'PASS')
    n_fail = sum(1 for r in results if r['quality'] == 'FAIL')
    
    print("\n" + "="*80)
    print(f"OVERALL QUALITY: {n_pass}/{len(results)} files PASSED")
    
    if n_fail > 0:
        print(f"\nFAILING FILES:")
        for r in results:
            if r['quality'] == 'FAIL':
                print(f"  - {r['file']}: missing={r['missing_pct']:.2f}%, gaps={r['gaps']}, NaN={r['n_nan']}")
    else:
        print("\nAll files passed quality checks!")
    
    print("="*80)
    
    # Save detailed report
    df_results.to_csv('docs/DATA_AUDIT_DETAILS.csv', index=False)
    print(f"\nDetailed report saved to: docs/DATA_AUDIT_DETAILS.csv")
    
    return results

if __name__ == '__main__':
    results = audit_all()

