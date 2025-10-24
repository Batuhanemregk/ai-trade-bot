# Kapsamlı Trading Sistemi Analizi

## İçindekiler
1. [Composite Signal Üretimi](#composite-signal-üretimi)
2. [Ağırlık Sistemleri](#ağırlık-sistemleri)
3. [Technical Analysis (TA) Özellikleri](#technical-analysis-ta-özellikleri)
4. [Machine Learning (ML) Özellikleri](#machine-learning-ml-özellikleri)
5. [Threshold Değerleri](#threshold-değerleri)
6. [Karar Algoritmaları](#karar-algoritmaları)
7. [Sistem Mimarisi](#sistem-mimarisi)

---

## Composite Signal Üretimi

### Genel Süreç
Composite signal, 4 ana bileşenin ağırlıklı ortalaması ile üretilir:

```python
final_score = (
    weights['ta'] * ta_score +      # %40 ağırlık
    weights['ml'] * ml_score +      # %25 ağırlık  
    weights['news'] * news_score +  # %20 ağırlık
    weights['risk'] * risk_score    # %15 ağırlık
)
```

### Bileşenler
1. **Technical Analysis (TA)**: 40% ağırlık
2. **Machine Learning (ML)**: 25% ağırlık
3. **News Sentiment**: 20% ağırlık
4. **Risk Assessment**: 15% ağırlık

### Final Karar
- **LONG**: Score ≥ 60
- **SHORT**: Score ≤ 40  
- **FLAT**: 40 < Score < 60 (nötr bölge)

---

## Ağırlık Sistemleri

### 1. Ana Composite Signal Ağırlıkları
```yaml
weights:
  ta: 0.40      # Technical Analysis
  ml: 0.25      # Machine Learning  
  news: 0.20    # News Sentiment
  risk: 0.15    # Risk Assessment
```

### 2. TA İç Ağırlıkları
```python
technical_score = (
    0.35 * trend_score +      # Trend analizi
    0.30 * momentum_score +   # Momentum göstergeleri
    0.20 * volatility_score + # Volatilite analizi
    0.15 * volume_score       # Hacim analizi
)
```

### 3. Risk Assessment Ağırlıkları
```yaml
risk_breakdown:
  volatility_risk: 25%
  liquidity_risk: 25%
  correlation_risk: 20%
  score_risk: 15%
  market_risk: 15%
```

---

## Technical Analysis (TA) Özellikleri

### 29 TA Özelliği Detayı

> **⚠️ ÖNEMLİ NOT**: 29 TA özelliğinden sadece **8 tanesi** aktif olarak skorlama hesaplamasında kullanılmaktadır. Diğer 21 özellik hesaplanır ancak doğrudan skorlamaya dahil edilmez.

#### Aktif Kullanılan 8 Özellik:
1. `sma_20` - 20 periyotluk basit ortalama
2. `sma_50` - 50 periyotluk basit ortalama  
3. `rsi` - 14 periyotluk RSI
4. `macd_histogram` - MACD histogram
5. `atr` - Ortalama gerçek aralık
6. `bb_width` - Bollinger Band genişliği
7. `volume_ratio` - Hacim oranı
8. `current_price` - Mevcut fiyat

#### 1. Trend Göstergeleri (8 özellik) - Sadece 2'si aktif ✅
- **SMA (Simple Moving Average)** ✅
  - `sma_20`: 20 periyotluk basit ortalama ✅ **AKTİF**
  - `sma_50`: 50 periyotluk basit ortalama ✅ **AKTİF**
- **EMA (Exponential Moving Average)** ❌
  - `ema_20`: 20 periyotluk üstel ortalama ❌ **PASİF**
  - `ema_50`: 50 periyotluk üstel ortalama ❌ **PASİF**
  - `ema_200`: 200 periyotluk üstel ortalama ❌ **PASİF**
- **ADX (Average Directional Index)** ❌
  - `adx`: Trend gücü göstergesi ❌ **PASİF**
  - `di_plus`: Pozitif yön göstergesi ❌ **PASİF**
  - `di_minus`: Negatif yön göstergesi ❌ **PASİF**
- **Supertrend** ❌
  - `supertrend`: Supertrend değeri ❌ **PASİF**
  - `supertrend_direction`: Supertrend yönü ❌ **PASİF**

#### 2. Momentum Göstergeleri (6 özellik) - Sadece 2'si aktif ✅
- **RSI (Relative Strength Index)** ✅
  - `rsi`: 14 periyotluk RSI ✅ **AKTİF**
- **MACD (Moving Average Convergence Divergence)** ✅
  - `macd`: MACD çizgisi ❌ **PASİF**
  - `macd_signal`: MACD sinyal çizgisi ❌ **PASİF**
  - `macd_histogram`: MACD histogram ✅ **AKTİF**
- **Stochastic** ❌
  - `stoch_k`: %K değeri ❌ **PASİF**
  - `stoch_d`: %D değeri ❌ **PASİF**

#### 3. Volatilite Göstergeleri (4 özellik) - Sadece 2'si aktif ✅
- **Bollinger Bands** ✅
  - `bb_upper`: Üst bant ❌ **PASİF**
  - `bb_middle`: Orta bant ❌ **PASİF**
  - `bb_lower`: Alt bant ❌ **PASİF**
  - `bb_width`: Bant genişliği ✅ **AKTİF**
- **ATR (Average True Range)** ✅
  - `atr`: Ortalama gerçek aralık ✅ **AKTİF**

#### 4. Hacim Göstergeleri (3 özellik) - Sadece 1'i aktif ✅
- **Volume Analysis** ✅
  - `volume_sma`: Hacim ortalaması ❌ **PASİF**
  - `volume_ratio`: Mevcut hacim / ortalama hacim ✅ **AKTİF**
- **Volume Profile** ❌
  - `volume_profile`: Hacim profili ❌ **PASİF**

#### 5. Fiyat Seviyeleri (3 özellik) - Sadece 1'i aktif ✅
- **Price Levels**
  - `high_20`: Son 20 barın en yüksek fiyatı ❌ **PASİF**
  - `low_20`: Son 20 barın en düşük fiyatı ❌ **PASİF**
  - `current_price`: Mevcut fiyat ✅ **AKTİF**

#### 6. Zaman Tabanlı Özellikler (5 özellik) - Hiçbiri aktif ❌
- **Time Features** ❌
  - `hour_of_day`: Günün saati (0-23) ❌ **PASİF**
  - `day_of_week`: Haftanın günü (0-6) ❌ **PASİF**
  - `is_weekend`: Hafta sonu kontrolü ❌ **PASİF**
  - `market_session`: Piyasa seansı ❌ **PASİF**
  - `time_since_open`: Açılıştan geçen süre ❌ **PASİF**

### Kullanım Durumu Özeti:
- **Toplam Özellik**: 29
- **Aktif Kullanılan**: 8 (%27.6)
- **Pasif (Hesaplanan ama kullanılmayan)**: 21 (%72.4)

### TA Skorlama Algoritması

#### Trend Skoru (35% ağırlık)
```python
def _score_trend(indicators):
    sma_20 = indicators['sma_20'].iloc[-1]
    sma_50 = indicators['sma_50'].iloc[-1]
    current_price = indicators['current_price'].iloc[-1]
    
    if sma_20 > sma_50 and current_price > sma_20:
        return 85.0  # Güçlü yükseliş
    elif sma_20 > sma_50:
        return 70.0  # Orta yükseliş
    elif sma_20 < sma_50 and current_price < sma_20:
        return 15.0  # Güçlü düşüş
    elif sma_20 < sma_50:
        return 30.0  # Orta düşüş
    else:
        return 50.0  # Yatay
```

#### Momentum Skoru (30% ağırlık)
```python
def _score_momentum(indicators):
    rsi = indicators['rsi'].iloc[-1]
    macd_hist = indicators['macd_histogram'].iloc[-1]
    
    # RSI skorlama
    if rsi > 70:
        rsi_score = 20.0  # Aşırı alım
    elif rsi < 30:
        rsi_score = 80.0  # Aşırı satım
    elif rsi > 60:
        rsi_score = 35.0  # Yükseliş ama aşırı alıma yakın
    elif rsi < 40:
        rsi_score = 65.0  # Düşüş ama aşırı satıma yakın
    else:
        rsi_score = 50.0  # Nötr
    
    # MACD skorlama
    if macd_hist > 0:
        macd_score = 60.0 + min(30.0, abs(macd_hist) * 100)
    else:
        macd_score = 40.0 - min(30.0, abs(macd_hist) * 100)
    
    return (rsi_score + macd_score) / 2
```

#### Volatilite Skoru (20% ağırlık)
```python
def _score_volatility(indicators):
    atr = indicators['atr'].iloc[-1]
    atr_20 = indicators['atr'].rolling(20).mean().iloc[-1]
    bb_width = indicators['bb_width'].iloc[-1]
    
    # ATR skorlama
    atr_ratio = atr / atr_20
    if atr_ratio > 1.5:
        atr_score = 30.0  # Yüksek volatilite (riskli)
    elif atr_ratio < 0.5:
        atr_score = 70.0  # Düşük volatilite (güvenli)
    else:
        atr_score = 50.0  # Normal volatilite
    
    # Bollinger Band genişliği skorlama
    if bb_width > 0.08:
        bb_score = 30.0  # Geniş bantlar (yüksek volatilite)
    elif bb_width < 0.02:
        bb_score = 70.0  # Dar bantlar (düşük volatilite)
    else:
        bb_score = 50.0  # Normal genişlik
    
    return (atr_score + bb_score) / 2
```

#### Hacim Skoru (15% ağırlık)
```python
def _score_volume(indicators):
    volume_ratio = indicators['volume_ratio'].iloc[-1]
    
    if volume_ratio > 2.0:
        return 80.0  # Yüksek hacim (iyi)
    elif volume_ratio > 1.5:
        return 70.0  # Ortalamanın üstü
    elif volume_ratio > 1.0:
        return 60.0  # Normal hacim
    elif volume_ratio > 0.7:
        return 40.0  # Ortalamanın altı
    else:
        return 20.0  # Düşük hacim (endişe verici)
```

### Strategy Flags (Strateji Bayrakları)
```python
flags = {
    "trend": "up/down/side",      # Trend yönü
    "meanrev": "on/off",          # Ortalama dönüş fırsatı
    "breakout": "on/off",         # Kırılım deseni
    "dir_hint": "LONG/SHORT/FLAT" # Yön önerisi
}
```

---

## Machine Learning (ML) Özellikleri

### ML Model Detayları
- **Model Tipi**: LightGBM Classifier
- **Eğitim Verisi**: 6 aylık OHLCV verisi (15m, 1h, 4h)
- **Özellik Sayısı**: 27 özellik
- **Cross-validation**: 5-fold
- **Calibration**: Isotonic Regression

### 27 ML Özelliği

> **ℹ️ NOT**: ML modelinde tüm 27 özellik aktif olarak kullanılmaktadır. Bu, TA sisteminden farklı olarak ML'de tüm hesaplanan özelliklerin model eğitiminde ve tahminlerinde kullanıldığını gösterir.

#### 1. Fiyat Özellikleri (8 özellik) - Tümü aktif ✅
- `open`, `high`, `low`, `close`: OHLC değerleri
- `price_change`: Fiyat değişimi
- `price_change_pct`: Fiyat değişim yüzdesi
- `high_low_ratio`: Yüksek/düşük oranı
- `close_open_ratio`: Kapanış/açılış oranı

#### 2. Hacim Özellikleri (4 özellik) - Tümü aktif ✅
- `volume`: Hacim ✅
- `volume_change`: Hacim değişimi ✅
- `volume_change_pct`: Hacim değişim yüzdesi ✅
- `volume_price_ratio`: Hacim/fiyat oranı ✅

#### 3. Teknik Göstergeler (15 özellik) - Tümü aktif ✅
- **Trend**: `sma_20`, `sma_50`, `ema_20`, `ema_50` ✅
- **Momentum**: `rsi`, `macd`, `macd_signal`, `macd_histogram` ✅
- **Volatilite**: `atr`, `bb_upper`, `bb_lower`, `bb_width` ✅
- **Hacim**: `volume_sma`, `volume_ratio` ✅
- **Fiyat Seviyeleri**: `high_20`, `low_20` ✅

### ML vs TA Özellik Kullanım Karşılaştırması:
- **ML Modeli**: 27/27 özellik aktif (%100)
- **TA Scorer**: 8/29 özellik aktif (%27.6)
- **Fark**: ML modeli çok daha kapsamlı özellik kullanımına sahip

### ML Skorlama Süreci
```python
def score(self, symbol, ohlcv_bundle):
    # 1. Özellik mühendisliği
    df_with_features = self.feature_engineer.create_features(main_df)
    
    # 2. Son satır özelliklerini al
    latest_features = df_with_features[feature_cols].iloc[-1:]
    
    # 3. Model tahmini
    p_up = self.model.predict_proba(latest_features)[0, 1]
    
    # 4. 0-100 skala dönüşümü
    ml_score = round(p_up * 100, 1)
    
    # 5. Güven seviyesi belirleme
    confidence = self._calculate_confidence(p_up)
    
    return ml_score, rationale, details
```

### Güven Seviyeleri
```python
def _calculate_confidence(p_up):
    if 0.48 <= p_up <= 0.52:
        return 'low'           # Nötr bant
    elif 0.52 < p_up < 0.55 or 0.45 < p_up < 0.48:
        return 'medium_low'    # Düşük-orta
    elif 0.55 <= p_up < 0.70 or 0.30 < p_up <= 0.45:
        return 'medium'        # Orta
    else:  # p_up >= 0.70 or p_up <= 0.30
        return 'high'          # Yüksek
```

---

## Threshold Değerleri

### 1. Karar Eşikleri
```yaml
decision_thresholds:
  enter_long: 60        # Score >= 60: LONG giriş
  exit_long: 45         # Score <= 45: LONG çıkış
  enter_short: 40       # Score <= 40: SHORT giriş
  exit_short: 55        # Score >= 55: SHORT çıkış
  flat_range: [45, 55]  # 45-55 arası: FLAT (nötr bölge)
```

### 2. Not Eşikleri
```yaml
grade_thresholds:
  A+: 90.0  # Mükemmel
  A: 80.0   # Çok iyi
  B: 70.0   # İyi
  C: 60.0   # Orta
  D: 0.0    # Düşük
```

### 3. Risk Eşikleri
```yaml
risk_thresholds:
  volatility_risk:
    BTC: {low: 0.15, medium: 0.35, high: 0.55}
    ETH: {low: 0.20, medium: 0.40, high: 0.60}
    tier_2: {low: 0.25, medium: 0.45, high: 0.65}
    tier_3: {low: 0.30, medium: 0.50, high: 0.70}
    tier_4: {low: 0.35, medium: 0.55, high: 0.75}
  
  liquidity_risk:
    BTC: {high: 50000000, medium: 10000000, low: 1000000}
    ETH: {high: 30000000, medium: 5000000, low: 500000}
    tier_2: {high: 10000000, medium: 2000000, low: 200000}
    tier_3: {high: 5000000, medium: 1000000, low: 100000}
    tier_4: {high: 1000000, medium: 200000, low: 20000}
```

### 4. Sinyal Eşikleri
```yaml
signal_thresholds:
  persistence_bars: 2     # Sinyal N bar sürmeli
  rev_confirm_bars: 2     # Ters dönüş onay barı
  rev_strength_min: 0.6   # Minimum ters dönüş gücü
  max_signal_age_bars: 6  # Maksimum sinyal yaşı
```

### 5. ML Güven Eşikleri
```yaml
ml_confidence_thresholds:
  high_threshold: 0.30    # |p_up - 0.5| > 0.30 = yüksek güven
  medium_threshold: 0.15  # |p_up - 0.5| > 0.15 = orta güven
  low_threshold: 0.05     # |p_up - 0.5| > 0.05 = düşük güven
```

---

## Karar Algoritmaları

### 1. Composite Signal Karar Algoritması
```python
def finalize(self, weights, thresholds, direction_hint=None):
    # 1. Ağırlıklı skor hesapla
    self.final_score = (
        weights['technical'] * self.technical.score +
        weights['ml'] * self.ml.score +
        weights['news'] * self.news.score +
        weights['risk'] * self.risk.score
    )
    
    # 2. Not belirle
    if self.final_score >= 90:
        self.grade = "A+"
    elif self.final_score >= 80:
        self.grade = "A"
    elif self.final_score >= 70:
        self.grade = "B"
    elif self.final_score >= 60:
        self.grade = "C"
    else:
        self.grade = "D"
    
    # 3. Karar belirle
    min_confidence = thresholds.get('min_confidence_pct', 50)
    
    if self.confidence_pct < min_confidence:
        self.decision = "FLAT"
    else:
        # Yön önerisi kullan veya teknik+ML konsensüsü
        if direction_hint and direction_hint in ["LONG", "SHORT"]:
            self.decision = direction_hint
        else:
            tech_direction = self.technical.flags.get("dir_hint", "FLAT")
            ml_direction = self._get_ml_direction()
            
            if tech_direction == ml_direction and tech_direction != "FLAT":
                self.decision = tech_direction
            elif tech_direction != "FLAT":
                self.decision = tech_direction
            elif ml_direction != "FLAT":
                self.decision = ml_direction
            else:
                self.decision = "FLAT"
```

### 2. ML Yön Belirleme
```python
def _get_ml_direction(self):
    ml_score = self.ml.score
    if ml_score >= 60:      # ML yön eşiği: 60
        return "LONG"
    elif ml_score <= 40:    # ML yön eşiği: 40
        return "SHORT"
    else:
        return "FLAT"
```

### 3. Risk Değerlendirme Algoritması
```python
def assess_risk(symbol, score, signal_type, market_data):
    # 1. Volatilite riski
    volatility_risk = calculate_volatility_risk(symbol, market_data)
    
    # 2. Likidite riski
    liquidity_risk = calculate_liquidity_risk(symbol, market_data)
    
    # 3. Korelasyon riski
    correlation_risk = calculate_correlation_risk(symbol, market_data)
    
    # 4. Skor riski
    score_risk = calculate_score_risk(score, signal_type)
    
    # 5. Piyasa riski
    market_risk = calculate_market_risk(market_data)
    
    # 6. Ağırlıklı risk skoru
    risk_score = (
        0.25 * volatility_risk +
        0.25 * liquidity_risk +
        0.20 * correlation_risk +
        0.15 * score_risk +
        0.15 * market_risk
    )
    
    return {
        'risk_score': risk_score,
        'risk_level': get_risk_level(risk_score),
        'recommendation': get_recommendation(risk_score),
        'risk_breakdown': {
            'volatility_risk': volatility_risk,
            'liquidity_risk': liquidity_risk,
            'correlation_risk': correlation_risk,
            'score_risk': score_risk,
            'market_risk': market_risk
        }
    }
```

---

## Sistem Mimarisi

### 1. Veri Akışı
```
OHLCV Data → Feature Engineering → ML Model → ML Score
     ↓
OHLCV Data → Technical Indicators → TA Score
     ↓
News APIs → Sentiment Analysis → News Score
     ↓
Market Data → Risk Assessment → Risk Score
     ↓
                    ↓
            Composite Signal
                    ↓
            Trading Decision
```

### 2. Bileşenler
- **Data Collectors**: Binance API, OKX API, News APIs
- **Feature Engineers**: TA indicators, ML features
- **Scorers**: TA, ML, News, Risk scorers
- **Signal Processors**: Composite signal, decision logic
- **Risk Managers**: Position sizing, risk assessment
- **Executors**: Order execution, position management

### 3. Konfigürasyon
- **Policy File**: `configs/policy.yaml`
- **Model Storage**: `models/` directory
- **Data Storage**: `data/ml_training/` directory
- **Logs**: `logs/` directory

### 4. Monitoring
- **Real-time Logging**: Loguru logger
- **Performance Tracking**: Metrics collection
- **Error Handling**: Comprehensive error management
- **Telegram Notifications**: Real-time alerts

---

## Özet

Bu trading sistemi, 4 ana bileşenin ağırlıklı kombinasyonu ile çalışır:

1. **Technical Analysis (40%)**: 29 özellik, 4 ana kategori
2. **Machine Learning (25%)**: 27 özellik, LightGBM modeli
3. **News Sentiment (20%)**: Gerçek zamanlı haber analizi
4. **Risk Assessment (15%)**: 5 risk kategorisi

Sistem, karmaşık karar algoritmaları ve çoklu eşik değerleri ile güvenilir trading sinyalleri üretir. Tüm bileşenler gerçek zamanlı olarak güncellenir ve sürekli performans izleme altındadır.
