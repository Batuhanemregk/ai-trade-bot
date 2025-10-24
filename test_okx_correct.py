"""
OKX API ile doğru parametrelerle 6 aylık veri çekme testi
"""

import requests
import time
from datetime import datetime, timezone, timedelta

def test_okx_api_correct():
    """OKX API'yi doğru parametrelerle test et."""
    
    base_url = 'https://www.okx.com'
    endpoint = '/api/v5/market/history-candles'
    
    print('Testing OKX API with correct parameters...')
    
    # Test 1: Basit veri çekme (before parametresi olmadan)
    print('\n=== TEST 1: Basic data fetch ===')
    params1 = {
        'instId': 'BTC-USDT-SWAP',
        'bar': '1H',
        'limit': '10'
    }
    
    r1 = requests.get(base_url + endpoint, params=params1, timeout=10)
    data1 = r1.json()
    
    print(f'Status: {r1.status_code}')
    print(f'Response code: {data1.get("code")}')
    print(f'Data length: {len(data1.get("data", []))}')
    
    if data1.get('data'):
        first_bar = data1['data'][0]
        last_bar = data1['data'][-1]
        first_time = datetime.fromtimestamp(int(first_bar[0])/1000)
        last_time = datetime.fromtimestamp(int(last_bar[0])/1000)
        print(f'First bar: {first_time}')
        print(f'Last bar: {last_time}')
        print(f'Time span: {(first_time - last_time).days} days')
    
    # Test 2: before parametresi ile (6 ay öncesinden)
    print('\n=== TEST 2: With before parameter ===')
    
    # 6 ay önceki timestamp
    six_months_ago = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
    print(f'6 months ago timestamp: {six_months_ago}')
    print(f'6 months ago date: {datetime.fromtimestamp(six_months_ago/1000)}')
    
    params2 = {
        'instId': 'BTC-USDT-SWAP',
        'bar': '1H',
        'limit': '300',
        'before': str(six_months_ago)  # 6 ay öncesinden başla
    }
    
    r2 = requests.get(base_url + endpoint, params=params2, timeout=10)
    data2 = r2.json()
    
    print(f'Status: {r2.status_code}')
    print(f'Response code: {data2.get("code")}')
    print(f'Data length: {len(data2.get("data", []))}')
    
    if data2.get('data'):
        first_bar = data2['data'][0]
        last_bar = data2['data'][-1]
        first_time = datetime.fromtimestamp(int(first_bar[0])/1000)
        last_time = datetime.fromtimestamp(int(last_bar[0])/1000)
        print(f'First bar: {first_time}')
        print(f'Last bar: {last_time}')
        print(f'Time span: {(first_time - last_time).days} days')
    
    # Test 3: after parametresi ile
    print('\n=== TEST 3: With after parameter ===')
    
    # 1 ay önceki timestamp
    one_month_ago = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
    print(f'1 month ago timestamp: {one_month_ago}')
    print(f'1 month ago date: {datetime.fromtimestamp(one_month_ago/1000)}')
    
    params3 = {
        'instId': 'BTC-USDT-SWAP',
        'bar': '1H',
        'limit': '300',
        'after': str(one_month_ago)  # 1 ay öncesinden başla
    }
    
    r3 = requests.get(base_url + endpoint, params=params3, timeout=10)
    data3 = r3.json()
    
    print(f'Status: {r3.status_code}')
    print(f'Response code: {data3.get("code")}')
    print(f'Data length: {len(data3.get("data", []))}')
    
    if data3.get('data'):
        first_bar = data3['data'][0]
        last_bar = data3['data'][-1]
        first_time = datetime.fromtimestamp(int(first_bar[0])/1000)
        last_time = datetime.fromtimestamp(int(last_bar[0])/1000)
        print(f'First bar: {first_time}')
        print(f'Last bar: {last_time}')
        print(f'Time span: {(first_time - last_time).days} days')
    
    # Test 4: Pagination ile 6 aylık veri çekme
    print('\n=== TEST 4: Pagination for 6 months ===')
    
    all_data = []
    current_time = int(time.time() * 1000)
    six_months_ago = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp() * 1000)
    
    params = {
        'instId': 'BTC-USDT-SWAP',
        'bar': '1H',
        'limit': '300',
        'before': str(current_time)
    }
    
    request_count = 0
    max_requests = 20
    
    while request_count < max_requests:
        print(f'Request {request_count + 1}: before={params["before"]}')
        
        r = requests.get(base_url + endpoint, params=params, timeout=10)
        data = r.json()
        
        if data.get('code') != '0' or not data.get('data'):
            print(f'No more data. Code: {data.get("code")}')
            break
        
        bars = data['data']
        print(f'Got {len(bars)} bars')
        
        # Veriyi ekle
        for bar in bars:
            ts = int(bar[0])
            if ts >= six_months_ago:  # 6 ay içindeyse ekle
                all_data.append(bar)
        
        # En eski timestamp'i bul
        oldest_ts = min(int(x[0]) for x in bars)
        if oldest_ts < six_months_ago:
            print(f'Reached 6-month limit: {datetime.fromtimestamp(oldest_ts/1000)}')
            break
        
        # Bir sonraki sayfa için before parametresini güncelle
        params['before'] = str(oldest_ts)
        request_count += 1
        
        time.sleep(0.1)  # Rate limiting
    
    print(f'\nTotal collected: {len(all_data)} bars')
    if all_data:
        first_time = datetime.fromtimestamp(int(all_data[0][0])/1000)
        last_time = datetime.fromtimestamp(int(all_data[-1][0])/1000)
        print(f'Date range: {first_time} to {last_time}')
        print(f'Duration: {(last_time - first_time).days} days')

if __name__ == "__main__":
    test_okx_api_correct()
