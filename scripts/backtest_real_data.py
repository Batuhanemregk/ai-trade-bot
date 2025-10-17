"""
Run backtest on real OKX historical data.
"""

import asyncio
from backtests.engine import BacktestEngine
from backtests.visualizer import EquityCurveVisualizer

async def main():
    print("\n" + "="*60)
    print("BACKTEST - REAL OKX DATA (30 DAYS)")
    print("="*60 + "\n")
    
    # Initialize
    engine = BacktestEngine(initial_capital=10000.0)
    viz = EquityCurveVisualizer()
    
    # Run backtest on BTC
    print("Running backtest on BTC-USDT (real data)...")
    results = await engine.run(
        data_file="BTC-USDTUSDT_15m.csv",
        symbol="BTC-USDT"
    )
    
    # Print summary
    engine.metrics_calc.print_summary(results['metrics'])
    
    # Export trades
    trades_csv = viz.export_trades_csv(results['trades'], "BTC-USDT")
    print(f"\n[OK] Trades exported: {trades_csv}")
    
    # Sample trades
    if len(results['trades']) > 0:
        print("\nFirst 5 Trades:")
        for i, trade in enumerate(results['trades'][:5], 1):
            print(f"  {i}. {trade['direction']} @ ${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f}, "
                  f"PnL=${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%), {trade['exit_reason']}")
        
        if len(results['trades']) > 5:
            print(f"  ... and {len(results['trades'])-5} more trades")
    
    print("\n[OK] Backtest complete!")
    print(f"\nResults summary:")
    print(f"  Initial Capital: ${results['metrics']['initial_capital']:,.2f}")
    print(f"  Final Capital:   ${results['metrics'].get('final_capital', 0):,.2f}")
    print(f"  Total Return:    {results['metrics']['total_return']:.2f}%")
    print(f"  Sharpe Ratio:    {results['metrics']['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:    {results['metrics']['max_drawdown_pct']:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())

