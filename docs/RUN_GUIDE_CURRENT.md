# 🚀 AiBotBS Çalıştırma Rehberi (Güncel)

## 1) Kısa Özet

- **Trading Bot**: Anlık piyasa analizi yapıp karar verir (TA, ML, News, Risk skorları hesaplanır)
- **Scheduler**: Periyodik işleri otomatik çalıştırır (15m'de bir trading analizi, 5m'de bir haber güncellemesi vs)
- **Mod Seçimi**: DRY_RUN (test), PAPER (kağıt üzerinde), LIVE (gerçek para)
- **Başlatma**: PowerShell/Bash script'leri veya Docker Compose
- **Loglar**: Attach modda otomatik akar; detach modda `docker logs -f` veya `Tail-Logs` kullan

## 2) Çalıştırma Modları

### DRY_RUN
- **Ne yapar**: Tüm analiz ve kararları yapar ama **asla emir göndermez**
- **Kullanım**: Geliştirme, test, debug
- **Ayar**: `TRADING_MODE=DRY_RUN` veya `OKX_ACCOUNT_MODE=paper` + `LIVE_TRADING=false`

### PAPER (Kağıt Üzerinde)
- **Ne yapar**: Test hesabında sanal emirler açar (OKX paper trading)
- **Kullanım**: Strateji testinde gerçek piyasa koşullarını simüle etmek
- **Ayar**: `OKX_ACCOUNT_MODE=paper` + `LIVE_TRADING=true`
- **Uyarı**: Paper hesabı için ayrı API key gerekli

### LIVE (Gerçek Para)
- **Ne yapar**: **GERÇEK HESAP**ta gerçek emirler açar
- **Kullanım**: Production, gerçek trading
- **Ayar**: `OKX_ACCOUNT_MODE=live` + `LIVE_TRADING=true`
- **⚠️ UYARI**: GERÇEK PARA RİSKİ! Dikkatli kullanın, küçük sermaye ile başlayın.

## 3) Giriş Komutları ve Kısayollar

### PowerShell (dev_simple.ps1)

| Komut | Ne Yapar | Örnek Kullanım |
|-------|----------|----------------|
| `Run-Trading` | Trading bot'u başlatır (scheduler'sız) | `. .\scripts\dev_simple.ps1; Run-Trading` |
| `Run-Scheduler` | Scheduler ile tüm işleri periyodik çalıştırır | `Run-Scheduler` |
| `Check-Health` | Sistem sağlığını kontrol eder (Bot, Docker, Metrics) | `Check-Health` |
| `Stop-Bot` | Çalışan tüm Python process'lerini durdurur | `Stop-Bot` |

**Hızlı Başlatma:**
```powershell
cd C:\Users\<user>\Desktop\ai_bot_trader\ai-trade-bot
. .\scripts\dev_simple.ps1
Run-Scheduler  # Scheduler ile başlat
```

### Bash (dev.sh)

| Komut | Ne Yapar | Örnek Kullanım |
|-------|----------|----------------|
| `run_trading` | Trading bot'u başlatır | `source scripts/dev.sh; run_trading` |
| `run_scheduler` | Scheduler ile tüm işleri çalıştırır | `run_scheduler` |
| `check_health` | Sistem sağlığını kontrol eder | `check_health` |
| `stop_bot` | Bot process'lerini durdurur | `stop_bot` |
| `tail_logs` | Log'ları canlı izler | `tail_logs 100 --follow` |

**Hızlı Başlatma:**
```bash
cd ~/ai-trade-bot
source scripts/dev.sh
run_scheduler
```

### Docker Compose

| Komut | Ne Yapar | Log Görünümü |
|-------|----------|--------------|
| `docker compose up` | **Attach mode** - loglar otomatik akar terminal'de | ✅ Canlı log akışı |
| `docker compose up -d` | **Detach mode** - arka planda çalışır | ❌ Log görmek için `logs -f` gerekli |
| `docker compose logs -f` | Detach modda log'ları takip et | ✅ Canlı log akışı |
| `docker compose down` | Container'ları durdur ve kaldır | - |

**Hızlı Başlatma (Docker):**
```bash
cd monitoring
docker compose up     # Prometheus & Grafana (attach mode)

# Başka bir terminal'de:
cd ..
docker compose up     # Bot (varsa bot compose file)
```

## 4) Scheduler İşleri

Scheduler, belirtilen periyotlarda otomatik olarak işleri tetikler:

