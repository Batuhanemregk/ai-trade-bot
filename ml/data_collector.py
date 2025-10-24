"""
Data Collector for ML Training
Collects 6 months of historical data for multiple symbols and timeframes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Dict, List, Optional
from loguru import logger

from infrastructure.bootstrap import load_env
import requests
import time
import math
from datetime import datetime, timedelta, timezone


class MLDataCollector:
    """Collects historical data for ML training."""
    
    def __init__(self):
        # Load environment first
        load_env()
        
        # OKX REST API v5 endpoints
        self.base_url = "https://www.okx.com"
        self.history_endpoint = "/api/v5/market/history-candles"
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        # Symbols to collect
        self.symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
        
        # Timeframes to collect
        self.timeframes = ['15m', '1h', '4h']
        
        # 6 months back - but OKX API has limits
        # We'll try to get as much historical data as possible
        self.end_time = datetime.now()
        self.start_time = self.end_time - timedelta(days=180)
        
        # Note: OKX API typically returns limited historical data
        # For 6 months of 15m data, we need ~17,280 bars
        # But API might only return 300-1000 bars per request
        
        logger.info(f"Data collection period: {self.start_time} to {self.end_time}")
    
    def fetch_okx_ohlcv_6m(self, instId: str, bar: str, max_rows: int = None) -> List[List]:
        """
        6 ay geriye kadar OHLCV çeker ve kronolojik sırada döndürür.
        bar: 1m, 5m, 15m, 1H, 4H, 1Dutc, 1Wutc, 1Mutc ...
        max_rows: İstersen üst limit koy (örn. eğitim için ~200k satır vs.)
        """
        # 6 ay önce (UTC ms) - OKX API gelecek tarih döndürüyor, filtrelemeyi kaldırıyoruz
        end_ts = int(time.time() * 1000)  # şimdi
        start_ts = int((datetime.now(timezone.utc) - timedelta(days=182)).timestamp() * 1000)
        
        # 6 aylık veri için gerekli bar sayısı
        if bar == '15m':
            bars_needed = 182 * 24 * 4  # 6 ay * 24 saat * 4 (15m per hour) = 17,472
        elif bar == '1H':
            bars_needed = 182 * 24  # 6 ay * 24 saat = 4,368
        elif bar == '4H':
            bars_needed = 182 * 6  # 6 ay * 6 (4h per day) = 1,092
        else:
            bars_needed = 20000  # Default
            
        logger.info(f"    Target: {bars_needed} bars for 6 months of {bar} data")

        all_rows = []
        params = {"instId": instId, "bar": bar, "limit": "300"}  # history-candles max 300
        cursor = None

        # OKX API gelecek tarih döndürüyor, before parametresini kaldırıyoruz
        # Sadece limit ile en son veriyi alacağız

        request_count = 0
        while True:
            try:
                logger.info(f"    Making request {request_count + 1} with params: {params}")
                r = requests.get(self.base_url + self.history_endpoint, params=params, timeout=20)
                r.raise_for_status()
                data = r.json()["data"]
                logger.info(f"    Response: {len(data) if data else 0} bars")
                if not data:
                    logger.info("    No more data, breaking")
                    break

                # OKX sıralaması en yeni -> en eski dönebilir; biz eklerken biriktiriyoruz
                # Her satır: [ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm]
                for row in data:
                    ts = int(row[0])
                    # Tüm veriyi al, filtrelemeyi sonra yapacağız
                    all_rows.append(row)

                # Bir sonraki sayfa için imleç: paketin en eski ts'sini "before" yapıp geriye git
                oldest_ts = min(int(x[0]) for x in data)
                if oldest_ts <= start_ts:
                    break

                params["before"] = str(oldest_ts)

                # 6 aylık veri için gerekli bar sayısına ulaştık mı?
                if len(all_rows) >= bars_needed:
                    logger.info(f"    ✅ Reached target: {len(all_rows)} bars (needed: {bars_needed})")
                    break
                    
                if max_rows and len(all_rows) >= max_rows:
                    break

                # nazik hız: rate limit 20 req/2s → ~10 rps; ufak uyku koyabilirsin
                time.sleep(0.1)
                
                request_count += 1
                logger.info(f"    Request {request_count}: Collected {len(data)} bars, total: {len(all_rows)}")

            except Exception as e:
                logger.error(f"    Error in request {request_count}: {e}")
                break

        # Kronolojik sıraya çevir (eski -> yeni)
        all_rows = sorted(all_rows, key=lambda x: int(x[0]))
        
        # OKX API gelecek tarih döndürüyor, filtrelemeyi kaldırıyoruz
        # Tüm veriyi al, 6 aylık sınırı max_rows ile kontrol et
        logger.info(f"    Collected: {len(all_rows)} bars")
        if all_rows:
            logger.info(f"    Data: {datetime.utcfromtimestamp(int(all_rows[0][0])/1000)} to {datetime.utcfromtimestamp(int(all_rows[-1][0])/1000)}")
        
        return all_rows

    def collect_all_data(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Collect data for all symbols and timeframes."""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Collecting data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self._collect_symbol_data(symbol, timeframe)
                    symbol_data[timeframe] = df
                    logger.info(f"    Collected {len(df)} bars")
                    
                    # Save individual file
                    filename = f"{symbol.replace('-', '_')}_{timeframe}_6months.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=True)
                    logger.info(f"    Saved to {filepath}")
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        # Save combined data - removed due to DataFrame index uniqueness issues
        
        return all_data
    
    def _collect_symbol_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Collect data for a single symbol and timeframe using OKX REST v5."""
        # Convert to futures symbol
        futures_symbol = symbol.replace('-USDT', '-USDT-SWAP')
        
        # Convert timeframe to OKX format
        tf_map = {
            '15m': '15m', '1h': '1H', '4h': '4H'
        }
        okx_tf = tf_map.get(timeframe, '15m')
        
        # Fetch 6 months of data using OKX REST v5
        logger.info(f"    Fetching 6 months of {timeframe} data for {symbol}...")
        rows = self.fetch_okx_ohlcv_6m(instId=futures_symbol, bar=okx_tf)
        
        if not rows:
            logger.warning(f"    No data collected for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        # OKX format: [ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm]
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vol_ccy', 'vol_ccy_quote', 'confirm'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
        df = df.set_index('timestamp')
        
        # Filter by date range
        cutoff_date = self.end_time - timedelta(days=180)
        df = df[df.index >= cutoff_date]
        
        logger.info(f"    Final data: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        return df
    
    
    def get_data_summary(self, all_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, any]:
        """Get summary of collected data."""
        summary = {
            "collection_time": datetime.now().isoformat(),
            "period": f"{self.start_time} to {self.end_time}",
            "symbols": {},
            "total_bars": 0
        }
        
        for symbol, timeframes in all_data.items():
            symbol_summary = {}
            for tf, df in timeframes.items():
                symbol_summary[tf] = {
                    "bars": len(df),
                    "start_date": df.index[0].isoformat() if not df.empty else None,
                    "end_date": df.index[-1].isoformat() if not df.empty else None,
                    "columns": list(df.columns)
                }
                summary["total_bars"] += len(df)
            
            summary["symbols"][symbol] = symbol_summary
        
        return summary


def main():
    """Main function to collect data."""
    logger.info("🚀 Starting ML data collection...")
    
    collector = MLDataCollector()
    
    # Collect all data
    all_data = collector.collect_all_data()
    
    # Get summary
    summary = collector.get_data_summary(all_data)
    
    # Save summary
    summary_file = collector.data_dir / "data_summary.json"
    import json
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("✅ Data collection completed!")
    logger.info(f"📊 Total bars collected: {summary['total_bars']}")
    
    return all_data, summary


if __name__ == "__main__":
    main()
