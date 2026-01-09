"""
Pre-compute and cache TA + ML scores for all coins.

This allows running thousands of backtest parameter combinations quickly
by reusing pre-computed scores instead of recalculating per bar.
"""

import asyncio
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import numpy as np
from loguru import logger

from backtest.data import BacktestDataLoader
from scoring.ta_scorer import TAScorer
from scoring.ml_scorer import MLScorer


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


class ScoreCache:
    """
    Pre-compute and cache TA + ML scores for all bars.
    
    Output structure per coin:
    {
        'timestamps': [...],
        'ta_scores': [...],
        'ml_scores': [...],
        'ohlcv': DataFrame
    }
    """
    
    def __init__(self, cache_dir: str = "data/score_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_loader = BacktestDataLoader()
        self.ta_scorer = TAScorer()
        self.ml_scorer = None
        
        try:
            self.ml_scorer = MLScorer()
            logger.info("[CACHE] ML scorer initialized")
        except Exception as e:
            logger.warning(f"[CACHE] ML scorer failed: {e}")
    
    def compute_scores(self, coin: str) -> Dict[str, Any]:
        """Compute TA and ML scores for all bars of a coin (uses all available data)."""
        
        logger.info(f"[CACHE] Computing scores for {coin}...")
        
        # Load ALL data (no date filter)
        df_15m = self.data_loader.load_ohlcv(coin, "15m")
        
        try:
            df_1h = self.data_loader.load_ohlcv(coin, "1h")
        except:
            df_1h = self.data_loader._aggregate_to_1h(df_15m)
        
        total_bars = len(df_15m)
        min_lookback = 50
        
        timestamps = []
        ta_scores = []
        ml_scores = []
        closes = []
        highs = []
        lows = []
        atrs = []
        
        logger.info(f"[CACHE] Processing {total_bars - min_lookback} bars for {coin}...")
        
        for i in range(min_lookback, total_bars):
            bar = df_15m.iloc[i]
            bar_time = df_15m.index[i]
            
            # Get OHLCV slice
            start_idx = max(0, i - 200)
            main_df = df_15m.iloc[start_idx:i + 1].copy()
            
            current_time = df_15m.index[i]
            trend_df = df_1h[df_1h.index <= current_time].tail(100)
            
            ohlcv_bundle = {'main': main_df, 'trend': trend_df}
            
            # TA score
            try:
                ta_score, _, _ = self.ta_scorer.score(main_df, coin)
            except:
                ta_score = 50.0
            
            # ML score
            ml_score = None
            if self.ml_scorer:
                try:
                    ml_score, _, _ = self.ml_scorer.score(coin, ohlcv_bundle)
                except:
                    pass
            
            # ATR for TP/SL
            if len(main_df) >= 15:
                high = main_df['high'].values
                low = main_df['low'].values
                close = main_df['close'].values
                tr1 = high[1:] - low[1:]
                tr2 = np.abs(high[1:] - np.roll(close, 1)[1:])
                tr3 = np.abs(low[1:] - np.roll(close, 1)[1:])
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
            
            if (i - min_lookback) % 1000 == 0:
                pct = (i - min_lookback) / (total_bars - min_lookback) * 100
                logger.info(f"[CACHE] {coin}: {pct:.1f}% ({i - min_lookback}/{total_bars - min_lookback})")
        
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
        
        logger.info(f"[CACHE] {coin}: {len(timestamps)} bars cached")
        
        return result
    
    def save_cache(self, coin: str, data: Dict[str, Any]):
        """Save cached scores to disk."""
        cache_file = self.cache_dir / f"{coin}_scores.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"[CACHE] Saved {cache_file}")
    
    def load_cache(self, coin: str) -> Dict[str, Any]:
        """Load cached scores from disk."""
        cache_file = self.cache_dir / f"{coin}_scores.pkl"
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def cache_all_coins(self, coins: list = None, force: bool = False):
        """Cache scores for all coins."""
        if coins is None:
            coins = COINS
        
        for coin in coins:
            cache_file = self.cache_dir / f"{coin}_scores.pkl"
            
            if cache_file.exists() and not force:
                logger.info(f"[CACHE] {coin} already cached, skipping")
                continue
            
            try:
                data = self.compute_scores(coin)
                self.save_cache(coin, data)
            except Exception as e:
                logger.error(f"[CACHE] Failed to cache {coin}: {e}")
        
        logger.info("[CACHE] All coins cached!")


def main():
    """Pre-compute scores for all coins."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-compute score cache")
    parser.add_argument('--force', action='store_true', help='Force recompute even if cached')
    parser.add_argument('--coins', nargs='+', default=None, help='Specific coins to cache')
    
    args = parser.parse_args()
    
    cache = ScoreCache()
    cache.cache_all_coins(coins=args.coins, force=args.force)


if __name__ == '__main__':
    main()