| İş | Periyot | Kaynak | Açıklama |
|----|---------|--------|----------|
| **risk_monitor** | 1 dakika | `application/jobs/risk_monitor.py` | Açık pozisyonların risk durumunu izler, TP/SL kontrol eder |
| **run_watchdog** | 1 dakika | `application/jobs/run_watchdog.py` | Kaçırılan job'ları yakalar ve retry yapar |
| **news_incremental_5m** | 5 dakika | `application/jobs/news_incremental_5m.py` | Haber kaynaklarından yeni haberleri çeker, LLM ile analiz eder |
| **trailing_5m** | 5 dakika | `application/jobs/trailing_5m.py` | Trailing stop-loss güncellemeleri yapar |
| **trading_analysis** | 15 dakika | `application/jobs/trading_analysis.py` | Ana trading analizi: TA, ML, News, Risk skorları → sinyal üretir |
| **market_overview** | 15 dakika | `application/jobs/market_overview.py` | Piyasa genel durumunu raporlar |
| **telegram_summary_15m** | 15 dakika | `application/jobs/telegram_summary_15m.py` | Telegram'a özet bildirim gönderir |
| **regime_1h** | 1 saat | `application/jobs/regime_1h.py` | Piyasa rejim analizi (trend/ranging) |
| **daily_report** | Günlük | `application/jobs/daily_report.py` | Günlük performans raporu oluşturur |

**Not:** İşler `configs/policy.yaml` dosyasında tanımlı cron formatında (ör. `*/15 * * * *`)

## 5) Loglar (Nasıl Görürüm?)

### Attach Modda (Otomatik Akış)

Botu `python -u -m infrastructure.scheduler_runner` veya `docker compose up` (attach) ile başlattıysan, loglar **otomatik olarak terminal'e akar**. Hiçbir şey yapman gerekmez.

### Detach Modda (Arka Plan)

Botu arka planda başlattıysan (`docker compose up -d` veya PowerShell `Start-Process`):

**PowerShell:**
```powershell
# Yöntem 1: Script ile
. .\scripts\dev_simple.ps1
# (Tail-Logs fonksiyonu yok, manuel yapmalısın)

# Yöntem 2: Manuel
Get-Content logs\aibotbs.log -Tail 50 -Wait -Encoding UTF8
```

**Bash:**
```bash
tail -f logs/aibotbs.log -n 100
```

**Docker:**
```bash
docker compose logs -f aibot  # container adı
```

### Log Dosyaları

- **Ana log**: `logs/aibotbs.log` (prod) veya `logs/dev.log` (dev mode)
- **Fallback log**: `logs/fallback.log` (logging init öncesi)
- **Job-specific**: `logs/agent_*.log`, `logs/service_*.log`

### Örnek Log Çıktısı

```log
2025-10-15 16:30:35.247 | INFO     | application.news_service:_bootstrap_symbol:148 - ? [NEWS] sym=LINK bootstrap completed: 8 articles
2025-10-15 16:30:35.247 | INFO     | application.news_service:lazy_bootstrap_symbol:124 - ?? [NEWS] Lazy bootstrap for UNI (no watermark)
2025-10-15 16:30:36.527 | INFO     | application.news_service:_fetch_news_for_symbol:223 - ?? [NEWS] sym=UNI timestamp filter: 21 -> 21 articles
2025-10-15 16:30:36.560 | INFO     | application.news_digest_manager:get_digest_status:128 - ?? [LLM] sym=UNI digest=CHANGED run=YES items=21
2025-10-15 16:30:36.561 | INFO     | application.news_service:_analyze_news_with_llm:288 - ?? [LLM] sym=UNI digest=CHANGED run=YES items=21
2025-10-15 16:30:39.320 | INFO     | application.news_llm_analyzer:_parse_analysis_result:180 - ?? [NEWSCLS] type=general sym=UNI conf=0.40 dir=neutral
2025-10-15 16:30:39.320 | INFO     | application.news_llm_analyzer:analyze_news_batch:49 - ? [LLM] sym=UNI analysis completed: 50.0 (['MARKET', 'REGULATION', 'TECHNOLOGY'])
2025-10-15 16:30:39.367 | INFO     | application.news_service:_analyze_news_with_llm:307 - ?? [NEWSCLS] type=general sym=UNI conf=0.50 title="Bitwise CIO Says Bitcoin Recovery Could Indicate..."
2025-10-15 16:30:39.367 | INFO     | application.news_service:_bootstrap_symbol:148 - ? [NEWS] sym=UNI bootstrap completed: 21 articles
2025-10-15 16:30:41.761 | ERROR    | application.jobs.trading_analysis:execute:135 - ? TradingAnalysisJob execution failed: Unsupported timeframe: 2025-10-15T13:30:00+00:00
2025-10-15 16:30:41.761 | WARNING  | __main__:_execute_with_retry:295 - [JOB] name=trading_analysis attempt=2 retry_in=30s error=Unsupported timeframe
2025-10-15 16:30:42.298 | INFO     | __main__:stop:356 - ?? Shutting down scheduler...
2025-10-15 16:30:42.300 | INFO     | application.analysis_cards:send_shutdown_message:70 - ?? [CARDS] Shutdown message sent
2025-10-15 16:30:42.300 | INFO     | __main__:stop:369 - ? Scheduler stopped gracefully
```

