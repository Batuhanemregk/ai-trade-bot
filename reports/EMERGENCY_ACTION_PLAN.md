# 🚨 ACİL EYLEM PLANI

**Durum:** 44 TP/SL emri + 60 USDT SOL pozisyonu açık  
**Toplam Bakiye:** 100 USDT  
**Risk:** %60 pozisyon açık (YÜKSEK!)

---

## ✅ YAPILAN FİXLER (HEMEN)

### 1. ✅ policy.yaml Fix
```yaml
# Önce:
mode: "live"  # ❌ KRİTİK HATA!

# Sonra:
mode: "paper"  # ✅ PAPER mode default
```

**Dosya:** `configs/policy.yaml:239`

### 2. ✅ Emergency Close Script
```bash
# Script oluşturuldu:
scripts/emergency_close_all.py
```

---

## 🎯 YAPMANZ GEREKENLER (SIRA İLE)

### ADIM 1: POZİSYONLARI KAPAT (MANUEL - ÖNERİLEN)

**OKX Web/App:**
```
1. Positions bölümüne git
2. SOL-USDT-SWAP pozisyonunu seç
3. "Close at Market" tıkla
4. Onaylayı
```

**VEYA Python Script:**
```bash
cd C:\Users\batuhan\Desktop\ai_bot_trader\ai-trade-bot
python scripts\emergency_close_all.py
```

**Not:** Manuel daha güvenli (script'e güvenmezseniz)

---

### ADIM 2: EMİRLERİ İPTAL ET

**OKX Web/App:**
```
1. Orders → Open Orders
2. "Cancel All" tıkla
3. Algo Orders → tüm trigger emirlerini iptal et
```

**VEYA Python Script:**
```bash
# Zaten emergency_close_all.py içinde
```

---

### ADIM 3: HASAR TESPİTİ

**OKX History kontrol:**
```
1. Order History → son 1 saat
2. Trade History → filled orders
3. Transaction History → fees

Bakılacaklar:
- Kaç işlem açıldı?
- Hangi fiyatlardan?
- TP/SL'ler tetiklendi mi?
- Toplam PnL ne?
- Fees ne kadar?
```

---

### ADIM 4: BOT'U TEST ET (PAPER MODE)

```powershell
# ENV değişkenlerini kontrol et
$env:PYTHONIOENCODING="utf-8"

# Bot'u başlat (artık paper mode)
cd C:\Users\batuhan\Desktop\ai_bot_trader\ai-trade-bot
. .\scripts\dev.ps1
Start-Scheduler
```

**Kontrol:**
```bash
# Prometheus metrics:
http://localhost:8000/metrics | Select-String "aibot_info_info"

# Beklenen:
aibot_info_info{mode="paper"}  # ✅ PAPER olmalı!
```

---

## 📊 HASAR TAHMİNİ

### Best Case (İyi Senaryo)
```
- SOL fiyatı stabil kaldı
- TP vurdu → +$10-20 kar
- Fees: ~$5
- Net: +$5-15 ✅
```

### Neutral Case (Nötr)
```
- Fiyat az hareket etti
- Pozisyon hala açık
- Fees: ~$5
- Net: -$5 ⚠️
```

### Worst Case (Kötü Senaryo)
```
- SOL fiyatı düştü
- SL vurdu → -$10-20 zarar
- Fees: ~$5
- Net: -$15-25 ❌
```

**Mevcut Durum:** Pozisyon hala açık → **Manual kapatma gerekli!**

---

## 🔧 UZUN VADELİ FİXLER

### 1. ENV Variable Override (KOD DEĞİŞİKLİĞİ)

**Problem:** ENV `TRADING_MODE` policy.yaml'ı override etmiyor

**Fix:**
```python
# infrastructure/runtime.py veya bootstrap.py
# Mode'u ENV'den al, yoksa policy'den
trading_mode = os.getenv('TRADING_MODE', 
                         policy.get('exchange', {}).get('mode', 'paper'))
```

### 2. gpt-5-nano JSON Fix

**Problem:** LLM boş response dönüyor

**Fix:**
```python
# application/news_llm_analyzer.py:_get_llm_analysis
# Fallback ekle:
if not response or not response.strip():
    logger.warning(f"Empty LLM response for {symbol}, using fallback")
    return {"sentiment": "neutral", "confidence": 0.5}
```

### 3. Position Size Validation

**Problem:** $60 position, $100 balance (%60!)

**Fix:**
```python
# infrastructure/runtime.py:_calculate_position_size
# Max position check:
max_position_percent = 0.30  # %30 max
max_allowed = balance * max_position_percent

if position_size_usd > max_allowed:
    logger.warning(f"Position ${position_size_usd} exceeds max ${max_allowed}")
    position_size_usd = max_allowed
```

---

## 📋 ÖNCELİK SİRALAMASI

| # | Eylem | Kritiklik | Süre | Durum |
|---|-------|-----------|------|-------|
| 1 | POZİSYONLARI KAPAT | 🔴 ACİL | 2 dk | ⏳ BEKLİYOR |
| 2 | EMİRLERİ İPTAL ET | 🔴 ACİL | 2 dk | ⏳ BEKLİYOR |
| 3 | HASAR TESPİTİ | 🟠 YÜKSEK | 10 dk | ⏳ BEKLİYOR |
| 4 | policy.yaml fix | 🟢 TAMAMLANDI | - | ✅ YAPILDI |
| 5 | BOT TEST (paper) | 🟡 ORTA | 10 dk | ⏳ BEKLİYOR |
| 6 | ENV override fix | 🟡 ORTA | 2 saat | ⏳ PLANLANDI |
| 7 | JSON parse fix | 🟡 ORTA | 4 saat | ⏳ PLANLANDI |
| 8 | Position size fix | 🟢 DÜŞÜK | 1 saat | ⏳ PLANLANDI |

---

## ✅ ÖNERİ

### ŞUAN YAPILACAKLAR (15 DAKİKA):

1. **MANUEL KAPAT** (OKX web/app) ← **EN GÜVENLİ**
   ```
   - Positions → SOL → Close at Market
   - Orders → Cancel All
   ```

2. **HASAR TESPİTİ**
   ```
   - Order history kontrol
   - PnL hesapla
   - Report oluştur
   ```

3. **BOT TEST**
   ```
   - Start-Scheduler
   - Metrics kontrol: mode="paper" ✅
   ```

### YARILMACAKLAR (BU HAFTA):

1. ENV override fix (2 saat)
2. JSON parse fix (4 saat)
3. Position size validation (1 saat)
4. Comprehensive test (paper, 2 saat)

---

## 📱 DESTEK

**Sorularınız için:**
- Log dosyaları: `reports/CRITICAL_*.txt`
- Hata analizi: `reports/DETAILED_ERROR_ANALYSIS.md`
- Bu action plan: `reports/EMERGENCY_ACTION_PLAN.md`

---

**Rapor Tarihi:** 2025-10-22 02:40  
**Durum:** ACİL EYLEM GEREKLİ  
**Sonraki Adım:** POZİSYONLARI KAPAT!

