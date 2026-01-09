"""
Fetch and cache OHLCV data from OKX for backtesting.

Usage:
    python -m backtest.fetch_data --symbol BTC-USDT-SWAP --days 540
"""

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from loguru import logger


async def fetch_ohlcv_from_okx(symbol: str, timeframe: str = '15m', days: int = 540):
    """
    Fetch OHLCV data from OKX and save to CSV.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
        timeframe: Timeframe (e.g., '15m', '1h')
        days: Number of days to fetch
    """
    output_dir = Path("data/backtest_ohlcv")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{symbol}_{timeframe}.csv"
    
    logger.info(f"Fetching {symbol} {timeframe} data for last {days} days...")
    
    try:
        from adapters.exchange_okx_ccxt import OKXCCXTAdapter
        
        adapter = OKXCCXTAdapter()
        
        # Calculate start time
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Fetch in chunks (OKX limit is 100-300 candles per request)
        all_candles = []
        current_end = end_time
        
        # Determine candle duration
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        minutes = tf_minutes.get(timeframe, 15)
        
        while current_end > start_time:
            try:
                # Fetch 200 candles at a time
                candles = await adapter.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=200
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Move window back
                oldest_ts = candles[0][0]
                current_end = datetime.fromtimestamp(oldest_ts / 1000)
                
                logger.info(f"Fetched {len(candles)} candles, oldest: {current_end}")
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Fetch error: {e}")
                break
        
        await adapter.close()
        
        if not all_candles:
            logger.error("No candles fetched")
            return
        
        # Create DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Sort and dedupe
        df.sort_values('timestamp', inplace=True)
        df.drop_duplicates(subset='timestamp', keep='first', inplace=True)
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        
        logger.info(f"✅ Saved {len(df)} candles to {output_file}")
        logger.info(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
    except ImportError:
        logger.error("OKX adapter not available. Please create CSV manually.")
        logger.info(f"\nExpected format for {output_file}:")
        logger.info("timestamp,open,high,low,close,volume")
        logger.info("2024-01-01 00:00:00,42000.0,42100.0,41900.0,42050.0,1000.5")
        
    except Exception as e:
        logger.exception(f"Failed to fetch data: {e}")


def main():
    parser = argparse.ArgumentParser(description="Fetch OHLCV data for backtesting")
    parser.add_argument('--symbol', type=str, default='BTC-USDT-SWAP', help='Trading symbol')
    parser.add_argument('--timeframe', '--tf', type=str, default='15m', help='Timeframe')
    parser.add_argument('--days', type=int, default=540, help='Days of history to fetch')
    
    args = parser.parse_args()
    
    asyncio.run(fetch_ohlcv_from_okx(args.symbol, args.timeframe, args.days))


if __name__ == '__main__':
    main()
