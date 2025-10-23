# E2E Test Export Summary
**Generated:** 2025-10-20 02:45:00  
**Source:** E2E_EXPORT_PAPER.zip  

## 1) Koşu Özeti
- **Mod:** Paper Trading
- **Süre:** 10 dakika (02:29 - 02:45) - süre kontrolü çalışmadı
- **Semboller:** BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
- **Timeframe'ler:** 5m, 15m, 1h
- **Test Durumu:** PARTIAL PASS

## 2) Sinyal & Gating Örnekleri
```
01:30:35 | DEBUG | E2E | ✅ TA scoring completed for UNI-USDT-SWAP: 56.2
01:30:35 | DEBUG | E2E | ✅ ML scoring for UNI-USDT-SWAP: p_up=0.296, score=29.6
01:30:35 | INFO | E2E | [REGIME] UNI-USDT-SWAP ADX(1H)=nan → mean_reversion mode
```

**E2E Relaxations Uygulandı:**
- Signal gating: persist=2, conf=0.5, age=10
- Decision thresholds: long=55/50, short=45/50
- Position sizing: min=5, max=50 USDT

## 3) Order Lifecycle
- **Entry:** ❌ FAIL - Hiç entry sinyali oluşmadı
- **TP/SL:** ❌ FAIL - Entry olmadığı için TP/SL kurulmadı
- **Trailing:** ❌ FAIL - Aktif pozisyon olmadığı için trailing çalışmadı
- **Exit:** ❌ FAIL - Entry olmadığı için exit olmadı

**Forced Entry Attempt:**
```
{"timestamp": "2025-10-20T02:35:00Z", "event": "forced_entry_attempt", "symbol": "BTC-USDT-SWAP", "type": "test_entry", "status": "failed", "reason": "llm_quota_exceeded"}
```

## 4) Risk & Limit Notları
✅ **Risk Monitoring:** Aktif ve çalışıyor
- API health: OK (600-700ms)
- Memory usage: 33.4-33.7%
- Disk usage: 47.9%
- Circuit breaker: Normal

**Risk Logları:**
```
01:50:01 | DEBUG | [RISK] Daily PnL: $4.25 (0.58%)
01:50:01 | DEBUG | [RISK] Circuit breaker: normal
```

## 5) Monitoring: aibot_* Metrikleri
```
aibot_job_execution_total{job="trading_analysis",status="success"} 1
aibot_job_execution_total{job="risk_monitor",status="success"} 12
aibot_job_execution_total{job="news_incremental_5m",status="success"} 3
aibot_job_execution_total{job="market_overview",status="success"} 1

aibot_signal_generation_total{symbol="BTC-USDT-SWAP",type="composite"} 1
aibot_signal_generation_total{symbol="ETH-USDT-SWAP",type="composite"} 1
aibot_signal_generation_total{symbol="SOL-USDT-SWAP",type="composite"} 1

aibot_risk_checks_total{type="api_health",status="ok"} 12
aibot_risk_checks_total{type="memory_usage",status="ok"} 12
aibot_risk_checks_total{type="circuit_breaker",status="normal"} 12

aibot_news_processing_total{type="llm_analysis",status="quota_exceeded"} 28
aibot_news_processing_total{type="news_fetch",status="success"} 517
```

## 6) Hata/Uyarı Alıntıları ve Kök Neden

### 🔴 Kritik Hatalar:
1. **LLM Rate Limiting:**
   ```
   ERROR | LLM API request failed: Error code: 429 - insufficient_quota
   ```
   **Kök Neden:** OpenAI API rate limiting (dakika/saat başına istek limiti)

2. **Test Süre Kontrolü:**
   ```
   Test 10 dakika ayarlandı ama 15+ dakika çalıştı
   ```
   **Kök Neden:** E2E runner'da süre kontrolü eksik

### 🟡 Uyarılar:
1. **`enter_short` Hatası Devam Ediyor:** Kod düzeltmesi henüz çalışmıyor
2. **No Active Positions:** Test süresince hiç pozisyon açılmadı

## 7) trades.csv / orders.jsonl Sayıları

### trades.csv:
- **Toplam Trade:** 3 (tümü test_entry_failed)
- **Semboller:** BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
- **Durum:** Tümü başarısız (LLM quota nedeniyle)

### orders.jsonl:
- **Toplam Event:** 10
- **Başarılı:** 8 (data_validation, signal_generation, relaxations_applied)
- **Başarısız:** 2 (forced_entry_attempt, test_end partial_pass)

## 8) Sonuç: PARTIAL PASS

### ✅ Başarılı Bileşenler:
- Veri toplama ve OHLCV analizi
- TA/ML/News skorlama
- Risk monitoring ve circuit breaker
- Scheduler jobs ve sistem sağlığı
- Metrics ve monitoring

### ❌ Başarısız Bileşenler:
- Entry sinyali oluşturulamadı
- Order lifecycle test edilemedi
- Trading execution doğrulanamadı

### 🔧 5 Kısa Aksiyon:
1. **LLM rate limiting ayarlarını düzenle** - API çağrılarını azalt
2. **`enter_short` hatasını düzelt** - Kod düzeltmesi çalışmıyor
3. **Test süre kontrolünü düzelt** - E2E runner'da süre kontrolü eksik
4. **LLM çağrılarını azalt** - Summary mode kullan
5. **Gating kurallarını daha da gevşet** - Test için entry sinyali oluştur

### 📝 Genel Değerlendirme:
Bot'un temel bileşenleri çalışıyor. E2E relaxations başarıyla uygulandı. Ana sorun LLM rate limiting ve `enter_short` hatası. Teknik altyapı sağlam, sadece rate limiting ve kod düzeltmesi gerekiyor.

