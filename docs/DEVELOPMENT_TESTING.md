# 🧪 **Development & Testing Guide**

## 🎯 **İKİ FARKLI MOD - NE ZAMAN HANGİSİ?**

---

## 📊 **Mod Karşılaştırması**

| Kullanım | Komut | Ne Zaman? | Scheduler Kullanır mı? |
|----------|-------|-----------|------------------------|
| **PRODUCTION (24/7)** | `python -m infrastructure.scheduler_runner` | Canlı sistem, uzun süreli çalışma | ✅ EVET (APScheduler) |
| **DEVELOPMENT/TEST** | `python main.py trading --timeout 300` | Hızlı test, feature development | ⚠️ HAYIR (while loop) |

---

## 🚀 **MODE 1: Production Scheduler (24/7 Çalışma)**

### **Komut:**
```bash
python -m infrastructure.scheduler_runner
```

### **Ne Yapar?**
```python
# scheduler_runner.py
class SchedulerRunner:
    async def start(self):
        # APScheduler başlat
        self.scheduler = AsyncIOScheduler()
        
        # Job'ları kaydet
        self.scheduler.add_job(trading_15m, cron='*/15 * * * *')
        self.scheduler.add_job(trailing_5m, cron='*/5 * * * *')
        # ... diğer job'lar
        
        # Başlat
        self.scheduler.start()
        
        # Sürekli çalış (graceful shutdown'a kadar)
        await self.shutdown_event.wait()
```

### **Çalışma Mantığı:**
- ✅ APScheduler engine (cron-based)
- ✅ Job'lar zamanında tetiklenir
- ✅ Idempotency (tekrar işlem yok)
- ✅ Retry mechanism
- ✅ Watchdog monitoring
- ✅ **7/24 kesintisiz çalışır**

### **Ne Zaman Kullan?**
- ✅ Production deployment
- ✅ 24 saat çalıştırma
- ✅ Canlı trading
- ✅ Paper trading (uzun süreli)

---

## 🔧 **MODE 2: Direct Trading (Development/Test)**

### **Komut:**
```bash
python main.py trading --timeout 300  # 5 dakika test
```

### **Ne Yapar?**
```python
# trading_orchestrator.py
class TradingOrchestrator:
    async def _main_loop(self):
        # Background task'ları başlat
        tasks = [
            asyncio.create_task(self._analysis_loop()),  # ← While loop
            asyncio.create_task(self._position_monitoring_loop()),
            asyncio.create_task(self._portfolio_update_loop()),
            asyncio.create_task(self._risk_monitoring_loop())
        ]
        
        await self.shutdown_event.wait()
    
    async def _analysis_loop(self):
        while self.running:  # ← SÜREKLI DÖNGÜ
            for symbol in symbols:
                # Analyze
                signal = await self._analyze_symbol(symbol, ohlcv)
                
                # Execute if valid
                if signal and signal['score'] > 0.6:
                    await self._execute_trade_signal(symbol, signal)
            
            # Config'ten interval (default 300s = 5 dakika)
            await asyncio.sleep(analysis_interval)  # ← BEKLE VE TEKRAR
```

### **Çalışma Mantığı:**
- ⚠️ While loops (continuous)
- ⚠️ asyncio.sleep() ile interval
- ⚠️ Scheduler VAR ama sadece event bus için (trading için DEĞİL)
- ❌ Idempotency yok
- ❌ Job management yok
- ✅ **Hızlı başlar, hızlı test edilir**

### **Ne Zaman Kullan?**
- ✅ Yeni özellik geliştirme
- ✅ Hızlı test (5-10 dakika)
- ✅ Debug (step-by-step)
- ✅ Single symbol test
- ✅ Algorithm tuning

---

## 🎓 **KULLANIM SENARYOLARı**

### **Senaryo 1: Yeni Bir Indicator Ekleme**

