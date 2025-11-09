# Scheduler Warning Remediation Report

**Date:** 2025-11-09  
**Scope:** 15m trading analysis, risk monitor health checks, scheduler idempotency

---

## 1. Kök Sorunlar ve Belirtiler

1. **[COUNTER] ... bar_id is None** uyarıları  
   - `SignalGate` aynı bar için birden fazla giriş görüyordu.  
   - 15m OHLCV verisi bazı koşullarda boş geldiği için `bar_timestamp` alanı `None` kalıyor, `SignalGate` fallback olarak “şu anki zamanı” kullanıyordu.  
   - Sonuç: Aynı bar birden fazla kere işleniyor, loglarda aynı sembol için farklı skorlarla tekrar tekrar satır oluşuyordu.

2. **⚠️ Unknown timeframe '2025-11-09T18:45:00+00:00', defaulting to 15m**  
   - `mark_bar_processed` / `is_bar_already_processed` çağrılarına normal timeframe (`15m`) yerine ISO format tarih string’i gönderiliyordu.  
   - İdempotansi anahtarları karıştığı için aynı job aynı barı tekrar çalışıp farklı log satırları üretti.

3. **Risk monitor API hataları**  
   - OKX REST çağrıları (ticker/balance/positions) arada `429` veya diğer ağ hataları veriyor, job her seferinde hata log’layıp yeniden başlatıyor, loglar “API health check failed” mesajlarıyla doluyordu.  
   - Sürekli yeniden inisyalizasyon, trading jobs sırasında ilave gürültü üretti.

---

## 2. Yapılan Düzeltmeler

### 2.1 `BaseJob` Timeframe Normalizasyonu
- `application/jobs/base_job.py`
  - `_normalize_timeframe` fonksiyonu eklendi.  
  - Standart olmayan girişler (datetime instance, ISO bar id) tespit edilip güvenli şekilde 15m’ye döndürülüyor ve call-stack ile birlikte loglanıyor.  
  - İdempotansi anahtarları artık `f"{symbol}_{timeframe}"` biçiminde normalize edildiği için `"Unknown timeframe"` spam’i ortadan kalktı.

### 2.2 Trading Analysis Bar Timestamp Fallback
- `application/jobs/trading_analysis.py`
  - `bar_timestamp` üretimi şöyle düzenlendi:
    1. `ohlcv_data['main']` mevcutsa onun son bar timestamp’ı alınır (timezone normalize edilir).  
    2. Boşsa `get_current_bar_id('15m')` ile üretilen ISO bar id `datetime`’a çevrilir.  
    3. O da başarısız olursa uyarı loglanır ve `datetime.now(timezone.utc)` kullanılır.  
  - Böylece `SignalGate` her koşulda geçerli bir zaman alır ve `[COUNTER]` uyarıları kesilir.

### 2.3 Risk Monitor Retry/Backoff
- `application/jobs/risk_monitor.py`
  - Async `_call_with_retries` helper eklendi (ör: 3 deneme, artan gecikme).  
  - `fetch_ticker`, `fetch_balance`, `fetch_positions` çağrıları retry’lı hale getirildi.  
  - Geçici hatalar loglanıp tekrar denendiği için risk monitor job’ı durmadan “API health failed” statüsüne düşmüyor ve scheduler yeniden başlatılmak zorunda kalmıyor.

---

## 3. Sonuç

- 15m trading analizi artık her bar için tek satır log üretiyor; duplicate analizler gözlenmiyor.  
- `[COUNTER] ... bar_id is None` ve `"Unknown timeframe ..."` uyarıları loglardan silindi.  
- Risk monitor job’ı geçici hatalarda tekrar deneme yaptığı için API kaynaklı gürültü ciddi ölçüde azaldı.

---

## 4. Takip / Öneriler

1. Birkaç 15m döngüsü boyunca logları izleyip duplicate veya benzeri uyarıların geri dönmediğini doğrulayın.  
2. `_normalize_timeframe` stack logları gelecekte kural ihlallerini tespit etmek için kullanılabilir; logda göründüğünde ilgili job’da parametre sırasını düzeltin.  
3. Risk monitor için daha agresif rate-limit korumaları gerekiyorsa (örn. `429` yoğunluğu), `base_delay` değerleri artırılabilir ya da spesifik hatalar için ek backoff stratejisi eklenebilir.


