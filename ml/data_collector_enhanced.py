"""
Enhanced Data Collector
OKX API limitlerini aşmak için farklı stratejiler.
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

class EnhancedMLDataCollector:
    """OKX API limitlerini aşmak için gelişmiş veri toplayıcı."""
    
    def __init__(self):
        load_env()
        
        self.base_url = "https://www.okx.com"
        self.history_endpoint = "/api/v5/market/history-candles"
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        self.symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
        self.timeframes = ['15m', '1h', '4h']
        
        logger.info("Enhanced data collector initialized")
    
    def fetch_extended_historical_data(self, instId: str, bar: str, days_back: int = 180) -> List[List]:
        """
        OKX API limitlerini aşmak için farklı stratejiler kullanır.
        """
        logger.info(f"Fetching {days_back} days of {bar} data for {instId}")
        
        all_data = []
        
        # Strateji 1: Farklı endpoint'ler dene
        endpoints_to_try = [
            "/api/v5/market/history-candles",
            "/api/v5/market/candles",  # Alternatif endpoint
        ]
        
        for endpoint in endpoints_to_try:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                data = self._fetch_from_endpoint(endpoint, instId, bar, days_back)
                if data:
                    all_data.extend(data)
                    logger.info(f"✅ Got {len(data)} bars from {endpoint}")
                    break
            except Exception as e:
                logger.warning(f"❌ Failed with {endpoint}: {e}")
                continue
        
        # Strateji 2: Farklı parametrelerle dene
        if not all_data:
            logger.info("Trying different parameters...")
            all_data = self._fetch_with_different_params(instId, bar, days_back)
        
        # Strateji 3: Multiple requests ile birleştir
        if not all_data:
            logger.info("Trying multiple requests strategy...")
            all_data = self._fetch_multiple_requests(instId, bar, days_back)
        
        return all_data
    
    def _fetch_from_endpoint(self, endpoint: str, instId: str, bar: str, days_back: int) -> List[List]:
        """Belirli endpoint'ten veri çeker."""
        params = {
            "instId": instId,
            "bar": bar,
            "limit": "300"
        }
        
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == '0':
            return data.get('data', [])
        return []
    
    def _fetch_with_different_params(self, instId: str, bar: str, days_back: int) -> List[List]:
        """Farklı parametrelerle veri çekmeyi dener."""
        all_data = []
        
        # Farklı limit değerleri dene
        limits = [100, 200, 300, 500]
        
        for limit in limits:
            try:
                params = {
                    "instId": instId,
                    "bar": bar,
                    "limit": str(limit)
                }
                
                response = requests.get(f"{self.base_url}{self.history_endpoint}", params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if data.get('code') == '0':
                    batch_data = data.get('data', [])
                    all_data.extend(batch_data)
                    logger.info(f"Got {len(batch_data)} bars with limit {limit}")
                    
                    if len(all_data) >= 1000:  # Yeterli veri varsa dur
                        break
                        
            except Exception as e:
                logger.warning(f"Failed with limit {limit}: {e}")
                continue
        
        return all_data
    
    def _fetch_multiple_requests(self, instId: str, bar: str, days_back: int) -> List[List]:
        """Çoklu request ile veri çeker."""
        all_data = []
        
        # Son 30 günlük veriyi çek
        end_time = int(time.time() * 1000)
        start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30 gün
        
        params = {
            "instId": instId,
            "bar": bar,
            "limit": "300",
            "before": str(end_time)
        }
        
        request_count = 0
        max_requests = 20  # Maksimum 20 request
        
        while request_count < max_requests:
            try:
                response = requests.get(f"{self.base_url}{self.history_endpoint}", params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if data.get('code') == '0':
                    batch_data = data.get('data', [])
                    if not batch_data:
                        break
                    
                    all_data.extend(batch_data)
                    
                    # Bir sonraki batch için before parametresini güncelle
                    oldest_ts = min(int(x[0]) for x in batch_data)
                    if oldest_ts <= start_time:
                        break
                    
                    params["before"] = str(oldest_ts)
                    request_count += 1
                    
                    logger.info(f"Request {request_count}: Got {len(batch_data)} bars, total: {len(all_data)}")
                    
                    time.sleep(0.1)  # Rate limiting
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Request {request_count} failed: {e}")
                break
        
        return all_data
    
    def collect_extended_data(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Gelişmiş veri toplama."""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Collecting extended data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self._collect_symbol_extended_data(symbol, timeframe)
                    symbol_data[timeframe] = df
                    logger.info(f"    Collected {len(df)} bars")
                    
                    # Save individual file
                    filename = f"{symbol.replace('-', '_')}_{timeframe}_extended.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=True)
                    logger.info(f"    Saved to {filepath}")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        return all_data
    
    def _collect_symbol_extended_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Tek sembol için gelişmiş veri toplama."""
        futures_symbol = symbol.replace('-USDT', '-USDT-SWAP')
        
        tf_map = {
            '15m': '15m', '1h': '1H', '4h': '4H'
        }
        okx_tf = tf_map.get(timeframe, '15m')
        
        # Gelişmiş veri çekme
        rows = self.fetch_extended_historical_data(instId=futures_symbol, bar=okx_tf, days_back=180)
        
        if not rows:
            logger.warning(f"No data collected for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # DataFrame'e çevir
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vol_ccy', 'vol_ccy_quote', 'confirm'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
        df = df.set_index('timestamp')
        
        # Tarih aralığını filtrele
        end_time = datetime.now()
        start_time = end_time - timedelta(days=180)
        df = df[df.index >= start_time]
        
        logger.info(f"Final data: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        return df

def main():
    """Test the enhanced collector."""
    logger.info("🚀 Starting Enhanced Data Collection...")
    
    collector = EnhancedMLDataCollector()
    all_data = collector.collect_extended_data()
    
    # Summary
    total_bars = sum(len(df) for symbol_data in all_data.values() for df in symbol_data.values())
    logger.info(f"✅ Enhanced collection completed! Total bars: {total_bars}")
    
    return all_data

if __name__ == "__main__":
    main()

