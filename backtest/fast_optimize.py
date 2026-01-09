"""
Fast Backtest Optimizer using pre-cached scores.

Uses cached TA + ML scores to run thousands of parameter combinations quickly.
"""

import asyncio
import json
import csv
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

import numpy as np
from loguru import logger


# Configuration
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

# Weight grid (ta + ml = 0.9)
WEIGHT_GRID = [
    (0.20, 0.70),
    (0.30, 0.60),
    (0.40, 0.50),
    (0.50, 0.40),
    (0.60, 0.30),
    (0.70, 0.20),
]

# Threshold grid
ENTER_LONG_RANGE = range(52, 62, 2)
EXIT_LONG_RANGE = range(42, 50, 2)
ENTER_SHORT_RANGE = range(36, 46, 2)
EXIT_SHORT_RANGE = range(50, 60, 2)

# Constants
INITIAL_BALANCE = 10000.0
FEE_BPS = 6.0
SLIPPAGE_BPS = 3.0
LEVERAGE = 5
SL_ATR_MULT = 2.0
TP_ATR_MULT = 3.0


@dataclass
class FastResult:
    coin: str
    ta_weight: float
    ml_weight: float
    enter_long: int
    exit_long: int
    enter_short: int
    exit_short: int
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_pnl_pct: float
    score: float


def generate_valid_thresholds() -> List[Tuple[int, int, int, int]]:
    """Generate valid threshold combinations."""
    valid = []
    for el in ENTER_LONG_RANGE:
        for xl in EXIT_LONG_RANGE:
            for es in ENTER_SHORT_RANGE:
                for xs in EXIT_SHORT_RANGE:
                    if el > xl + 5 and xs > es + 5 and el > xs and es < xl:
                        valid.append((el, xl, es, xs))
    return valid


