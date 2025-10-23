# News Pipeline Koşu Checklist'i
**Tarih:** 2025-10-21  
**Amaç:** News pipeline koşu öncesi/sırası/sonrası kontrol listesi

## ✅ Koşu Öncesi Kontrol Listesi

### ENV Değişkenleri
```bash
# Zorunlu
□ OPENAI_API_KEY ayarlı mı?
  echo $env:OPENAI_API_KEY  # (PowerShell)
  echo $OPENAI_API_KEY      # (Bash)

# Opsiyonel (Varsayılanlar)
□ NEWS_VERBOSITY (varsayılan: summary)
□ LLM_VERBOSITY (varsayılan: summary)
□ OPENAI_MODEL (varsayılan: gpt-3.5-turbo)
□ LOG_LEVEL (varsayılan: INFO)
```

### Policy.yaml Ayarları
```bash
# Kontrol komutları
cat configs/policy.yaml | grep -A 10 "news:"
cat configs/policy.yaml | grep -A 10 "news_llm:"
cat configs/policy.yaml | grep -A 10 "news_scoring:"

□ news.lookback_hours_bootstrap: 24
□ news.overlap_minutes: 30
□ news_llm.enabled: true
□ news_llm.digest.max_items_per_symbol: 20-30 arası
□ news_llm.cache.ttl_minutes: 60
□ exchange.symbols.supported_pairs: En az 1 sembol
```

### Dosya/Dizin Durumu
```bash
□ data/ dizini var mı?
  ls -la data/ || dir data\

□ Storage dosyaları yazılabilir mi?
  - data/news_watermarks.json
  - data/news_llm_digest.json
  - data/news_storage.json

□ logs/ dizini var mı?
  ls -la logs/ || dir logs\
```

### Network & API Erişimi
```bash
# CryptoCompare API test
□ curl -s "https://min-api.cryptocompare.com/data/v2/news/?limit=1" | jq .

# OpenAI API test
□ curl -s https://api.openai.com/v1/models \
    -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[0].id'

# Prometheus endpoint (varsa)
□ curl -s http://localhost:8000/metrics | grep aibot_news_score
```

### Scheduler Durumu
```bash
□ Scheduler çalışıyor mu?
  ps aux | grep scheduler  # (Bash)
  Get-Process | Where-Object {$_.ProcessName -like "*python*"}  # (PowerShell)

□ news_incremental_5m job kayıtlı mı?
  # Logları kontrol et
  grep "news_incremental_5m" logs/bot.log | tail -5
```

## 🔄 Koşu Sırasında İzleme

### Log Kalıpları (Beklenen Davranış)

#### Normal Run (İlk 30 saniye)
```bash
# Terminal komutları
tail -f logs/bot.log | grep -E "\[NEWS\]|\[LLM\]"
```

**Beklenen log sırası:**
```
[t+0s]  [JOB] name=news_incremental_5m status=STARTING
[t+1s]  📊 [NEWS] sym=BTC incremental: X new, Y total
[t+1s]  📊 [LLM] sym=BTC digest=CHANGED run=YES items=20
[t+3s]  📊 [LLM] sym=BTC req_id=... tokens=4500+650
[t+3s]  📊 [NEWS] sym=ETH incremental: X new, Y total
[t+3s]  📊 [LLM] sym=ETH digest=SAME run=NO items=15
[t+5s]  [JOB] name=news_incremental_5m status=SUCCESS dur=5.2s
```

#### Bootstrap Run (İlk Çalışma)
```
[t+0s]  🔄 [NEWS] Lazy bootstrap for BTC (no watermark)
[t+2s]  ✅ [NEWS] sym=BTC incremental: 42 new, 42 total
[t+2s]  📊 [LLM] sym=BTC digest=CHANGED run=YES items=30
[t+5s]  📊 [LLM] sym=BTC req_id=... tokens=5200+780
...
```

### Grep Komutları (Real-time)

#### Haber Güncellemeleri
```bash
# Yeni haber sayısı
grep "\[NEWS\] sym=" logs/bot.log | grep "incremental:" | tail -10

# Bootstrap kontrolü
grep "Lazy bootstrap" logs/bot.log
```

