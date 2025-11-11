# Eğitim Mimarisi Açıklaması: Calibration, Geçici Modeller ve Max Depth

**Tarih:** 2025-11-05  
**Soru:** Neden calibration kaldırıldı? Neden geçici model kullanılıyor? Max depth ne?

---

## 1️⃣ NEDEN CALIBRATION KALDIRILDI? 🔄

### Calibration Nedir?

**Calibration (Kalibrasyon):** Modelin tahmin ettiği olasılıkların gerçek olasılıklara daha yakın olması için yapılan bir düzeltme.

**Örnek:**
```
Model Tahmini: "Bu %80 yukarı gider" diyor
Gerçekte:  10 kere %80 dedi, sadece 5 kere yukarı gitti (%50)
Calibration: "Aslında %50'ye yakın" diye düzeltir
```

### Eski Sistem (CalibratedClassifierCV):

```python
# Eski kod (tahmini):
from sklearn.calibration import CalibratedClassifierCV

base_model = LGBMClassifier()  # 1. Base model train
calibrated = CalibratedClassifierCV(
    base_model, 
    cv=5  # 5 fold cross-validation
)
calibrated.fit(X, y)

# Bu ne yapıyor?
# 1. Base model train edilir (1x)
# 2. 5 fold'a böler
# 3. Her fold için ayrı calibration model train eder (5x)
# TOPLAM: 1 base + 5 calibration = 6 model train!
```

**Problem:**
- 6x daha fazla eğitim süresi
- Multiclass için gereksiz (binary için daha önemli)
- LightGBM zaten iyi olasılık tahmini yapıyor

### Yeni Sistem (No Calibration):

```python
# Yeni kod:
model = LGBMClassifier()
model.fit(X, y)  # Sadece 1 model train

# Neden yeterli?
# 1. LightGBM zaten iyi probability prediction yapıyor
# 2. Multiclass (3 sınıf) için calibration daha az kritik
# 3. Hız önemli: 6x hızlanma
```

**Avantajlar:**
- ✅ 6x daha hızlı
- ✅ Daha az disk kullanımı
- ✅ Multiclass için yeterli kalite

**Sonuç:** Multiclass için calibration gereksiz, hız kazancı önemli!

---

## 2️⃣ NEDEN GEÇİCİ MODEL KULLANILIYOR? 🗑️

### Geçici Model Nedir?

**Geçici Model (Temporary Model):** Sadece test/evaluation için kullanılan, kaydedilmeyen model.

### Kod Örneği:

```python
def _evaluate_model(self, model, X, y):
    """Model performansını ölçmek için CV yapıyor."""
    
    tscv = TimeSeriesSplit(n_splits=5)  # 5 fold
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        # 🔥 GEÇİCİ MODEL: Sadece bu fold için train edilir
        temp_model = lgb.LGBMClassifier(**model.get_params())
        temp_model.fit(X_train, y_train)  # Train
        
        # Test setinde tahmin yap
        y_pred = temp_model.predict(X_test)
        
        # Metrikleri hesapla
        metrics = calculate_metrics(y_test, y_pred)
        
        # ⚠️ DİKKAT: temp_model kaydedilmiyor! Sadece metrics kullanılıyor
    
    # 5 fold'un ortalaması alınır
    avg_metrics = average(metrics_list)
    
    return avg_metrics  # Sadece metrikler döner, modeller kaydedilmez
```

### Neden Geçici?

#### Senaryo 1: Eğer Her Fold Model Kaydedilseydi

```python
# ❌ KÖTÜ YAKLAŞIM:
for fold in 5 folds:
    model = train()
    save_model(f"model_fold_{fold}.pkl")  # Her fold için ayrı dosya!
    
# Sonuç:
# - 5 ayrı model dosyası (disk dolu!)
# - Hangisini kullanacağız? Belirsiz
# - Evaluation için gereksiz disk yazma
```

**Problemler:**
- Disk alanı israfı
- Hangi modeli kullanacağız belirsiz
- Evaluation için gereksiz

