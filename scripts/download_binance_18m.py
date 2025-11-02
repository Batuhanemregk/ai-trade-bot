"""
Download 18 months of historical OHLCV data from Binance for ML training.
"""

import ccxt.async_support as ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class BinanceDataDownloader:
    """Download historical data from Binance."""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        self.output_dir = Path("data/ml_training")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        days: int = 540  # 18 months
    ) -> pd.DataFrame:
        """Download OHLCV data from Binance."""
        logger.info(f"Downloading {days} days of {timeframe} data for {symbol}")
        
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Convert to milliseconds
            since = int(start_time.timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            # Download in batches
            while True:
                try:
                    logger.info(f"Fetching data from {datetime.fromtimestamp(current_since/1000)}")
                    
                    ohlcv = await self.exchange.fetch_ohlcv(
                        symbol,
                        timeframe=timeframe,
                        since=current_since,
                        limit=1000  # Binance max is 1000
                    )
                    
                    if not ohlcv:
                        break
                    
                    all_data.extend(ohlcv)
                    
                    # Update since to last timestamp + 1ms
                    current_since = ohlcv[-1][0] + 1
                    
                    # Check if we've reached the end
                    if datetime.fromtimestamp(current_since/1000) >= end_time:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
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
        # Create filename matching existing format
        symbol_clean = symbol.replace('/', '').replace('USDT', 'USDT')
        filename = f"{symbol_clean}_{timeframe}_18months_binance.csv"
        filepath = self.output_dir / filename
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        logger.info(f"Saved {len(df)} bars to {filepath}")
        return str(filepath)
    
    async def download_and_save(
        self,
        symbol: str,
        timeframe: str,
        days: int = 540
    ) -> str:
        """Download data and save to CSV."""
        df = await self.download_ohlcv(symbol, timeframe, days)
        filepath = await self.save_to_csv(df, symbol, timeframe)
        return filepath
    
    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()


async def main():
    """Download 18 months of data for ML training."""
    downloader = BinanceDataDownloader()
    
    # Symbols to download
    symbols = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT"
    ]
    
    timeframes = ['15m', '1h', '4h']
    days = 540  # 18 months
    
    logger.info(f"Starting download: {len(symbols)} symbols, {len(timeframes)} TFs, {days} days")
    
    try:
        for symbol in symbols:
            for tf in timeframes:
                symbol_display = symbol.replace('/', '')
                logger.info(f"\n{'='*80}")
                logger.info(f"Downloading {symbol_display} {tf}...")
                
                try:
                    filepath = await downloader.download_and_save(
                        symbol=symbol,
                        timeframe=tf,
                        days=days
                    )
                    
                    # Load and display summary
                    df = pd.read_csv(filepath)
                    logger.info(f"[OK] {symbol_display} {tf}: {len(df)} bars")
                    logger.info(f"     Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
                    
                except Exception as e:
                    logger.error(f"[FAIL] {symbol_display} {tf}: {e}")
        
        logger.info("\n" + "="*80)
        logger.info("[OK] Download complete!")
        logger.info("="*80)
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Binance 18-Month Data Downloader for ML Training")
    print("="*80 + "\n")
    
    asyncio.run(main())