```bash
# 1. Kodu değiştir (örnek: scoring/ta_scorer.py)
# - Yeni indicator ekle: Williams %R

# 2. Hızlı test (Direct mode)
python main.py trading --symbols BTC-USDT --timeout 300

# Çıktı:
# [12:00:00] Analysis loop started
# [12:00:05] BTC-USDT analyzed: TA=65.4 (new indicator works!)
# [12:05:05] BTC-USDT analyzed again
# [12:10:00] Timeout reached, stopping

# 3. Eğer çalışıyorsa, scheduler'da test et
python -m infrastructure.scheduler_runner
# → Birkaç cycle gözlemle (30-45 dakika)

# 4. Eğer stable ise, production'a al
```

### **Senaryo 2: Signal Filtreleme Logic'i Değiştirme**

```bash
# 1. Kodu değiştir (application/signal_gate.py)
# - Persistence bar count: 2 → 3

# 2. Hızlı test
python main.py trading --symbols BTC-USDT,ETH-USDT --timeout 600

# Çıktı:
# [12:00:00] Signal: LONG (persistence: 1/3) → Skipped
# [12:05:00] Signal: LONG (persistence: 2/3) → Skipped
# [12:10:00] Signal: LONG (persistence: 3/3) → APPROVED!

# 3. Scheduler'da uzun test
python -m infrastructure.scheduler_runner
# → 2-3 saat gözlemle
```

### **Senaryo 3: Risk Parametresi Tuning**

```bash
# 1. policy.yaml değiştir
# max_position_size: 0.10 → 0.05

# 2. Hızlı test
python main.py trading --timeout 600

# Position sizing log'larını gözlemle:
# [INFO] Position size: $50 (5% instead of 10%)

# 3. Eğer iyi ise production scheduler'da test
python -m infrastructure.scheduler_runner
```

### **Senaryo 4: Yeni Job Ekleme**

```bash
# 1. Yeni job class oluştur
# application/jobs/funding_rate_monitor.py

from .base_job import BaseJob

class FundingRateMonitorJob(BaseJob):
    async def initialize(self):
        # Setup
        pass
    
    async def execute(self):
        # Funding rate monitoring logic
        logger.info("Checking funding rates...")

# 2. scheduler_runner.py'a ekle
self.jobs['funding_rate_monitor'] = FundingRateMonitorJob(...)

# 3. Register job
self.scheduler.add_job(
    self._execute_job,
    CronTrigger.from_crontab('0 */8 * * *'),  # Her 8 saatte
    args=['funding_rate_monitor'],
    id='funding_rate_monitor'
)

# 4. Test
python scripts/test_scheduler.py
python -m infrastructure.scheduler_runner
```

---

## 🧪 **Development Workflow**

### **Adım 1: Kod Değişikliği**
```bash
# Örnek: scoring/ta_scorer.py'da değişiklik
# - Yeni indicator ekle
# - Weight'leri ayarla
```

### **Adım 2: Unit Test**
```bash
# Sadece değiştirdiğin modülü test et
pytest tests/test_ta_scorer.py -v
```

### **Adım 3: Integration Test (Quick)**
```bash
# Direct mode ile 5-10 dakika test
python main.py trading --symbols BTC-USDT --timeout 600

# Log'da kontrol et:
grep "TA Score" logs/main.log
```

### **Adım 4: Integration Test (Full)**
```bash
# Scheduler mode ile 30-60 dakika test
python -m infrastructure.scheduler_runner

# 2-4 cycle gözlemle
# → 15m × 3 = 45 dakika
```

### **Adım 5: Validation**
```bash
# Test suite çalıştır
pytest tests/ -v

# Smoke test
pytest -m smoke

# Linting
ruff check .
```

### **Adım 6: Production Deploy**
```bash
# Son kez scheduler test
python scripts/test_scheduler.py

# Production'a al
python -m infrastructure.scheduler_runner
```

---

## ⚡ **Hızlı Test Komutları**

### **5 Dakika Test (Single Symbol):**
```bash
python main.py trading --symbols BTC-USDT --timeout 300
```

**Ne olur:**
- 1 cycle @ 00:00
- 1 cycle @ 05:00
- Timeout @ 05:00
- Exit

### **10 Dakika Test (Multiple Symbols):**
```bash
python main.py trading --symbols BTC-USDT,ETH-USDT,SOL-USDT --timeout 600
```

**Ne olur:**
- 2 cycle (0m, 5m)
- 3 symbol × 2 = 6 analysis