def run_fast_backtest(
    cache_data: Dict[str, Any],
    ta_weight: float,
    ml_weight: float,
    enter_long: int,
    exit_long: int,
    enter_short: int,
    exit_short: int
) -> FastResult:
    """
    Run a single backtest using cached scores.
    
    Much faster than full backtest - no TA/ML recalculation.
    """
    coin = cache_data['coin']
    timestamps = cache_data['timestamps']
    ta_scores = cache_data['ta_scores']
    ml_scores = cache_data['ml_scores']
    closes = cache_data['closes']
    highs = cache_data['highs']
    lows = cache_data['lows']
    atrs = cache_data['atrs']
    
    n_bars = len(timestamps)
    
    # State
    balance = INITIAL_BALANCE
    position = None  # {'side': 'long'/'short', 'entry_price': float, 'size': float, 'tp': float, 'sl': float}
    trades = []
    equity_curve = [balance]
    
    fee_mult = FEE_BPS / 10000
    slip_mult = SLIPPAGE_BPS / 10000
    
    for i in range(n_bars):
        ta_score = ta_scores[i]
        ml_score = ml_scores[i]
        close = closes[i]
        high = highs[i]
        low = lows[i]
        atr = atrs[i]
        
        # Compute composite score
        if np.isnan(ml_score):
            # TA only mode
            composite = ta_weight * ta_score + (1 - ta_weight - 0.1) * 50 + 0.05 * 50 + 0.05 * 50
        else:
            composite = ta_weight * ta_score + ml_weight * ml_score + 0.05 * 50 + 0.05 * 50
        
        # Check TP/SL first
        if position:
            exit_reason = None
            exit_price = close
            
            if position['side'] == 'long':
                if low <= position['sl']:
                    exit_reason = 'SL'
                    exit_price = position['sl']
                elif high >= position['tp']:
                    exit_reason = 'TP'
                    exit_price = position['tp']
            else:  # short
                if high >= position['sl']:
                    exit_reason = 'SL'
                    exit_price = position['sl']
                elif low <= position['tp']:
                    exit_reason = 'TP'
                    exit_price = position['tp']
            
            # Signal-based exit
            if exit_reason is None:
                if position['side'] == 'long' and composite <= exit_long:
                    exit_reason = 'SIGNAL'
                elif position['side'] == 'short' and composite >= exit_short:
                    exit_reason = 'SIGNAL'
            
            if exit_reason:
                # Close position
                if position['side'] == 'long':
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                else:
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
                
                notional = position['size'] * LEVERAGE
                pnl = notional * pnl_pct
                fee = notional * fee_mult
                
                balance += pnl - fee
                
                trades.append({
                    'side': position['side'],
                    'pnl_pct': pnl_pct * 100,
                    'pnl': pnl,
                    'reason': exit_reason
                })
                
                position = None
        
        # Entry logic
        if position is None:
            side = None
            if composite >= enter_long:
                side = 'long'
            elif composite <= enter_short:
                side = 'short'
            
            if side:
                # Position sizing (simplified tier-based)
                strength = abs(composite - 50) / 50
                if strength < 0.3:
                    size_pct = 0.02
                elif strength < 0.5:
                    size_pct = 0.04
                elif strength < 0.7:
                    size_pct = 0.06
                else:
                    size_pct = 0.08
                
                size = balance * size_pct
                
                # Entry with slippage
                if side == 'long':
                    entry_price = close * (1 + slip_mult)
                    sl = entry_price - SL_ATR_MULT * atr
                    tp = entry_price + TP_ATR_MULT * atr
                else:
                    entry_price = close * (1 - slip_mult)
                    sl = entry_price + SL_ATR_MULT * atr
                    tp = entry_price - TP_ATR_MULT * atr
                
                # Entry fee
                fee = size * LEVERAGE * fee_mult
                balance -= fee
                
                position = {
                    'side': side,
                    'entry_price': entry_price,
                    'size': size,
                    'tp': tp,
                    'sl': sl
                }
        
        equity_curve.append(balance)
    
    # Close any remaining position
    if position:
        if position['side'] == 'long':
            pnl_pct = (closes[-1] - position['entry_price']) / position['entry_price']
        else:
            pnl_pct = (position['entry_price'] - closes[-1]) / position['entry_price']
        
        notional = position['size'] * LEVERAGE
        pnl = notional * pnl_pct
        fee = notional * fee_mult
        balance += pnl - fee
        
        trades.append({
            'side': position['side'],
            'pnl_pct': pnl_pct * 100,
            'pnl': pnl,
            'reason': 'END'
        })
    
    # Calculate metrics
    if len(trades) == 0:
        return FastResult(
            coin=coin, ta_weight=ta_weight, ml_weight=ml_weight,
            enter_long=enter_long, exit_long=exit_long,
            enter_short=enter_short, exit_short=exit_short,
            total_trades=0, win_rate=0, profit_factor=0, sharpe_ratio=0,
            max_drawdown=0, total_pnl_pct=0, score=0
        )
    
    # Win rate
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = len(wins) / len(trades) if trades else 0
    
    # Profit factor
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0
    
    # Max drawdown
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak * 100
    max_dd = np.max(drawdown)
    
    # Sharpe ratio
    returns = [t['pnl_pct'] for t in trades]
    if len(returns) > 1:
        sharpe = np.mean(returns) / (np.std(returns) + 0.001) * np.sqrt(252)
    else:
        sharpe = 0
    
    total_pnl_pct = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
    score = profit_factor * sharpe if profit_factor > 0 and sharpe > 0 else 0
    
    return FastResult(
        coin=coin,
        ta_weight=ta_weight,
        ml_weight=ml_weight,
        enter_long=enter_long,
        exit_long=exit_long,
        enter_short=enter_short,
        exit_short=exit_short,
        total_trades=len(trades),
        win_rate=round(win_rate, 4),
        profit_factor=round(min(profit_factor, 999), 4),
        sharpe_ratio=round(sharpe, 4),
        max_drawdown=round(max_dd, 4),
        total_pnl_pct=round(total_pnl_pct, 4),
        score=round(score, 4)
    )


