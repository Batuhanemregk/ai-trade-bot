# İşlem Açma Karar Mekanizması - Detaylı Özet

## 📊 Genel Bakış

İşlem açma kararı **4 aşamalı** bir süreçten geçer:
1. **Composite Signal Hesaplama** (Ağırlıklı skor)
2. **Decision Thresholds** (Eşik kontrolü)
3. **Signal Gate** (Filtreleme: Persistence, Confirmation, Age, Hysteresis)
4. **State Transition** (Durum geçişi: OPEN_LONG, OPEN_SHORT, MAINTAIN, CLOSE_REVERSE)

---

## 1️⃣ Composite Signal Hesaplama (Ağırlıklar)

### Base Ağırlıklar (Policy'den)

```yaml
ta_weight: 0.3      # Technical Analysis: %30
ml_weight: 0.5      # Machine Learning: %50
news_weight: 0.1    # News Sentiment: %10
risk_weight: 0.07   # Risk Score: %7
```

**Toplam:** 0.97 (normalize edilerek 1.0'a çıkarılıyor)

### Regime-Adaptive Ağırlıklar (Dinamik)

**Koşul:** `trend_strength > 0.6` ve `volatility > 0.7` (Yüksek trend + Düşük risk)

```python
ta_weight: min(0.3 * 1.1, 0.8) = 0.33  # +10% (max 0.8)
ml_weight: 0.5                          # Değişmez
news_weight: 0.1                        # Değişmez
risk_weight: max(0.07 * 0.9, 0.05) = 0.063  # -10% (min 0.05)
```

**Diğer durumlar:** Base ağırlıklar kullanılır.

### Final Score Hesaplama

```python
final_score = (
    ta_weight * ta_score +
    ml_weight * ml_score +
    news_weight * news_score +
    risk_weight * risk_score
)
```

**Not:** Eğer `news_score` veya `risk_score` `None` ise:
- Ağırlık diğer komponentlere dağıtılır
- Hesaplama için `50.0` (neutral) kullanılır

---

## 2️⃣ Decision Thresholds (Eşikler)

### Entry/Exit Eşikleri

```yaml
enter_long: 60    # Score >= 60 → LONG entry
enter_short: 40   # Score <= 40 → SHORT entry
exit_long: 45     # Score <= 45 → LONG exit/reversal
exit_short: 55    # Score >= 55 → SHORT exit/reversal
flat_range: [47, 53]  # 47-53 arası → FLAT (neutral zone)
```

### Hysteresis (Gecikme Mekanizması)

**LONG:**
- **Entry:** Score >= 60
- **Exit:** Score <= 45
- **Hysteresis:** 15 puan fark (60 - 45 = 15)

**SHORT:**
- **Entry:** Score <= 40
- **Exit:** Score >= 55
- **Hysteresis:** 15 puan fark (55 - 40 = 15)

**Flat Zone:**
- **Range:** 47-53 (6 puan genişlik)
- **Amaç:** Gürültüyü filtrelemek, gereksiz giriş/çıkışları engellemek

### Decision Logic

```python
if final_score >= 60:
    decision = "LONG"
elif final_score <= 40:
    decision = "SHORT"
elif 47 <= final_score <= 53:
    decision = "FLAT"
else:
    # 53 < score < 60 veya 40 < score < 47
    decision = "FLAT"  # Neutral zone dışı ama eşik altı
```

---

## 3️⃣ Signal Gate (Filtreleme)

### Persistence (Dayanıklılık)

**Requirement:** `persistence_bars: 2`

**Mantık:**
- Sinyal **2 bar** boyunca aynı yönde ve eşik üzerinde olmalı
- Her bar'da `final_score >= 60` (LONG) veya `final_score <= 40` (SHORT) olmalı
- Eğer bir bar'da eşik altına düşerse, sayaç sıfırlanır

**Örnek:**
```
Bar 1: Score = 65 (LONG) → Count = 1
Bar 2: Score = 62 (LONG) → Count = 2 → PASS (2/2)
Bar 3: Score = 58 (FLAT) → Count = 0 → FAIL (eşik altı)
```

### Confirmation (Onay)

**Requirement:** `rev_confirm_bars: 2`

**Mantık:**
- **Entry sinyalleri:** Confirmation **gerekli değil** (sadece persistence yeterli)
- **Reversal sinyalleri:** Confirmation **gerekli** (2 bar)
- Confirmation için: `final_score >= (enter_long + margin)` veya `final_score <= (enter_short - margin)`
- **Margin:** `confirmation_margin: 2.0` (ekstra 2 puan)

**Örnek (Reversal):**
```
LONG → SHORT reversal:
- Bar 1: Score = 38 (SHORT, 40-2=38) → Count = 1
- Bar 2: Score = 37 (SHORT, 40-2=38) → Count = 2 → PASS (2/2)
```

### Age (Yaş)

**Requirement:** `max_signal_age_bars: 6`

**Mantık:**
- Sinyal **max 6 bar** yaşında olmalı
- Eğer sinyal 6 bar'dan eskiyse, geçersiz sayılır
- Age, signal history'deki toplam sinyal sayısına göre hesaplanır

### Hysteresis (Gecikme)

**Mantık:**
- Entry ve exit eşikleri arasında **15 puan fark** var
- Bu, sinyal gürültüsünü filtreler ve gereksiz giriş/çıkışları engeller
- Örnek: LONG pozisyonu açmak için 60, kapatmak için 45 gerekli (15 puan fark)

---

## 4️⃣ State Transition (Durum Geçişi)

### State Machine

```
READY → LONG_OPEN: Score >= 60 + Gate PASS
READY → SHORT_OPEN: Score <= 40 + Gate PASS
LONG_OPEN → SHORT_OPEN: Score <= 45 + Confirmation (2 bar) + Min hold bars (3)
SHORT_OPEN → LONG_OPEN: Score >= 55 + Confirmation (2 bar) + Min hold bars (3)
LONG_OPEN → LONG_OPEN: Score >= 60 → IGNORE (same direction)
SHORT_OPEN → SHORT_OPEN: Score <= 40 → IGNORE (same direction)
```

### Transition Rules

#### 1. ReadyToOpenRule (READY → LONG_OPEN/SHORT_OPEN)

**Koşullar:**
- `current_state == READY`
- `gate_pass == True` (Signal gate'den geçmeli)
- `size > 0` (Position size hesaplanmış olmalı)
- `mode in ('LIVE', 'PAPER')` (DRY-RUN değil)
- `final_score >= 60` (LONG) veya `final_score <= 40` (SHORT)

**Action:**
- `OPEN_LONG` veya `OPEN_SHORT`

#### 2. SameDirectionIgnoreRule (Aynı Yönde Sinyal)

**Koşullar:**
- `current_state == LONG_OPEN` ve `final_score >= 60`
- `current_state == SHORT_OPEN` ve `final_score <= 40`

**Action:**
- `IGNORE` (pozisyon korunur, yeni işlem açılmaz)

#### 3. ReversalRule (LONG_OPEN → SHORT_OPEN, SHORT_OPEN → LONG_OPEN)

**Koşullar:**
- `current_state == LONG_OPEN` ve `final_score <= 45` ve `holding_bars >= 3`
- `current_state == SHORT_OPEN` ve `final_score >= 55` ve `holding_bars >= 3`
- `confirmation_bars >= 2` (reversal confirmation gerekli)

**Action:**
- `CLOSE_REVERSE` (pozisyon kapatılır, ters yönde açılır)

#### 4. CooldownRule (COOLDOWN state)

**Koşullar:**
- Pozisyon TP/SL ile kapatıldı
- Manual close yapıldı

**Action:**
- `COOLDOWN` (cooldown period başlar)

#### 5. CooldownToReadyRule (COOLDOWN → READY)

**Koşullar:**
- `current_state == COOLDOWN`
- `cooldown_period` doldu (`entry_cooldown_bars: 2`)

**Action:**
- `READY` (yeni işlem açılabilir)

---

## 5️⃣ Position Sizing (Pozisyon Boyutlandırma)

### Base Sizing

```yaml
min_percentage: 0.01    # %1 minimum
max_percentage: 0.10    # %10 maximum
score_multiplier: 0.09  # Skor çarpanı
regime_multiplier: 0.6  # Low ADX regime multiplier
```

### Sizing Formula

```python
# Base size
base_size = score_multiplier * (final_score / 100.0)

# Regime adjustment
if regime == 'mean_reversion' (Low ADX):
    base_size = base_size * regime_multiplier  # 0.6x

# Grade multiplier
if grade == 'A+': multiplier = 1.0
elif grade == 'A': multiplier = 0.7
elif grade == 'B': multiplier = 0.5
elif grade == 'C': multiplier = 0.3
else: multiplier = 0.0

final_size = base_size * multiplier

# Clamp to min/max
final_size = max(0.01, min(0.10, final_size))
```

### Risk Management

```yaml
max_position_size_pct: 0.01    # %1 per position
max_total_risk_pct: 0.60       # %60 total risk
max_concurrent_positions: 20   # Max 20 positions
max_position_age_hours: 24     # Max 24h position age
```

---

## 6️⃣ Grade System (Not Sistemi)

### Grade Thresholds

```python
A+: final_score >= 90
A:  final_score >= 80
B:  final_score >= 70
C:  final_score >= 60
D:  final_score < 60
```

### Grade Multipliers (Position Size)

```python
A+: 1.0  # Full position
A:  0.7  # 70% position
B:  0.5  # 50% position
C:  0.3  # 30% position
D:  0.0  # No trade
```

---

## 7️⃣ Örnek Senaryo

### Senaryo: BTC LONG Entry

**1. Composite Signal Hesaplama:**
```
TA Score: 75
ML Score: 68
News Score: 55
Risk Score: 42

Final Score = 0.3 * 75 + 0.5 * 68 + 0.1 * 55 + 0.07 * 42
            = 22.5 + 34.0 + 5.5 + 2.94
            = 64.94
```

**2. Decision Threshold:**
```
final_score = 64.94 >= 60 → LONG
```

**3. Signal Gate:**
```
Bar 1: Score = 65 (LONG) → Persist = 1/2
Bar 2: Score = 64.94 (LONG) → Persist = 2/2 → PASS
Age: 2/6 → PASS
Confirmation: Entry için gerekli değil
Gate Result: PASS
```

**4. State Transition:**
```
current_state: READY
signal: LONG, Gate PASS, Size > 0
transition: READY → LONG_OPEN
action: OPEN_LONG
```

**5. Position Sizing:**
```
base_size = 0.09 * (64.94 / 100) = 0.058
grade = 'B' → multiplier = 0.5
final_size = 0.058 * 0.5 = 0.029 (≈ %3)
```

---

## 8️⃣ Özet Tablo

| Özellik | Değer | Açıklama |
|---------|-------|----------|
| **TA Weight** | 0.3 (30%) | Technical Analysis ağırlığı |
| **ML Weight** | 0.5 (50%) | Machine Learning ağırlığı |
| **News Weight** | 0.1 (10%) | News Sentiment ağırlığı |
| **Risk Weight** | 0.07 (7%) | Risk Score ağırlığı |
| **Enter Long** | >= 60 | LONG giriş eşiği |
| **Enter Short** | <= 40 | SHORT giriş eşiği |
| **Exit Long** | <= 45 | LONG çıkış eşiği |
| **Exit Short** | >= 55 | SHORT çıkış eşiği |
| **Flat Range** | [47, 53] | Neutral zone |
| **Persistence** | 2 bar | Sinyal dayanıklılığı |
| **Confirmation** | 2 bar | Reversal onayı (entry için gerekli değil) |
| **Max Age** | 6 bar | Maximum sinyal yaşı |
| **Confirmation Margin** | 2.0 | Ekstra puan (reversal için) |
| **Min Hold Bars** | 3 bar | Minimum tutma süresi (reversal için) |
| **Min Position Size** | %1 | Minimum pozisyon boyutu |
| **Max Position Size** | %10 | Maximum pozisyon boyutu |
| **Max Total Risk** | %60 | Maximum toplam risk |
| **Max Positions** | 20 | Maximum eşzamanlı pozisyon |

---

## 9️⃣ Önemli Notlar

1. **Entry vs Reversal:**
   - **Entry:** Sadece persistence gerekli (2 bar)
   - **Reversal:** Persistence + Confirmation gerekli (2 bar + 2 bar)

2. **Hysteresis:**
   - Entry ve exit eşikleri arasında **15 puan fark** var
   - Bu, sinyal gürültüsünü filtreler

3. **Flat Zone:**
   - 47-53 arası sinyaller FLAT olarak kabul edilir
   - Bu, gereksiz giriş/çıkışları engeller

4. **Regime-Adaptive Weights:**
   - Yüksek trend + Düşük risk durumunda TA ağırlığı artar (+10%, max 0.8)
   - Diğer durumlarda base ağırlıklar kullanılır
   - ML ağırlığı en yüksek (%50), TA ağırlığı ikinci sırada (%30)

5. **None Handling:**
   - Eğer `news_score` veya `risk_score` `None` ise:
   - Ağırlık diğer komponentlere dağıtılır
   - Hesaplama için `50.0` (neutral) kullanılır

---

## 🔟 Dosya Referansları

- **Policy:** `configs/policy.yaml` (lines 125-147)
- **Composite Signal:** `scoring/composite_signal.py`
- **Signal Gate:** `application/signal_gate.py`
- **State Manager:** `application/position_state_manager.py`
- **Runtime:** `infrastructure/runtime.py` (lines 982-1033)

