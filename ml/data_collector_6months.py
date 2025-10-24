"""
OKX API ile 6 aylık veri çeken düzeltilmiş collector
Kullanıcının verdiği kodu sistemimize uyarladık.
"""

import time
import math
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from infrastructure.bootstrap import load_env

class MLDataCollector6Months:
    """OKX API ile gerçek 6 aylık veri çeken collector."""
    
    def __init__(self):
        load_env()
        
        self.base_url = "https://www.okx.com"
        self.history_endpoint = "/api/v5/market/history-candles"
        
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
        self.symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
        self.timeframes = ['15m', '1h', '4h']
        
        logger.info("6-month data collector initialized")
    
    def utc_ms_now(self):
        """Şu anki UTC zamanı milisaniye cinsinden."""
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    
    def months_ago_ms(self, n_months: int = 6):
        """N ay önceki UTC zamanı milisaniye cinsinden."""
        days = 30 * n_months
        return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    
    def fetch_okx_history(self, instId: str, bar: str, months: int = 6, 
                         limit_per_req: int = 100, sleep_sec: float = 0.12, 
                         max_retries: int = 5) -> pd.DataFrame:
        """
        OKX v5 /market/history-candles ile 'months' kadar geçmişi geriye sayfalar.
        
        Args:
            instId: 'BTC-USDT', 'BTC-USDT-SWAP' vb.
            bar: '5m', '15m', '1H', '4H' 
            months: Kaç ay geriye gidilecek
            limit_per_req: Her request'te kaç bar çekilecek
            sleep_sec: Request'ler arası bekleme süresi
            max_retries: Maksimum deneme sayısı
            
        Returns:
            DataFrame with OHLCV data
        """
        start_ts = self.months_ago_ms(months)
        cursor_before = self.utc_ms_now()
        
        logger.info(f"Fetching {months} months of {bar} data for {instId}")
        logger.info(f"Date range: {datetime.fromtimestamp(start_ts/1000)} to {datetime.fromtimestamp(cursor_before/1000)}")
        
        all_rows = []
        session = requests.Session()
        request_count = 0
        
        while True:
            params = {
                "instId": instId,
                "bar": bar,
                "limit": str(limit_per_req),
                "before": str(cursor_before),
            }
            
            # Retry logic
            for attempt in range(1, max_retries + 1):
                try:
                    logger.debug(f"Request {request_count + 1}, attempt {attempt}: {params}")
                    r = session.get(self.base_url + self.history_endpoint, params=params, timeout=20)
                    r.raise_for_status()
                    payload = r.json()
                    data = payload.get("data", [])
                    break
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt} failed: {e}, retrying...")
                    time.sleep(0.5 * attempt)
            
            if not data:
                logger.info("No more data available")
                break
            
            # Veri filtreleme ve ekleme
            stop_here = False
            added_count = 0
            
            for row in data:
                ts = int(row[0])
                if ts < start_ts:
                    stop_here = True
                    continue
                all_rows.append(row)
                added_count += 1
            
            logger.info(f"Request {request_count + 1}: Got {len(data)} bars, added {added_count} (total: {len(all_rows)})")
            
            # Bir sonraki sayfa için cursor güncelle
            oldest_ts = min(int(x[0]) for x in data)
            cursor_before = oldest_ts
            
            if stop_here:
                logger.info(f"Reached {months}-month limit: {datetime.fromtimestamp(oldest_ts/1000)}")
                break
            
            # Rate limiting
            time.sleep(sleep_sec)
            request_count += 1
            
            # Güvenlik için maksimum request sayısı
            if request_count > 200:
                logger.warning("Reached maximum request limit (200)")
                break
        
        # Kronolojik sıraya diz (eski -> yeni)
        all_rows.sort(key=lambda x: int(x[0]))
        
        # 6 ay sınırından daha eski satırlar varsa ayıkla
        all_rows = [row for row in all_rows if int(row[0]) >= start_ts]
        
        # Kapanmamış son mumu at (confirm = 0 olabilir)
        if all_rows:
            last_confirm = int(all_rows[-1][8]) if len(all_rows[-1]) > 8 else 1
            if last_confirm == 0:
                all_rows = all_rows[:-1]
                logger.info("Removed unconfirmed last candle")
        
        # DataFrame oluştur
        df = pd.DataFrame(all_rows, columns=[
            "ts", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm"
        ])
        
        if not df.empty:
            df["time_utc"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
            # Sütunları düzenle
            df = df[["time_utc", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm", "ts"]]
            
            # OHLCV sütunlarını float'a çevir
            df = df.astype({
                'open': float, 'high': float, 'low': float, 'close': float, 'volume': float
            })
            
            logger.info(f"✅ Collected {len(df)} bars from {df['time_utc'].iloc[0]} to {df['time_utc'].iloc[-1]}")
        
        return df
    
    def collect_all_data_6months(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Tüm semboller ve zaman dilimleri için 6 aylık veri topla."""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Collecting 6 months data for {symbol}...")
            symbol_data = {}
            
            for timeframe in self.timeframes:
                logger.info(f"  Collecting {timeframe} data...")
                try:
                    df = self._collect_symbol_data_6months(symbol, timeframe)
                    symbol_data[timeframe] = df
                    logger.info(f"    Collected {len(df)} bars")
                    
                    # Save individual file
                    filename = f"{symbol.replace('-', '_')}_{timeframe}_6months_real.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=False)
                    logger.info(f"    Saved to {filepath}")
                    
                    time.sleep(1)  # Rate limiting between symbols
                    
                except Exception as e:
                    logger.error(f"    Failed to collect {symbol} {timeframe}: {e}")
                    continue
            
            all_data[symbol] = symbol_data
        
        return all_data
    
    def _collect_symbol_data_6months(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Tek sembol için 6 aylık veri toplama."""
        # Spot sembol kullan (SWAP değil)
        spot_symbol = symbol  # BTC-USDT, ETH-USDT, SOL-USDT
        
        # Timeframe formatını OKX'e uyarla
        tf_map = {
            '15m': '15m', 
            '1h': '1H', 
            '4h': '4H'
        }
        okx_tf = tf_map.get(timeframe, '15m')
        
        # 6 aylık veri çek
        df = self.fetch_okx_history(instId=spot_symbol, bar=okx_tf, months=6)
        
        if df.empty:
            logger.warning(f"No data collected for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # Timestamp'i index yap
        df = df.set_index('time_utc')
        df = df[['open', 'high', 'low', 'close', 'volume']]  # Sadece OHLCV
        
        logger.info(f"    Final data: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        return df

def main():
    """Test the 6-month collector."""
    logger.info("🚀 Starting 6-Month Data Collection...")
    
    collector = MLDataCollector6Months()
    all_data = collector.collect_all_data_6months()
    
    # Summary
    total_bars = sum(len(df) for symbol_data in all_data.values() for df in symbol_data.values())
    logger.info(f"✅ 6-month collection completed! Total bars: {total_bars}")
    
    # Detailed summary
    for symbol, timeframes_data in all_data.items():
        logger.info(f"\n{symbol}:")
        for tf, df in timeframes_data.items():
            if not df.empty:
                duration = (df.index.max() - df.index.min()).days
                logger.info(f"  {tf}: {len(df)} bars, {duration} days")

if __name__ == "__main__":
    main()

