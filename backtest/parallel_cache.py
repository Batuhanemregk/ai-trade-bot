"""
Parallel Score Cache - Uses all CPU cores to cache 10 coins simultaneously.
"""

import pickle
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np


COINS = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "DOGE-USDT-SWAP",
    "OP-USDT-SWAP",
    "SUI-USDT-SWAP",
    "UNI-USDT-SWAP",
    "VET-USDT-SWAP",
    "AVAX-USDT-SWAP",
    "ARB-USDT-SWAP",
]

CACHE_DIR = Path("data/score_cache")
DATA_DIR = Path("data/backtest_ohlcv")


def load_ohlcv(coin: str, timeframe: str = "15m") -> pd.DataFrame:
    """Load OHLCV data for a coin."""
    file_path = DATA_DIR / f"{coin}_{timeframe}.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    if df['timestamp'].dt.tz is not None:
        df['timestamp'] = df['timestamp'].dt.tz_localize(None)
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    
    return df


def compute_ta_score(df: pd.DataFrame) -> float:
    """Simplified TA scoring (RSI + MACD based)."""
    if len(df) < 50:
        return 50.0
    
    close = df['close'].values
    
    # RSI (14)
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.mean(gain[-14:])
    avg_loss = np.mean(loss[-14:])
    
    if avg_loss == 0:
        rsi = 100 if avg_gain > 0 else 50
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = pd.Series(close).ewm(span=12).mean().iloc[-1]
    ema26 = pd.Series(close).ewm(span=26).mean().iloc[-1]
    macd = ema12 - ema26
    signal = pd.Series(close).ewm(span=12).mean().diff().ewm(span=9).mean().iloc[-1]
    macd_hist = macd - signal if not np.isnan(signal) else 0
    
    # Score
    rsi_score = 50 + (rsi - 50) * 0.5
    macd_score = 50 + np.tanh(macd_hist / (close[-1] * 0.001)) * 30
    
    score = 0.6 * rsi_score + 0.4 * macd_score
    return max(0, min(100, score))


def compute_ml_score(coin: str, df: pd.DataFrame) -> float:
    """
    Compute ML score using the actual ML scorer.
    This is called per-process so each has its own scorer instance.
    """
    try:
        from scoring.ml_scorer import MLScorer
        
        # Create scorer if not exists
        if not hasattr(compute_ml_score, '_scorer'):
            compute_ml_score._scorer = MLScorer()
        
        # Build OHLCV bundle
        ohlcv_bundle = {'main': df.copy()}
        
        ml_score, _, _ = compute_ml_score._scorer.score(coin, ohlcv_bundle)
        return ml_score
        
    except Exception as e:
        return None


def process_coin(coin: str) -> Tuple[str, Dict[str, Any]]:
    """Process a single coin - compute all scores."""
    print(f"[CACHE] Starting {coin}...")
    
    try:
        df_15m = load_ohlcv(coin, "15m")
        
        # Aggregate to 1h
        df_1h = df_15m.resample('1H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        total_bars = len(df_15m)
        min_lookback = 50
        
        timestamps = []
        ta_scores = []
        ml_scores = []
        closes = []
        highs = []
        lows = []
        atrs = []
        
        print(f"[CACHE] {coin}: Processing {total_bars - min_lookback} bars...")
        
        for i in range(min_lookback, total_bars):
            bar = df_15m.iloc[i]
            bar_time = df_15m.index[i]
            
            # Get OHLCV slice
            start_idx = max(0, i - 200)
            main_df = df_15m.iloc[start_idx:i + 1].copy()
            
            # TA score
            ta_score = compute_ta_score(main_df)
            
            # ML score
            ml_score = compute_ml_score(coin, main_df)
            
            # ATR for TP/SL
            if len(main_df) >= 15:
                high = main_df['high'].values
                low = main_df['low'].values
                close_arr = main_df['close'].values
                tr1 = high[1:] - low[1:]
                tr2 = np.abs(high[1:] - np.roll(close_arr, 1)[1:])
                tr3 = np.abs(low[1:] - np.roll(close_arr, 1)[1:])
                tr = np.maximum(tr1, np.maximum(tr2, tr3))
                atr = float(np.mean(tr[-14:]))
            else:
                atr = bar['close'] * 0.02
            
            timestamps.append(bar_time)
            ta_scores.append(ta_score)
            ml_scores.append(ml_score)
            closes.append(bar['close'])
            highs.append(bar['high'])
            lows.append(bar['low'])
            atrs.append(atr)
            
            if (i - min_lookback) % 5000 == 0:
                pct = (i - min_lookback) / (total_bars - min_lookback) * 100
                print(f"[CACHE] {coin}: {pct:.1f}% ({i - min_lookback}/{total_bars - min_lookback})")
        
        result = {
            'coin': coin,
            'timestamps': timestamps,
            'ta_scores': np.array(ta_scores, dtype=np.float32),
            'ml_scores': np.array([s if s is not None else np.nan for s in ml_scores], dtype=np.float32),
            'closes': np.array(closes, dtype=np.float32),
            'highs': np.array(highs, dtype=np.float32),
            'lows': np.array(lows, dtype=np.float32),
            'atrs': np.array(atrs, dtype=np.float32),
        }
        
        # Save to disk
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{coin}_scores.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
        
        print(f"[CACHE] {coin}: DONE - {len(timestamps)} bars saved")
        return (coin, {"status": "success", "bars": len(timestamps)})
        
    except Exception as e:
        print(f"[CACHE] {coin}: FAILED - {e}")
        return (coin, {"status": "failed", "error": str(e)})


def main():
    """Run parallel caching for all coins."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parallel Score Cache")
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers')
    parser.add_argument('--coins', nargs='+', default=None, help='Specific coins to cache')
    
    args = parser.parse_args()
    
    coins = args.coins if args.coins else COINS
    workers = min(args.workers, len(coins))
    
    print(f"[CACHE] Starting parallel cache with {workers} workers for {len(coins)} coins...")
    print(f"[CACHE] CPU cores available: {mp.cpu_count()}")
    
    start_time = datetime.now()
    
    # Run in parallel
    with mp.Pool(workers) as pool:
        results = pool.map(process_coin, coins)
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    print(f"\n{'='*60}")
    print(f"CACHE COMPLETE - {elapsed:.1f} minutes")
    print(f"{'='*60}")
    
    for coin, result in results:
        if result['status'] == 'success':
            print(f"  ✓ {coin}: {result['bars']} bars")
        else:
            print(f"  ✗ {coin}: {result['error']}")
    
    print(f"\nCache files saved to: {CACHE_DIR}")
    print(f"Next step: python -m backtest.fast_optimize")


if __name__ == '__main__':
    main()
