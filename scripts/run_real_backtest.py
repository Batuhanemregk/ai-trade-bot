"""
Run backtest with REAL bot strategy and save results.
"""

import asyncio
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtests.real_strategy_engine import RealStrategyBacktestEngine
from loguru import logger


async def main():
    """Run real strategy backtest and save results."""
    
    print("\n" + "="*60)
    print("REAL BOT STRATEGY BACKTEST")
    print("="*60 + "\n")
    
    # Initialize engine
    engine = RealStrategyBacktestEngine(initial_capital=10000.0)
    
    # Initialize components
    await engine.initialize_strategy_components()
    
    # Run backtest
    symbol = "BTC-USDT"
    data_file = "BTC-USDTUSDT_15m.csv"
    
    results = await engine.run(
        symbol=symbol,
        data_file=data_file
    )
    
    # Save trades to CSV
    if len(results['trades']) > 0:
        trades_df = pd.DataFrame(results['trades'])
        output_file = "backtests/real_strategy_trades.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n[OK] Saved {len(trades_df)} trades to {output_file}")
        
        # Show sample trades
        print("\nSample Trades:")
        print(trades_df[['entry_time', 'direction', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']].head(10))
    else:
        print("\n[WARNING] No trades executed")
    
    # Show performance summary
    engine.metrics_calc.print_summary(results['metrics'])
    
    print(f"\n[DONE] Backtest complete!")
    print(f"   Period: {results['start_date']} to {results['end_date']}")
    print(f"   Bars processed: {results['bars_processed']}")


if __name__ == "__main__":
    asyncio.run(main())