class FastOptimizer:
    """Fast optimizer using cached scores."""
    
    def __init__(self, cache_dir: str = "data/score_cache", output_dir: str = "data/optimization_results"):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.threshold_grid = generate_valid_thresholds()
        self.results: List[FastResult] = []
        
        logger.info(f"[FAST] {len(WEIGHT_GRID)} weight combos × {len(self.threshold_grid)} threshold combos")
        logger.info(f"[FAST] {len(COINS)} coins = {len(WEIGHT_GRID) * len(self.threshold_grid) * len(COINS)} total runs")
    
    def load_cache(self, coin: str) -> Dict[str, Any]:
        """Load cached scores."""
        cache_file = self.cache_dir / f"{coin}_scores.pkl"
        if not cache_file.exists():
            raise FileNotFoundError(f"Cache not found: {cache_file}. Run 'python -m backtest.cache' first.")
        
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    def optimize_coin(self, coin: str) -> List[FastResult]:
        """Optimize all parameter combinations for one coin."""
        logger.info(f"[FAST] Optimizing {coin}...")
        
        cache_data = self.load_cache(coin)
        results = []
        
        total = len(WEIGHT_GRID) * len(self.threshold_grid)
        current = 0
        
        for ta_w, ml_w in WEIGHT_GRID:
            for el, xl, es, xs in self.threshold_grid:
                result = run_fast_backtest(cache_data, ta_w, ml_w, el, xl, es, xs)
                results.append(result)
                current += 1
                
                if current % 100 == 0:
                    logger.info(f"[FAST] {coin}: {current}/{total} ({100*current/total:.1f}%)")
        
        return results
    
    def optimize_all(self, parallel: bool = True, max_workers: int = 8):
        """Optimize all coins."""
        start_time = datetime.now()
        
        for coin in COINS:
            try:
                coin_results = self.optimize_coin(coin)
                self.results.extend(coin_results)
                logger.info(f"[FAST] {coin} complete: {len(coin_results)} results")
            except FileNotFoundError as e:
                logger.error(str(e))
                logger.error("Run 'python -m backtest.cache' first to generate score cache!")
                return
        
        self.save_results()
        
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f"[FAST] Optimization complete in {elapsed:.1f} minutes")
    
    def save_results(self):
        """Save optimization results."""
        # All results
        all_path = self.output_dir / "all_results.csv"
        with open(all_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'coin', 'ta_weight', 'ml_weight', 'enter_long', 'exit_long',
                'enter_short', 'exit_short', 'total_trades', 'win_rate',
                'profit_factor', 'sharpe_ratio', 'max_drawdown', 'total_pnl_pct', 'score'
            ])
            for r in self.results:
                writer.writerow([
                    r.coin, r.ta_weight, r.ml_weight, r.enter_long, r.exit_long,
                    r.enter_short, r.exit_short, r.total_trades, r.win_rate,
                    r.profit_factor, r.sharpe_ratio, r.max_drawdown, r.total_pnl_pct, r.score
                ])
        logger.info(f"[FAST] Saved {len(self.results)} results to {all_path}")
        
        # Best per coin
        best_per_coin = {}
        for r in self.results:
            if r.coin not in best_per_coin or (r.score > best_per_coin[r.coin].score and r.max_drawdown < 25):
                if r.max_drawdown < 25:
                    best_per_coin[r.coin] = r
        
        best_path = self.output_dir / "best_per_coin.csv"
        with open(best_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['coin', 'ta_weight', 'ml_weight', 'enter_long', 'exit_long',
                           'enter_short', 'exit_short', 'pf', 'sharpe', 'pnl', 'score'])
            for coin, r in best_per_coin.items():
                writer.writerow([coin, r.ta_weight, r.ml_weight, r.enter_long, r.exit_long,
                               r.enter_short, r.exit_short, r.profit_factor, r.sharpe_ratio,
                               f"{r.total_pnl_pct:.1f}%", r.score])
        
        # Global best
        param_scores = {}
        for r in self.results:
            key = (r.ta_weight, r.ml_weight, r.enter_long, r.exit_long, r.enter_short, r.exit_short)
            if key not in param_scores:
                param_scores[key] = []
            if r.max_drawdown < 25:
                param_scores[key].append(r.score)
        
        best_key = None
        best_avg = 0
        for key, scores in param_scores.items():
            if len(scores) >= 5:
                avg = np.mean(scores)
                if avg > best_avg:
                    best_avg = avg
                    best_key = key
        
        global_best = {
            "ta_weight": best_key[0] if best_key else 0.5,
            "ml_weight": best_key[1] if best_key else 0.4,
            "enter_long": best_key[2] if best_key else 54,
            "exit_long": best_key[3] if best_key else 46,
            "enter_short": best_key[4] if best_key else 40,
            "exit_short": best_key[5] if best_key else 52,
            "avg_score": round(best_avg, 4)
        }
        
        global_path = self.output_dir / "global_best.json"
        with open(global_path, 'w') as f:
            json.dump(global_best, f, indent=2)
        
        # Print summary
        print("\n" + "="*70)
        print("OPTIMIZATION RESULTS")
        print("="*70)
        print("\nBest parameters per coin:")
        for coin, r in best_per_coin.items():
            print(f"  {coin:20s} | PF={r.profit_factor:.2f} | Sharpe={r.sharpe_ratio:.2f} | "
                  f"PnL={r.total_pnl_pct:+.1f}% | Score={r.score:.2f}")
        
        print(f"\nGlobal Best (avg across coins):")
        for k, v in global_best.items():
            print(f"  {k}: {v}")
        print("="*70)


def main():
    """Run fast optimization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fast Backtest Optimizer")
    parser.add_argument('--output', type=str, default='data/optimization_results')
    
    args = parser.parse_args()
    
    optimizer = FastOptimizer(output_dir=args.output)
    optimizer.optimize_all()


if __name__ == '__main__':
    main()
