# News Digest TTL Optimizasyonu Sonuç Raporu
**Tarih:** 2025-10-21  
**Test Süresi:** 30-60 dakika (PAPER mode)  
**Durum:** ✅ Konfigüre Edildi (Test Bekliyor)

## 📊 Konfigürasyon Değişiklikleri

### ENV & Policy Ayarları
```yaml
# configs/policy.yaml

news:
  overlap_minutes: 15  # ÖNCE: 30 (↓50%)
  
news_llm:
  cache:
    ttl_minutes: 120  # ÖNCE: 60 (↑100%)
```

### Beklenen Etki
| Parametre | ÖNCE | SONRA | Etki |
|-----------|------|-------|------|
| **TTL** | 60 min | 120 min | Cache 2x uzun süre geçerli |
| **Overlap** | 30 min | 15 min | Daha az duplicate haber |
| **Digest Hit Rate** | ~40% | ~70% | +75% cache utilization |
| **LLM Calls/Hour** | 36 | ~11 | -69% API calls |

## 🎯 Test Planı (30-60 dakika PAPER mode)

### Başlatma Komutu
```powershell
$env:PYTHONIOENCODING="utf-8"
$env:TRADING_MODE="paper"
$env:SYMBOLS="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP"
$env:NEWS_LLM_MODEL="gpt-5-nano"
$env:NEWS_VERBOSITY="summary"

python main.py scheduler
```

### İzlenecek Metrikler

#### 1. Digest Status (5 dakikada bir)
```bash
# Log pattern
grep "\[LLM\]" logs/bot.log | grep "digest=" | tail -20

# Beklenen dağılım (30 dk test)
digest=CHANGED: ~9 kez  (6 run × 3 sembol × 50% change)
digest=SAME:   ~27 kez  (6 run × 3 sembol × 150% same)
Hit rate: 75%
```

#### 2. News Items (sent_to_llm breakdown)
```bash
# Prometheus query
curl -s http://localhost:8000/metrics | grep "aibot_news_items_total"

# Beklenen sonuç (30 dk)
aibot_news_items_total{sent_to_llm="true"} 27   # Digest CHANGED items
aibot_news_items_total{sent_to_llm="false"} 81  # Digest SAME (cache hit)
```

#### 3. Digest Hits Counter
```bash
# Prometheus query
curl -s http://localhost:8000/metrics | grep "aibot_news_digest_hits_total"

# Beklenen sonuç (30 dk)
aibot_news_digest_hits_total 27  # SAME count
```

#### 4. LLM Calls & Cost
```bash
# LLM requests
curl -s http://localhost:8000/metrics | grep "aibot_llm_requests_total"

# Beklenen sonuç (30 dk)
aibot_llm_requests_total{status="2xx"} 9   # 6 runs × 3 symbols × 50% change
aibot_llm_cost_usd_total 0.0011            # 9 calls × ~$0.00012
```

## 📈 Beklenen Sonuçlar (Projeksiyonlar)

### 30 Dakikalık Test Penceresi

**Baseline (ÖNCE: TTL=60, overlap=30):**
- Run count: 6 (her 5 dakika)
- Symbols: 3 (BTC, ETH, SOL)
- Total opportunities: 18 (6 runs × 3 symbols)
- Digest CHANGED: ~11 (60% change rate)
- Digest SAME: ~7 (40% hit rate)
- LLM calls: 11
- Cost: ~$0.0013

**Optimized (SONRA: TTL=120, overlap=15):**
- Run count: 6
- Symbols: 3
- Total opportunities: 18
- Digest CHANGED: ~5 (28% change rate)
- Digest SAME: ~13 (72% hit rate) ✅
- LLM calls: 5 (-55%)
- Cost: ~$0.0006 (-54%)

### 60 Dakikalık Test Penceresi

**Optimized (TTL=120, overlap=15):**
- Run count: 12
- Symbols: 3
- Total opportunities: 36
- Digest CHANGED: ~10 (28%)
- Digest SAME: ~26 (72%) ✅
- LLM calls: 10 (-58% from baseline)
- Cost: ~$0.0012 (-58%)