#### LLM Çağrıları
```bash
# Digest değişimleri
grep "\[LLM\]" logs/bot.log | grep "digest=CHANGED" | tail -10

# Cache hit'ler
grep "\[LLM\]" logs/bot.log | grep "digest=SAME" | tail -10

# Token tüketimi
grep "LLM_SUCCESS" logs/bot.log | awk '{print $NF}' | tail -10
```

#### Hatalar
```bash
# LLM hataları
grep "❌ \[LLM\]" logs/bot.log | tail -10

# 429 rate limits
grep "status=429" logs/bot.log | tail -5

# Job başarısızlıkları
grep "news_incremental_5m" logs/bot.log | grep "status=FAILED"
```

### Prometheus Metrikleri (Beklenen Artış)

```bash
# 5 dakikalık run sonrası beklenen değişimler
curl -s http://localhost:8000/metrics | grep aibot_news_score
curl -s http://localhost:8000/metrics | grep aibot_llm_requests_total
curl -s http://localhost:8000/metrics | grep aibot_llm_request_tokens_sum
```

**Beklenen artışlar (10 sembol için):**
```
# Run öncesi vs sonrası
aibot_llm_requests_total{status="2xx"}  +3 to +10  # Digest değişimine göre
aibot_llm_request_tokens_sum            +15,000 to +50,000  # Token tüketimi
aibot_llm_response_tokens_sum           +2,000 to +8,000
aibot_news_score{symbol="BTC"}          50-90 arası (güncellendi)
```

### Console Output (Tek Satır Özet)

**NEWS_VERBOSITY=summary (varsayılan):**
```
02:35:03 | [JOB] news_incremental_5m STARTING
02:35:04 | 📊 [NEWS] sym=BTC incremental: 3 new, 45 total
02:35:04 | 📊 [LLM] sym=BTC digest=CHANGED run=YES items=20
02:35:06 | 📊 [LLM] sym=BTC req_id=req_xyz tokens=4200+580
02:35:08 | [JOB] news_incremental_5m SUCCESS dur=5.1s
```

**NEWS_VERBOSITY=full (debug):**
```
+ Her haber item detayı
+ API response headers
+ Dedup logic detayı
+ Digest hash value
+ Cache hit/miss detayı
```

## 📊 Koşu Sonrası Doğrulama

### Storage Dosyaları

#### Watermarks
```bash
cat data/news_watermarks.json | jq .

# Beklenen format
{
  "BTC": "2025-10-21T02:35:00+00:00",
  "ETH": "2025-10-21T02:34:45+00:00",
  ...
}

□ Her sembol için timestamp var mı?
□ Timestamp'ler ilerledi mi? (önceki run'dan daha yeni)
```

#### Digest Cache
```bash
cat data/news_llm_digest.json | jq 'keys | length'
cat data/news_llm_digest.json | jq '.[keys[0]]'

# Beklenen entry format
{
  "BTC_ff63fdde12345678": {
    "timestamp": "2025-10-21T02:35:00+00:00",
    "result": {
      "score": 75.5,
      "categories": ["MARKET"],
      "rationale": "...",
      "volatility_impact": 0.65
    },
    "digest": "ff63fdde12345678"
  },
  "BTC_last": { ... }
}

□ Cache entry sayısı arttı mı?
□ TTL içinde mi? (timestamp < 60 dakika önce)
```

#### News Storage
```bash
cat data/news_storage.json | jq 'keys | length'
cat data/news_storage.json | jq '.BTC | length'

□ Her sembol için haber listesi var mı?
□ Haber sayısı makul mı? (10-100 arası)
```

### Digest Hit Oranı Hesaplama

```bash
# Son 10 run'da kaç digest CHANGED vs SAME?
grep "\[LLM\]" logs/bot.log | tail -50 | grep -c "digest=CHANGED"
grep "\[LLM\]" logs/bot.log | tail -50 | grep -c "digest=SAME"

# Hedef hit rate: %60-80 (yani %20-40 CHANGED)
# Çok düşük (<10%): TTL çok düşük, maliyet yüksek
# Çok yüksek (>90%): Haberler güncellenmiyor, data stale
```

