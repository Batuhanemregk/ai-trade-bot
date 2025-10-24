"""
Fixed Data Collector - OKX API ile gerçek 6 aylık veri çekme
"""

import requests
import time
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd

from infrastructure.bootstrap import load_env

class FixedMLDataCollector:
    """OKX API ile gerçek 6 aylık veri çeken düzeltilmiş collector."""
    
    def __init__(self):
        load_env()
        
        self.base_url = "https://www.okx.com"
        self.history_endpoint = "/api/v5/market/history-candles"
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        self.symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
        self.timeframes = ['15m', '1h', '4h']
        
        logger.info("Fixed data collector initialized")
    
    def fetch_okx_ohlcv_6m_fixed(self, instId: str, bar: str, max_rows: int = None) -> List[List]:
        """
        OKX API ile gerçek 6 aylık veri çeker.
        """
        # 6 ay önce (UTC ms)
        end_ts = int(time.time() * 1000)  # şimdi
        start_ts = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
        
        logger.info(f"    Fetching 6 months of {bar} data for {instId}")
        logger.info(f"    Date range: {datetime.utcfromtimestamp(start_ts/1000)} to {datetime.utcfromtimestamp(end_ts/1000)}")
        
        all_rows = []
        params = {
            "instId": instId, 
            "bar": bar, 
            "limit": "300",
            "before": str(end_ts)  # En son veriden başla
        }

        request_count = 0
        max_requests = 200  # 6 ay için yeterli request
        
        while request_count < max_requests:
            try:
                logger.info(f"    Request {request_count + 1}: {params}")
                r = requests.get(self.base_url + self.history_endpoint, params=params, timeout=30)
                r.raise_for_status()
                
                data = r.json()
                if data.get('code') != '0':
                    logger.error(f"    OKX API error: {data.get('msg', 'Unknown error')}")
                    break
                    
                bars = data.get('data', [])
                logger.info(f"    Response: {len(bars)} bars")
                
                if not bars:
                    logger.info("    No more data available")
                    break

                # Veriyi ekle (6 aylık aralıkta olanları)
                added_count = 0
                for row in bars:
                    ts = int(row[0])
                    if start_ts <= ts <= end_ts:
                        all_rows.append(row)
                        added_count += 1

                logger.info(f"    Added {added_count} bars (total: {len(all_rows)})")

                # En eski timestamp'i bul
                oldest_ts = min(int(x[0]) for x in bars)
                
                # 6 aylık aralığın dışına çıktık mı?
                if oldest_ts < start_ts:
                    logger.info(f"    ✅ Reached 6-month limit: {datetime.utcfromtimestamp(oldest_ts/1000)}")
                    break

                # Bir sonraki sayfa için before parametresini güncelle
                params["before"] = str(oldest_ts)
                
                # Maksimum veri sayısına ulaştık mı?
                if max_rows and len(all_rows) >= max_rows:
                    logger.info(f"    Reached max_rows limit: {len(all_rows)}")
                    break

                # Rate limiting
                time.sleep(0.2)  # OKX rate limit: 20 req/2s
                request_count += 1

            except Exception as e:
                logger.error(f"    Error in request {request_count}: {e}")
                break

        # Kronolojik sıraya çevir (eski -> yeni)
        all_rows = sorted(all_rows, key=lambda x: int(x[0]))
        
        logger.info(f"    ✅ Final result: {len(all_rows)} bars")
        if all_rows:
            start_date = datetime.utcfromtimestamp(int(all_rows[0][0])/1000)
            end_date = datetime.utcfromtimestamp(int(all_rows[-1][0])/1000)
            duration_days = (end_date - start_date).days
            logger.info(f"    Date range: {start_date} to {end_date}")
            logger.info(f"    Duration: {duration_days} days ({duration_days/30.44:.1f} months)")
        
        return all_rows
    
    def collect_all_data_fixed(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Düzeltilmiş veri toplama."""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Collecting 6 months data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self._collect_symbol_data_fixed(symbol, timeframe)
                    symbol_data[timeframe] = df
                    logger.info(f"    Collected {len(df)} bars")
                    
                    # Save individual file
                    filename = f"{symbol.replace('-', '_')}_{timeframe}_6months_fixed.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=True)
                    logger.info(f"    Saved to {filepath}")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        return all_data
    
    def _collect_symbol_data_fixed(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Tek sembol için düzeltilmiş veri toplama."""
        futures_symbol = symbol.replace('-USDT', '-USDT-SWAP')
        
        tf_map = {
            '15m': '15m', '1h': '1H', '4h': '4H'
        }
        okx_tf = tf_map.get(timeframe, '15m')
        
        # Düzeltilmiş veri çekme
        rows = self.fetch_okx_ohlcv_6m_fixed(instId=futures_symbol, bar=okx_tf)
        
        if not rows:
            logger.warning(f"No data collected for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # DataFrame'e çevir
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vol_ccy', 'vol_ccy_quote', 'confirm'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
        df = df.set_index('timestamp')
        
        logger.info(f"    Final data: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        return df

def main():
    """Test the fixed collector."""
    logger.info("🚀 Starting Fixed Data Collection (6 months)...")
    
    collector = FixedMLDataCollector()
    all_data = collector.collect_all_data_fixed()
    
    # Summary
    total_bars = sum(len(df) for symbol_data in all_data.values() for df in symbol_data.values())
    logger.info(f"✅ Fixed collection completed! Total bars: {total_bars}")
    
    # Detailed summary
    for symbol, timeframes_data in all_data.items():
        logger.info(f"\n{symbol}:")
        for tf, df in timeframes_data.items():
            if not df.empty:
                duration = (df.index.max() - df.index.min()).days
                logger.info(f"  {tf}: {len(df)} bars, {duration} days")

if __name__ == "__main__":
    main()

