# ML Analizinin Short ve Long Mekanizması

## 📋 Genel Bakış

ML (Machine Learning) analizi, sistemin **short** ve **long** sinyallerini üretmek için kullanılan 4 ana bileşenden biridir (TA, ML, News, Risk). ML scorer, eğitilmiş LightGBM modelleri kullanarak fiyatın **yukarı gitme olasılığını** (`p_up`) tahmin eder ve bunu 0-100 arası bir skora dönüştürür.

---

## 🔄 ML Analiz Akışı

### 1. **Veri Hazırlama** (`infrastructure/runtime.py`)

```python
# Multi-timeframe veri çekme
ohlcv_data = await _fetch_multi_timeframe_data(exchange_adapter, symbol, live)
# İçerik:
# - 'main' (15m): Ana timeframe
# - '1h': Trend analizi
# - '4h': ML features için
```

### 2. **ML Scoring** (`scoring/ml_scorer.py`)

#### 2.1. Model Seçimi
```python
# Model key: "BTC_15m", "ETH_1h", "SOL_4h" gibi
model_key = f"{symbol_short}_{tf}"
# 9 ayrı model var: 3 symbol × 3 timeframe
```

#### 2.2. Feature Engineering (`ml/features/builder.py`)
```python
# 73 feature oluşturuluyor:
# - TA Indicators (20+): RSI, MACD, ATR, Bollinger Bands, ADX, etc.
# - Price Action (14+): Body/wick ratios, Heikin-Ashi, HH/HL/LH/LL
# - Statistics (10+): Log returns, rolling mean/std, skewness, kurtosis
# - Multi-timeframe (6+): RSI_1h, MACD_hist_4h, trend_strength_4h
```

#### 2.3. Tahmin ve Skor Dönüşümü
```python
# Model p_up (probability of price going up) tahmin ediyor
p_up = model.predict_proba(latest_features_df)[0, 1]

# p_up -> 0-100 skoruna dönüştürme:
if p_up >= 0.65:
    ml_score = 70-100 (LONG - Güçlü)
elif p_up >= 0.50:
    ml_score = 60-69 (LONG_WEAK - Zayıf)
elif p_up >= 0.35:
    ml_score = 40-59 (NEUTRAL - Nötr)
elif p_up >= 0.20:
    ml_score = 20-39 (SHORT_WEAK - Zayıf)
else:
    ml_score = 0-19 (SHORT - Güçlü)
```

#### 2.4. Yön Belirleme
```python
# ML'in yönü:
ml_score >= 60 → LONG
ml_score <= 40 → SHORT
40 < ml_score < 60 → FLAT (Nötr)
```

---

## 🎯 Short ve Long Sinyaldeki Rolü

### **Composite Signal'deki Ağırlığı**

ML scorer'ın composite signal'e katkısı:

```python
# Ağırlıklar (policy.yaml'dan):
weights = {
    'technical_weight': 0.40,  # TA: %40
    'ml_weight': 0.35,         # ML: %35 (İKİNCİ EN ÖNEMLİ)
    'news_weight': 0.10,       # News: %10
    'risk_weight': 0.15        # Risk: %15
}

# Final score hesaplama:
final_score = (
    ta_score * 0.40 +
    ml_score * 0.35 +  # ML'in %35 ağırlığı var
    news_score * 0.10 +
    risk_score * 0.15
)
```

### **Karar Verme Süreci** (`scoring/composite_signal.py`)

```python
# 1. Final score hesaplanıyor (weighted)
final_score = weighted_sum_of_all_components

# 2. Minimum confidence eşiği kontrol ediliyor
min_confidence = 50  # Varsayılan
if final_score < min_confidence:
    decision = "FLAT"
else:
    # 3. Yön belirleme (konsensus)
    tech_direction = TA'dan gelen yön hint'i
    ml_direction = _get_ml_direction()  # ML'in yönü
    
    # Konsensus kontrolü:
    if tech_direction == ml_direction and tech_direction != "FLAT":
        decision = tech_direction  # ✅ TA ve ML aynı yönde → Karar ver
    elif tech_direction != "FLAT":
        decision = tech_direction  # TA'ya güven
    elif ml_direction != "FLAT":
        decision = ml_direction    # ML'e güven
    else:
        decision = "FLAT"  # İkisi de nötr → FLAT
```

