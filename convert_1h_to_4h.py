"""
1H verisini 4H ye dönüştürme
"""

import pandas as pd
from datetime import datetime, timedelta, timezone

def convert_1h_to_4h():
    print('=== 1H VERISINI 4H YE DONUSTURME TESTI ===')

    # Mevcut 1h verisini oku
    df_1h = pd.read_csv('data/ml_training/BTC_USDT_USDT_1h_6months.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h = df_1h.set_index('timestamp')

    print(f'1H veri: {len(df_1h)} bars')
    print(f'Date range: {df_1h.index.min()} to {df_1h.index.max()}')
    print(f'Duration: {(df_1h.index.max() - df_1h.index.min()).days} days')

    # 1h verisini 4h'ye dönüştür
    df_4h = df_1h.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    print(f'\n4H veri (1H den donusturulmus): {len(df_4h)} bars')
    print(f'Date range: {df_4h.index.min()} to {df_4h.index.max()}')
    print(f'Duration: {(df_4h.index.max() - df_4h.index.min()).days} days')

    # 6 aylık veri için gerekli bar sayısı
    bars_needed_6months = 180 * 6  # 6 ay * 6 (4h per day) = 1080
    print(f'\nBars needed for 6 months: {bars_needed_6months}')
    print(f'Current bars: {len(df_4h)}')
    print(f'Missing bars: {bars_needed_6months - len(df_4h)}')

    # CSV'ye kaydet
    df_4h.to_csv('data/ml_training/BTC_USDT_USDT_4h_6months_converted.csv')
    print(f'\nSaved to: data/ml_training/BTC_USDT_USDT_4h_6months_converted.csv')
    
    return df_4h

if __name__ == "__main__":
    convert_1h_to_4h()

