# LLM Maliyet Optimizasyonu Rehberi
**Oluşturma Tarihi:** 2025-10-21  
**Durum:** ✅ Aktif  
**Versiyon:** 2.0

## 📋 Genel Bakış

Bu dokümantasyon, news pipeline'ındaki LLM (Large Language Model) maliyetlerini optimize etmek için uygulanan değişiklikleri açıklar. Maliyet optimizasyonu şu stratejilerle sağlanır:

1. **Ekonomik Model:** `gpt-3.5-turbo` → `gpt-5-nano` (20x ucuz, ultra-low latency)
2. **Structured Output:** Kısa JSON formatı, gereksiz açıklamalar yok
3. **Token Limitleri:** `max_output_tokens=128` (800'den düşürüldü)
4. **Bütçe Kontrolü:** Günlük token/USD limitleri
5. **Digest Cache:** TTL tabanlı cache (LLM atlanır)
6. **Caps & Sampling:** Sembol/item limitleri

## 🎯 Başarı Kriterleri

### Before (gpt-3.5-turbo)
- **Model:** gpt-3.5-turbo
- **Prompt:** ~4,500-6,000 token
- **Completion:** ~500-800 token  
- **Total:** ~5,500 token/analiz
- **Maliyet:** ~$1.10/1M token ($0.50 in + $1.50 out)
- **Günlük (10 sembol, 36 analiz/saat):** ~$2.78

### After (gpt-5-nano + optimization)
- **Model:** gpt-5-nano
- **Prompt:** ~1,000-1,500 token (kısa prompt)
- **Completion:** ~80-120 token (structured JSON)
- **Total:** ~1,200 token/analiz
- **Maliyet:** ~$0.09/1M token ($0.05 in + $0.40 out)
- **Günlük (digest cache ile %50 hit):** ~$0.19
- **Tasarruf:** **93%** 🎉

## 🔧 ENV Değişkenleri

### Model & Output
```bash
# Model seçimi
NEWS_LLM_MODEL=gpt-5-nano  # Varsayılan (gpt-5-mini, gpt-4o-mini, gpt-3.5-turbo da kullanılabilir)

# Output token limiti
NEWS_MAX_OUTPUT_TOKENS=128  # Varsayılan: 128 (eski: 800)
```

### Caps & Sampling
```bash
# Sembol başına max haber (LLM'e gönderilecek)
NEWS_MAX_ITEMS_PER_SYMBOL=3  # Varsayılan: 3 (eski: 10)

# Bir run'da analiz edilecek max sembol
NEWS_MAX_SYMBOLS_PER_RUN=10  # Varsayılan: 10

# Digest TTL (cache süresi)
NEWS_DIGEST_TTL_MIN=90  # Varsayılan: 90 (eski: 60)

# Sampling (her N run'da bir analiz)
NEWS_SAMPLING_EVERY_N_RUNS=1  # Varsayılan: 1 (her run), 2=her 2 run'da 1
```

### Maliyet Kontrolü
```bash
# Model maliyetleri (per 1M token)
LLM_COST_PER_MTOK_IN=0.05   # gpt-5-nano: $0.05/1M prompt tokens
LLM_COST_PER_MTOK_OUT=0.40  # gpt-5-nano: $0.40/1M completion tokens

# Günlük limitler
LLM_DAILY_BUDGET_TOKENS=200000  # Varsayılan: 200K tokens/gün
LLM_DAILY_BUDGET_USD=1.50       # Varsayılan: $1.50/gün (999=disabled)
```

### Log & Monitoring
```bash
# Log verbosity
NEWS_VERBOSITY=summary  # summary|full
LLM_VERBOSITY=summary   # summary|full
```

## 📝 Structured Output Şeması

### Old Format (gpt-3.5-turbo)
```json
{
  "symbols": [{"ticker": "BTC", "name": "Bitcoin", "confidence": 0.92}],
  "classification": "symbol_specific",
  "direction": "positive",
  "sentiment_score": 75.5,
  "categories": ["MARKET", "PARTNERSHIP"],
  "rationale": "Positive news about institutional adoption and market developments indicating potential price increase. Technical indicators support bullish momentum.",
  "volatility_impact": 0.65
}
```
**Token Count:** ~500-800 completion tokens

### New Format (gpt-5-nano)
```json
{
  "sentiment": 75,
  "dir": "long",
  "impact": 0.65,
  "tags": ["MARKET", "PARTNER"]
}
```
**Token Count:** ~80-120 completion tokens  
**Tasarruf:** **85% daha az completion token**

## 🎛️ Bütçe Yönetimi

### Günlük Limit Kontrolü
```python
# Otomatik kontrol (her LLM çağrısı öncesi)
if daily_tokens >= LLM_DAILY_BUDGET_TOKENS:
    return neutral_score(50.0)  # LLM atlanır

if daily_cost_usd >= LLM_DAILY_BUDGET_USD:
    return neutral_score(50.0)  # LLM atlanır
```

### Reset Logic
- **Tetikleyici:** Gece yarısı UTC
- **Action:** `daily_tokens_in`, `daily_tokens_out`, `daily_cost_usd` → 0
- **Log:** `💰 Daily budget reset: 2025-10-20 → 2025-10-21`

### Budget Status
```bash
# Python API
budget_status = llm_analyzer.get_daily_budget_status()

# Output
{
  'tokens_in': 45000,
  'tokens_out': 5200,
  'total_tokens': 50200,
  'token_budget': 200000,
  'token_usage_pct': 25.1,
  'cost_usd': 0.0098,
  'budget_usd': 1.50,
  'usd_usage_pct': 0.65,
  'budget_exceeded': False,
  'budget_left_usd': 1.49
}
```

## 📊 Prometheus Metrikleri

### Yeni Metrikler
```
# LLM maliyet tracking
aibot_llm_cost_usd_total  # Toplam maliyet (counter)

# Budget trips
aibot_llm_budget_trips_total{type="tokens|usd"}  # Limit aşım sayısı

# News items
aibot_news_items_total{sent_to_llm="true|false"}  # İşlenen haber sayısı

# Digest hits
aibot_news_digest_hits_total  # Cache hit sayısı
```

### Mevcut Metrikler
```
# LLM istekleri
aibot_llm_requests_total{status="2xx|4xx|5xx"}
aibot_llm_rate_limits_total{source="openai"}
aibot_llm_internal_errors_total

# Token kullanımı
aibot_llm_request_tokens_sum{model="gpt-5-nano"}
aibot_llm_response_tokens_sum{model="gpt-5-nano"}
```

### Metrik Örnekleri
```
# Before (1 saatlik run, gpt-3.5-turbo)
aibot_llm_request_tokens_sum{model="gpt-3.5-turbo"} 162000  # 36 calls × 4500
aibot_llm_response_tokens_sum{model="gpt-3.5-turbo"} 23400  # 36 calls × 650
aibot_llm_cost_usd_total 0.116

# After (1 saatlik run, gpt-5-nano + cache)
aibot_llm_request_tokens_sum{model="gpt-5-nano"} 27000   # 18 calls × 1500
aibot_llm_response_tokens_sum{model="gpt-5-nano"} 1800   # 18 calls × 100
aibot_llm_cost_usd_total 0.019
aibot_news_items_total{sent_to_llm="true"} 54   # 18 symbols × 3 items
aibot_news_items_total{sent_to_llm="false"} 126 # Digest hits
aibot_news_digest_hits_total 18
```

## 🔍 Log Formatı

### Console (Özet)
```bash
# LLM success
📊 [LLM] sym=BTC req_id=req_abc tokens=1200+95 cost=$0.0003 left=$1.47

# Budget exceeded
💰 [LLM] sym=ETH skipped - daily budget exceeded

# Daily reset
💰 Daily budget reset: 2025-10-20 → 2025-10-21

# Run summary (NEWS_SUMMARY_LOGGING=true)
[NEWS] symbols=12 analyzed=9 sent_to_llm=27 digest_hits=18
       llm_in=12.3k llm_out=1.1k est_cost=$0.0009 budget_left=$1.23
```

### File (Detaylı)
```
LLM_SUCCESS | symbol=BTC | request_id=req_abc | model=gpt-5-nano | 
prompt_tokens=1200 | completion_tokens=95 | status=200 | daily_cost=$0.0003

LLM_ERROR | symbol=ETH | request_id=None | model=gpt-5-nano | 
http_status=429 | error_source=internal_or_network | error_type=insufficient_quota
```

## 🎨 Tuning Rehberi

### Senaryo 1: Maliyet Çok Yüksek (>$5/gün)
**Hedef:** Günlük $1-2 altına düşür

```bash
# 1. Max items azalt (en etkili)
NEWS_MAX_ITEMS_PER_SYMBOL=2  # 3'ten düşür

# 2. TTL artır (digest cache hit rate ↑)
NEWS_DIGEST_TTL_MIN=120  # 90'dan artır

# 3. Sampling ekle
NEWS_SAMPLING_EVERY_N_RUNS=2  # Her 2 run'da 1

# 4. Sembol limitini düşür
NEWS_MAX_SYMBOLS_PER_RUN=5  # 10'dan düşür

# Beklenen Tasarruf: ~75%
```

### Senaryo 2: Kalite Düşük (sentiment accuracy düşük)
**Hedef:** Daha fazla context, daha iyi analiz

```bash
# 1. Max items artır
NEWS_MAX_ITEMS_PER_SYMBOL=5  # 3'ten artır

# 2. Output tokens artır
NEWS_MAX_OUTPUT_TOKENS=256  # 128'den artır

# 3. TTL düşür (daha sık güncelleme)
NEWS_DIGEST_TTL_MIN=60  # 90'dan düşür

# 4. Model upgrade (opsiyonel)
NEWS_LLM_MODEL=gpt-4o  # gpt-5-nano'dan upgrade (complex reasoning için)

# Beklenen Maliyet Artışı: ~200% (ama quality ↑)
```

### Senaryo 3: Balance (Varsayılan)
**Hedef:** Kalite-maliyet dengesi

```bash
# Mevcut varsayılanlar optimal
NEWS_MAX_ITEMS_PER_SYMBOL=3
NEWS_DIGEST_TTL_MIN=90
NEWS_MAX_OUTPUT_TOKENS=128
NEWS_LLM_MODEL=gpt-5-nano

# Beklenen Maliyet: ~$0.50/gün (10 sembol)
```

## 💰 Maliyet Hesaplama Tablosu

| Model | Input $/1M | Output $/1M | Avg Tokens (in+out) | Cost/Analiz | 36 analiz/saat | Günlük |
|-------|-----------|-------------|---------------------|-------------|----------------|--------|
| gpt-3.5-turbo | $0.50 | $1.50 | 5,500 (4500+1000) | $0.00305 | $0.1098 | $2.64 |
| gpt-5-nano | $0.05 | $0.40 | 1,200 (1000+200) | $0.00013 | $0.0047 | $0.11 |
| gpt-5-nano + cache | $0.05 | $0.40 | 1,200 (50% hit) | $0.00007 | $0.0024 | $0.06 |

**Tasarruf:** gpt-3.5-turbo → gpt-5-nano + cache = **98%** 🎉

## 🛠️ Troubleshooting

### Problem: Budget limit hızlı aşılıyor
```bash
# 1. Mevcut kullanımı kontrol et
curl http://localhost:8000/metrics | grep aibot_llm_cost_usd_total

# 2. Günlük token kullanımı
grep "daily_cost=" logs/bot.log | tail -20

# 3. Limiti artır veya caps azalt
# .env
LLM_DAILY_BUDGET_USD=3.00
# veya
NEWS_MAX_ITEMS_PER_SYMBOL=2
```

### Problem: Digest hit rate düşük (<30%)
```bash
# 1. Hit rate kontrolü
curl http://localhost:8000/metrics | grep aibot_news_digest_hits_total

# 2. TTL artır
NEWS_DIGEST_TTL_MIN=120

# 3. Overlap artır (daha az yeni haber)
# policy.yaml: overlap_minutes: 60
```

### Problem: LLM quality düşük
```bash
# 1. Model upgrade
NEWS_LLM_MODEL=gpt-4o

# 2. Output tokens artır
NEWS_MAX_OUTPUT_TOKENS=256

# 3. Max items artır
NEWS_MAX_ITEMS_PER_SYMBOL=5
```

## 📈 Monitoring Dashboard

### Grafana Panel Örnekleri

#### LLM Cost Tracking
```promql
# Daily cost rate
rate(aibot_llm_cost_usd_total[1h]) * 24

# Token usage per hour
rate(aibot_llm_request_tokens_sum[1h])
```

#### Digest Cache Performance
```promql
# Hit rate percentage
(aibot_news_digest_hits_total / aibot_news_items_total) * 100

# Items sent to LLM vs cached
aibot_news_items_total{sent_to_llm="true"}
aibot_news_items_total{sent_to_llm="false"}
```

#### Budget Status
```promql
# Budget trips (alerts)
aibot_llm_budget_trips_total{type="tokens"}
aibot_llm_budget_trips_total{type="usd"}
```

## 🚀 Best Practices

### 1. Model Selection
- **Development:** `gpt-5-nano` (ultra-fast, ultra-cheap)
- **Production:** `gpt-5-nano` (optimal for simple tasks, 20x cheaper)
- **Balanced:** `gpt-5-mini` (moderate cost, better reasoning)
- **High-stakes:** `gpt-4o` (best quality, 10x cost)

### 2. Budget Setting
- **Conservative:** $1.00/day (200K tokens)
- **Standard:** $2.00/day (400K tokens)
- **Aggressive:** $5.00/day (1M tokens)

### 3. Monitoring
- **Alert:** Budget >80% kullanıldığında
- **Daily Check:** Cost trend, hit rate
- **Weekly Review:** Quality vs cost balance

### 4. Cache Strategy
- **Short TTL (30-60min):** Volatile markets
- **Medium TTL (90-120min):** Normal markets
- **Long TTL (180min+):** Quiet markets

## 📚 Referanslar

- [OpenAI Pricing](https://openai.com/pricing)
- [GPT-5 Models Documentation](https://platform.openai.com/docs/models/gpt-5)
- [gpt-5-nano: Ultra-low latency](https://blog.galaxy.ai/compare/gpt-5-mini-vs-gpt-5-nano)
- [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [News Pipeline Overview](./NEWS_PIPELINE_OVERVIEW.md)
- [LLM 429 Diagnostic](./LLM_429_DIAGNOSTIC.md)

---

**Doküman Versiyonu:** 1.0  
**Son Güncelleme:** 2025-10-21  
**Durum:** ✅ Aktif
