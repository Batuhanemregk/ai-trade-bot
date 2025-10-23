# 30 Dakikalık Test İzleme Planı
**Başlangıç:** 2025-10-22 01:51:00 UTC  
**Bitiş:** 2025-10-22 02:21:00 UTC  
**Durum:** 🟢 Çalışıyor

## 📊 İzleme Noktaları

### 5 Dakikada Bir (T+5, T+10, T+15, T+20, T+25, T+30)
- ✅ enter_short hatası var mı? (YOK olmalı)
- ✅ LLM çağrıları başarılı mı?
- ✅ Digest CHANGED/SAME dengesi nasıl?
- ✅ Unclosed session warnings var mı?
- ✅ Job'lar SUCCESS mu?

### 15 Dakikada Bir (T+15, T+30)
- Prometheus metrics snapshot
- aibot_* metrikler
- Cost tracking

### 30 Dakika Sonunda
- Final metrics
- Log summary
- Raporları doldur

## ⏰ Zaman Çizelgesi

```
T+0  (01:51) - ✅ Bot başladı
T+2  (01:53) - İlk kontrol
T+5  (01:56) - News job çalıştı mı?
T+10 (02:01) - Metrics check
T+15 (02:06) - Trading job çalıştı mı?
T+20 (02:11) - Digest hit rate kontrolü
T+25 (02:16) - Cost tracking
T+30 (02:21) - ✅ Final snapshot ve raporlar
```

**Şu an:** Bot çalışıyor, izleme başladı!