## 🔍 Validasyon Kriterleri

### ✅ PASS Koşulları

1. **Digest Hit Rate ≥ 65%**
   ```bash
   # Hesaplama
   hit_rate = digest_SAME / (digest_CHANGED + digest_SAME)
   # Hedef: ≥ 0.65
   ```

2. **sent_to_llm="false" > sent_to_llm="true"**
   ```bash
   # Cache'den dönen > LLM'e giden
   false_count > true_count
   ```

3. **LLM Calls < 15 (30 dk test)**
   ```bash
   aibot_llm_requests_total{status="2xx"} < 15
   ```

4. **Cost < $0.002 (30 dk test)**
   ```bash
   aibot_llm_cost_usd_total < 0.002
   ```

5. **Log'larda dengeli CHANGED/SAME**
   ```bash
   grep "digest=SAME" logs/bot.log | wc -l  # Should be higher
   grep "digest=CHANGED" logs/bot.log | wc -l
   ```

### ❌ FAIL Koşulları

1. **Digest her run CHANGED (hit rate < 30%)**
   - TTL çok kısa veya overlap çok geniş
   - Haberler sürekli değişiyor (normal olabilir)

2. **Hiç SAME görünmüyor**
   - Cache çalışmıyor
   - Digest hash problemi

3. **LLM calls > 25 (30 dk)**
   - Optimization çalışmıyor
   - Her sembol her run'da CHANGED

## 📝 Test Sonuçları (Gerçek Koşudan Doldurulacak)

### Test Bilgileri
```
Start Time: [TO BE FILLED]
End Time: [TO BE FILLED]
Duration: [TO BE FILLED] minutes
Mode: PAPER
Symbols: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
```

### Digest İstatistikleri
```
Total Runs: [TO BE FILLED]
Total Symbols Processed: [TO BE FILLED]
Total Opportunities: [TO BE FILLED]

Digest CHANGED: [TO BE FILLED] ([TO BE FILLED]%)
Digest SAME: [TO BE FILLED] ([TO BE FILLED]%)
Hit Rate: [TO BE FILLED]%

✅/❌ PASS Kriteri: Hit rate ≥ 65%
```

### LLM Çağrıları
```
Total LLM Calls: [TO BE FILLED]
Success (2xx): [TO BE FILLED]
Errors (4xx/5xx): [TO BE FILLED]

Total Tokens (in): [TO BE FILLED]
Total Tokens (out): [TO BE FILLED]
Total Cost: $[TO BE FILLED]

✅/❌ PASS Kriteri: Calls < 15, Cost < $0.002
```

### Prometheus Metrics Snapshot
```
aibot_news_digest_hits_total [TO BE FILLED]
aibot_news_items_total{sent_to_llm="true"} [TO BE FILLED]
aibot_news_items_total{sent_to_llm="false"} [TO BE FILLED]
aibot_llm_requests_total{status="2xx"} [TO BE FILLED]
aibot_llm_cost_usd_total [TO BE FILLED]
```

### Log Örnekleri
```
[TO BE FILLED - Real log samples from test run]

Expected patterns:
📊 [LLM] sym=BTC digest=CHANGED run=YES items=20
📊 [LLM] sym=ETH digest=SAME run=NO items=15
📊 [LLM] sym=SOL digest=SAME run=NO items=18
```

## 🎉 Sonuç

**Konfigürasyon:** ✅ Tamamlandı
- TTL: 60 → 120 (+100%)
- Overlap: 30 → 15 (-50%)

**Test:** ⏳ Bekliyor
- PAPER mode 30-60 dk run gerekli
- Gerçek metrikler doldurulacak

**Beklenen:** ✅ Pass
- Hit rate: ~70% (hedef ≥65%)
- LLM calls: ~10 (hedef <15)
- Cost: ~$0.0006 (hedef <$0.002)

---

**Not:** Bu rapor test koşulduktan sonra gerçek verilerle güncellenecek.

