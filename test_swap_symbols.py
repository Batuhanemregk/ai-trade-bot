# SWAP sembolleri ile test et
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

BASE_URL = 'https://www.okx.com'
HIST_EP = '/api/v5/market/history-candles'

def test_swap_symbols():
    symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
    bar = '1H'
    
    for symbol in symbols:
        print(f'\n=== Testing {symbol} ===')
        
        params = {
            'instId': symbol,
            'bar': bar,
            'limit': '10'
        }
        
        try:
            r = requests.get(BASE_URL + HIST_EP, params=params, timeout=10)
            data = r.json()
            
            print(f'Status: {r.status_code}')
            print(f'Code: {data.get("code")}')
            print(f'Data length: {len(data.get("data", []))}')
            
            if data.get('data'):
                first_bar = data['data'][0]
                last_bar = data['data'][-1]
                first_time = datetime.fromtimestamp(int(first_bar[0])/1000)
                last_time = datetime.fromtimestamp(int(last_bar[0])/1000)
                print(f'First: {first_time}')
                print(f'Last: {last_time}')
                print(f'Duration: {(first_time - last_time).days} days')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == "__main__":
    test_swap_symbols()