### **30 Dakika Test (Scheduler - Mini Production):**
```bash
# Terminal 1
python -m infrastructure.scheduler_runner

# Terminal 2 (30 dakika sonra)
# Ctrl+C (graceful shutdown)
```

**Ne olur:**
- 2x trading_15m (0m, 15m)
- 6x trailing_5m
- 6x news_5m
- 30x risk_1m
- Full production behavior

---

## 📊 **Hangi Modu Ne İçin?**

### **✅ Direct Trading (`python main.py trading`):**

**İYİ İÇİN:**
- ✅ Hızlı prototyping
- ✅ Algorithm debugging
- ✅ Single symbol focus
- ✅ Quick iterations (5-10 dakika)
- ✅ Step-by-step debugging
- ✅ Feature development
- ✅ Parameter tuning

**KÖTÜ İÇİN:**
- ❌ 24/7 running (unreliable)
- ❌ Production deployment
- ❌ Long-term testing
- ❌ Multiple job coordination

**Örnek:**
```bash
# Yeni bir TA indicator test ediyorsun
# scoring/ta_scorer.py'da Williams %R ekledin

# Quick test:
python main.py trading --symbols BTC-USDT --timeout 300
# → 5 dakikada görürsün çalışıyor mu

# Eğer çalışıyorsa, scheduler'da test et:
python -m infrastructure.scheduler_runner
# → 1 saat gözlemle
```

---

### **✅ Scheduler Trading (`python -m infrastructure.scheduler_runner`):**

**İYİ İÇİN:**
- ✅ **Production (24/7)**
- ✅ Long-term testing (>1 saat)
- ✅ Full system test
- ✅ Performance evaluation
- ✅ Strategy backtesting (live simulation)
- ✅ Stability testing

**KÖTÜ İÇİN:**
- ❌ Quick debugging (çok yavaş)
- ❌ Single-step debugging
- ❌ Rapid iterations

**Örnek:**
```bash
# Strateji değişikliği yaptın
# Uzun süreli test gerekli

# Scheduler ile 24 saat çalıştır:
python -m infrastructure.scheduler_runner

# Sonuçları analiz et:
cat data/run_history.jsonl | jq 'select(.status=="SUCCESS")' | wc -l
```

---

## 🎮 **Pratik Kullanım Örnekleri**

### **Örnek 1: TA Weight Değişikliği**

```yaml
# configs/policy.yaml
trading:
  scoring:
    ta_weight: 0.4  → 0.5  # TA weight artır
    ml_weight: 0.25 → 0.15  # ML weight azalt
```

**Test:**
```bash
# 1. Quick test (10 dakika)
python main.py trading --timeout 600

# Log'da kontrol:
grep "final_score" logs/main.log
# → Score'lar değişti mi?

# 2. Eğer mantıklı ise, scheduler'da 1 saat test
python -m infrastructure.scheduler_runner
```

### **Örnek 2: Yeni Bias Filter Ekleme**

```python
# application/bias_service.py
async def volume_guard(self, signal):
    """Düşük volume'da trade yapma"""
    if volume_ratio < 0.8:
        signal.downgrade(10)  # -10 point
```

**Test:**
```bash
# 1. Quick test - Düşük volume sembol seç
python main.py trading --symbols PENGU-USDT --timeout 300

# Log'da:
# [INFO] volume_guard applied: -10 points

# 2. Multi-symbol test
python main.py trading --timeout 900  # 15 dakika

# 3. Production test
python -m infrastructure.scheduler_runner  # 2 saat gözlemle
```

### **Örnek 3: Position Sizing Logic Değişikliği**

```python
# infrastructure/runtime.py _calculate_position_size()
# Base percentage değiştir: 1-10% → 0.5-5%
signal_percentage = 0.005 + (composite_score / 100.0) * 0.045
```

**Test:**
```bash
# 1. Dry-run quick test
python main.py trading --timeout 600

# Log'da kontrol:
grep "position size" logs/main.log
# → Size'lar beklendiği gibi mi?

# 2. Scheduler ile uzun test
python -m infrastructure.scheduler_runner
# → 4-8 saat çalıştır, pozisyon size'ları gözlemle
```

---

## 🧪 **Test Türleri**

