"""
Backtest Parameter Optimizer.

Grid search for optimal:
- TA/ML weights
- Entry/Exit thresholds

Metric: Profit Factor × Sharpe Ratio
"""

import asyncio
import json
import csv
import itertools
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np
from loguru import logger

from backtest.backtest_engine import BacktestEngine


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

# Date range
START_DATE = "2023-07-01"
END_DATE = "2025-01-01"

# Weight grid (ta + ml = 0.9, news=0.05, risk=0.05)
WEIGHT_GRID = [
    (0.20, 0.70),
    (0.30, 0.60),
    (0.40, 0.50),
    (0.50, 0.40),
    (0.60, 0.30),
    (0.70, 0.20),
]

# Threshold grid - full search
ENTER_LONG_RANGE = range(52, 62, 2)    # 52, 54, 56, 58, 60
EXIT_LONG_RANGE = range(42, 50, 2)      # 42, 44, 46, 48
ENTER_SHORT_RANGE = range(36, 46, 2)    # 36, 38, 40, 42, 44
EXIT_SHORT_RANGE = range(50, 60, 2)     # 50, 52, 54, 56, 58


@dataclass
class OptimizationResult:
    """Result of a single optimization run."""
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
    score: float  # Profit Factor × Sharpe


def generate_valid_thresholds() -> List[Tuple[int, int, int, int]]:
    """Generate valid threshold combinations."""
    valid = []
    for el in ENTER_LONG_RANGE:
        for xl in EXIT_LONG_RANGE:
            for es in ENTER_SHORT_RANGE:
                for xs in EXIT_SHORT_RANGE:
                    # Validity constraints
                    if el > xl + 5 and xs > es + 5 and el > xs and es < xl:
                        valid.append((el, xl, es, xs))
    return valid


