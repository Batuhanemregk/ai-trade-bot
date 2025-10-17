# 📋 **25 MADDELİK GELİŞTİRME PLANI - MEVCUT DURUM ANALİZİ**

> **Son Güncelleme:** 2025-10-09  
> **Durum:** Kapsamlı kod taraması tamamlandı

---

## ✅ **MEVCUT ÖZELLIKLER (Çalışıyor)**

### **✅ 1. Konfigürasyon Standartları** - %70 TAMAMLANDI

**Mevcut:**
- ✅ `configs/policy.yaml` - Tek kaynak politika
- ✅ `configs/policy.py` - Load/save/validate functions
- ✅ Environment variables (.env)
- ✅ YAML validation (check_yaml.py)

**Eksik:**
- ❌ JSON schema dosyası yok
- ❌ Pydantic model validation yok
- ❌ Detaylı schema validation yok

---

### **⚠️ 2. Log ve Karar İzlenebilirliği** - %40 TAMAMLANDI

**Mevcut:**
- ✅ Log formatı var (loguru)
- ✅ Decision logging (basic)
- ✅ run_history.jsonl (job history)

**Eksik:**
- ❌ Structured decision log yok (logs/decisions/*.jsonl)
- ❌ Kompakt format yok (t=... sym=... comp=...)
- ❌ Full trade replay capability yok

---

### **✅ 3. Hata Yönetimi ve Kurtarma** - %80 TAMAMLANDI

**Mevcut:**
- ✅ Retry logic (scheduler: 3x exponential backoff)
- ✅ Idempotency (bar-based, runtime_state.json)
- ✅ Graceful shutdown (signal handlers)
- ✅ Error logging

**Eksik:**
- ❌ Distributed lock yok
- ❌ RUNBOOK.md eksik (operations guide var ama dedicated runbook yok)

---

### **✅ 4. Risk Kalkanları** - %75 TAMAMLANDI

**Mevcut:**
- ✅ Correlation risk calculation (tier-based)
- ✅ Exposure limits (max_total_risk: 60%)
- ✅ Regime sizing adjustment (ADX-based)
- ✅ Position sizing limits

**Eksik:**
- ❌ Rolling 200 bar correlation matrix yok
- ❌ Correlation veto (>0.8) enforcement eksik

---

### **❌ 5. Backtest MVP** - %0 TAMAMLANDI

**Mevcut:**
- ❌ Backtest framework yok
- ❌ Historical simulation yok

**Eksik:**
- ❌ `backtests/mvp.py` yok
- ❌ CSV OHLCV loader yok
- ❌ Equity curve, metrics yok

---

### **⚠️ 6. Gerçek ML** - %20 TAMAMLANDI

**Mevcut:**
- ✅ ML scorer framework hazır
- ✅ Feature engineering (basic)
- ✅ Fallback simulation working

**Eksik:**
- ❌ Gerçek model yok (RandomForest, LSTM, XGBoost)
- ❌ Model training pipeline yok
- ❌ Model versioning yok
- ❌ `models/*.pkl` yok

---

### **✅ 7. Strategy/Gating İyileştirmeleri** - %85 TAMAMLANDI

**Mevcut:**
- ✅ SignalGate (persistence, confirmation)
- ✅ BiasService (trend filter, news guard, volatility guard)
- ✅ Reversal manager
- ✅ Signal hysteresis

**Durum:** **ÇOK İYİ ÇALIŞIYOR, KURCALAMA! ✅**

---

### **✅ 8. Trailing & Bracket Parametrizasyonu** - %90 TAMAMLANDI

**Mevcut:**
- ✅ Bracket executor (TP/SL)
- ✅ Trailing stops (trailing_5m job)
- ✅ R-multiple system (0.5R, 1.0R, 1.5R)
- ✅ ATR-based levels
- ✅ Policy parametrization

**Durum:** **ÇOK İYİ, EKSİK YOK! ✅**

---

### **⚠️ 9. Paper Trading** - %60 TAMAMLANDI

**Mevcut:**
- ✅ Dry-run mode (simulation)
- ✅ OKX testnet support
- ⚠️ Paper mode var ama limited

**Eksik:**
- ❌ Dedicated paper trading tracker yok
- ❌ `docs/PAPER_RESULTS.md` yok

---

### **❌ 10. Monitoring (Prometheus/Grafana)** - %0 TAMAMLANDI

**Mevcut:**
- ❌ Prometheus exporter yok
- ❌ Grafana dashboard yok
- ✅ Basic logging var

**Eksik:**
- ❌ `monitoring/prometheus.py` yok
- ❌ `grafana/dashboard.json` yok
- ❌ Metrics endpoint yok

---

### **✅ 11. Test Kapsamı** - %65 TAMAMLANDI

**Mevcut:**
- ✅ 26+ tests (core + integration)
- ✅ pytest setup
- ✅ Test markers (smoke, core, glue)
- ✅ ruff, mypy configured

**Eksik:**
- ❌ GitHub Actions CI/CD yok
- ❌ Coverage <80%
- ❌ `.github/workflows/ci.yml` yok

---

### **⚠️ 12. Acil Durum ve Güvenlik** - %50 TAMAMLANDI

**Mevcut:**
- ✅ Drawdown tracking
- ✅ Exposure limits
- ⚠️ Circuit breaker (partial)
- ✅ Telegram commands

**Eksik:**
- ❌ Daily loss limit enforcement yok
- ❌ Consecutive loss pause yok
- ❌ `/stop`, `/pause`, `/resume` commands eksik
- ❌ `docs/SECURITY.md` eksik
- ❌ Emergency shutdown automation eksik

---

### **❌ 13. Parametre Arama** - %0 TAMAMLANDI

**Eksik:**
- ❌ Grid search yok
- ❌ Parameter optimization yok
- ❌ `tuning/` klasörü yok

---

### **✅ 14. News/LLM Cache** - %90 TAMAMLANDI

**Mevcut:**
- ✅ LLM digest cache (60 min TTL)
- ✅ News storage
- ✅ Watermark tracking
- ✅ Cost management

**Durum:** **ÇOK İYİ ÇALIŞIYOR! ✅**

---

### **✅ 15. Prevalidation** - %95 TAMAMLANDI

**Mevcut:**
- ✅ `execution/prevalidation.py` tam
- ✅ Quantization
- ✅ Min qty, price tick validation
- ✅ Symbol formatting

**Durum:** **EKSİKSİZ! ✅**

---

### **⚠️ 16. Portfolio Raporlama** - %40 TAMAMLANDI

**Mevcut:**
- ✅ Portfolio tracking
- ✅ PnL calculation
- ✅ Telegram summary (basic)

**Eksik:**
- ❌ Günlük/haftalık rapor automation yok
- ❌ Detailed CSV/JSON export yok
- ❌ `reports/` klasörü yok

---

### **❌ 17. Backtest Framework v1** - %0 TAMAMLANDI

**Eksik:**
- ❌ Advanced backtest engine yok
- ❌ Walk-forward analysis yok
- ❌ Commission/slippage modeling yok

---

### **❌ 18. ML Ensemble** - %0 TAMAMLANDI

**Eksik:**
- ❌ Ensemble models yok
- ❌ Model versioning yok
- ❌ `models/version.json` yok

---

### **❌ 19. Dashboard** - %0 TAMAMLANDI

**Eksik:**
- ❌ FastAPI backend yok
- ❌ Frontend yok
- ❌ WebSocket yok
- ❌ `dashboard/` klasörü yok

---

### **❌ 20. Dağıtık Mimari** - %0 TAMAMLANDI

**Eksik:**
- ❌ Message queue yok
- ❌ Microservices yok
- ❌ Distributed job execution yok

---

### **⚠️ 21. Güvenlik Sertleştirme** - %30 TAMAMLANDI

**Mevcut:**
- ✅ .env için gitignore
- ✅ Environment isolation

**Eksik:**
- ❌ Secret manager integration yok
- ❌ Log redaction yok (API keys sızabilir)
- ❌ `docs/SECURITY.md` eksik

---

### **❌ 22. Canary Live** - %0 TAMAMLANDI

**Eksik:**
- ❌ Canary deployment strategy yok
- ❌ Micro position testing yok
- ❌ `docs/LIVE_READINESS.md` yok

---

### **✅ 23. Belgeler** - %80 TAMAMLANDI

**Mevcut:**
- ✅ QUICKSTART.md
- ✅ DEVELOPMENT_TESTING.md
- ✅ SCHEDULER_* guides
- ✅ ARCHITECTURE.md
- ✅ CONFIG.md
- ✅ EXECUTION.md

**Eksik:**
- ❌ RUNBOOK.md (operations)
- ❌ RISK.md (risk details)
- ❌ ML.md (ML integration)
- ❌ LOGGING.md (logging standards)
- ❌ SECURITY.md

---

## 📊 **ÖZET TABLO**

| # | Madde | Durum | Tamamlanma | Öncelik |
|---|-------|-------|------------|---------|
| 1 | Konfigürasyon Standartları | ⚠️ Partial | 70% | 🔴 HIGH |
| 2 | Log İzlenebilirliği | ⚠️ Partial | 40% | 🔴 HIGH |
| 3 | Hata Yönetimi | ✅ Good | 80% | 🟡 MEDIUM |
| 4 | Risk Kalkanları | ✅ Good | 75% | 🟡 MEDIUM |
| 5 | Backtest MVP | ❌ Missing | 0% | 🔴 HIGH |
| 6 | Gerçek ML | ⚠️ Framework | 20% | 🔴 HIGH |
| 7 | Strategy/Gating | ✅ **EXCELLENT** | 85% | 🟢 LOW |
| 8 | Trailing & Bracket | ✅ **EXCELLENT** | 90% | 🟢 LOW |
| 9 | Paper Trading | ⚠️ Partial | 60% | 🟡 MEDIUM |
| 10 | Monitoring | ❌ Missing | 0% | 🟡 MEDIUM |
| 11 | Test Coverage | ⚠️ Partial | 65% | 🟡 MEDIUM |
| 12 | Acil Durum | ⚠️ Partial | 50% | 🔴 HIGH |
| 13 | Parametre Arama | ❌ Missing | 0% | 🟢 LOW |
| 14 | News/LLM Cache | ✅ **EXCELLENT** | 90% | 🟢 LOW |
| 15 | Prevalidation | ✅ **EXCELLENT** | 95% | 🟢 LOW |
| 16 | Portfolio Rapor | ⚠️ Partial | 40% | 🟡 MEDIUM |
| 17 | Backtest v1 | ❌ Missing | 0% | 🟡 MEDIUM |
| 18 | ML Ensemble | ❌ Missing | 0% | 🟢 LOW |
| 19 | Dashboard | ❌ Missing | 0% | 🟢 LOW |
| 20 | Dağıtık Mimari | ❌ Missing | 0% | 🟢 LOW |
| 21 | Güvenlik | ⚠️ Partial | 30% | 🔴 HIGH |
| 22 | Canary Live | ❌ Missing | 0% | 🟡 MEDIUM |
| 23 | Belgeler | ✅ Good | 80% | 🟡 MEDIUM |

---

## 🎯 **ÖNCELİK SIRALAMASI**

### **🔴 HIGH Priority (Hemen Yapılmalı)**

```
1. Konfigürasyon Schema Validation
2. Log İzlenebilirliği (Decision JSONL)
5. Backtest MVP Framework
6. Gerçek ML Model Integration
12. Acil Durum & Circuit Breaker
21. Security & Log Redaction
```

### **🟡 MEDIUM Priority (1-2 Hafta)**

```
3. Hata Yönetimi İyileştirme
4. Risk Kalkanları (Correlation Matrix)
9. Paper Trading Enhancement
10. Prometheus Monitoring
11. Test Coverage (→80%)
16. Portfolio Reporting
22. Canary Live Testing
```

### **🟢 LOW Priority (Gelecek)**

```
13. Grid Search / Param Optimization
17. Advanced Backtest Framework
18. ML Ensemble & Versioning
19. Web Dashboard
20. Distributed Architecture
```

---

## 📋 **DETAYLI TODO PLAN**

---

### **🔴 TODO #1: Configuration Schema Validation**

**Durum:** %70 Tamamlandı, schema validation eksik

**Yapılacaklar:**

```python
# 1. Schema dosyası oluştur
File: configs/schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["exchange", "trading", "telegram"],
  "properties": {
    "exchange": {
      "type": "object",
      "required": ["mode", "symbols"],
      "properties": {
        "mode": {"enum": ["live", "dry-run"]},
        "symbols": {"type": "object"}
      }
    },
    "trading": {
      "type": "object",
      "properties": {
        "risk": {
          "type": "object",
          "properties": {
            "max_position_size": {"type": "number", "minimum": 0, "maximum": 1},
            "max_total_risk": {"type": "number", "minimum": 0, "maximum": 1}
          }
        },
        "scoring": {
          "type": "object",
          "properties": {
            "ta_weight": {"type": "number", "minimum": 0, "maximum": 1},
            "ml_weight": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      }
    }
  }
}

# 2. Pydantic models
File: configs/schemas.py
from pydantic import BaseModel, Field, validator

class RiskConfig(BaseModel):
    max_position_size: float = Field(ge=0.01, le=0.5)
    max_total_risk: float = Field(ge=0.1, le=1.0)
    stop_loss_pct: float = Field(ge=0.005, le=0.1)
    
class ScoringConfig(BaseModel):
    ta_weight: float = Field(ge=0, le=1)
    ml_weight: float = Field(ge=0, le=1)
    news_weight: float = Field(ge=0, le=1)
    risk_weight: float = Field(ge=0, le=1)
    
    @validator('*')
    def weights_sum_to_one(cls, v, values):
        total = sum(values.values()) + v
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v

class PolicyConfig(BaseModel):
    exchange: ExchangeConfig
    trading: TradingConfig
    telegram: TelegramConfig

# 3. Validation command
File: scripts/validate_config.py
def validate_policy_schema():
    import jsonschema
    policy = load_policy()
    schema = json.load(open('configs/schema.json'))
    jsonschema.validate(policy, schema)
    
# 4. Integrate in bootstrap
File: infrastructure/bootstrap.py
def load_policy(path):
    policy = yaml.load(...)
    validate_policy_schema(policy)  # ← Add validation
    return policy
```

**Test:**
```bash
python scripts/validate_config.py
python main.py config  # Should use schema validation
```

**Başarı Kriteri:**
- ❌ Yanlış config → Anlamlı hata mesajı
- ✅ Doğru config → Başarılı yüklenme

**Dosyalar:**
- `configs/schema.json`
- `configs/schemas.py` (Pydantic models)
- `scripts/validate_config.py`
- `docs/CONFIG.md` (update with schema)

---

### **🔴 TODO #2: Decision Log İzlenebilirliği**

**Durum:** %40, structured decision log yok

**Yapılacaklar:**

```python
# 1. Decision logger
File: infrastructure/decision_logger.py

class DecisionLogger:
    def __init__(self, log_dir='logs/decisions'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def log_decision(self, symbol, composite_signal, action, position_size, tp, sl):
        # Compact format
        timestamp = datetime.now(timezone.utc)
        log_entry = {
            't': timestamp.isoformat(),
            'sym': symbol,
            'comp': round(composite_signal.final_score, 2),
            'dir': composite_signal.decision,
            'ta': round(composite_signal.technical.score, 2),
            'ml': round(composite_signal.ml.score, 2),
            'news': round(composite_signal.news.score, 2),
            'risk': round(composite_signal.risk.score, 2),
            'gate': self._get_gate_status(composite_signal),
            'size': round(position_size, 6),
            'tp': round(tp, 2) if tp else None,
            'sl': round(sl, 2) if sl else None,
            'action': action,  # 'OPEN', 'CLOSE', 'SKIP'
            'reason': self._get_reason(composite_signal)
        }
        
        # Write to JSONL
        date_str = timestamp.strftime('%Y-%m-%d')
        log_file = self.log_dir / f"decisions_{date_str}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also log compact line
        compact = (f"t={timestamp:%H:%M:%S} sym={symbol} comp={composite_signal.final_score:.1f} "
                  f"dir={composite_signal.decision} ta={composite_signal.technical.score:.0f} "
                  f"ml={composite_signal.ml.score:.0f} news={composite_signal.news.score:.0f} "
                  f"risk={composite_signal.risk.score:.0f} size={position_size:.4f} action={action}")
        logger.info(f"[DECISION] {compact}")

# 2. Integrate in trading job
File: application/jobs/trading_analysis.py

from infrastructure.decision_logger import DecisionLogger

class TradingAnalysisJob:
    def __init__(self, ...):
        self.decision_logger = DecisionLogger()
    
    async def _process_symbol(self, symbol):
        # ... scoring logic ...
        
        # Log every decision
        self.decision_logger.log_decision(
            symbol, composite_signal, action, size, tp, sl
        )

# 3. Replay utility
File: scripts/replay_decisions.py

def replay_trade(decision_entry):
    """Reconstruct trade from decision log"""
    print(f"Symbol: {decision_entry['sym']}")
    print(f"Composite Score: {decision_entry['comp']}")
    print(f"Decision: {decision_entry['dir']}")
    print(f"Components: TA={decision_entry['ta']} ML={decision_entry['ml']}")
    # ... full reconstruction
```

**Başarı Kriteri:**
- ✅ Her decision JSONL'e yazılır
- ✅ Compact log formatı okunabilir
- ✅ Trade replay mümkün

**Dosyalar:**
- `infrastructure/decision_logger.py`
- `logs/decisions/*.jsonl` (auto-created)
- `scripts/replay_decisions.py`
- `docs/LOGGING.md`

---

### **🔴 TODO #5: Backtest MVP Framework**

**Durum:** %0, hiç yok

**Yapılacaklar:**

```python
# 1. Backtest engine
File: backtests/mvp.py

class BacktestMVP:
    def __init__(self, policy):
        self.policy = policy
        self.trades = []
        self.equity_curve = []
        
    async def run(self, ohlcv_csv_path, start_date, end_date):
        """Run backtest on historical data"""
        # Load CSV
        df = pd.read_csv(ohlcv_csv_path)
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        # Simulate trading
        for i in range(100, len(df)):
            window = df.iloc[i-100:i]
            
            # Score (use real scoring)
            from scoring.ta_scorer import ta_scorer
            ta_score, _, _ = ta_scorer.score(window, 'BTC-USDT')
            
            # Simple decision
            if ta_score >= 60:
                # Simulate entry
                entry = self._simulate_entry(df.iloc[i], 'LONG')
                self.trades.append(entry)
            
            # Update equity
            equity = self._calculate_equity()
            self.equity_curve.append({'timestamp': df.iloc[i]['timestamp'], 'equity': equity})
        
        # Generate report
        return self._generate_report()
    
    def _generate_report(self):
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] < 0]
        
        return {
            'total_trades': len(self.trades),
            'win_rate': len(wins) / len(self.trades) if self.trades else 0,
            'total_pnl': sum(t['pnl'] for t in self.trades),
            'max_drawdown': self._calculate_max_dd(),
            'profit_factor': self._calculate_pf(),
            'expectancy': sum(t['pnl'] for t in self.trades) / len(self.trades) if self.trades else 0
        }

# 2. Run script
File: scripts/run_backtest.py

import asyncio
from backtests.mvp import BacktestMVP

async def main():
    backtest = BacktestMVP(load_policy())
    result = await backtest.run(
        'data/BTC-USDT-1h.csv',
        '2024-01-01',
        '2024-12-31'
    )
    
    print(json.dumps(result, indent=2))
    
    # Save report
    with open('backtests/report_btc_2024.json', 'w') as f:
        json.dump(result, f, indent=2)

# 3. Equity curve plot
File: backtests/plot_equity.py

import matplotlib.pyplot as plt
import pandas as pd

def plot_equity_curve(report_file):
    with open(report_file) as f:
        report = json.load(f)
    
    equity = pd.DataFrame(report['equity_curve'])
    plt.plot(equity['timestamp'], equity['equity'])
    plt.title('Equity Curve')
    plt.savefig('backtests/equity_curve.png')
```

**Başarı Kriteri:**
- ✅ CSV → Backtest → Report çalışıyor
- ✅ Metrics: winrate, PnL, maxDD, PF
- ✅ Equity curve PNG oluşuyor

**Dosyalar:**
- `backtests/mvp.py`
- `backtests/plot_equity.py`
- `scripts/run_backtest.py`
- `backtests/report_*.json`
- `backtests/equity_curve.png`
- `docs/BACKTESTING.md`

---

### **🔴 TODO #6: Gerçek ML Model Integration**

**Durum:** %20, sadece framework ve simulation

**Yapılacaklar:**

```python
# 1. Feature engineering
File: ml/feature_engineering.py

def extract_features(ohlcv_df):
    """Extract ML features from OHLCV"""
    features = pd.DataFrame()
    
    # Technical indicators as features
    features['rsi'] = ta.momentum.rsi(ohlcv_df['close'], 14)
    features['macd_hist'] = ta.trend.macd_diff(ohlcv_df['close'])
    features['atr_pct'] = ta.volatility.atr(ohlcv_df['high'], ohlcv_df['low'], ohlcv_df['close']) / ohlcv_df['close']
    features['bb_position'] = (ohlcv_df['close'] - bb_lower) / (bb_upper - bb_lower)
    
    # Returns
    features['ret_1'] = ohlcv_df['close'].pct_change(1)
    features['ret_5'] = ohlcv_df['close'].pct_change(5)
    features['ret_20'] = ohlcv_df['close'].pct_change(20)
    
    # Time features
    features['hour'] = ohlcv_df.index.hour
    features['day_of_week'] = ohlcv_df.index.dayofweek
    
    return features.dropna()

# 2. Model training
File: ml/train_model.py

from sklearn.ensemble import RandomForestClassifier
import joblib

def train_rf_model(ohlcv_csv):
    df = pd.read_csv(ohlcv_csv)
    features = extract_features(df)
    
    # Target: Next bar direction
    target = (df['close'].shift(-1) > df['close']).astype(int)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, shuffle=False
    )
    
    # Train
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Save
    joblib.dump(model, 'models/rf_v1.pkl')
    
    # Evaluate
    score = model.score(X_test, y_test)
    print(f"Model accuracy: {score:.2%}")

# 3. Update ML scorer
File: scoring/ml_scorer.py

class MLScorer:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        model_path = Path('models/rf_v1.pkl')
        if model_path.exists():
            import joblib
            self.model = joblib.load(model_path)
            logger.info("✅ ML model loaded: rf_v1.pkl")
            self.models_available = True
        else:
            logger.info("ℹ️ No ML model, using simulation")
            self.models_available = False
    
    def score(self, symbol, ohlcv_bundle):
        if not self.models_available:
            return self._neutral_score(symbol)
        
        # Real prediction
        features = extract_features(ohlcv_bundle['main'])
        proba = self.model.predict_proba(features.iloc[-1:])[:,1][0]
        ml_score = proba * 100  # 0-100
        
        return (
            ml_score,
            f"RandomForest prediction: {proba:.2%} bullish",
            {"model": "rf_v1", "probability": proba}
        )
```

**Başarı Kriteri:**
- ✅ Model train edilebiliyor
- ✅ Model load ediliyor
- ✅ ML score gerçek tahmine dayanıyor
- ✅ Log'da "rf_v1" source görünüyor

**Dosyalar:**
- `ml/feature_engineering.py`
- `ml/train_model.py`
- `models/rf_v1.pkl`
- `models/metadata.json`
- `scripts/train_ml_model.py`
- `docs/ML.md`

---

### **🔴 TODO #12: Acil Durum & Circuit Breaker**

**Durum:** %50, partial implementation

**Yapılacaklar:**

```python
# 1. Circuit breaker service
File: application/circuit_breaker.py

class CircuitBreaker:
    def __init__(self, policy):
        self.policy = policy
        self.state = 'NORMAL'  # NORMAL, WARNING, EMERGENCY
        self.daily_start_balance = None
        self.consecutive_losses = 0
        
    async def check_and_act(self, portfolio):
        """Check circuit breaker conditions"""
        
        # Daily loss limit
        if self.daily_start_balance:
            daily_loss_pct = (portfolio.total_value - self.daily_start_balance) / self.daily_start_balance
            
            if daily_loss_pct < -0.25:  # 25% daily loss
                await self._trigger_emergency_stop("Daily loss exceeded 25%")
                return 'EMERGENCY'
        
        # Consecutive losses
        if self.consecutive_losses >= 3:
            await self._trigger_pause(hours=24, reason="3 consecutive losses")
            return 'PAUSED'
        
        # Max drawdown
        if portfolio.max_drawdown > 0.15:  # 15%
            await self._trigger_warning("Drawdown exceeded 15%")
            return 'WARNING'
        
        return 'NORMAL'
    
    async def _trigger_emergency_stop(self, reason):
        logger.critical(f"🚨 EMERGENCY STOP: {reason}")
        
        # Close all positions
        await self.close_all_positions()
        
        # Pause trading
        self.pause_trading(hours=24)
        
        # Send Telegram alert
        await self.send_alert(
            "🚨 EMERGENCY STOP",
            f"Reason: {reason}\nAll positions closed.\nTrading paused for 24h."
        )

# 2. Telegram emergency commands
File: telegram_bot/commands.py

@bot.command('stop')
async def emergency_stop_command(update, context):
    """Emergency stop - close all positions"""
    await circuit_breaker.trigger_emergency_stop("Manual stop via Telegram")
    await update.message.reply_text("🚨 Emergency stop triggered")

@bot.command('pause')
async def pause_trading_command(update, context):
    """Pause trading for N hours"""
    hours = int(context.args[0]) if context.args else 24
    circuit_breaker.pause_trading(hours=hours)
    await update.message.reply_text(f"⏸️ Trading paused for {hours}h")

@bot.command('resume')
async def resume_trading_command(update, context):
    """Resume trading"""
    circuit_breaker.resume_trading()
    await update.message.reply_text("▶️ Trading resumed")

# 3. Integrate in risk monitor
File: application/jobs/risk_monitor.py

class RiskMonitorJob(BaseJob):
    def __init__(self, ...):
        self.circuit_breaker = CircuitBreaker(policy)
    
    async def execute(self):
        portfolio = await self.get_portfolio()
        
        # Check circuit breaker
        state = await self.circuit_breaker.check_and_act(portfolio)
        
        if state == 'EMERGENCY':
            logger.critical("🚨 Circuit breaker triggered - EMERGENCY")
            # Stop scheduler?
        elif state == 'PAUSED':
            logger.warning("⏸️ Trading paused by circuit breaker")
```

**Başarı Kriteri:**
- ✅ Daily loss 25% → Auto close all
- ✅ 3 consecutive losses → 24h pause
- ✅ Telegram `/stop` çalışıyor
- ✅ Graceful recovery after pause

**Dosyalar:**
- `application/circuit_breaker.py`
- `telegram_bot/commands.py` (update)
- `application/jobs/risk_monitor.py` (update)
- `docs/RUNBOOK.md` (emergency procedures)
- `docs/SECURITY.md` (safety features)

---

### **🔴 TODO #21: Security & Log Redaction**

**Durum:** %30, basic security var ama log redaction yok

**Yapılacaklar:**

```python
# 1. Log redaction filter
File: infrastructure/log_redaction.py

import re

class LogRedactionFilter:
    """Filter sensitive data from logs"""
    
    PATTERNS = [
        (r'api_key["\']?\s*[:=]\s*["\']?([A-Za-z0-9-]+)', 'api_key=***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\']?([A-Za-z0-9-]+)', 'secret=***REDACTED***'),
        (r'passphrase["\']?\s*[:=]\s*["\']?([A-Za-z0-9-]+)', 'passphrase=***REDACTED***'),
        (r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9:-]+)', 'token=***REDACTED***'),
        (r'password["\']?\s*[:=]\s*["\']?([A-Za-z0-9-]+)', 'password=***REDACTED***'),
    ]
    
    def filter(self, record):
        message = record['message']
        
        for pattern, replacement in self.PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        record['message'] = message
        return record

# 2. Integrate in logger
File: infrastructure/logger.py

from infrastructure.log_redaction import LogRedactionFilter

def init_logging():
    # Add redaction filter
    logger.add(
        "logs/main.log",
        filter=LogRedactionFilter().filter,  # ← Add filter
        rotation="1 day",
        retention="7 days"
    )

# 3. Secret manager (optional)
File: infrastructure/secrets.py

import os
from typing import Optional

class SecretManager:
    """Manage secrets securely"""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> str:
        """Get secret from environment or secret store"""
        # Try environment first
        value = os.getenv(key)
        if value:
            return value
        
        # Try AWS Secrets Manager / Azure Key Vault (future)
        # ...
        
        return default
    
    @staticmethod
    def mask_secret(secret: str, visible_chars: int = 4) -> str:
        """Mask secret for logging"""
        if len(secret) <= visible_chars:
            return '*' * len(secret)
        return secret[:visible_chars] + '...'

# 4. Update exchange adapter
File: adapters/exchange_okx_ccxt.py

from infrastructure.secrets import SecretManager

class OKXCCXTAdapter:
    def __init__(self, config):
        api_key = SecretManager.get_secret('OKX_API_KEY')
        logger.info(f"🔑 API Key: {SecretManager.mask_secret(api_key)}")  # Safe log
```

**Başarı Kriteri:**
- ✅ API keys log'a düşmüyor
- ✅ Sensitive data masked
- ✅ .env gitignore'da

**Dosyalar:**
- `infrastructure/log_redaction.py`
- `infrastructure/secrets.py`
- `docs/SECURITY.md`

---

### **🟡 TODO #10: Prometheus Monitoring**

**Durum:** %0, hiç yok

**Yapılacaklar:**

```python
# 1. Prometheus exporter
File: monitoring/prometheus.py

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Metrics
trades_total = Counter('trades_total', 'Total trades', ['symbol', 'side', 'result'])
win_trades = Counter('win_trades', 'Winning trades', ['symbol'])
pnl_realized = Gauge('pnl_realized', 'Realized PnL', ['symbol'])
composite_score_last = Gauge('composite_score_last', 'Last composite score', ['symbol'])
drawdown_current = Gauge('drawdown_current', 'Current drawdown')
exposure_pct = Gauge('exposure_pct', 'Portfolio exposure percentage')
job_duration = Histogram('job_duration_seconds', 'Job execution time', ['job_name'])

class PrometheusExporter:
    def __init__(self, port=8000):
        self.port = port
        
    def start(self):
        start_http_server(self.port)
        logger.info(f"📊 Prometheus metrics: http://localhost:{self.port}/metrics")
    
    def record_trade(self, symbol, side, result, pnl):
        trades_total.labels(symbol=symbol, side=side, result=result).inc()
        if result == 'win':
            win_trades.labels(symbol=symbol).inc()
        pnl_realized.labels(symbol=symbol).set(pnl)
    
    def update_score(self, symbol, score):
        composite_score_last.labels(symbol=symbol).set(score)
    
    def update_portfolio(self, drawdown, exposure):
        drawdown_current.set(drawdown)
        exposure_pct.set(exposure)

# 2. Integrate in scheduler_runner
File: infrastructure/scheduler_runner.py

from monitoring.prometheus import PrometheusExporter

class SchedulerRunner:
    async def initialize(self):
        # ... existing code ...
        
        # Start Prometheus exporter
        if self.policy.get('monitoring', {}).get('prometheus', {}).get('enabled', False):
            self.prometheus = PrometheusExporter(port=8000)
            self.prometheus.start()

# 3. Grafana dashboard
File: monitoring/grafana/dashboard.json

{
  "dashboard": {
    "title": "AiBotBS Trading Dashboard",
    "panels": [
      {
        "title": "Total Trades",
        "targets": [{"expr": "trades_total"}]
      },
      {
        "title": "Win Rate",
        "targets": [{"expr": "win_trades / trades_total"}]
      },
      {
        "title": "Realized PnL",
        "targets": [{"expr": "pnl_realized"}]
      }
    ]
  }
}

# 4. Add to policy
File: configs/policy.yaml

monitoring:
  prometheus:
    enabled: true
    port: 8000
  
  alerts:
    drawdown_threshold: 0.10
    exposure_threshold: 0.70
```

**Başarı Kriteri:**
- ✅ Prometheus metrics http://localhost:8000/metrics
- ✅ Grafana dashboard import ediliyor
- ✅ Real-time metrics görünüyor

**Dosyalar:**
- `monitoring/prometheus.py`
- `monitoring/grafana/dashboard.json`
- `requirements.txt` (add: prometheus_client)
- `docs/MONITORING.md`

---

### **🟡 TODO #16: Portfolio Reporting**

**Durum:** %40, basic tracking var ama automated reporting yok

**Yapılacaklar:**

```python
# 1. Report generator
File: application/portfolio_reporter.py

class PortfolioReporter:
    async def generate_daily_report(self, portfolio, trades):
        """Generate daily performance report"""
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'summary': {
                'total_trades': len(trades),
                'win_rate': self._calculate_win_rate(trades),
                'total_pnl': sum(t['pnl'] for t in trades),
                'avg_r': self._calculate_avg_r(trades),
                'max_drawdown': portfolio.max_drawdown,
                'exposure_pct': portfolio.exposure / portfolio.total_value
            },
            'trades': trades,
            'positions': portfolio.positions
        }
        
        # Save as JSON
        report_path = f'reports/daily_{report["date"]}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save as CSV
        df = pd.DataFrame(trades)
        df.to_csv(f'reports/trades_{report["date"]}.csv', index=False)
        
        return report
    
    async def send_telegram_report(self, report):
        """Send report via Telegram"""
        message = f"""
📊 **Daily Report - {report['date']}**

**Performance:**
• Total Trades: {report['summary']['total_trades']}
• Win Rate: {report['summary']['win_rate']:.1%}
• Total PnL: ${report['summary']['total_pnl']:.2f}
• Avg R: {report['summary']['avg_r']:.2f}R
• Max DD: {report['summary']['max_drawdown']:.1%}
• Exposure: {report['summary']['exposure_pct']:.1%}
"""
        
        await telegram.send_message(message)
        
        # Send detailed CSV as file
        await telegram.send_document(f'reports/trades_{report["date"]}.csv')

# 2. Daily report job
File: application/jobs/daily_report.py

class DailyReportJob(BaseJob):
    async def execute(self):
        """Generate and send daily report"""
        portfolio = await self.get_portfolio()
        trades = await self.get_today_trades()
        
        reporter = PortfolioReporter()
        report = await reporter.generate_daily_report(portfolio, trades)
        await reporter.send_telegram_report(report)

# 3. Schedule in scheduler_runner
File: infrastructure/scheduler_runner.py

# Add daily report job (midnight)
self.scheduler.add_job(
    self._execute_job,
    CronTrigger.from_crontab('0 0 * * *'),  # Every day at midnight
    args=['daily_report'],
    id='daily_report'
)
```

**Başarı Kriteri:**
- ✅ Her gün midnight'ta otomatik rapor
- ✅ JSON + CSV export
- ✅ Telegram'a özet + dosya

**Dosyalar:**
- `application/portfolio_reporter.py`
- `application/jobs/daily_report.py`
- `reports/*.json` (auto-generated)
- `reports/*.csv` (auto-generated)

---

## 📊 **PRİORİTELENDİRİLMİŞ ROADMAP**

### **Sprint 1 (1-2 Hafta) - Critical**

```
Priority 1:
□ TODO #1: Config Schema Validation
□ TODO #2: Decision Log JSONL
□ TODO #12: Circuit Breaker & Emergency Stop
□ TODO #21: Log Redaction & Security

Sonuç: Production güvenliği artar
```

### **Sprint 2 (2-3 Hafta) - ML & Backtesting**

```
Priority 2:
□ TODO #5: Backtest MVP
□ TODO #6: Real ML Models (RF v1)
□ TODO #16: Portfolio Reporting

Sonuç: Stratejiler test edilebilir, ML gerçek olur
```

### **Sprint 3 (3-4 Hafta) - Monitoring & Optimization**

```
Priority 3:
□ TODO #10: Prometheus + Grafana
□ TODO #11: Test Coverage →80%
□ TODO #4: Correlation Matrix (rolling 200)

Sonuç: Gözlemlenebilirlik ve güvenilirlik artar
```

### **Sprint 4+ (Future) - Advanced**

```
Priority 4:
□ TODO #13: Parameter Grid Search
□ TODO #17: Advanced Backtest
□ TODO #18: ML Ensemble
□ TODO #19: Web Dashboard
□ TODO #22: Canary Live

Sonuç: Sistem tam otomasyona ve ölçeklenmeye hazır
```

---

## 📁 **DOSYA YAPILANMASI (SOLID Prensipleri)**

### **Yeni Eklenecek Klasörler:**

```
ai-trade-bot/
├── monitoring/                 ← TODO #10
│   ├── __init__.py
│   ├── prometheus.py
│   └── grafana/
│       └── dashboard.json
│
├── ml/                         ← TODO #6
│   ├── __init__.py
│   ├── feature_engineering.py
│   ├── train_model.py
│   └── evaluate.py
│
├── models/                     ← TODO #6
│   ├── rf_v1.pkl
│   ├── metadata.json
│   └── version.json
│
├── backtests/                  ← TODO #5, #17
│   ├── __init__.py
│   ├── mvp.py
│   ├── engine/
│   ├── report_*.json
│   └── equity_curve.png
│
├── reports/                    ← TODO #16
│   ├── daily_*.json
│   ├── weekly_*.json
│   └── trades_*.csv
│
├── tuning/                     ← TODO #13
│   ├── grid_search.py
│   └── results_*.csv
│
└── dashboard/                  ← TODO #19 (future)
    ├── backend/
    └── frontend/
```

### **Yeni/Güncellenecek Docs:**

```
docs/
├── LOGGING.md                  ← TODO #2
├── RUNBOOK.md                  ← TODO #3, #12
├── SECURITY.md                 ← TODO #12, #21
├── RISK.md                     ← TODO #4
├── ML.md                       ← TODO #6
├── BACKTESTING.md              ← TODO #5
├── MONITORING.md               ← TODO #10
├── PAPER_RESULTS.md            ← TODO #9
└── LIVE_READINESS.md           ← TODO #22
```

---

## 🎯 **HEMEN YAPILACAKLAR (Bu Hafta)**

### **#1 Priority - Config Schema (2-3 saat):**
```bash
1. configs/schema.json oluştur
2. configs/schemas.py (Pydantic)
3. scripts/validate_config.py
4. Test: python main.py config
```

### **#2 Priority - Decision Logger (3-4 saat):**
```bash
1. infrastructure/decision_logger.py
2. Integrate in trading_analysis.py
3. scripts/replay_decisions.py
4. Test: logs/decisions/*.jsonl check
```

### **#3 Priority - Circuit Breaker (4-6 saat):**
```bash
1. application/circuit_breaker.py
2. Telegram commands (/stop, /pause, /resume)
3. Integrate in risk_monitor.py
4. Test scenarios
5. docs/RUNBOOK.md
```

---

## 💡 **ÖNERİ: Kademeli Yaklaşım**

### **Bu Hafta (Critical):**
- Config schema validation
- Decision logging
- Circuit breaker

### **Gelecek Hafta (Important):**
- Backtest MVP
- Real ML (RF v1)
- Log redaction

### **2-3 Hafta Sonra (Enhancement):**
- Prometheus monitoring
- Portfolio reporting
- Test coverage

### **1-2 Ay Sonra (Advanced):**
- Grid search
- Dashboard
- ML ensemble

---

**🎯 Toplam: 25 madde, 12'si eksik/partial, 13'ü tamamlanacak**

Şimdi bunlardan hangisini başlatmamı istersiniz? 🚀