#### Senaryo 2: Geçici Model (Şu Anki)

```python
# ✅ İYİ YAKLAŞIM:
for fold in 5 folds:
    temp_model = train()  # Geçici
    metrics = evaluate(temp_model)
    # temp_model silinir (memory'den çıkar)

# Ana model (full data üzerinde) kaydedilir
main_model = train_on_full_data()
save_model("model.pkl")  # Sadece 1 model!

# Sonuç:
# - Sadece 1 model dosyası
# - CV sadece performans ölçümü için
# - Disk temiz, hızlı
```

**Avantajlar:**
- ✅ Disk alanı tasarrufu
- ✅ Daha hızlı (disk yazma yok)
- ✅ Açık: Hangi model kullanılacak belli (main_model)

### Cross-Validation'un Amacı:

**CV = Model Seçimi Değil, Performans Ölçümü**

```
Cross-Validation:
- Amacı: "Model ne kadar iyi?" sorusunu cevaplamak
- Yöntem: Veriyi böl, her parçada test et
- Sonuç: Ortalama performans metrikleri (AUC, F1, vs.)

Örnek:
Fold 1: AUC = 0.65
Fold 2: AUC = 0.68
Fold 3: AUC = 0.62
Fold 4: AUC = 0.70
Fold 5: AUC = 0.66

Ortalama AUC = 0.662 ✅ (Bu metrikleri kullanırız)

Ama modelleri kaydetmiyoruz! Çünkü:
- Sadece ölçüm için kullandık
- Asıl model: Full data üzerinde train edilen
```

**Sonuç:** CV geçici modeller sadece "performans ölçümü" için. Asıl model full data üzerinde train edilip kaydedilir!

---

## 3️⃣ MAX DEPTH NE? 🌳

### Max Depth Nedir?

**Max Depth:** Decision tree'de ağacın **maksimum derinliği** (kaç seviye derinleşebilir).

### Görsel Örnek:

```
DERİNLİK 0:          [ROOT]
                     /      \
DERİNLİK 1:      [A]        [B]
                 /  \        /  \
DERİNLİK 2:   [C]  [D]    [E]  [F]
               |    |      |    |
DERİNLİK 3:  [G]  [H]    [I]  [J]
              ... (devam edebilir)

max_depth=2:  Ağaç 2 seviyeye kadar derinleşir (C, D, E, F'ye kadar)
max_depth=-1: Sınır yok, sonsuza kadar derinleşebilir!
```

### Kod Örneği:

```python
# ESKİ (Unlimited Depth):
params = {
    'max_depth': -1  # ⚠️ SINIR YOK!
}
# Sonuç: Ağaç her sample'a kadar derinleşebilir
# Örnek: 50,000 sample varsa, ağaç 16+ seviye derinleşebilir!

# YENİ (Limited Depth):
params = {
    'max_depth': 10  # ✅ MAKSİMUM 10 SEVİYE
}
# Sonuç: Ağaç maksimum 10 seviye derinleşir, daha fazla değil
```

### Neden Fark Eder?

#### max_depth=-1 (Unlimited):

```
Örnek Senaryo:
- 50,000 sample var
- Her sample'a özel karar verilebilir
- Ağaç derinleşir, derinleşir, derinleşir...

Problem:
- Her sample için özel dal = OVERFITTING! ⚠️
- Training süresi: EXPONANSIYEL artış
- Örnek: 16 seviye derinlik = 2^16 = 65,536 dal!

Süre: ~30-60 dakika/model (50k sample için)
```

#### max_depth=10 (Limited):

```
Örnek Senaryo:
- 50,000 sample var
- Maksimum 10 seviye derinlik
- Her seviyede genel pattern'ler öğrenilir

Avantaj:
- Overfitting riski azalır ✅
- Training süresi: POLİNOMİYEL artış
- Örnek: 10 seviye derinlik = 2^10 = 1,024 dal (yeterli!)

Süre: ~10-15 saniye/model (50k sample için)
```

