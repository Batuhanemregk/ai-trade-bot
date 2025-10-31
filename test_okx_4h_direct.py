"""
OKX REST API ile 4h veri testi
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

def test_okx_4h_direct():
    print('=== OKX REST API 4H VERİ TESTİ ===')

    # OKX REST API v5
    base_url = 'https://www.okx.com'
    endpoint = '/api/v5/market/history-candles'

    # 6 ay önce
    since = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    print(f'Since: {datetime.fromtimestamp(since/1000)}')
    print(f'Now: {datetime.fromtimestamp(now/1000)}')

    symbol = 'BTC-USDT-SWAP'
    timeframe = '4H'

    print(f'\nTesting {symbol} {timeframe} with OKX REST API...')

    all_data = []
    cursor_before = now  # En son veriden başla
    request_count = 0
    max_requests = 20

    while cursor_before > since and request_count < max_requests:
        try:
            print(f'Request {request_count + 1}: before={datetime.fromtimestamp(cursor_before/1000)}')
            
            params = {
                'instId': symbol,
                'bar': timeframe,
                'limit': '300',
                'before': str(cursor_before)
            }
            
            response = requests.get(base_url + endpoint, params=params, timeout=20)
            data = response.json()
            
            if data.get('code') != '0' or not data.get('data'):
                print(f'API Error: {data.get("msg", "Unknown error")}')
                break
            
            bars = data['data']
            if not bars:
                print('No more data')
                break
            
            all_data.extend(bars)
            print(f'Got {len(bars)} bars (total: {len(all_data)})')
            
            # Bir sonraki sayfa için cursor güncelle
            oldest_timestamp = min(int(bar[0]) for bar in bars)
            cursor_before = oldest_timestamp - 1
            
            time.sleep(0.1)
            request_count += 1
            
        except Exception as e:
            print(f'Error: {e}')
            break

    if all_data:
        # DataFrame oluştur
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vol_ccy', 'vol_ccy_quote', 'confirm'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        df = df[~df.timestamp.duplicated(keep='first')]
        
        print(f'\nFinal result: {len(df)} bars')
        print(f'Date range: {df.timestamp.min()} to {df.timestamp.max()}')
        print(f'Duration: {(df.timestamp.max() - df.timestamp.min()).days} days')
        
        # 6 aylık veri için gerekli bar sayısı
        bars_needed_6months = 180 * 6  # 6 ay * 6 (4h per day) = 1080
        print(f'Bars needed for 6 months: {bars_needed_6months}')
        print(f'Current bars: {len(df)}')
        print(f'Missing bars: {bars_needed_6months - len(df)}')
        
        return df
    else:
        print('No data collected')
        return None

if __name__ == "__main__":
    test_okx_4h_direct()

