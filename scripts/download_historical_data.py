"""
Download historical OHLCV data from OKX exchange.
Saves to CSV format for backtesting.
"""

import asyncio
import ccxt.async_support as ccxt
from datetime import datetime, timedelta, timezone
import pandas as pd
from pathlib import Path
from loguru import logger
import os
from dotenv import load_dotenv


class OKXDataDownloader:
    """Download historical data from OKX."""
    
    def __init__(self):
        load_dotenv()
        self.exchange = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_API_SECRET'),
            'password': os.getenv('OKX_API_PASSPHRASE'),
            'enableRateLimit': True,
        })
        self.output_dir = Path("backtests/data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_ohlcv(
        self,
        symbol: str = "BTC/USDT:USDT",
        timeframe: str = "15m",
        days: int = 30,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Download OHLCV data from OKX.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT:USDT" for swap)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            days: Number of days to download
            limit: Bars per request (max 300 for OKX)
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Downloading {days} days of {timeframe} data for {symbol}")
        
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Convert to milliseconds
            since = int(start_time.timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            # Download in batches
            while True:
                try:
                    logger.info(f"Fetching data from {datetime.fromtimestamp(current_since/1000, timezone.utc)}")
                    
                    ohlcv = await self.exchange.fetch_ohlcv(
                        symbol,
                        timeframe=timeframe,
                        since=current_since,
                        limit=min(limit, 300)  # OKX max is 300
                    )
                    
                    if not ohlcv:
                        break
                    
                    all_data.extend(ohlcv)
                    
                    # Update since to last timestamp + 1ms
                    current_since = ohlcv[-1][0] + 1
                    
                    # Check if we've reached the end
                    if datetime.fromtimestamp(current_since/1000, timezone.utc) >= end_time:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error fetching batch: {e}")
                    break
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            
            # Add symbol column
            df['symbol'] = symbol.split('/')[0] + '-USDT'  # BTC/USDT:USDT -> BTC-USDT
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
            
            logger.info(f"Downloaded {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            raise
    
    async def save_to_csv(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> str:
        """Save DataFrame to CSV file."""
        # Create filename
        symbol_clean = symbol.replace('/', '-').replace(':', '')
        filename = f"{symbol_clean}_{timeframe}.csv"
        filepath = self.output_dir / filename
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        logger.info(f"Saved {len(df)} bars to {filepath}")
        return str(filepath)
    
    async def download_and_save(
        self,
        symbol: str = "BTC/USDT:USDT",
        timeframe: str = "15m",
        days: int = 30
    ) -> str:
        """Download data and save to CSV."""
        df = await self.download_ohlcv(symbol, timeframe, days)
        filepath = await self.save_to_csv(df, symbol, timeframe)
        return filepath
    
    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()


async def main():
    """Download historical data for multiple symbols."""
    downloader = OKXDataDownloader()
    
    # Symbols to download
    symbols = [
        ("BTC/USDT:USDT", "BTC-USDT"),
        ("ETH/USDT:USDT", "ETH-USDT"),
    ]
    
    timeframe = "15m"
    days = 180  # Last 180 days for ML training
    
    logger.info(f"Starting download: {len(symbols)} symbols, {days} days, {timeframe} timeframe")
    
    try:
        for okx_symbol, display_symbol in symbols:
            logger.info(f"\nDownloading {display_symbol}...")
            
            try:
                filepath = await downloader.download_and_save(
                    symbol=okx_symbol,
                    timeframe=timeframe,
                    days=days
                )
                
                # Load and display summary
                df = pd.read_csv(filepath)
                logger.info(f"[OK] {display_symbol}: {len(df)} bars")
                logger.info(f"     Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
                logger.info(f"     Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                
            except Exception as e:
                logger.error(f"[FAIL] {display_symbol}: {e}")
        
        logger.info("\n[OK] Download complete!")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("OKX Historical Data Downloader")
    print("="*60 + "\n")
    
    asyncio.run(main())

