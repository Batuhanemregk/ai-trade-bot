# Bot Başlatma Yöntemleri Karşılaştırması

Bu dokümanda AI Trading Bot için mevcut üç farklı başlatma yöntemi açıklanmaktadır.

## 📊 Karşılaştırma Tablosu

| Özellik | `start_bot.py` | `dev.ps1` → `runtime trading` | `dev.ps1` → `scheduler_runner` |
|---------|---------------|------------------------------|-------------------------------|
| **Mimari** | Basit loop | CLI routing | Professional scheduler |
| **Scheduling** | Manuel (15 dk) | CLI parametreleri | APScheduler (cron) |
| **Jobs** | Tek job | Tek job (`trading_main`) | Çoklu job sistemi |
| **Telegram** | ✅ Entegre | ❌ Yok | ✅ Entegre (jobs üzerinden) |
| **Kullanım** | Basit, doğrudan | CLI üzerinden | Production-ready |
| **Monitoring** | ❌ Yok | ❌ Yok | ✅ Prometheus |
| **State Management** | ❌ Yok | ❌ Yok | ✅ Persistent state |

## 1. `start_bot.py` - Basit Loop + Telegram

### Amaç
Basit, tek seferlik trading bot başlatma scripti. Telegram bot entegrasyonu ile.

### Nasıl Çalışır?
```python
# 15 dakikada bir trading_main() çağırır
async def continuous_trading():
    while True:
        await trading_main(live=live_mode)
        await asyncio.sleep(900)  # 15 dakika
```

### Özellikleri
- ✅ **Basit**: Minimal kod, kolay anlaşılır
- ✅ **Telegram Entegrasyonu**: `init_telegram_app()` ile otomatik başlatma
- ✅ **Paper Mode**: Default olarak paper mode
- ❌ **Manual Scheduling**: Sabit 15 dakika interval
- ❌ **Tek Job**: Sadece `trading_main()` çalıştırır
- ❌ **State Yönetimi Yok**: Her cycle bağımsız

### Kullanım
```bash
python start_bot.py
```

### Ne Zaman Kullanılmalı?
- Hızlı test için
- Basit trading loop için
- Telegram bot ile birlikte çalıştırmak için

---

## 2. `dev.ps1` → `Start-Trading` - CLI Routing

### Amaç
Developer script üzerinden CLI routing kullanarak bot başlatma.

### Nasıl Çalışır?
```powershell
# dev.ps1 içinde:
Start-Trading
# → python -m infrastructure.runtime trading
```

```python
# infrastructure/runtime.py içinde:
def main():
    if command == "trading":
        # CLI parametrelerini parse eder
        # trading_main() veya scheduler'ı çağırır
```

### Özellikleri
- ✅ **CLI Routing**: Komut satırı üzerinden parametre geçişi
- ✅ **Esnek**: `--once`, `--timeout`, `--dry-run` parametreleri
- ✅ **Development-Friendly**: PowerShell script ile kolay kullanım
- ❌ **Telegram Yok**: Telegram bot entegrasyonu yok
- ❌ **Manuel Scheduling**: Ya `--once` ya da manuel tekrar başlatma

### Kullanım
```powershell
# Script yükle
. .\scripts\dev.ps1

# Trading başlat
Start-Trading

# Tek seferlik çalıştır
Start-Trading -Once

# Dry-run modu
Start-Trading -DryRun
```

### Ne Zaman Kullanılmalı?
- Development ortamında test için
- CLI parametreleriyle esnek çalıştırma için
- Tek seferlik trading cycle için

---

## 3. `dev.ps1` → `Start-Scheduler` - Professional Scheduler

### Amaç
Production-ready, multi-job scheduler sistemi. APScheduler ile cron-based scheduling.

### Nasıl Çalışır?
```powershell
# dev.ps1 içinde:
Start-Scheduler
# → python -m infrastructure.scheduler_runner
```

```python
# scheduler_runner.py içinde:
async def main():
    runner = SchedulerRunner()
    await runner.initialize()
    await runner.start()  # APScheduler başlar
```