### Log Seviyeleri

- **DEBUG** (🐞): Detaylı debug bilgisi (sadece dev modda)
- **INFO** (ℹ️): Normal işleyiş bilgileri
- **WARNING** (⚠️): Uyarılar (işlem devam eder)
- **ERROR** (❌): Hatalar (işlem başarısız oldu)
- **CRITICAL** (🚨): Kritik hatalar (sistem durabilir)

**Dev Mode:** Emoji'li, renkli log'lar (Windows'ta colorama ile)  
**Prod Mode:** Düz log'lar, dosyaya yazılır

### Beklenen İlk Çıktılar

Scheduler başlatıldığında göreceğin ilk log'lar:

```
| INFO | Scheduler initialized successfully
| INFO | Scheduler started successfully
| INFO | Registered jobs:
| INFO |   - Risk Monitor (1m) (risk_monitor): 2025-10-15 16:31:00+03:00
| INFO |   - Trading Analysis (15m) (trading_analysis): 2025-10-15 16:30:00+03:00
| INFO | Telegram client worker started
```

Trading analizi tetiklendiğinde:

```
| INFO | [JOB] name=trading_analysis status=STARTING
| INFO | Composite score: BTC TA=68.5 ML=72.3 NEWS=55.0 RISK=60.0 → FINAL=64.2
| INFO | Signal: LONG BTC size=0.05 leverage=2x
| INFO | [JOB] name=trading_analysis status=SUCCESS dur=12.3s
```

## 6) Metrics & Health

### Metrics Endpoint

Bot çalışırken Prometheus metrics'leri şu adreste yayınlanır:

```
http://localhost:8000/metrics
```

**Görüntüleme:**
```bash
curl http://localhost:8000/metrics
```

**Örnek metrics:**
- `aibot_trades_total` - Toplam trade sayısı
- `aibot_pnl_realized_usd` - Gerçekleşen kar/zarar (USD)
- `aibot_portfolio_value_usd` - Portfolio değeri
- `aibot_ml_score` - ML skoru
- `aibot_ta_score` - TA skoru
- `aibot_news_score` - News skoru
- `aibot_risk_score` - Risk skoru

### Health Check

**PowerShell:**
```powershell
. .\scripts\dev_simple.ps1
Check-Health
```

**Bash:**
```bash
source scripts/dev.sh
check_health
```

**Python (CLI):**
```bash
python -m infrastructure.health
```

**Çıktı örneği:**
```
==================================================
  HEALTH CHECK
==================================================

✅ OKX_API: Connected and whitelisted
✅ TELEGRAM: Client initialized
✅ SCHEDULER: 8 jobs registered
✅ METRICS: 25 bot metrics exposed
✅ LOGS: 5 files (12.3 MB)
==================================================
```

### Prometheus & Grafana

**Başlatma:**
```bash
cd monitoring
docker compose up -d
```

**Erişim:**
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

**Grafana Dashboard:**
1. Tarayıcıda http://localhost:3000 aç
2. Login: `admin` / `admin`
3. Dashboards → Browse → "AI Trading Bot Dashboard"
4. Gerçek zamanlı grafikleri gör (PnL, Win Rate, Scores, etc.)

**Log'ları görme:**
```bash
docker compose logs -f prometheus
docker compose logs -f grafana
```

## 7) ENV & Policy Anahtarları

### Önemli ENV Değişkenleri

**Mod ve Ortam:**
- `APP_ENV` - Ortam (dev/prod)
- `DEV_CONSOLE` - Dev console logları (1/0)
- `LOG_LEVEL` - Log seviyesi (DEBUG/INFO/WARNING/ERROR)
- `PYTHONUNBUFFERED` - Buffering kapalı (1)
- `PYTHONPATH` - Python modül path (.)

**Trading Modu:**
- `TRADING_MODE` - Mod (DRY_RUN/PAPER/LIVE)
- `OKX_ACCOUNT_MODE` - OKX hesap tipi (paper/live)
- `LIVE_TRADING` - Canlı trade (true/false)

**API Keys (Değerler .env'de):**
- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSPHRASE`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENAI_API_KEY`
- `CRYPTOCOMPARE_API_KEY`

**Monitoring:**
- `METRICS_ENABLED` - Prometheus metrics (true/false)
- `PROMETHEUS_PORT` - Metrics port (8000)

**Log Ayarları:**
- `CONSOLE_LOG` - Console log (1/0)
- `FILE_LOG` - Dosya log (1/0)
- `LOG_EMOJI` - Emoji'li log (1/0)

### Hızlı Örnek Bloklar

**PowerShell (Dev Mode):**
```powershell
$env:APP_ENV="dev"
$env:DEV_CONSOLE="1"
$env:LOG_LEVEL="DEBUG"
$env:PYTHONUNBUFFERED="1"
$env:PYTHONPATH="."
$env:TRADING_MODE="DRY_RUN"

python -u -m infrastructure.scheduler_runner
```

**Bash (Dev Mode):**
```bash
export APP_ENV=dev
export DEV_CONSOLE=1
export LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1
export PYTHONPATH=.
export TRADING_MODE=DRY_RUN

python -u -m infrastructure.scheduler_runner
```

**Production Mode:**
```bash
export APP_ENV=prod
export LOG_LEVEL=INFO
export CONSOLE_LOG=0
export FILE_LOG=1
export TRADING_MODE=LIVE  # DİKKATLİ!
```

## 8) Trading vs Scheduler (Basit Anlatım)

### Trading (Anlık Analiz)

**Ne yapar:**
- Piyasa verilerini çeker (OHLCV)
- Teknik analiz yapar (TA sinyalleri)
- ML modeli ile tahmin yapar
- Haberleri değerlendirir (sentiment)
- Risk hesaplar (korelasyon, likidite, volatilite)
- **Tüm skorları birleştirir** → AL/SAT/BEKLE kararı
- Emir açar (moda göre: DRY/PAPER/LIVE)
- TP/SL (take profit / stop loss) belirler
- Telegram'a bildirim gönderir

**Ne zaman kullan:**
- Manuel test yapmak istediğinde
- Tek bir analiz döngüsü görmek istediğinde
- Debug/geliştirme aşamasında

**Nasıl çalıştırılır:**
```powershell
. .\scripts\dev_simple.ps1
Run-Trading
```

### Scheduler (Periyodik İşler)

**Ne yapar:**
- **Zamanlanmış** olarak işleri tetikler
- **15 dakikada bir** trading analizi yapar
- **5 dakikada bir** haberleri günceller
- **1 dakikada bir** risk izler
- **1 saatte bir** piyasa rejimi günceller
- Birden fazla işi **paralel** yönetir
- Hataları **retry** yapar
- Kaçırılan job'ları **yakalayıp telafi eder**

**Ne zaman kullan:**
- 7/24 sürekli çalışacaksa
- Periyodik izleme gerekiyorsa
- Production'da (gerçek trading)

**Nasıl çalıştırılır:**
```powershell
. .\scripts\dev_simple.ps1
Run-Scheduler
```

### Farklar Özet

| Özellik | Trading | Scheduler |
|---------|---------|-----------|
| **Çalışma** | Tek seferlik | Sürekli/periyodik |
| **Kullanım** | Test, debug | Production |
| **İşler** | Sadece trading analizi | Tüm işler (news, risk, trading, etc.) |
| **Mod** | Manuel tetiklemeli | Otomatik tetiklemeli |
| **Süre** | 30-60 saniye | Sonsuz (durdurulana kadar) |

## 9) Sorun Giderme (Kısa Rehber)

### 1. Log'lar Gelmiyor / Görünmüyor

**Sebep:** Detach modda (`-d`) başlatmış olabilirsin.

**Çözüm:**
```bash
# Docker:
docker compose logs -f

# PowerShell:
Get-Content logs\aibotbs.log -Tail 100 -Wait

# Bash:
tail -f logs/aibotbs.log
```

### 2. Log'lar Geç Geliyor / Buffering Var

**Sebep:** Python output buffering aktif.

**Çözüm:**
```bash
export PYTHONUNBUFFERED=1
python -u -m infrastructure.scheduler_runner
```

PowerShell:
```powershell
$env:PYTHONUNBUFFERED="1"
python -u -m infrastructure.scheduler_runner
```

### 3. Trading Analizi Tetiklenmiyor

**Sebep:** Scheduler periyot bekliyor (15 dakika).

**Çözüm:**
- Trading'i direkt çalıştır: `Run-Trading`
- Veya bir sonraki 15'in katı dakikayı bekle (ör. 16:15, 16:30)
- Veya `policy.yaml`'da periyodu azalt (ör. `*/5 * * * *`)

### 4. OKX API Hatası: Error 50110

**Hata mesajı:**
```
Your IP X.X.X.X is not included in your API key's IP whitelist.
```

**Çözüm:**
1. OKX hesabına gir: https://www.okx.com/account/my-api
2. API Key → Edit
3. IP Whitelist'e şu anki IP'ni ekle
4. Veya "Unrestricted" seç (riskli ama test için uygundur)

### 5. Telegram Bildirimleri Gelmiyor

**Sebep:** Bot token veya chat ID yanlış/eksik.

**Çözüm:**
- `.env` dosyasını kontrol et:
  ```
  TELEGRAM_BOT_TOKEN=your_bot_token
  TELEGRAM_CHAT_ID=your_chat_id
  ```
- `configs/notifications.yaml` → `telegram.enabled: true` olmalı
- Health check yap: `Check-Health` → Telegram durumunu gör

### 6. ModuleNotFoundError: prometheus_client

**Hata:**
```
ModuleNotFoundError: No module named 'prometheus_client'
```

**Çözüm:**
```bash
venv\Scripts\pip install prometheus-client  # Windows
# veya
pip install -r requirements.txt
```

### 7. Emoji/Renk Sorunları (Windows)

**Sebep:** Windows console encoding.

**Çözüm:**
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

Veya emoji'leri kapat:
```powershell
$env:LOG_EMOJI="0"
```

### 8. Bot Sürekli Kapanıyor / Crash Oluyor

**Kontrol edilecekler:**
- Log dosyasında son hata mesajını bul: `Get-Content logs\aibotbs.log -Tail 50`
- API key'lerin doğru olduğundan emin ol
- Internet bağlantısını kontrol et
- RAM/CPU kullanımını kontrol et
- OKX API rate limit'e takılmış olabilir (log'da "rate limit" ara)

## 10) Hızlı Başlangıç (Kopyala-Yapıştır)

### PowerShell

**Dev Test (Scheduler):**
```powershell
cd C:\Users\<user>\Desktop\ai_bot_trader\ai-trade-bot
. .\scripts\dev_simple.ps1
Run-Scheduler
```

**Production (7/24, Arka Plan):**
```powershell
cd C:\Users\<user>\Desktop\ai_bot_trader\ai-trade-bot
.\start_bot_safe.ps1
```

**Health Check:**
```powershell
. .\scripts\dev_simple.ps1
Check-Health
```

**Bot Durdur:**
```powershell
Get-Process python | Stop-Process -Force
```

**Log İzle:**
```powershell
Get-Content logs\aibotbs.log -Tail 100 -Wait
```

### Bash

**Dev Test (Scheduler):**
```bash
cd ~/ai-trade-bot
source scripts/dev.sh
run_scheduler
```

**Production (7/24, Arka Plan):**
```bash
cd ~/ai-trade-bot
nohup python -u -m infrastructure.scheduler_runner &
```

**Health Check:**
```bash
source scripts/dev.sh
check_health
```

**Bot Durdur:**
```bash
pkill -f "python.*infrastructure"
```

**Log İzle:**
```bash
tail -f logs/aibotbs.log -n 100
```

### Docker Compose

**Monitoring Başlat (Prometheus + Grafana):**
```bash
cd monitoring
docker compose up -d
```

**Log'ları İzle:**
```bash
docker compose logs -f prometheus
docker compose logs -f grafana
```

**Durdur:**
```bash
docker compose down
```

---

**Bu dosya otomatik üretildi. Tarih: 2025-10-15 16:35 UTC+03:00**

