"""
OKX API - 6 ay önceden ileri doğru "after" ile (doğru yön)
- Spot örnek: BTC-USDT
- Perp örnek: BTC-USDT-SWAP
- Barlar: 5m, 15m, 1H, 4H
"""

import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

BASE_URL = "https://www.okx.com"
HIST_EP = "/api/v5/market/history-candles"  # uzun dönem tarihsel (sayfalı)

def utc_ms_now():
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def months_ago_ms(n_months=6):
    # ~30 gün varsayımı (basit ve yeterli)
    days = 30 * n_months
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)

def fetch_okx_forward_after(instId: str, bar: str, months: int = 6,
                            limit_per_req: int = 100, sleep_sec: float = 0.12,
                            max_requests: int = 2000):
    """
    6 ay önceden (start_ts) ileri doğru "after" ile sayfalama.
    OKX yanıtı: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
    """
    start_ts = months_ago_ms(months)
    now_ts = utc_ms_now()

    print(f"Fetching {months} months of {bar} data for {instId}")
    print(f"Start time (UTC): {datetime.utcfromtimestamp(start_ts/1000)}")
    print(f"End time   (UTC): {datetime.utcfromtimestamp(now_ts/1000)}")

    session = requests.Session()
    all_rows = []
    cursor_after = start_ts  # 6 ay önceden başla (ileri gideceğiz)
    req = 0
    last_max_ts_seen = None

    while cursor_after < now_ts and req < max_requests:
        params = {
            "instId": instId,
            "bar": bar,
            "limit": str(limit_per_req),
            "after": str(cursor_after)   # <-- KRİTİK DÜZELTME: AFTER
        }

        print(f"\nRequest {req + 1}: after={cursor_after} ({datetime.utcfromtimestamp(cursor_after/1000)})")
        r = session.get(BASE_URL + HIST_EP, params=params, timeout=20)
        try:
            r.raise_for_status()
        except Exception as e:
            print("HTTP error:", e, "| payload:", r.text)
            break

        payload = r.json()
        code = payload.get("code")
        data = payload.get("data", [])
        print(f"Response: code={code}, bars={len(data)}")

        if not data:
            print("No more data available (empty page).")
            break

        # Gelen paket tipik olarak "en yeni -> en eski" olabilir; ts'leri yakala
        ts_list = [int(x[0]) for x in data]
        min_ts = min(ts_list)
        max_ts = max(ts_list)

        # Hedef aralıkta olanları ekle
        added = 0
        for row in data:
            ts = int(row[0])
            if start_ts <= ts <= now_ts:
                all_rows.append(row)
                added += 1

        print(f"Added {added} bars (total: {len(all_rows)}) | min_ts={min_ts} | max_ts={max_ts}")

        # İlerleme kontrolü (sonsuz döngü önlemi)
        if last_max_ts_seen is not None and max_ts <= last_max_ts_seen:
            # İlerlemiyorsa "before" yerine yanlış yön kullanıyoruz demektir; kır.
            print("No forward progress detected; stopping to avoid loop.")
            break
        last_max_ts_seen = max_ts

        # Bir sonraki sayfa için "after" = bu paketin en büyük ts'si
        cursor_after = max_ts

        # 6 ay hedefini geçtik mi?
        if cursor_after >= now_ts:
            print("Reached current time boundary.")
            break

        time.sleep(sleep_sec)
        req += 1

    # Kronolojik sıraya diz (eski -> yeni)
    all_rows.sort(key=lambda x: int(x[0]))

    # 6 ay sınırı dışında kalanları kırp
    all_rows = [row for row in all_rows if start_ts <= int(row[0]) <= now_ts]

    # Kapanmamış son mumu at (confirm=0 olabiliyor)
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
        df = df[["time_utc","open","high","low","close","volume","volCcy","volCcyQuote","confirm","ts"]]
        print(f"\nFinal: {len(df)} bars")
        print(f"Range: {df['time_utc'].iloc[0]}  ->  {df['time_utc'].iloc[-1]}")
    else:
        print("Final: 0 bars")

    return df


if __name__ == "__main__":
    # ÖRNEK kullanım — sembol ve barı istediğin gibi değiştir
    instId = "BTC-USDT-SWAP"  # SWAP sembolü ile test et
    bars = ["5m", "15m", "1H", "4H"]
    months = 6

    for bar in bars:
        print(f"\n=== {instId} | {bar} | last {months} months ===")
        df = fetch_okx_forward_after(instId=instId, bar=bar, months=months)
        if not df.empty:
            out = f"okx_{instId}_{bar}_{months}ay_after.csv".replace("/", "-")
            df.to_csv(out, index=False)
            print(f"Saved: {out}")
        else:
            print("No data collected for this bar.")