### **1. Unit Test (En Hızlı)**
```bash
# Sadece değiştirdiğin dosyayı test et
pytest tests/test_ta_scorer.py -v

# Belirli bir test
pytest tests/test_ta_scorer.py::test_rsi_calculation -v
```

### **2. Integration Test (Hızlı - 5-10 dk)**
```bash
# Direct mode, timeout ile
python main.py trading --timeout 300
```

### **3. System Test (Orta - 30-60 dk)**
```bash
# Scheduler mode, manuel durdurma
python -m infrastructure.scheduler_runner
# → 30-60 dakika sonra Ctrl+C
```

### **4. Production Simulation (Uzun - 24 saat)**
```bash
# Scheduler mode, dry-run
# policy.yaml: mode: "dry-run"
python -m infrastructure.scheduler_runner
# → 24 saat kesintisiz çalıştır
```

---

## 🎯 **Development Best Practices**

### **Feature Development Cycle:**

```
1. KOD DEĞİŞİKLİĞİ
   ├─ Dosyayı düzenle
   └─ Unit test yaz
         ↓
2. UNIT TEST
   ├─ pytest tests/test_your_module.py
   └─ Tüm testler geçene kadar düzelt
         ↓
3. QUICK INTEGRATION TEST
   ├─ python main.py trading --timeout 300
   └─ 5 dakika gözlemle
         ↓
4. MEDIUM INTEGRATION TEST  
   ├─ python main.py trading --timeout 1800
   └─ 30 dakika gözlemle
         ↓
5. SCHEDULER TEST
   ├─ python -m infrastructure.scheduler_runner
   └─ 2-4 saat gözlemle
         ↓
6. VALIDATION
   ├─ pytest tests/ -v (full suite)
   ├─ ruff check .
   └─ mypy .
         ↓
7. PRODUCTION DEPLOY
   └─ python -m infrastructure.scheduler_runner (24/7)
```

---

## 📝 **Clean Code & SOLID Principles**

### **Yeni Feature Ekleme Kuralları:**

#### **1. Single Responsibility**
```python
# ❌ YANLIŞ: Tek dosyada her şey
def trading_job():
    fetch_data()
    calculate_ta()
    calculate_ml()
    execute_trade()
    send_notification()

# ✅ DOĞRU: Her işlem ayrı modülde
# data_fetcher.py
async def fetch_multi_timeframe_data(...)

# scoring/ta_scorer.py
def score(self, df, symbol)

# execution/order_executor.py
async def execute_market_order(...)
```

#### **2. Open/Closed Principle**
```python
# ✅ Yeni job eklemek için mevcut kodu değiştirme
# Yeni job class oluştur:

# application/jobs/your_new_job.py
class YourNewJob(BaseJob):  # ← BaseJob'dan türet
    async def execute(self):
        # Your logic
        pass

# scheduler_runner.py'a sadece register et
self.jobs['your_new_job'] = YourNewJob(...)
```

#### **3. Dependency Inversion**
```python
# ✅ Interface/abstraction kullan
from .base_job import BaseJob  # ← Abstract base

class MyJob(BaseJob):  # ← Concrete implementation
    pass

# scheduler_runner.py
jobs: Dict[str, BaseJob] = {}  # ← Abstraction'a depend
```

---

## 📂 **Dosya Organizasyonu**

### **Development/Testing Guides:**

```
docs/
├── DEVELOPMENT_TESTING.md       ← Bu dosya
├── CONTRIBUTING.md              ← Contribution guidelines
├── TESTING.md                   ← Test strategy
└── ARCHITECTURE_FINAL.md        ← Architecture

(Root)
├── QUICKSTART.md                ← 5-minute start
├── SCHEDULER_CALISTIRMA_KILAVUZU.md  ← Türkçe scheduler guide
├── BASLATMA_ONEMLI.md           ← Kritik notlar
├── SCHEDULER_PRODUCTION_READY.md     ← Production readiness
└── SCHEDULER_OZET.md            ← Kısa özet
```

---

## 🔧 **Debug Techniques**

### **1. Verbose Logging:**
```bash
# .env dosyasında
LOG_LEVEL=DEBUG

# Yeniden başlat
python main.py trading --timeout 300
```