### Özellikleri
- ✅ **Multi-Job System**: Çoklu job (trading_analysis, trailing_5m, regime_1h, risk_monitor, vb.)
- ✅ **Cron Scheduling**: APScheduler ile bar-aligned execution
- ✅ **State Persistence**: Runtime state dosyaya kaydedilir
- ✅ **Prometheus Monitoring**: Metrics toplama ve izleme
- ✅ **Retry Logic**: Exponential backoff ile retry
- ✅ **Graceful Shutdown**: Signal handlers ile temiz kapanış
- ✅ **Job Watchdog**: Missed runs kontrolü
- ✅ **Global Adapters**: Shared exchange adapter ve news service
- ✅ **Concurrency Control**: Semaphore ile paralel çalışma kontrolü

### Jobs Listesi
| Job | Schedule | Açıklama |
|-----|----------|----------|
| `trading_analysis` | 15m | Trading analizi ve sinyal üretimi |
| `trailing_5m` | 5m | Trailing stop güncellemeleri |
| `news_incremental_5m` | 5m | News verilerinin güncellenmesi |
| `regime_1h` | 1h | Regime analizi güncellemeleri |
| `risk_monitor` | 1m | Risk kontrolü ve circuit breaker |
| `market_overview` | 15m | Piyasa özeti |
| `telegram_summary_15m` | 15m | Telegram özet mesajları |
| `run_watchdog` | 1m | Missed runs kontrolü |

### Kullanım
```powershell
# Script yükle
. .\scripts\dev.ps1

# Scheduler başlat
Start-Scheduler

# Full stack (Docker + Bot)
Start-FullStack
```

### Ne Zaman Kullanılmalı?
- **Production ortamında**
- **Çoklu job gerektiğinde**
- **Monitoring ve metrics gerektiğinde**
- **State persistence gerektiğinde**
- **Bar-aligned execution gerektiğinde**

---

## 🎯 Hangisini Seçmeli?

### Basit Test / Development
```bash
python start_bot.py
```
- Hızlı başlatma
- Telegram entegrasyonu ile
- Basit loop

### CLI Üzerinden Test
```powershell
. .\scripts\dev.ps1
Start-Trading -Once
```
- Parametre geçişi ile esnek test
- Tek seferlik çalıştırma

### Production / Full System
```powershell
. .\scripts\dev.ps1
Start-FullStack
```
- Multi-job system
- Monitoring ve metrics
- State persistence
- Professional scheduling

---

## 🔄 Bot Başlatma Akış Diyagramı

```
┌─────────────────────────────────────────────────────────────┐
│                    STARTUP OPTIONS                          │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│ start_bot.py │   │ dev.ps1           │   │ dev.ps1      │
│              │   │ Start-Trading     │   │ Start-       │
│ Simple Loop  │   │                   │   │ Scheduler    │
│ + Telegram   │   │ CLI Routing       │   │              │
│              │   │                   │   │ Professional │
└──────┬───────┘   └─────────┬─────────┘   │ Scheduler   │
       │                     │              │             │
       │                     │              └──────┬──────┘
       │                     │                     │
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│ trading_main │   │ infrastructure    │   │ scheduler_   │
│ (every 15m) │   │ .runtime trading  │   │ runner.py    │
│              │   │                   │   │              │
│ Telegram Bot│   │ trading_main()    │   │ Multi-Job    │
│ Running     │   │ (once/manual)     │   │ System       │
│              │   │                   │   │              │
│              │   │ No Telegram      │   │ APScheduler  │
│              │   │                   │   │ Prometheus   │
└──────────────┘   └──────────────────┘   └──────────────┘
```

---

## 📝 Özet

| Durum | Önerilen Yöntem |
|-------|----------------|
| **İlk kurulum / test** | `start_bot.py` |
| **CLI test** | `dev.ps1` → `Start-Trading -Once` |
| **Development** | `dev.ps1` → `Start-Trading` |
| **Production** | `dev.ps1` → `Start-Scheduler` veya `Start-FullStack` |

---

## 🔧 Entegrasyon Notları

### `start_bot.py` ve `scheduler_runner.py` Entegrasyonu
Şu anda **iki ayrı sistem** var:
1. **Basit loop** (`start_bot.py`) - Telegram bot ile birlikte
2. **Professional scheduler** (`scheduler_runner.py`) - Multi-job system

### Önerilen Yaklaşım
- **Development**: `start_bot.py` (basit, hızlı)
- **Production**: `scheduler_runner.py` (professional, multi-job)

### Gelecek İyileştirmeler
- `start_bot.py`'yi scheduler'a geçirebilir
- Veya `scheduler_runner.py`'ye Telegram bot entegrasyonu eklenebilir
- İkisini birleştiren tek bir entry point oluşturulabilir

