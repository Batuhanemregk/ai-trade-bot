"""
Binance API ile 6 aylık veri çeken collector
Binance API daha uzun geçmiş veri sağlıyor.
"""

import requests
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

class BinanceDataCollector:
    """Binance API ile 6 aylık veri çeken collector."""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.klines_endpoint = "/api/v3/klines"
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        # Binance sembolleri
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.timeframes = ['15m', '1h', '4h']
        
        logger.info("Binance data collector initialized")
    
    def fetch_binance_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> List[List]:
        """
        Binance API ile klines verisi çeker.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '15m', '1h', '4h')
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            
        Returns:
            List of klines data
        """
        all_data = []
        limit = 1000  # Binance max limit per request
        
        while start_time < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': min(start_time + limit * self._interval_to_ms(interval), end_time),
                'limit': limit
            }
            
            try:
                logger.info(f"Fetching {symbol} {interval} from {datetime.fromtimestamp(start_time/1000)}")
                response = requests.get(self.base_url + self.klines_endpoint, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    break
                
                all_data.extend(data)
                logger.info(f"Got {len(data)} bars, total: {len(all_data)}")
                
                # Bir sonraki batch için start_time güncelle
                start_time = int(data[-1][0]) + 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching {symbol} {interval}: {e}")
                break
        
        return all_data
    
    def _interval_to_ms(self, interval: str) -> int:
        """Convert interval to milliseconds."""
        interval_map = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return interval_map.get(interval, 60 * 1000)
    
    def collect_6months_data(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """6 aylık veri topla."""
        all_data = {}
        
        # 6 ay önce
        end_time = int(time.time() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
        
        logger.info(f"Collecting 6 months data from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
        
        for symbol in self.symbols:
            logger.info(f"Collecting data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self._collect_symbol_data(symbol, timeframe, start_time, end_time)
                    symbol_data[timeframe] = df
                    logger.info(f"    Collected {len(df)} bars")
                    
                    # Save individual file
                    filename = f"{symbol}_{timeframe}_6months_binance.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=True)
                    logger.info(f"    Saved to {filepath}")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        return all_data
    
    def _collect_symbol_data(self, symbol: str, timeframe: str, start_time: int, end_time: int) -> pd.DataFrame:
        """Tek sembol için veri toplama."""
        # Binance interval formatı
        interval_map = {
            '15m': '15m',
            '1h': '1h', 
            '4h': '4h'
        }
        binance_interval = interval_map.get(timeframe, '15m')
        
        # Veri çek
        klines = self.fetch_binance_klines(symbol, binance_interval, start_time, end_time)
        
        if not klines:
            logger.warning(f"No data collected for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # DataFrame oluştur
        # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Timestamp'i datetime'a çevir
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df = df.set_index('timestamp')
        
        # Sadece OHLCV sütunlarını al
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        logger.info(f"    Final data: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        return df

def main():
    """Test the Binance collector."""
    logger.info("🚀 Starting Binance 6-Month Data Collection...")
    
    collector = BinanceDataCollector()
    all_data = collector.collect_6months_data()
    
    # Summary
    total_bars = sum(len(df) for symbol_data in all_data.values() for df in symbol_data.values())
    logger.info(f"✅ Binance collection completed! Total bars: {total_bars}")
    
    # Detailed summary
    for symbol, timeframes_data in all_data.items():
        logger.info(f"\n{symbol}:")
        for tf, df in timeframes_data.items():
            if not df.empty:
                duration = (df.index.max() - df.index.min()).days
                logger.info(f"  {tf}: {len(df)} bars, {duration} days")

if __name__ == "__main__":
    main()