class BacktestOptimizer:
    """
    Grid search optimizer for backtest parameters.
    """
    
    def __init__(self, output_dir: str = "data/optimization_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results: List[OptimizationResult] = []
        self.threshold_grid = generate_valid_thresholds()
        
        logger.info(f"[OPT] Weight combinations: {len(WEIGHT_GRID)}")
        logger.info(f"[OPT] Valid threshold combinations: {len(self.threshold_grid)}")
        logger.info(f"[OPT] Total coins: {len(COINS)}")
        
        total_runs = len(WEIGHT_GRID) * len(self.threshold_grid) * len(COINS)
        logger.info(f"[OPT] Total optimization runs: {total_runs}")
    
    async def run_single(
        self,
        coin: str,
        ta_weight: float,
        ml_weight: float,
        enter_long: int,
        exit_long: int,
        enter_short: int,
        exit_short: int
    ) -> OptimizationResult:
        """Run a single backtest with given parameters."""
        
        # Create engine with custom params
        engine = BacktestEngine(
            symbol=coin,
            initial_balance=10000.0,
            fee_bps=6.0,
            slippage_bps=3.0,
            intrabar_mode="conservative",
            output_dir=str(self.output_dir / "temp")
        )
        
        # Override parameters
        engine.ta_weight = ta_weight
        engine.ml_weight = ml_weight
        engine.enter_long = enter_long
        engine.exit_long = exit_long
        engine.enter_short = enter_short
        engine.exit_short = exit_short
        
        try:
            start_dt = datetime.fromisoformat(START_DATE)
            end_dt = datetime.fromisoformat(END_DATE)
            
            summary = await engine.run(start_dt, end_dt)
            
            # Calculate score
            pf = summary.get('profit_factor', 0) or 0
            sharpe = summary.get('sharpe_ratio', 0) or 0
            score = pf * sharpe if pf > 0 and sharpe > 0 else 0
            
            return OptimizationResult(
                coin=coin,
                ta_weight=ta_weight,
                ml_weight=ml_weight,
                enter_long=enter_long,
                exit_long=exit_long,
                enter_short=enter_short,
                exit_short=exit_short,
                total_trades=summary.get('total_trades', 0),
                win_rate=summary.get('win_rate', 0),
                profit_factor=pf,
                sharpe_ratio=sharpe,
                max_drawdown=summary.get('max_drawdown_pct', 0),
                total_pnl_pct=summary.get('total_pnl_pct', 0),
                score=score
            )
            
        except Exception as e:
            logger.warning(f"[OPT] Failed {coin} with params: {e}")
            return OptimizationResult(
                coin=coin,
                ta_weight=ta_weight,
                ml_weight=ml_weight,
                enter_long=enter_long,
                exit_long=exit_long,
                enter_short=enter_short,
                exit_short=exit_short,
                total_trades=0,
                win_rate=0,
                profit_factor=0,
                sharpe_ratio=0,
                max_drawdown=0,
                total_pnl_pct=0,
                score=0
            )
    
    async def optimize_all(self, quick_mode: bool = False):
        """
        Run full optimization.
        
        Args:
            quick_mode: If True, only test weight combinations with default thresholds
        """
        start_time = datetime.now()
        
        if quick_mode:
            # Quick mode: only weights
            thresholds = [(54, 46, 40, 52)]  # Default
            logger.info("[OPT] Quick mode: testing only weight combinations")
        else:
            thresholds = self.threshold_grid
        
        total = len(WEIGHT_GRID) * len(thresholds) * len(COINS)
        current = 0
        
        for coin in COINS:
            logger.info(f"\n[OPT] {'='*50}")
            logger.info(f"[OPT] Optimizing {coin}")
            logger.info(f"[OPT] {'='*50}")
            
            for ta_w, ml_w in WEIGHT_GRID:
                for el, xl, es, xs in thresholds:
                    current += 1
                    
                    result = await self.run_single(
                        coin, ta_w, ml_w, el, xl, es, xs
                    )
                    self.results.append(result)
                    
                    if current % 10 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        eta_seconds = (elapsed / current) * (total - current)
                        eta_minutes = eta_seconds / 60
                        
                        logger.info(
                            f"[OPT] Progress: {current}/{total} ({100*current/total:.1f}%) | "
                            f"ETA: {eta_minutes:.0f} min | "
                            f"Score: {result.score:.2f}"
                        )
        
        # Save results
        self.save_results()
        
        elapsed_total = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f"\n[OPT] Optimization complete in {elapsed_total:.1f} minutes")
    
    def save_results(self):
        """Save optimization results."""
        
        # 1. All results CSV
        all_results_path = self.output_dir / "all_results.csv"
        with open(all_results_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'coin', 'ta_weight', 'ml_weight', 'enter_long', 'exit_long',
                'enter_short', 'exit_short', 'total_trades', 'win_rate',
                'profit_factor', 'sharpe_ratio', 'max_drawdown', 'total_pnl_pct', 'score'
            ])
            for r in self.results:
                writer.writerow([
                    r.coin, r.ta_weight, r.ml_weight, r.enter_long, r.exit_long,
                    r.enter_short, r.exit_short, r.total_trades, f"{r.win_rate:.4f}",
                    f"{r.profit_factor:.4f}", f"{r.sharpe_ratio:.4f}", 
                    f"{r.max_drawdown:.4f}", f"{r.total_pnl_pct:.4f}", f"{r.score:.4f}"
                ])
        logger.info(f"[OPT] Saved all results to {all_results_path}")
        
        # 2. Best per coin
        best_per_coin = {}
        for r in self.results:
            if r.coin not in best_per_coin or r.score > best_per_coin[r.coin].score:
                if r.max_drawdown < 25:  # Constraint
                    best_per_coin[r.coin] = r
        
        per_coin_path = self.output_dir / "best_per_coin.csv"
        with open(per_coin_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'coin', 'ta_weight', 'ml_weight', 'enter_long', 'exit_long',
                'enter_short', 'exit_short', 'profit_factor', 'sharpe', 'pnl_pct', 'score'
            ])
            for coin, r in best_per_coin.items():
                writer.writerow([
                    coin, r.ta_weight, r.ml_weight, r.enter_long, r.exit_long,
                    r.enter_short, r.exit_short, f"{r.profit_factor:.2f}",
                    f"{r.sharpe_ratio:.2f}", f"{r.total_pnl_pct:.1f}%", f"{r.score:.2f}"
                ])
        logger.info(f"[OPT] Saved best per coin to {per_coin_path}")
        
        # 3. Global best (average across coins)
        # Group by params, average score
        param_scores = {}
        for r in self.results:
            key = (r.ta_weight, r.ml_weight, r.enter_long, r.exit_long, r.enter_short, r.exit_short)
            if key not in param_scores:
                param_scores[key] = []
            if r.max_drawdown < 25:  # Constraint
                param_scores[key].append(r.score)
        
        # Find best average
        best_key = None
        best_avg = 0
        for key, scores in param_scores.items():
            if len(scores) >= 5:  # At least 5 coins
                avg = np.mean(scores)
                if avg > best_avg:
                    best_avg = avg
                    best_key = key
        
        if best_key:
            global_best = {
                "ta_weight": best_key[0],
                "ml_weight": best_key[1],
                "enter_long": best_key[2],
                "exit_long": best_key[3],
                "enter_short": best_key[4],
                "exit_short": best_key[5],
                "avg_score": round(best_avg, 4),
                "coins_used": len(param_scores[best_key])
            }
        else:
            global_best = {"error": "No valid params found"}
        
        global_path = self.output_dir / "global_best.json"
        with open(global_path, 'w', encoding='utf-8') as f:
            json.dump(global_best, f, indent=2)
        logger.info(f"[OPT] Saved global best to {global_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("OPTIMIZATION SUMMARY")
        print("="*60)
        print(f"\nBest per coin:")
        for coin, r in best_per_coin.items():
            print(f"  {coin}: PF={r.profit_factor:.2f}, Sharpe={r.sharpe_ratio:.2f}, "
                  f"PnL={r.total_pnl_pct:+.1f}%, Score={r.score:.2f}")
        
        print(f"\nGlobal Best Parameters:")
        for k, v in global_best.items():
            print(f"  {k}: {v}")
        print("="*60)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest Parameter Optimizer")
    parser.add_argument('--quick', action='store_true', help='Quick mode: only weight optimization')
    parser.add_argument('--output', type=str, default='data/optimization_results', help='Output directory')
    
    args = parser.parse_args()
    
    optimizer = BacktestOptimizer(output_dir=args.output)
    await optimizer.optimize_all(quick_mode=args.quick)


if __name__ == '__main__':
    asyncio.run(main())