### LLM Çağrı Adedi

```bash
# Son 1 saatte kaç LLM çağrısı?
grep "LLM_SUCCESS\|LLM_ERROR" logs/bot.log | \
  awk '{print $2}' | \
  grep "$(date +%H):" | wc -l

# Beklenen: 10 sembol × 12 run/saat × %30 digest change = ~36 çağrı/saat
```

### Token Tüketimi & Maliyet Tahmini

```bash
# Son 10 LLM çağrısının token ortalaması
grep "LLM_SUCCESS" logs/bot.log | tail -10 | \
  awk -F'prompt_tokens=' '{print $2}' | awk '{print $1}' | \
  awk '{sum+=$1; count++} END {print "Avg prompt:", sum/count}'

grep "LLM_SUCCESS" logs/bot.log | tail -10 | \
  awk -F'completion_tokens=' '{print $2}' | awk '{print $1}' | \
  awk '{sum+=$1; count++} END {print "Avg completion:", sum/count}'
```

**Maliyet Hesabı (GPT-3.5-turbo):**
```
# Fiyatlar (Ocak 2025)
Prompt: $0.50 / 1M token
Completion: $1.50 / 1M token

# Örnek hesap (saatlik)
36 calls/hour × (4,500 prompt + 650 completion) = 185,400 tokens/hour
Prompt: 36 × 4,500 = 162,000 tokens × $0.50/1M = $0.081
Completion: 36 × 650 = 23,400 tokens × $1.50/1M = $0.035
Toplam: $0.116/saat ≈ $2.78/gün ≈ $83/ay
```

### PASS/FAIL Kriterleri

#### ✅ PASS Koşulları (Tümü Sağlanmalı)

1. **Job Başarısı:**
   ```bash
   □ [JOB] status=SUCCESS görüldü
   □ Duration < 30 saniye
   □ Retry yok (attempt=1)
   ```

2. **Digest Değişimi:**
   ```bash
   □ En az 1 sembol için digest=CHANGED
   □ Yeni haber sayısı > 0 veya bootstrap
   ```

3. **LLM Çağrısı:**
   ```bash
   □ Digest değişen semboller için LLM çağrıldı
   □ HTTP 200 alındı (LLM_SUCCESS log'u var)
   □ Structured output parse edildi
   ```

4. **Watermark Güncellemesi:**
   ```bash
   □ Watermark dosyası güncellendi
   □ Timestamp ilerledi (önceki run'dan sonra)
   ```

5. **Haber Sayısı Limiti:**
   ```bash
   □ max_items_per_symbol aşılmadı
   □ Total news < 1000 (memory limiti)
   ```

6. **Metrik Güncellemesi:**
   ```bash
   □ aibot_news_score güncellendi
   □ aibot_llm_requests_total arttı
   □ aibot_llm_*_tokens_sum arttı
   ```

#### ❌ FAIL Koşulları (Herhangi Biri)

1. **Job Başarısızlığı:**
   ```bash
   ✗ [JOB] status=FAILED
   ✗ Exception/traceback görüldü
   ✗ Retry attempts > 1
   ```

2. **API Hatası (Persistent):**
   ```bash
   ✗ 3 retry sonrası hala CryptoCompare hata veriyor
   ✗ OpenAI API 5xx hatası (server error)
   ✗ Network timeout (30s+)
   ```

3. **Quota Aşımı:**
   ```bash
   ✗ status=429 insufficient_quota (OpenAI)
   ✗ Günlük token limiti aşıldı
   ```

4. **Data Corruption:**
   ```bash
   ✗ Watermark dosyası parse edilemiyor
   ✗ Digest cache corrupt
   ✗ News storage invalid JSON
   ```

5. **Logic Hatası:**
   ```bash
   ✗ Digest CHANGED ama LLM çağrılmadı
   ✗ LLM çağrıldı ama cache'e yazılmadı
   ✗ Watermark güncellemedi (stuck)
   ```

### Hızlı Sağlık Kontrolü (One-liner)