### **ML'in Yön Belirleme Eşikleri**

```python
def _get_ml_direction(self) -> str:
    ml_score = self.ml.score
    if ml_score >= 60:    # ML skoru 60+ → LONG
        return "LONG"
    elif ml_score <= 40:  # ML skoru 40- → SHORT
        return "SHORT"
    else:                 # 40 < ml_score < 60 → FLAT
        return "FLAT"
```

---

## ⚠️ Mevcut Problem: Tek Yönlü Öğrenme

### **Şu Anki Durum**

1. **Label Oluşturma** (`ml/features/builder.py`):
   ```python
   # Sadece "yukarı hareket" için label var:
   future_return = ((future_close - df['close']) / df['close']) * 100
   label = (future_return > threshold_pct).astype(int)  # 1 = yukarı, 0 = yukarı değil
   ```
   - Model sadece **"fiyat yukarı mı gidecek?"** sorusunu öğreniyor
   - **"Fiyat aşağı mı gidecek?"** için ayrı bir öğrenme yok

2. **Model Çıktısı**:
   - `p_up`: Fiyatın yukarı gitme olasılığı
   - `p_down = 1 - p_up`: Türetilmiş (doğrudan öğrenilmemiş)

3. **Short Sinyal Problemi**:
   - Short sinyal, `p_up < 0.20` olmasına dayanıyor
   - Ama model **short için eğitilmemiş** - sadece "yukarı değil" durumunu öğreniyor
   - Bu, short sinyallerin daha az güvenilir olmasına neden olabilir

---

## 🔧 İki Yönlü Öğrenme Çözümü

### **Önerilen Yaklaşım**

#### **Seçenek 1: Multi-Class Classification (3 Sınıf)**

```python
# Label oluşturma:
future_return = ((future_close - df['close']) / df['close']) * 100

if future_return > threshold_pct:
    label = 2  # LONG
elif future_return < -threshold_pct:
    label = 0  # SHORT
else:
    label = 1  # FLAT/NEUTRAL

# Model: 3 sınıflı LightGBM
model = lgb.LGBMClassifier(
    objective='multiclass',
    num_class=3,
    ...
)

# Çıktı:
# - p_long: LONG olasılığı
# - p_short: SHORT olasılığı
# - p_flat: FLAT olasılığı
```

**Avantajlar:**
- ✅ Her yön için ayrı öğrenme
- ✅ FLAT durumu da öğreniliyor
- ✅ Daha dengeli sınıf dağılımı

**Dezavantajlar:**
- ⚠️ 3 sınıf → daha karmaşık model
- ⚠️ FLAT sınıfı çok fazla olabilir (dengesizlik)

#### **Seçenek 2: İki Ayrı Binary Classifier**

```python
# Model 1: LONG Classifier
# Label: future_return > threshold_pct → 1, else → 0
model_long = lgb.LGBMClassifier(...)

# Model 2: SHORT Classifier
# Label: future_return < -threshold_pct → 1, else → 0
model_short = lgb.LGBMClassifier(...)

# Çıktı:
p_long = model_long.predict_proba()[0, 1]
p_short = model_short.predict_proba()[0, 1]

# Skor dönüşümü:
if p_long > p_short:
    ml_score = 50 + (p_long * 50)  # 50-100 (LONG)
else:
    ml_score = 50 - (p_short * 50)  # 0-50 (SHORT)
```

**Avantajlar:**
- ✅ Her yön için optimize edilmiş model
- ✅ Daha esnek hyperparameter tuning
- ✅ LONG ve SHORT için farklı eşikler kullanılabilir

**Dezavantajlar:**
- ⚠️ 2x model eğitimi (18 model → 36 model)
- ⚠️ Daha fazla kaynak kullanımı

#### **Seçenek 3: Binary Classification + Simetri (Önerilen)**