### **2. Single Symbol Debugging:**
```bash
# Tek bir symbol'e odaklan
python main.py trading --symbols BTC-USDT --timeout 300

# Log'da daha az noise
```

### **3. Breakpoint Debugging:**
```python
# trading_orchestrator.py içinde
async def _analyze_symbol(self, symbol, ohlcv):
    import pdb; pdb.set_trace()  # ← Breakpoint
    
    # Step-by-step debug
```

### **4. Custom Log Messages:**
```python
# Geçici debug log'ları ekle
logger.debug(f"🔍 DEBUG: RSI value = {rsi}")
logger.debug(f"🔍 DEBUG: Signal strength = {signal_strength}")

# Test
python main.py trading --timeout 300

# Log'da göreceksin:
# [DEBUG] 🔍 DEBUG: RSI value = 45.3
```

---

## 📊 **Comparison Table**

### **Direct vs Scheduler - Feature Matrix:**

| Feature | Direct Trading | Scheduler Trading |
|---------|---------------|-------------------|
| **Başlatma** | `python main.py trading` | `python -m infrastructure.scheduler_runner` |
| **Execution** | While loops | Cron jobs |
| **Interval** | Config (default 300s) | Policy.yaml (cron) |
| **Idempotency** | ❌ | ✅ Bar-based |
| **Retry** | ❌ | ✅ 3x exponential |
| **Watchdog** | ❌ | ✅ Auto catch-up |
| **History** | Logs only | JSONL structured |
| **State** | Runtime only | Persistent |
| **Shutdown** | Immediate | Graceful |
| **Best for** | Development, quick test | Production, long-term |
| **Speed** | ⚡ Fast start | 🐢 Slower (more setup) |
| **Reliability** | 🟡 OK | 🟢 High |
| **Production** | ⚠️ Beta | ✅ Recommended |

---

## 💡 **Özet: Ne Zaman Hangisi?**

### **🔧 DEVELOPMENT & TESTING:**
```bash
# Yeni özellik eklerken
# Hızlı test ederken
# Debug yaparken
# Parameter tuning

→ python main.py trading --timeout 300-900
```

### **🚀 PRODUCTION & LONG-TERM:**
```bash
# 24/7 çalıştırma
# Canlı trading
# Paper trading (uzun süreli)
# Performance evaluation

→ python -m infrastructure.scheduler_runner
```

---

## ✅ **Checklist: Yeni Feature Eklerken**

```
Development:
□ Kodu yaz (SOLID principles)
□ Unit test ekle
□ pytest ile test et
□ Direct mode quick test (5-10 dk)
□ Log'ları gözlemle
□ Debugging (gerekirse)

Integration:
□ Direct mode extended test (30 dk)
□ Multiple symbols test
□ Error scenarios test

Scheduler:
□ Scheduler mode test (2-4 saat)
□ Job coordination check
□ Idempotency validation
□ Performance monitoring

Production:
□ Full test suite (pytest)
□ Linting (ruff)
□ Type checking (mypy)
□ Documentation update
□ Deploy to scheduler (24/7)
```

---

## 🎯 **FINAL ANSWER**

### **Sorularınızın Cevapları:**

**Q1: `python -m infrastructure.scheduler_runner` ile 24 saat başlatıyorum, doğru mu?**
- ✅ **EVET, DOĞRU!** Bu production mode, 24/7 için.

**Q2: Yeni özellikler ve testler için nasıl başlatmalı?**
- ✅ **Hızlı test:** `python main.py trading --timeout 300-900`
- ✅ **Uzun test:** `python -m infrastructure.scheduler_runner`

**Q3: `python main.py trading` loop mu çalıştırıyor?**
- ✅ **EVET**, `while self.running` loop kullanıyor
- ⚠️ APScheduler kullanmıyor (sadece event bus için var)
- 🎯 Development/test için ideal, production için DEĞİL

---

**🎓 Yeni workflow:**

```bash
# 1. Development
python main.py trading --timeout 300

# 2. Testing
python main.py trading --timeout 1800

# 3. Pre-production
python -m infrastructure.scheduler_runner  # 4-8 saat

# 4. Production
python -m infrastructure.scheduler_runner  # 24/7
```

Tamam mı? 🚀

