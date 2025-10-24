# okx_6ay_indir.py
# Gerekenler: pip install requests pandas
import time
import math
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

BASE_URL = "https://www.okx.com"
HIST_EP  = "/api/v5/market/history-candles"  # Geçmiş mumlar (sayfalı)
# NOT: Güncel son blok için /api/v5/market/candles var ama 6 ay için history-candles yeterli.

# --------------------------
# Yardımcı fonksiyonlar
# --------------------------
def utc_ms_now():
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def months_ago_ms(n_months=6):
    # Basit yaklaşım: ~30 gün * ay
    days = 30 * n_months
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)

def fetch_okx_history(instId: str, bar: str, months: int = 6, limit_per_req: int = 100,
                      sleep_sec: float = 0.12, max_retries: int = 5):
    """
    OKX v5 /market/history-candles ile 'months' kadar geçmişi geriye sayfalar.
    - instId: 'BTC-USDT', 'BTC-USDT-SWAP' vb.
    - bar: '5m', '15m', '1H', '4H' (günlük/haftalık/aylıkta '1Dutc' gibi utc suffix kullanılabilir)
    Dönen satır formatı (OKX): [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    """
    start_ts = months_ago_ms(months)
    cursor_before = utc_ms_now()

    print(f"Fetching {months} months of {bar} data for {instId}")
    print(f"Date range: {datetime.fromtimestamp(start_ts/1000)} to {datetime.fromtimestamp(cursor_before/1000)}")

    all_rows = []
    session = requests.Session()

    while True:
        params = {
            "instId": instId,
            "bar": bar,
            "limit": str(limit_per_req),
            "before": str(cursor_before),
        }

        # Basit retry
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Request: {params}")
                r = session.get(BASE_URL + HIST_EP, params=params, timeout=20)
                r.raise_for_status()
                payload = r.json()
                data = payload.get("data", [])
                print(f"Response: {len(data)} bars")
                break
            except Exception as e:
                if attempt == max_retries:
                    raise
                print(f"Attempt {attempt} failed: {e}, retrying...")
                time.sleep(0.5 * attempt)

        if not data:
            # Daha geride veri yok
            print("No more data available")
            break

        # Veri genelde "en yeni -> en eski" geliyor. Biz filtreleyip biriktiriyoruz.
        # Her satır: [0]ts, [1]open, [2]high, [3]low, [4]close, [5]vol, [6]volCcy, [7]volCcyQuote, [8]confirm
        stop_here = False
        added_count = 0
        for row in data:
            ts = int(row[0])
            if ts < start_ts:
                # Hedef aralığın dışına düştük; bu paketle işimiz bitti
                stop_here = True
                continue
            all_rows.append(row)
            added_count += 1

        print(f"Added {added_count} bars (total: {len(all_rows)})")

        # Bir sonraki sayfa için: bu paketin en eski ts'sini before yap
        oldest_ts = min(int(x[0]) for x in data)
        cursor_before = oldest_ts

        if stop_here:
            # Artık 6 ay sınırına ulaştık (daha eskiye gitmeye gerek yok)
            print(f"Reached {months}-month limit: {datetime.fromtimestamp(oldest_ts/1000)}")
            break

        # Rate limit (OKX tipik 20 req / 2s). Nazik bekleme:
        time.sleep(sleep_sec)

    # Kronolojik sıraya diz (eski -> yeni)
    all_rows.sort(key=lambda x: int(x[0]))

    # 6 ay sınırından daha eski satırlar varsa ayıkla
    all_rows = [row for row in all_rows if int(row[0]) >= start_ts]

    # Kapanmamış son mumu at (confirm = 0 olabilir)
    if all_rows:
        last_confirm = int(all_rows[-1][8]) if len(all_rows[-1]) > 8 else 1
        if last_confirm == 0:
            all_rows = all_rows[:-1]
            print("Removed unconfirmed last candle")

    # DataFrame
    df = pd.DataFrame(all_rows, columns=[
        "ts","open","high","low","close","volume","volCcy","volCcyQuote","confirm"
    ])
    if not df.empty:
        df["time_utc"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
        # Sütunları düzenle
        df = df[["time_utc","open","high","low","close","volume","volCcy","volCcyQuote","confirm","ts"]]

    return df

def save_csv(df: pd.DataFrame, instId: str, bar: str, months: int):
    if df.empty:
        print(f"[WARN] Veri yok: {instId} {bar}")
        return None
    fname = f"okx_{instId}_{bar}_{months}ay.csv".replace("/", "-")
    df.to_csv(fname, index=False)
    print(f"[OK] Kaydedildi: {fname} | Satır: {len(df)} | İlk: {df['time_utc'].iloc[0]} | Son: {df['time_utc'].iloc[-1]}")
    return fname

# --------------------------
# KULLANIM
# --------------------------
if __name__ == "__main__":
    # ÖRNEK: Spot BTC-USDT için 6 aylık 1H
    instId = "BTC-USDT"  # Perp isterse: "BTC-USDT-SWAP"
    bar = "1H"
    months = 6

    print(f"\n=== {instId} | {bar} | Son {months} ay ===")
    df = fetch_okx_history(instId=instId, bar=bar, months=months, limit_per_req=100, sleep_sec=0.12)
    save_csv(df, instId, bar, months)

