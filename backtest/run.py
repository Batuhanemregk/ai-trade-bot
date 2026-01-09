"""
Backtest CLI Entrypoint.

Usage:
    python -m backtest.run --symbol BTC-USDT-SWAP --tf 15m --start 2024-07-01 --end 2025-12-26

Examples:
    # Basic run
    python -m backtest.run --symbol BTC-USDT-SWAP
    
    # Full options
    python -m backtest.run \
        --symbol BTC-USDT-SWAP \
        --tf 15m \
        --start 2024-07-01 \
        --end 2025-12-26 \
        --initial_balance 10000 \
        --intrabar_mode conservative \
        --fee_bps 6 \
        --slippage_bps 3 \
        --output_dir data/backtest_results/my_run
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

# Configure logger for backtest
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)


def main():
    parser = argparse.ArgumentParser(
        description="Event-Driven Backtest for ai-trade-bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backtest.run --symbol BTC-USDT-SWAP
  python -m backtest.run --symbol ETH-USDT-SWAP --start 2024-01-01 --end 2024-06-01
  python -m backtest.run --symbol BTC-USDT-SWAP --intrabar_mode optimistic --fee_bps 4
        """
    )
    
    # Required
    parser.add_argument(
        '--symbol', 
        type=str, 
        default='BTC-USDT-SWAP',
        help='Trading symbol (default: BTC-USDT-SWAP)'
    )
    
    # Date range
    parser.add_argument(
        '--tf',
        type=str,
        default='15m',
        help='Timeframe (default: 15m)'
    )
    parser.add_argument(
        '--start',
        type=str,
        default=None,
        help='Start date YYYY-MM-DD (default: 2024-07-01)'
    )
    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='End date YYYY-MM-DD (default: today)'
    )
    
    # Capital
    parser.add_argument(
        '--initial_balance',
        type=float,
        default=10000.0,
        help='Initial balance in USDT (default: 10000)'
    )
    
    # Execution params
    parser.add_argument(
        '--intrabar_mode',
        type=str,
        choices=['conservative', 'optimistic'],
        default='conservative',
        help='Intrabar TP/SL tie-break: conservative=SL wins, optimistic=TP wins (default: conservative)'
    )
    parser.add_argument(
        '--fee_bps',
        type=float,
        default=6.0,
        help='Taker fee in basis points (default: 6 = 0.06%%)'
    )
    parser.add_argument(
        '--slippage_bps',
        type=float,
        default=3.0,
        help='Slippage in basis points (default: 3 = 0.03%%)'
    )
    
    # Output
    parser.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='Output directory (default: data/backtest_results/SYMBOL_YYYYMMDD_HHMMSS)'
    )
    
    # Logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Parse dates
    if args.start:
        start_date = args.start
    else:
        # Default: 18 months ago
        start_date = (datetime.now() - timedelta(days=540)).strftime('%Y-%m-%d')
    
    if args.end:
        end_date = args.end
    else:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f"data/backtest_results/{args.symbol}_{timestamp}"
    
    # Print config
    print("\n" + "="*60)
    print("BACKTEST CONFIGURATION")
    print("="*60)
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.tf}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Balance: ${args.initial_balance:,.2f}")
    print(f"Intrabar Mode: {args.intrabar_mode}")
    print(f"Fee: {args.fee_bps} bps ({args.fee_bps/100:.3f}%)")
    print(f"Slippage: {args.slippage_bps} bps ({args.slippage_bps/100:.3f}%)")
    print(f"Output: {output_dir}")
    print("="*60 + "\n")
    
    # Check data file exists
    data_file = Path(f"data/backtest_ohlcv/{args.symbol}_15m.csv")
    if not data_file.exists():
        print(f"❌ ERROR: Data file not found: {data_file}")
        print(f"\nTo create data file, run:")
        print(f"  python -m backtest.fetch_data --symbol {args.symbol}")
        print(f"\nOr manually create CSV with columns: timestamp,open,high,low,close,volume")
        sys.exit(1)
    
    # Run backtest
    try:
        from backtest.backtest_engine import run_backtest
        
        summary = run_backtest(
            symbol=args.symbol,
            start_date=start_date,
            end_date=end_date,
            initial_balance=args.initial_balance,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
            intrabar_mode=args.intrabar_mode,
            output_dir=output_dir
        )
        
        print(f"\n✅ Backtest complete! Results saved to: {output_dir}/")
        print(f"   - trades.csv")
        print(f"   - summary.json")
        print(f"   - gate_stats.csv")
        print(f"   - equity_curve.csv")
        
        return summary
        
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