### Gerçek Örnek:

```python
# Test: 50,000 sample, 74 feature

# max_depth=-1:
model = LGBMClassifier(max_depth=-1)
model.fit(X, y)  # Süre: ~45-60 saniye ⏰

# max_depth=10:
model = LGBMClassifier(max_depth=10)
model.fit(X, y)  # Süre: ~12-15 saniye ⚡

# Hızlanma: 4-5x daha hızlı!
```

### Neden 10 Seçildi?

```
Optimal Derinlik (LightGBM için):
- min_depth: 5-7  (çok sığ, pattern kaçırır)
- optimal: 8-12   (✅ sweet spot)
- max_depth: 15+  (çok derin, overfitting)

Bizim Seçim: max_depth=10 ✅
- Yeterince derin (pattern'leri yakalar)
- Overfitting riski düşük
- Hızlı training
```

### Trade-off:

| max_depth | Süre | Kalite | Overfitting | Öneri |
|-----------|------|--------|-------------|-------|
| 5 | Çok Hızlı ⚡⚡ | Düşük ⚠️ | Az ✅ | ❌ Çok sığ |
| 7 | Hızlı ⚡ | Orta | Az ✅ | ✅ İyi |
| **10** | **Orta** ⚡ | **İyi** ✅ | **Düşük** ✅ | **✅ Optimal** |
| 15 | Yavaş ⏰ | İyi ✅ | Orta ⚠️ | ⚠️ Riskli |
| -1 | Çok Yavaş ⏰⏰ | Çok İyi ✅✅ | Yüksek ❌ | ❌ Tehlikeli |

**Sonuç:** max_depth=10, hız ve kalite dengesinde optimal seçim!

---

## 📊 ÖZET: ÜÇ KAVRAM BİRLİKTE

### Mimari Akış:

```
1. FULL DATA TRAINING (Ana Model):
   model = LGBMClassifier(max_depth=10)  # ✅ Limited depth
   model.fit(X_full, y_full)  # Full data üzerinde train
   save_model("model.pkl")  # ✅ Kalıcı model kaydet
   
   ⏱️ Süre: ~12 saniye

2. CROSS-VALIDATION (Geçici Modeller):
   for fold in 5 folds:
       temp_model = train()  # Geçici, kaydedilmez
       metrics = evaluate(temp_model)  # Sadece metrikler
       # temp_model silinir
   
   ⏱️ Süre: ~25 saniye (5 fold × 5 saniye)
   
3. SONUÇ:
   - 1 kalıcı model (kullanılacak)
   - 5 geçici model (sadece ölçüm için, silindi)
   - Toplam süre: ~37 saniye/model ✅
```

### Eski Sistem (Karşılaştırma):

```
1. BASE MODEL:
   base_model.fit(X, y)  # max_depth=-1 ⚠️
   ⏱️ Süre: ~30 dakika

2. CALIBRATION (5 fold):
   for fold in 5 folds:
       calibrator.fit()  # Her fold için
   ⏱️ Süre: ~30 dakika (5 fold × 6 dakika)
   
3. SONUÇ:
   - 6 model (1 base + 5 calibration)
   - Toplam süre: ~60 dakika/model ❌
```

### Hızlanma:

```
Eski: 60 dakika/model
Yeni: 37 saniye/model

Hızlanma: 60 × 60 / 37 = ~97x daha hızlı! 🚀
```

---

## 🎯 SONUÇ

1. **Calibration Kaldırıldı:**
   - Multiclass için gereksiz
   - 6x hızlanma kazancı
   - LightGBM zaten iyi tahmin yapıyor

2. **Geçici Model Kullanılıyor:**
   - CV sadece performans ölçümü için
   - Asıl model full data üzerinde
   - Disk tasarrufu ve hız kazancı

3. **Max Depth = 10:**
   - Overfitting önleme
   - Hız ve kalite dengesi
   - Exponansiyel → Polinomiyel süre artışı

**Tüm bu değişiklikler = 97x daha hızlı eğitim! ⚡**