```python
# Label oluşturma:
future_return = ((future_close - df['close']) / df['close']) * 100

# Simetrik label:
if future_return > threshold_pct:
    label = 1  # LONG (yukarı)
elif future_return < -threshold_pct:
    label = 0  # SHORT (aşağı)
else:
    label = None  # FLAT - eğitimden çıkar

# Model: Binary (LONG=1, SHORT=0)
model = lgb.LGBMClassifier(
    objective='binary',
    ...
)

# Çıktı:
p_long = model.predict_proba()[0, 1]  # LONG olasılığı
p_short = 1 - p_long  # SHORT olasılığı (simetrik)

# Skor dönüşümü:
if p_long >= 0.65:
    ml_score = 70-100 (LONG)
elif p_long >= 0.50:
    ml_score = 60-69 (LONG_WEAK)
elif p_long >= 0.35:
    ml_score = 40-59 (FLAT)
elif p_long >= 0.20:
    ml_score = 20-39 (SHORT_WEAK)
else:
    ml_score = 0-19 (SHORT)
```

**Avantajlar:**
- ✅ Simetrik öğrenme (LONG ve SHORT eşit önemde)
- ✅ Mevcut kod yapısına minimal değişiklik
- ✅ FLAT durumu eğitimden çıkarılıyor (daha temiz)

**Dezavantajlar:**
- ⚠️ FLAT durumu için özel işlem gerekiyor

---

## 📊 Mevcut Model Performansı

### **AUC Değerleri** (Tek Yönlü - Mevcut)

| Symbol_TF | AUC    | Durum        |
|-----------|--------|--------------|
| BTC_15m   | ~0.58  | ⚠️ Düşük     |
| BTC_1h    | ~0.62  | ⚠️ Orta      |
| BTC_4h    | ~0.65  | ⚠️ Orta      |
| ETH_15m   | ~0.56  | ⚠️ Düşük     |
| ETH_1h    | ~0.60  | ⚠️ Orta      |
| ETH_4h    | ~0.63  | ⚠️ Orta      |
| SOL_15m   | ~0.55  | ⚠️ Düşük     |
| SOL_1h    | ~0.59  | ⚠️ Orta      |
| SOL_4h    | ~0.61  | ⚠️ Orta      |

**Ortalama AUC: ~0.60** (Hedef: 0.70-0.80)

### **Sınıf Dengesizliği**

- **Pozitif Label (LONG):** ~15-20%
- **Negatif Label (SHORT değil, sadece "yukarı değil"):** ~80-85%
- **Problem:** Model "yukarı değil" durumunu öğreniyor, ama "aşağı" durumunu öğrenmiyor

---

## 🎯 İki Yönlü Öğrenme ile Beklenen İyileştirmeler

### **1. AUC Artışı**

- **Mevcut:** 0.60 (tek yönlü)
- **Hedef:** 0.70-0.80 (iki yönlü)
- **Neden:** Her yön için optimize edilmiş öğrenme

### **2. Short Sinyal Güvenilirliği**

- **Mevcut:** Short sinyal, "yukarı değil" durumuna dayanıyor
- **Hedef:** Short sinyal, "aşağı gitme" durumuna dayanıyor
- **Sonuç:** Daha güvenilir short sinyaller

### **3. Daha Dengeli Sınıf Dağılımı**

- **Mevcut:** LONG: 15%, "Yukarı değil": 85% (dengesiz)
- **Hedef:** LONG: 15%, SHORT: 15%, FLAT: 70% (daha dengeli)
- **Sonuç:** Model daha iyi öğrenir

---

## 📝 Özet

### **ML'in Short/Long Sinyaldeki Rolü:**

1. **Ağırlık:** Composite signal'de **%35 ağırlık** (TA'dan sonra en önemli)
2. **Yön Belirleme:** ML skoru 60+ → LONG, 40- → SHORT
3. **Konsensus:** TA ve ML aynı yönde ise → Karar verilir
4. **Mevcut Problem:** Model sadece "yukarı" için eğitilmiş, "aşağı" için değil

### **İyileştirme Önerisi:**

- **Seçenek 3 (Binary + Simetri)** önerilir
- Her yön için eşit öğrenme
- Mevcut kod yapısına minimal değişiklik
- AUC hedefi: 0.70-0.80

---

## 🔗 İlgili Dosyalar

- `scoring/ml_scorer.py`: ML scoring mantığı
- `ml/features/builder.py`: Feature engineering ve label oluşturma
- `ml/training/train_lgbm_per_symbol_tf.py`: Model eğitimi
- `scoring/composite_signal.py`: Composite signal ve karar verme
- `infrastructure/runtime.py`: ML analiz akışı


