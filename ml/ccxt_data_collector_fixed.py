"""
Düzeltilmiş CCXT Data Collector - Veri atlamalarını önler
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
from pathlib import Path
from loguru import logger

class CCXTDataCollectorFixed:
    """Düzeltilmiş CCXT ile 6 aylık veri çeken collector."""
    
    def __init__(self):
        self.exchange = ccxt.okx({
            'sandbox': False,
            'rateLimit': 100,
        })
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        # ML için gerekli semboller ve timeframes
        self.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        self.timeframes = ['15m', '1h', '4h']
        
        logger.info("Fixed CCXT data collector initialized")
    
    def fetch_with_fixed_pagination(self, symbol, timeframe, months=6):
        """Düzeltilmiş sayfalama ile veri çekme - atlamaları önler."""
        
        # 6 ay önce
        since = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"Fetching {months} months of {timeframe} data for {symbol}")
        logger.info(f"Since: {datetime.fromtimestamp(since/1000)}")
        logger.info(f"Now: {datetime.fromtimestamp(now/1000)}")
        
        all_ohlcv = []
        current_since = since
        request_count = 0
        max_requests = 100
        last_timestamp = None
        
        while current_since < now and request_count < max_requests:
            try:
                logger.debug(f"Request {request_count + 1}: since={datetime.fromtimestamp(current_since/1000)}")
                
                # CCXT ile veri çek
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=1000
                )
                
                if not ohlcv:
                    logger.info("No more data available")
                    break
                
                # Veri atlamalarını kontrol et
                if last_timestamp and ohlcv[0][0] > last_timestamp + 1:
                    logger.warning(f"Data gap detected! Last: {last_timestamp}, Current: {ohlcv[0][0]}")
                    # Eksik veriyi doldurmak için since'i güncelle
                    current_since = last_timestamp + 1
                    continue
                
                # Veriyi ekle
                all_ohlcv.extend(ohlcv)
                logger.info(f"Got {len(ohlcv)} bars (total: {len(all_ohlcv)})")
                
                # Bir sonraki sayfa için since güncelle
                last_timestamp = ohlcv[-1][0]
                current_since = last_timestamp + 1
                
                # Rate limiting
                time.sleep(0.2)  # Daha yavaş
                request_count += 1
                
            except Exception as e:
                logger.error(f"Error in request {request_count + 1}: {e}")
                break
        
        if all_ohlcv:
            # DataFrame oluştur
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            # Duplicate'leri kaldır
            df = df[~df.index.duplicated(keep='first')]
            
            # Veri atlamalarını kontrol et
            df = df.sort_index()
            time_diff = df.index.to_series().diff()
            expected_interval = self._get_expected_interval(timeframe)
            
            # Büyük atlamaları bul
            large_gaps = time_diff[time_diff > expected_interval * 2]
            if not large_gaps.empty:
                logger.warning(f"Large gaps detected in {timeframe} data:")
                for gap_time, gap_duration in large_gaps.items():
                    logger.warning(f"  Gap at {gap_time}: {gap_duration}")
            
            logger.info(f"Final result: {len(df)} bars")
            logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"Duration: {(df.index.max() - df.index.min()).days} days")
            
            return df
        else:
            logger.warning("No data collected")
            return pd.DataFrame()
    
    def _get_expected_interval(self, timeframe):
        """Beklenen zaman aralığını döndür."""
        intervals = {
            '15m': pd.Timedelta(minutes=15),
            '1h': pd.Timedelta(hours=1),
            '4h': pd.Timedelta(hours=4)
        }
        return intervals.get(timeframe, pd.Timedelta(hours=1))
    
    def collect_all_data_fixed(self):
        """Düzeltilmiş veri toplama."""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Collecting data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self.fetch_with_fixed_pagination(symbol, timeframe, months=6)
                    symbol_data[timeframe] = df
                    
                    if not df.empty:
                        # ML training formatına uygun kaydet
                        filename = f"{symbol.replace('/', '_').replace(':', '_')}_{timeframe}_6months_fixed.csv"
                        filepath = self.data_dir / filename
                        df.to_csv(filepath)
                        logger.info(f"    Saved {len(df)} bars to {filepath}")
                    else:
                        logger.warning(f"    No data for {symbol} {timeframe}")
                    
                    time.sleep(2)  # Daha uzun bekleme
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        return all_data

def main():
    """Düzeltilmiş veri toplama."""
    logger.info("🚀 Starting Fixed CCXT 6-Month Data Collection...")
    
    collector = CCXTDataCollectorFixed()
    all_data = collector.collect_all_data_fixed()
    
    # Summary
    total_bars = sum(len(df) for symbol_data in all_data.values() for df in symbol_data.values())
    logger.info(f"✅ Fixed CCXT collection completed! Total bars: {total_bars}")
    
    # Detailed summary
    for symbol, timeframes_data in all_data.items():
        logger.info(f"\n{symbol}:")
        for tf, df in timeframes_data.items():
            if not df.empty:
                duration = (df.index.max() - df.index.min()).days
                logger.info(f"  {tf}: {len(df)} bars, {duration} days")

if __name__ == "__main__":
    main()

