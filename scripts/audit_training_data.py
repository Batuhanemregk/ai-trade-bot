"""
Audit ML training data for completeness and quality.
"""

import pandas as pd
from pathlib import Path
from loguru import logger


def audit_data():
    """Audit all training data files."""
    symbols = ['BTC', 'ETH', 'SOL']
    timeframes = ['15m', '1h', '4h']
    
    results = []
    
    for symbol in symbols:
        for tf in timeframes:
            filepath = Path(f"data/ml_training/{symbol}_USDT_{tf}_6months_binance.csv")
            
            if not filepath.exists():
                logger.warning(f"Missing: {filepath.name}")
                continue
            
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate expected bars for 6 months
            timeframe_seconds = {
                '15m': 900,   # 15 minutes
                '1h': 3600,   # 1 hour
                '4h': 14400   # 4 hours
            }
            
            days = 180  # 6 months
            expected_bars = (days * 24 * 3600) / timeframe_seconds[tf]
            
            # Data quality checks
            total_bars = len(df)
            date_range = df['timestamp'].max() - df['timestamp'].min()
            missing_ratio = 1 - (total_bars / expected_bars)
            
            # Check for duplicates
            duplicates = df['timestamp'].duplicated().sum()
            
            # Check for gaps
            df_sorted = df.sort_values('timestamp')
            time_diffs = df_sorted['timestamp'].diff()
            expected_diff = pd.Timedelta(seconds=timeframe_seconds[tf])
            gaps = (time_diffs > expected_diff * 2).sum()  # More than 2x expected gap
            
            # Check OHLCV validity
            invalid_ohlcv = (
                (df['high'] < df['low']).sum() +
                (df['high'] < df['open']).sum() +
                (df['high'] < df['close']).sum() +
                (df['low'] > df['open']).sum() +
                (df['low'] > df['close']).sum()
            )
            
            results.append({
                'symbol': symbol,
                'timeframe': tf,
                'total_bars': total_bars,
                'expected_bars': expected_bars,
                'completeness': total_bars / expected_bars,
                'date_range_days': date_range.days,
                'date_range_hours': date_range.seconds / 3600 if hasattr(date_range, 'seconds') else 0,
                'missing_ratio': missing_ratio,
                'duplicates': duplicates,
                'gaps': gaps,
                'invalid_ohlcv': invalid_ohlcv,
                'start_date': df['timestamp'].min(),
                'end_date': df['timestamp'].max()
            })
    
    return results


if __name__ == '__main__':
    results = audit_data()
    
    # Print summary
    print("\n" + "="*100)
    print("DATA AUDIT REPORT")
    print("="*100)
    print(f"\n{'Symbol':<8} {'TF':<6} {'Bars':<8} {'Expected':<10} {'Complete %':<12} {'Gaps':<8} {'Invalid':<8}")
    print("-"*100)
    
    for r in results:
        print(f"{r['symbol']:<8} {r['timeframe']:<6} {r['total_bars']:<8} {r['expected_bars']:<10.0f} "
              f"{r['completeness']*100:<12.2f} {r['gaps']:<8} {r['invalid_ohlcv']:<8}")
    
    print("\n" + "="*100)
    print("DETAILED RESULTS")
    print("="*100)
    
    for r in results:
        print(f"\n{r['symbol']} {r['timeframe']}:")
        print(f"  Total bars: {r['total_bars']:,}")
        print(f"  Expected: {r['expected_bars']:.0f}")
        print(f"  Completeness: {r['completeness']*100:.2f}%")
        print(f"  Date range: {r['start_date']} to {r['end_date']}")
        print(f"  Days covered: {r['date_range_days']}")
        print(f"  Missing ratio: {r['missing_ratio']*100:.2f}%")
        print(f"  Duplicates: {r['duplicates']}")
        print(f"  Gaps: {r['gaps']}")
        print(f"  Invalid OHLCV: {r['invalid_ohlcv']}")

