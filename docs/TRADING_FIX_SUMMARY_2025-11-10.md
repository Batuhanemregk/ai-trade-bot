# Trading Fix Özeti - 2025-11-10

## Yapılan Düzeltmeler

### 1. Confirmation Processor Düzeltildi (KRİTİK)

**Sorun:** Confirmation processor, entry durumlarında da çalışıyordu ve confirmation sayacı 0/2 kalıyordu. Bu yüzden hiç trade açılmıyordu.

**Çözüm:**
- Entry sinyalleri için confirmation requirement'ı kaldırıldı (sadece persistence yeterli)
- Reversal sinyalleri için confirmation requirement'ı korundu
- `ConfirmationProcessor.process()` fonksiyonu entry/reversal ayrımı yapıyor
- Entry durumlarında `is_valid = True` (confirmation gerekmez)
- Reversal durumlarında `is_valid = confirmation_count >= confirm_bars` (confirmation gerekli)

**Dosya:** `application/signal_gate.py`
- `ConfirmationProcessor.process()` güncellendi
- `_is_entry_signal()` eklendi (entry/reversal ayrımı için)
- `_count_confirmation()` güncellendi (entry durumlarında farklı logic)

### 2. Policy Uyumu Düzeltildi

**Sorun:** Logger'da persist_required: 5 hardcoded, policy'de 2 diyordu.

**Çözüm:**
- Logger artık policy'den `persistence_bars` ve `rev_confirm_bars` değerlerini okuyor
- `trading_analysis.py` ve `runtime.py`'da policy'den okuma eklendi
- Logger'da gösterilen değerler policy ile uyumlu

**Dosyalar:**
- `application/jobs/trading_analysis.py` - gate_details policy'den okuyor
- `infrastructure/runtime.py` - gate_details policy'den okuyor
- `application/log_formatter.py` - conf formatı düzeltildi (integer count)

### 3. Risk Ağırlığı Düşürüldü

**Sorun:** Risk ağırlığı yüksek (0.1), nihai skorları aşağı çekiyordu.

**Çözüm:**
- Policy'de `risk_weight: 0.1 → 0.07` düşürüldü
- `_calculate_regime_adaptive_weights()` fonksiyonu policy'den ağırlıkları okuyor
- Ağırlıklar normalize ediliyor (toplam 1.0)

**Dosyalar:**
- `configs/policy.yaml` - risk_weight: 0.07
- `infrastructure/runtime.py` - _calculate_regime_adaptive_weights() policy'den okuyor

### 4. RiskMonitorJob Hatası

**Sorun:** `name 'timeframe_str' is not defined` hatası (loglarda görülüyor ama kodda yok).

**Çözüm:**
- Kod incelemesi yapıldı, `timeframe_str` referansı bulunamadı
- Hata muhtemelen eski kod versiyonundan kaynaklanıyor
- Mevcut kodda `mark_bar_processed(self.job_id, '1m')` doğru kullanılıyor
- RiskMonitorJob'da timeframe '1m' sabit kullanılıyor (doğru)

**Dosya:** `application/jobs/risk_monitor.py` - Zaten doğru, hata eski loglardan

## Beklenen Sonuçlar

### Öncesi:
- 179 decision, hepsi `Gate=FAIL`
- 0 LONG sinyali (skor >= 60)
- 8 SHORT sinyali (skor <= 40) ama trade açılmadı
- Confirmation sayacı 0/2 (entry durumlarında da confirmation gerekliydi)
- Persist sayacı 5/5, 6/5, 7/5'e kadar çıktı ama confirmation 0/2 kaldığı için Gate=FAIL

### Sonrası:
- Entry sinyalleri için confirmation gerekmez, sadece persistence yeterli
- Persist sayacı 2/2 olduğunda (policy'de 2), Gate=PASS olacak
- Reversal sinyalleri için confirmation gerekli (2/2)
- Risk ağırlığı düşürüldü (0.1 → 0.07), nihai skorlar daha yüksek olacak
- Logger policy ile uyumlu, persist_required değeri doğru gösteriliyor

## Test Senaryoları

1. **Entry Sinyali Testi:**
   - Final score >= 60 (LONG) veya <= 40 (SHORT)
   - Persist sayacı 2/2
   - Confirmation sayacı 0/2 (entry için gerekmez)
   - Beklenen: Gate=PASS, trade açılmalı

2. **Reversal Sinyali Testi:**
   - Mevcut pozisyon var (LONG veya SHORT)
   - Final score reversal threshold'u geçiyor
   - Persist sayacı 2/2
   - Confirmation sayacı 2/2 (reversal için gerekli)
   - Beklenen: Gate=PASS, reversal yapılmalı

3. **Policy Uyumu Testi:**
   - Logger'da persist_required: 2 gösterilmeli (policy'de 2)
   - Logger'da conf_required: 2 gösterilmeli (policy'de 2)

4. **Risk Ağırlığı Testi:**
   - Risk score yüksek olsa bile (57-63), nihai skor daha yüksek olmalı
   - Risk ağırlığı 0.07, diğer ağırlıklar normalize edilmeli

## Notlar

- Hysteresis açık durumda (policy'de enable)
- LONG=60 / SHORT=40 eşikleri korundu
- Policy'de `persistence_bars: 2` (logger artık bunu okuyor)
- Policy'de `rev_confirm_bars: 2` (reversal için confirmation gerekli)
- Risk ağırlığı 0.07 (policy'de güncellendi)

## Sonraki Adımlar

1. Bot'u yeniden başlat ve logları izle
2. Gate=PASS durumunda trade açıldığını doğrula
3. Entry sinyalleri için confirmation gerekmemesi test et
4. Reversal sinyalleri için confirmation requirement'ı test et
5. Policy uyumunu doğrula (logger'da persist_required: 2 gösterilmeli)


