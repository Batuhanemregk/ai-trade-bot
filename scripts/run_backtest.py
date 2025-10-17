"""
Run a simple backtest for testing purposes.
"""

import asyncio
from backtests.engine import BacktestEngine

async def main():
    print("\n" + "="*60)
    print("Running Backtest MVP Test")
    print("="*60 + "\n")
    
    # Initialize engine
    engine = BacktestEngine(initial_capital=10000.0)
    
    # Run backtest
    print("Running backtest on sample data...")
    results = await engine.run(
        data_file="BTC-USDT_15m_sample.csv",
        symbol="BTC-USDT"
    )
    
    # Print summary
    engine.metrics_calc.print_summary(results['metrics'])
    
    # Print sample trades
    if len(results['trades']) > 0:
        print("First 5 Trades:")
        for i, trade in enumerate(results['trades'][:5], 1):
            print(f"  {i}. {trade['direction']} @ ${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f}, "
                  f"PnL=${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%), {trade['exit_reason']}")
        
        if len(results['trades']) > 5:
            print(f"  ... and {len(results['trades'])-5} more trades")
    
    print("\n[OK] Backtest MVP test complete!")

if __name__ == "__main__":
    asyncio.run(main())

