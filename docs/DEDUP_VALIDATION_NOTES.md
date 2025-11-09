## Dedup Validation Notes (Step 5 & 6)

### 1. Özet
- Haber LLM çağrıları için `(symbol, tf, digest, window, model, locale, source_set)` bazlı TTL cache devreye alındı; `[NEWS_DEDUP]` logları miss/hit gerekçelerini raporluyor.
- Risk değerlendirmesi giriş parametrelerine dayalı TTL cache’e geçti; pozisyon state’i değişmediği sürece aynı bar içinde tekrar hesaplama yapılmıyor, `[RISK_CACHE]` logları durumları gösteriyor.
- Scheduler ve analiz logları `run_id` / `bar_id` bilgisiyle standartlaştırıldı; `[RUN]`, `[COMPOSITE]`, `[BATCH]` satırları tutarlı.
- TTL cache kullanımına ait Prometheus sayaçları (`aibot_cache_hits_total`, `aibot_cache_misses_total`, `aibot_cache_items`) eklendi.

### 2. Çalıştırılan Testler
```
python -m pytest \
  tests/unit/test_ttl_cache.py \
  tests/test_news_dedup.py \
  tests/test_risk_cache.py \
  tests/test_runtime_dedup.py \
  tests/unit/test_basic_functionality.py
```

- `tests/test_news_dedup.py` → Aynı bar/pencere içinde ikinci çağrı cache üzerinden dönüyor; pencere veya içerik değişince LLM tekrar tetikleniyor.
- `tests/test_risk_cache.py` → Aynı `position_snapshot_hash` ile 2. çağrı cache hit; state değişince miss.
- `tests/test_runtime_dedup.py` → Haber ve risk cache’lerinin birlikte çalıştığı end-to-end senaryo.
- `tests/unit/test_ttl_cache.py` → TTL cache derin kopya & metrik sayaçları doğrulaması.
- `tests/unit/test_basic_functionality.py` → `LogDedupService`’in yeni imzası ile güncellendi.

### 3. Örnek Log Satırları
```
[RUN] job=trading_analysis run_id=5b1a42f3 bar_id=2025-11-09T18:45:00Z status=starting
[NEWS_DEDUP] key=8f0b1c72e4f5 miss reason=cold_start
[NEWS_DEDUP] key=8f0b1c72e4f5 hit reason=ttl
[RISK_CACHE] key=4d6fa902b8a1 miss reason=cold_start
[RISK_CACHE] key=4d6fa902b8a1 hit reason=ttl
[COMPOSITE] sym=BTC-USDT tf=15m news=skip risk=47.4 final=52.8 reason=FLAT
[RUN] job=trading_analysis run_id=5b1a42f3 bar_id=2025-11-09T18:45:00Z status=SUCCESS
[BATCH] timeframe=15m bar=2025-11-09T18:45:00Z run=5b1a42f3 total=4 success=4 fail=0 | ...
```
> Daha uzun örnek için `docs/SAMPLE_LOGS_DEDUP.txt` dosyasına bakınız.

### 4. Prometheus Metrikleri
- `aibot_cache_hits_total{cache="news"}`
- `aibot_cache_misses_total{cache="risk"}`
- `aibot_cache_items{cache="news"}`

Exporter üzerinden yapılan manuel doğrulamada her cache başarıyla raporlanıyor.

### 5. İzlenecek Noktalar
- `NEWS_DEDUP_TTL_SECONDS` ve `RISK_CACHE_TTL_SECONDS` değerleri değişirse dosya/ENV güncellemesi yapmayı unutma.
- Haber digest’leri kaynak listesi değiştiğinde invalidate edildiği için yeni kaynak eklenince ilk çalıştırmada miss görülmesi normal.
- Risk cache’i state hash’ini `PositionStateManager` verisine göre ürettiğinden, persistent state harici değişiklikler (ör. dış kaynaklı pozisyon açılması) hash uyuşmazlığı yaratabilir; loglarda `reason=config_change` görülebilir.