```bash
# Bash
tail -100 logs/bot.log | grep "news_incremental_5m" | grep "SUCCESS" && \
grep "digest=CHANGED" logs/bot.log | tail -3 && \
echo "✅ Pipeline HEALTHY"

# PowerShell
Get-Content logs\bot.log -Tail 100 | Select-String "news_incremental_5m" | Select-String "SUCCESS" ; `
Get-Content logs\bot.log | Select-String "digest=CHANGED" | Select-Object -Last 3 ; `
Write-Host "✅ Pipeline HEALTHY"
```

## 🔧 Troubleshooting Komutları

### Problem: Digest hiç CHANGED olmuyor
```bash
# 1. Watermark sıfırla (force bootstrap)
python -c "
from application.news_watermark_manager import NewsWatermarkManager
wm = NewsWatermarkManager()
wm.clear_all_watermarks()
"

# 2. Cache temizle
rm data/news_llm_digest.json

# 3. Test run
python -c "
import asyncio
from application.jobs.news_incremental_5m import NewsIncremental5mJob
from configs.policy import load_policy

async def test():
    policy = load_policy('configs/policy.yaml')
    job = NewsIncremental5mJob(policy, asyncio.Semaphore(1), {})
    await job.initialize()
    await job.execute()

asyncio.run(test())
"
```

### Problem: LLM 429 rate limit
```bash
# 1. Mevcut rate limit durumu
grep "429" logs/bot.log | tail -10

# 2. Prometheus metrics
curl -s http://localhost:8000/metrics | grep llm_rate_limits_total

# 3. Geçici çözüm: TTL artır
# policy.yaml: ttl_minutes: 120

# 4. Uzun vadeli: Batch size azalt
# policy.yaml: max_items_per_symbol: 15
```

### Problem: Job timeout / çok yavaş
```bash
# 1. Son run süreleri
grep "news_incremental_5m" logs/bot.log | grep "dur=" | tail -10

# 2. En yavaş sembol?
grep "\[NEWS\]" logs/bot.log | grep "dur=" | sort -k8 -n | tail -5

# 3. Network latency test
time curl -s "https://min-api.cryptocompare.com/data/v2/news/?limit=50" > /dev/null
time curl -s "https://api.openai.com/v1/models" \
  -H "Authorization: Bearer $OPENAI_API_KEY" > /dev/null

# 4. Çözüm: Timeout artır
# news_llm_analyzer.py: timeout=60
```

### Problem: Memory leak / file size büyümesi
```bash
# 1. Dosya boyutları
ls -lh data/news_*.json

# 2. News storage item sayısı
cat data/news_storage.json | jq '[.[] | length] | add'

# 3. Temizlik
python -c "
from application.news_service import NewsService
ns = NewsService({'news': {}, 'news_llm': {}, 'news_scoring': {}})
for symbol in ns.news_data.keys():
    ns.news_data[symbol] = ns.news_data[symbol][-50:]  # Keep last 50
ns._save_news_storage()
"

# 4. Digest cache pruning
python -c "
from application.news_digest_manager import NewsDigestManager
dm = NewsDigestManager()
stats = dm.get_cache_stats()
print(f'Expired entries: {stats[\"expired_entries\"]}')
# Manual cleanup: loop and delete expired
"
```

## 📋 Günlük Rapor Şablonu

```markdown
## News Pipeline Daily Report - {DATE}

### Özet
- **Total Runs:** {COUNT}
- **Success Rate:** {PERCENT}%
- **Avg Duration:** {SECONDS}s
- **LLM Calls:** {COUNT}
- **Total Tokens:** {COUNT} (~${COST})

### Metrikler
- **aibot_llm_requests_total{status="2xx"}:** {COUNT}
- **aibot_llm_requests_total{status="4xx"}:** {COUNT}
- **aibot_llm_rate_limits_total:** {COUNT}
- **Digest Hit Rate:** {PERCENT}%

### Sorunlar
- [ ] 429 rate limits: {COUNT}
- [ ] Network timeouts: {COUNT}
- [ ] Job failures: {COUNT}

### Aksiyonlar
1. {ACTION_ITEM}
2. {ACTION_ITEM}
```

---

**Checklist Versiyonu:** 1.0  
**Son Güncelleme:** 2025-10-21  
**Durum:** ✅ Aktif

