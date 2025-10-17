# Bot Özellikleri Detaylı Denetim Raporu

## 📋 Amaç
Backtest'in botun **TÜM özelliklerini** içerip içermediğini kontrol et.

## 🔍 Bot'un TAM Stratejisi

### 1. **Skor Hesaplama Katmanı**

#### ✅ TA (Technical Analysis) Skorlama
- **Dosya:** `scoring/ta_scorer.py`
- **Durum:** ✅ ÇALIŞIYOR (backtest'te aktif)
- **İçerik:**
  - RSI, MACD, Bollinger Bands, ATR
  - Trend strength, momentum, volatility
- **Backtest'te:** ✅ Entegre (`self.ta_scorer.score()`)

#### ❌ ML (Machine Learning) Skorlama  
- **Dosya:** `scoring/ml_scorer.py`
- **Durum:** ❌ HATA VERİYOR (backtest'te fallback)
- **İçerik:**
  - RandomForest, LSTM, XGBoost tahminleri
  - Simulated predictions (modeller yok)
- **Backtest'te:** ⚠️ Entegre ama çalışmıyor
- **SORUN:** DataFrame format hatası
- **ÇÖZüM:** `scoring/ml_scorer.py` düzeltilmeli

#### ⚠️ News Skorlama
- **Dosya:** `scoring/news_scorer.py`
- **Durum:** ⚠️ FALLBACK (LLM API key yok)
- **İçerik:**
  - NewsService ile LLM-based sentiment
  - Keyword-based fallback
- **Backtest'te:** ✅ Entegre ama nötr (50) dönüyor
- **SORUN:** OpenAI API key yok
- **ÇÖZüM:** API key ekle veya simulated news data kullan

#### ✅ Risk Skorlama
- **Dosya:** `application/risk_service.py`
- **Durum:** ✅ ÇALIŞIYOR (backtest'te aktif)
- **İçerik:**
  - Volatility risk
  - Liquidity risk
  - Correlation risk
  - Market risk
- **Backtest'te:** ✅ Entegre (`self.risk_service.assess_risk()`)

---

### 2. **Signal Gating Katmanı**

#### ❌ Persistence Gate
- **Dosya:** `application/signal_gate.py` (`PersistenceProcessor`)
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Signal'in N bar boyunca devam etmesi gerekir
  - `persistence_bars` config'den alınır (örn: 2-3 bar)
- **Backtest'te:** ❌ Entegre DEĞİL
- **ÇÖZüM:** `SignalGate.process_signal()` backtest'e ekle

#### ❌ Confirmation Gate
- **Dosya:** `application/signal_gate.py` (`ConfirmationProcessor`)
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Reversal confirmation için N bar bekler
  - `rev_confirm_bars` config'den alınır
- **Backtest'te:** ❌ Entegre DEĞİL
- **ÇÖZüM:** `SignalGate.process_signal()` backtest'e ekle

#### ❌ Hysteresis Gate
- **Dosya:** `application/signal_gate.py` (`HysteresisProcessor`)
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Entry ve exit için farklı eşikler
  - False signal'ları önler
- **Backtest'te:** ❌ Entegre DEĞİL
- **ÇÖZüM:** `SignalGate.process_signal()` backtest'e ekle

#### ❌ Regime Detection
- **Dosya:** `application/signal_gate.py` (`RegimeProcessor`)
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - ADX ile trend/ranging/choppy tespit
  - Confidence multiplier uygular
- **Backtest'te:** ❌ Entegre DEĞİL
- **ÇÖZüM:** `SignalGate.process_signal()` backtest'e ekle

---

### 3. **State Management Katmanı**

#### ❌ Position State Manager
- **Dosya:** `application/position_state_manager.py`
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - State transitions (IDLE → SIGNAL_DETECTED → IN_POSITION → COOLDOWN)
  - Prevents duplicate entries
- **Backtest'te:** ❌ Entegre DEĞİL
- **ÇÖZüM:** `PositionStateManager.process_signal()` ekle

#### ❌ Bias Service
- **Dosya:** `application/bias_service.py`
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Directional bias check
  - Prevents counter-trend trades
- **Backtest'te:** ❌ Entegre DEĞİL

#### ❌ Reversal Manager
- **Dosya:** `application/reversal_manager.py`
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Reversal detection and approval
  - IGNORED, COOLDOWN states
- **Backtest'te:** ❌ Entegre DEĞİL

---

### 4. **Position Sizing Katmanı**

#### ❌ Dynamic Position Sizing
- **Dosya:** `infrastructure/runtime.py:726` (`_calculate_position_size`)
- **Durum:** ❌ BACKTEST'TE BASITLEŞTIRILMIŞ
- **Gerçek Bot:**
  ```python
  # Signal strength: 1% to 10% of portfolio
  signal_percentage = 0.01 + (composite_score / 100.0) * 0.09
  
  # Risk adjustment: higher risk = smaller position  
  risk_multiplier = 1.0 - (risk_score / 100.0) * 0.5
  
  # Final = signal * risk adjustment
  base_percentage = signal_percentage * risk_multiplier
  position_size_usdt = usdt_balance * base_percentage
  ```
- **Backtest'te:**
  ```python
  # Sabit $500
  position_size_usd = self.current_capital * 0.05  # 5% fixed
  ```
- **ÇÖZüM:** Gerçek `_calculate_position_size` fonksiyonunu kullan

#### ❌ Dynamic Leverage
- **Dosya:** `main.py.backup:1140` (`_calculate_dynamic_leverage`)
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Volatility ve trend strength'e göre leverage
  - Düşük volatility = yüksek leverage
  - Yüksek volatility = düşük leverage
- **Backtest'te:** ❌ Entegre DEĞİL (futures değil, spot sim)

---

### 5. **Risk Management Katmanı**

#### ⚠️ Risk Service
- **Dosya:** `application/risk_service.py`
- **Durum:** ⚠️ KISMEN ÇALIŞIYOR
- **Gerçek Bot:**
  - Volatility risk (live price data)
  - Liquidity risk (live volume data)
  - Correlation risk
  - Score risk
- **Backtest'te:** ⚠️ Basit versiyon (default values kullanıyor)

#### ❌ Risk Manager
- **Dosya:** `application/risk_manager.py`
- **Durum:** ❌ BACKTEST'TE YOK
- **İçerik:**
  - Portfolio-wide risk limits
  - Max positions limit
  - Max total exposure
- **Backtest'te:** ❌ Entegre DEĞİL

---

## 📊 ÖZET: Backtest vs Gerçek Bot

| Özellik | Gerçek Bot | Backtest | Durum |
|---------|-----------|----------|-------|
| **TA Skorlama** | ✅ RSI, MACD, Bollinger, ATR | ✅ Aynı | ✅ ÇALIŞIYOR |
| **ML Skorlama** | ✅ RF/LSTM/XGB simulated | ⚠️ Hata veriyor | ❌ BOZUK |
| **News Skorlama** | ✅ LLM-based sentiment | ⚠️ Fallback (50) | ⚠️ EKSIK (API key) |
| **Risk Skorlama** | ✅ 4 risk türü | ⚠️ Default values | ⚠️ BASITLEŞTIRILMIŞ |
| **Signal Gate** | ✅ 4 gate (P/C/H/R) | ❌ YOK | ❌ EKSIK |
| **State Management** | ✅ State machine | ❌ YOK | ❌ EKSIK |
| **Bias Check** | ✅ Directional bias | ❌ YOK | ❌ EKSIK |
| **Reversal Manager** | ✅ Reversal approval | ❌ YOK | ❌ EKSIK |
| **Dynamic Pos Size** | ✅ Score + risk based | ❌ Fixed 5% | ❌ BASITLEŞTIRILMIŞ |
| **Dynamic Leverage** | ✅ Volatility based | ❌ YOK (spot) | ❌ YOK |
| **Stop Loss/TP** | ✅ ATR-based | ✅ Policy-based | ✅ ÇALIŞIYOR |
| **Commission/Slippage** | ✅ Gerçek | ✅ Simulated | ✅ ÇALIŞIYOR |

## 🎯 Detaylı Düzeltme Planı

### 📌 **Faz 1: Bot'u Tam Çalışır Hale Getir** (Öncelik: YÜKSEK)

#### 1.1 ML Skorlamayı Düzelt
**Sorun:**
```python
# scoring/ml_scorer.py hatası
ERROR: 'str' object has no attribute 'get'
```

**Çözüm:**
- `ml_scorer.py`'deki DataFrame handling'i düzelt
- Simulated predictions için uygun format kullan
- Test et: `python -c "from scoring.ml_scorer import MLScorer; import pandas as pd; ..."`

**Tahmini Süre:** 15-20 dakika

---

#### 1.2 News Skorlamayı Kontrol Et
**Sorun:**
- OpenAI API key yok
- Fallback score=50 dönüyor

**Seçenekler:**
- **A.** OpenAI API key ekle → Gerçek LLM analizi
- **B.** Simulated news data kullan → Backtest için yeterli

**Tahmini Süre:** 10 dakika (simulated) veya 5 dakika (API key ekle)

---

#### 1.3 Signal Gate'leri Entegre Et
**Eksikler:**
- `PersistenceProcessor` - Signal 2-3 bar boyunca devam etmeli
- `ConfirmationProcessor` - Reversal için confirmation bekle
- `HysteresisProcessor` - Entry/exit için farklı eşikler
- `RegimeProcessor` - ADX-based trend/ranging detection

**Çözüm:**
```python
# backtests/real_strategy_engine.py içine ekle:
from application.signal_gate import SignalGate

# Initialize
self.signal_gate = SignalGate(self.policy)

# Process signal
gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h_list)
```

**Tahmini Süre:** 30-40 dakika

---

#### 1.4 Position State Manager Ekle
**Eksik:**
- State transitions (IDLE → SIGNAL_DETECTED → IN_POSITION)
- Duplicate entry prevention
- Cooldown management

**Çözüm:**
```python
from application.position_state_manager import PositionStateManager

self.state_manager = PositionStateManager(self.policy)
transition = self.state_manager.process_signal(symbol, gated_signal)
```

**Tahmini Süre:** 20-30 dakika

---

#### 1.5 Dinamik Position Sizing Ekle
**Eksik:**
- Score-based sizing (1%-10%)
- Risk adjustment multiplier
- Portfolio risk limits

**Çözüm:**
```python
# infrastructure/runtime.py:726'daki gerçek fonksiyonu kullan
from infrastructure.runtime import _calculate_position_size

position_size_usdt = await _calculate_position_size(
    composite_signal, symbol, self.exchange_adapter
)
```

**Tahmini Süre:** 15-20 dakika

---

#### 1.6 Bias Service Ekle
**Eksik:**
- Directional bias check
- Long/short preference

**Çözüm:**
```python
from application.bias_service import BiasService

self.bias_service = BiasService(self.policy)
bias_check = self.bias_service.check_bias(symbol, gated_signal)
```

**Tahmini Süre:** 10-15 dakika

---

#### 1.7 Reversal Manager Ekle
**Eksik:**
- Reversal detection
- IGNORED/COOLDOWN states

**Çözüm:**
```python
from application.reversal_manager import ReversalManager

self.reversal_manager = ReversalManager(self.policy)
transition = self.reversal_manager.process(symbol, gated_signal)
```

**Tahmini Süre:** 10-15 dakika

---

### 📌 **Faz 2: Normal Eşiklere Geri Dön**

#### 2.1 Eşikleri Düzelt
**Şu an (Backtest için düşürülmüş):**
```python
min_score = 55  # Lowered for backtest
if final_score > 55: decision = 'LONG'
elif final_score < 45: decision = 'SHORT'
```

**Olması Gereken (Policy'den al):**
```python
min_score = self.policy['trading']['scoring']['min_composite_score'] * 100  # 60
enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']  # 60
enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']  # 40
```

**Tahmini Süre:** 5 dakika

---

### 📌 **Faz 3: Gerçek Veri Hazırla**

#### 3.1 90 Günlük Veri İndir
**Komut:**
```bash
python scripts/download_historical_data.py --symbol BTC-USDT --timeframe 15m --days 90
```

**Tahmini Süre:** 5-10 dakika (API hızına bağlı)

---

### 📌 **Faz 4: Tam Bot'u Backtest Modunda Çalıştır**

#### 4.1 Yeni Backtest Engine: "Full Bot Mode"
**Yeni Dosya:** `backtests/full_bot_engine.py`

**İçerik:**
- Gerçek bot'un **TÜM** bileşenlerini kullan
- Signal generation → Gating → State management → Execution
- Gerçek `infrastructure/runtime.py` akışını takip et

**Pseudo-code:**
```python
class FullBotBacktestEngine:
    def __init__(self):
        # Initialize ALL components (same as real bot)
        self.ta_scorer = TAScorer()
        self.ml_scorer = MLScorer()
        self.news_scorer = NewsScorer()
        self.risk_service = RiskService(policy)
        self.signal_gate = SignalGate(policy)
        self.state_manager = PositionStateManager(policy)
        self.bias_service = BiasService(policy)
        self.reversal_manager = ReversalManager(policy)
        
    async def process_bar(self, bar, hist_df):
        # 1. Generate composite signal (TA+ML+News+Risk)
        composite_signal = await self._generate_composite_signal(...)
        
        # 2. Signal gating (Persistence, Confirmation, Hysteresis, Regime)
        gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h)
        
        # 3. State transition (IDLE → SIGNAL_DETECTED → IN_POSITION)
        transition = self.state_manager.process_signal(symbol, gated_signal)
        
        # 4. Bias check
        bias_check = self.bias_service.check_bias(symbol, gated_signal)
        
        # 5. Reversal check
        reversal_approval = self.reversal_manager.process(symbol, gated_signal)
        
        # 6. Dynamic position sizing
        position_size = await self._calculate_position_size(composite_signal, symbol)
        
        # 7. Execute (if all checks pass)
        if transition.action == 'ENTER' and bias_check['passed'] and reversal_approval['approved']:
            await self._enter_position(bar, gated_signal, position_size)
```

**Tahmini Süre:** 60-90 dakika

---

## 🚀 Uygulama Planı

### **Adım 1: ML Düzeltmesi** (15-20 dk)
```bash
# ML scorer'ı düzelt
# Test et
python -c "from scoring.ml_scorer import MLScorer; m = MLScorer(); print('ML OK')"
```

### **Adım 2: News Kontrolü** (10 dk)
```bash
# News scorer'ı kontrol et
# Simulated data veya API key ekle
```

### **Adım 3: Signal Gates Entegrasyonu** (30-40 dk)
```python
# backtests/full_bot_engine.py oluştur
# Signal Gate'leri ekle
```

### **Adım 4: State Management Ekle** (20-30 dk)
```python
# PositionStateManager entegre et
# Bias/Reversal manager ekle
```

### **Adım 5: Dynamic Sizing Ekle** (15-20 dk)
```python
# _calculate_position_size fonksiyonunu kullan
```

### **Adım 6: Normal Eşikler** (5 dk)
```python
# Hardcoded 55 → Policy'den al (60)
```

### **Adım 7: 90 Günlük Veri** (5-10 dk)
```bash
python scripts/download_historical_data.py --days 90
```

### **Adım 8: Tam Backtest** (10 dk çalışma süresi)
```bash
python backtests/full_bot_engine.py
```

---

## ⏱️ Toplam Tahmini Süre

| Faz | Süre |
|-----|------|
| Faz 1: Bot'u düzelt | 90-120 dakika |
| Faz 2: Eşikler | 5 dakika |
| Faz 3: Veri | 5-10 dakika |
| Faz 4: Backtest | 10 dakika |
| **TOPLAM** | **~2-2.5 saat** |

---

## ✅ Başarı Kriterleri

Backtest tamamlandığında şunlar OLMALI:

1. ✅ **9 bileşen entegre:**
   - TA Scorer ✅
   - ML Scorer ✅ (düzeltilmiş)
   - News Scorer ✅ (çalışır)
   - Risk Service ✅
   - Signal Gate ✅ (4 processor)
   - State Manager ✅
   - Bias Service ✅
   - Reversal Manager ✅
   - Dynamic Position Sizing ✅

2. ✅ **Gerçek bot akışı:**
   - Signal generation → Gating → State → Sizing → Execution
   - Her adım log edilmiş

3. ✅ **90 günlük veri:**
   - Farklı market koşulları (bull, bear, ranging)
   - Yeterli trade sayısı (50-100+ trade)

4. ✅ **Gerçekçi sonuçlar:**
   - Sharpe > 0 (ideal: > 1)
   - Win rate > 50% (ideal: > 55%)
   - Max DD < 10%

---

## 🎯 Sonraki Adım

**Şimdi ne yapmalıyız?**

**ÖNERİM:** Sırayla adım adım git:

1. ✅ **ML skorlamayı düzelt** (15 dk) → Bot'un kritik bileşeni
2. ✅ **News'i kontrol et** (10 dk) → Simulated veya API
3. ✅ **Full Bot Engine oluştur** (60-90 dk) → Tüm bileşenleri entegre et
4. ✅ **90 günlük veri indir** (5 dk)
5. ✅ **Tam backtest çalıştır** (10 dk)

**Onaylarsan başlayalım!** İlk adım: ML skorlamayı düzeltelim mi?

