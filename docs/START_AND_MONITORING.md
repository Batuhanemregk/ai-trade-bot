# Geliştirme Ortamı ve İzleme Kılavuzu

**Oluşturulma Tarihi:** 15 Ekim 2025, 18:25  
**Versiyon:** 1.0

---

## 📋 Kısa Özet

Bu dokümanda AI Trading Bot projesi için geliştirme ortamı kurulumu, başlatma scriptleri ve monitoring (izleme) altyapısı açıklanmaktadır:

1. **PowerShell ve Bash Scriptleri:** Tek merkezli, otomatik venv yönetimli başlatma komutları
2. **Scheduler ve Once Modları:** Hem periyodik hem de tek seferlik çalıştırma seçenekleri
3. **Prometheus İzleme:** Bot metrikleri otomatik toplanıyor, hedef durumu: **UP** ✅
4. **Grafana Dashboard:** Otomatik provisioning ile hazır paneller
5. **Health Check Komutları:** Sistem durumunu hızlıca kontrol etme araçları
6. **Hızlı Başlangıç:** Kopyala-yapıştır komutlarıyla anında çalışma

---

## 1. Geliştirme Scriptleri

### 1.1 PowerShell (Windows)

**Konum:** `scripts/dev.ps1`

#### Kullanılabilir Fonksiyonlar

| Fonksiyon | Açıklama |
|-----------|----------|
| `Start-Trading` | Trading bot'u başlatır (sürekli mod) |
| `Start-Trading -Once` | Tek seferlik çalıştırma (test için) |
| `Start-Scheduler` | Zamanlayıcıyı başlatır (sadece bot) |
| `Start-FullStack` | 🚀 **Docker + Bot'u birlikte başlatır** |
| `Watch-Logs -Follow` | Canlı log izleme |
| `Test-Health` | Sistem sağlık kontrolü |
| `Show-Python` | Python yapılandırmasını gösterir |
| `Install-Req` | requirements.txt paketlerini yükler |
| `Stop-Bot` | Bot süreçlerini durdurur |

#### Parametreler

- `-VenvPath <path>`: Belirli bir venv kullan
- `-NoVenv`: Sistem Python'u kullan (venv yok)
- `-Once`: Tek seferlik çalıştırma
- `-Tail <sayı>`: Gösterilecek satır sayısı
- `-Follow`: Canlı takip modu

#### Script Yükleme

```powershell
# Execution policy ayarla (sadece ilk seferde)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Script dosyasını engelden çıkar (sadece ilk seferde)
Unblock-File .\scripts\dev.ps1

# Script'i yükle
. .\scripts\dev.ps1
```

#### Kullanım Örnekleri

```powershell
# Python yapılandırmasını göster
Show-Python

# Tek seferlik test çalıştırma
Start-Trading -Once

# Scheduler'ı başlat (sadece bot)
Start-Scheduler

# 🚀 YENİ: Docker + Bot birlikte başlat
Start-FullStack

# Canlı log takibi
Watch-Logs -Follow

# Sistem sağlık kontrolü
Test-Health

# Paketleri yükle
Install-Req

# Bot'u durdur
Stop-Bot

# Özel venv kullan
Start-Trading -VenvPath "C:\custom\venv" -Once

# Sistem Python ile çalıştır
Start-Trading -NoVenv -Once
```

---

### 1.2 Bash (Linux/Mac)

**Konum:** `scripts/dev.sh`

#### Kullanılabilir Fonksiyonlar

| Fonksiyon | Açıklama |
|-----------|----------|
| `run_trading` | Trading bot'u başlatır (sürekli mod) |
| `run_trading --once` | Tek seferlik çalıştırma |
| `run_scheduler` | Zamanlayıcıyı başlatır |
| `tail_logs 50 --follow` | Canlı log izleme |
| `check_health` | Sistem sağlık kontrolü |
| `show_python` | Python yapılandırmasını gösterir |
| `install_req` | requirements.txt paketlerini yükler |
| `stop_bot` | Bot süreçlerini durdurur |

#### Parametreler

- `--venv-path <path>`: Belirli bir venv kullan
- `--no-venv`: Sistem Python'u kullan
- `--once`: Tek seferlik çalıştırma
- `--follow`: Canlı takip modu

#### Script Yükleme

```bash
# Script'i yükle (source komutuyla)
source scripts/dev.sh
```

#### Kullanım Örnekleri

```bash
# Python yapılandırmasını göster
show_python

# Tek seferlik test çalıştırma
run_trading --once

# Scheduler'ı başlat
run_scheduler

# Canlı log takibi
tail_logs 100 --follow

# Sistem sağlık kontrolü
check_health

# Paketleri yükle
install_req

# Bot'u durdur
stop_bot

# Özel venv kullan
run_trading --venv-path "/home/user/venv" --once

# Sistem Python ile çalıştır
run_trading --no-venv --once
```

---

## 2. Python Venv Yönetimi

### Otomatik Tespit Sırası

Scriptler otomatik olarak Python'u şu sırada arar:

**Windows (PowerShell):**
1. `venv\Scripts\python.exe` (varsayılan)
2. `.venv\Scripts\python.exe` (alternatif)
3. Sistem Python: `py` → `python` → `python3`

**Linux/Mac (Bash):**
1. `venv/bin/python` (varsayılan)
2. `.venv/bin/python` (alternatif)
3. Sistem Python: `python3` → `python` → `py`

### Manuel Venv Belirleme

```powershell
# PowerShell
Run-Trading -VenvPath "D:\projeler\myenv" -Once
```

```bash
# Bash
run_trading --venv-path "/opt/myenv" --once
```

### Sistem Python Kullanımı

```powershell
# PowerShell
Run-Trading -NoVenv -Once
```

```bash
# Bash
run_trading --no-venv --once
```

---

## 3. Docker Monitoring Stack

### 3.1 Konteyner Durumu

**Gerçek Çıktı (15 Ekim 2025, 18:20):**

```
NAME               IMAGE                    COMMAND                  SERVICE      CREATED         STATUS         PORTS
aibot_grafana      grafana/grafana:latest   "/run.sh"                grafana      5 minutes ago   Up 5 minutes   0.0.0.0:3000->3000/tcp
aibot_prometheus   prom/prometheus:latest   "/bin/prometheus --c…"   prometheus   5 minutes ago   Up 5 minutes   0.0.0.0:9090->9090/tcp
```

**Durum:** ✅ Her iki konteyner de çalışıyor

---

### 3.2 Prometheus

#### Hazır Durumu

**Endpoint:** `http://localhost:9090/-/ready`

**Gerçek Çıktı:**
```
StatusCode: 200 OK
Content: Prometheus Server is Ready.
```

**Durum:** ✅ Prometheus hazır ve çalışıyor

#### Hedef (Target) Durumu

**Endpoint:** `http://localhost:9090/targets`

**aibot Hedefi:**
```json
{
  "job": "ai-trading-bot",
  "scrapeUrl": "http://host.docker.internal:8000/metrics",
  "health": "up",
  "lastScrape": "2025-10-15T15:20:34.913057096Z",
  "lastScrapeDuration": 0.005089896,
  "scrapeInterval": "10s"
}
```

**Durum:** ✅ aibot hedefi **UP** (bot çalıştığında metrics toplanıyor)

#### Yapılandırma

**Dosya:** `monitoring/prometheus.yml`

```yaml
scrape_configs:
  - job_name: 'ai-trading-bot'
    scrape_interval: 10s
    scrape_timeout: 5s
    static_configs:
      - targets: ['host.docker.internal:8000']
        labels:
          app: 'ai-trading-bot'
          service: 'main'
```

**Not:** `host.docker.internal` Windows/Mac için host makineye erişim sağlar. Linux'ta `172.17.0.1` kullanabilirsiniz.

---

### 3.3 Grafana

#### Health Kontrolü

**Endpoint:** `http://localhost:3000/api/health`

**Gerçek Çıktı:**
```json
{
  "database": "ok",
  "version": "12.2.0",
  "commit": "92f1fba9b4b6700328e99e97328d6639df8ddc3d"
}
```

**Durum:** ✅ Database ve Grafana sağlıklı

#### Giriş Bilgileri

- **URL:** http://localhost:3000
- **Kullanıcı:** `admin`
- **Şifre:** `admin` (ilk girişte değiştirin!)

#### Otomatik Provisioning

**Datasource:** Prometheus otomatik yükleniyor  
**Dashboard:** AiBotBS Trading Dashboard otomatik yükleniyor

**Dosyalar:**
- `monitoring/grafana/provisioning/datasources/prometheus.yml`
- `monitoring/grafana/provisioning/dashboards/dashboard.yml`
- `monitoring/grafana/provisioning/dashboards/aibot-dashboard.json`

---

## 4. Hızlı Komutlar (Kopyala-Yapıştır)

### 4.1 PowerShell (Windows)

```powershell
# Script yükleme ve başlatma
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Unblock-File .\scripts\dev.ps1
. .\scripts\dev.ps1

# Tek test çalıştırması
Start-Trading -Once

# Sadece scheduler başlat
Start-Scheduler

# 🚀 Docker + Bot birlikte (Full Stack)
Start-FullStack

# Logları izle
Watch-Logs -Follow

# Sağlık kontrolü
Test-Health
```

### 4.2 Bash (Linux/Mac)

```bash
# Script yükleme ve başlatma
source scripts/dev.sh

# Tek test çalıştırması
run_trading --once

# Scheduler başlat
run_scheduler

# Logları izle
tail_logs 100 --follow

# Sağlık kontrolü
check_health
```

### 4.3 Docker Monitoring

```bash
# Monitoring stack'i başlat
cd monitoring
docker compose up -d

# Logları izle
docker compose logs -f

# Konteyner durumu
docker compose ps

# Stack'i durdur
docker compose down
```

---

## 5. Sorun Giderme

### Problem: Log gelmiyor

**Sebep:** Docker detach modda çalışıyor, konsolda log görünmüyor.

**Çözüm:**
```bash
cd monitoring
docker compose logs -f
```

### Problem: `/metrics` endpoint erişilemiyor

**Kontrol Listesi:**
1. Bot çalışıyor mu? → `Check-Health` / `check_health`
2. Port açık mı? → `http://localhost:8000/metrics` (bot çalışırken)
3. Firewall engelliyor mu? → Windows Defender / iptables kontrol et
4. `METRICS_ENABLED=true` mi? → `.env` dosyasını kontrol et

### Problem: Prometheus aibot hedefi DOWN

**Sebep:** Bot metrics sunmuyor veya ağ bağlantısı yok.

**Çözüm:**
```bash
# Bot çalışıyor mu?
Test-Health  # PowerShell
check_health  # Bash

# Metrics endpoint test et
curl http://localhost:8000/metrics

# Docker'dan erişim test et
docker exec aibot_prometheus wget -qO- http://host.docker.internal:8000/metrics
```

**Linux için:**
`monitoring/prometheus.yml` içinde `host.docker.internal:8000` yerine `172.17.0.1:8000` kullanın.

### Problem: Grafana dashboard boş

**Kontrol Listesi:**
1. Datasource doğru mu? → Grafana → Configuration → Data Sources
2. Prometheus URL doğru mu? → `http://prometheus:9090`
3. Provisioning mount edilmiş mi? → `docker compose logs grafana`
4. Dashboard yüklü mü? → Grafana → Dashboards → AiBotBS Trading Dashboard

**Çözüm:**
```bash
cd monitoring
docker compose restart grafana
```

### Problem: OKX API 50110 Hatası

**Sebep:** IP whitelist hatası (OKX API key'iniz bu IP'den erişime izin vermiyor).

**Çözüm:**
1. OKX.com → API Management → IP Whitelist
2. Sunucu IP'nizi ekleyin
3. `.env` dosyasında API key/secret/passphrase doğru mu kontrol edin

### Problem: Python bulunamadı

**PowerShell:**
```powershell
Show-Python  # Mevcut durumu göster

# Python yükle (Windows)
# https://www.python.org/downloads/
# veya
winget install Python.Python.3.11

# Venv oluştur
python -m venv venv
```

**Bash:**
```bash
show_python  # Mevcut durumu göster

# Python yükle (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv

# Venv oluştur
python3.11 -m venv venv
```

---

## 6. Komut Fonksiyon Referansı

### PowerShell Fonksiyonları

```
Get-PythonPath    - Python yolu tespit eder (internal)
Show-Banner       - Renkli banner gösterir (internal)
Show-Python       - Python yapılandırmasını gösterir
Install-Req       - requirements.txt yükler
Start-Trading     - Trading bot'u başlatır
Start-Scheduler   - Scheduler'ı başlatır (sadece bot)
Start-FullStack   - Docker + Bot birlikte başlatır 🚀
Start-Backtest    - Backtest çalıştırır
Watch-Logs        - Log dosyalarını görüntüler
Test-Health       - Sistem sağlık kontrolü
Stop-Bot          - Bot'u durdurur
Clear-Logs        - Eski logları siler
Show-Menu         - Yardım menüsünü gösterir
```

### Bash Fonksiyonları

```
get_python_path   - Python yolu tespit eder (internal)
show_banner       - Renkli banner gösterir (internal)
show_python       - Python yapılandırmasını gösterir
install_req       - requirements.txt yükler
run_trading       - Trading bot'u başlatır
run_scheduler     - Scheduler'ı başlatır
run_backtest      - Backtest çalıştırır
tail_logs         - Log dosyalarını görüntüler
check_health      - Sistem sağlık kontrolü
stop_bot          - Bot'u durdurur
clean_logs        - Eski logları siler
show_menu         - Yardım menüsünü gösterir
```

---

## 7. Ortam Değişkenleri

Scriptler otomatik olarak şu geliştirme ortam değişkenlerini ayarlar:

```bash
APP_ENV=dev                  # Geliştirme modu
DEV_CONSOLE=1               # Konsol çıktısı aktif
LOG_LEVEL=DEBUG             # Detaylı loglama
PYTHONUNBUFFERED=1          # Python çıktısı buffersız
PYTHONPATH=.                # Proje root path
CONSOLE_LOG=1               # Konsol log formatı
LOG_EMOJI=1                 # Emoji'li loglar
```

**Üretim için** bu scriptleri kullanmayın! Üretim dağıtımı için `.env` dosyasını ve Docker Compose'u kullanın.

---

## 8. Monitoring Dosya Yapısı

```
monitoring/
├── docker-compose.yml              # Ana compose dosyası
├── docker-compose.override.yml     # Geliştirme override
├── prometheus.yml                  # Prometheus config
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml      # Prometheus datasource
│   │   └── dashboards/
│   │       ├── dashboard.yml       # Dashboard provider
│   │       └── aibot-dashboard.json # AI Bot dashboard
│   └── dashboard.json              # (eski versiyon)
└── prometheus_exporter.py          # Python metrics exporter
```

---

## 9. Yapılan Değişiklikler

Bu dokümanda belirtilen iyileştirmeler için yapılan değişiklikler:

### ✅ Güncellenen Dosyalar

1. **scripts/dev.ps1**
   - Otomatik venv tespiti eklendi
   - `Get-PythonPath` fonksiyonu: venv yoksa sistem Python kullanır
   - `Show-Python` fonksiyonu: Python yapılandırmasını gösterir
   - `Install-Req` fonksiyonu: requirements.txt yükler
   - `Start-Trading` ve `Start-Scheduler`: `-VenvPath` ve `-NoVenv` parametreleri eklendi
   - `Watch-Logs`: `-Tail` parametresi eklendi (eski `-Lines` yerine)
   - `Test-Health`: Python version kontrolü eklendi
   - **PSScriptAnalyzer uyumlu**: Tüm fonksiyonlar approved verbs kullanıyor

2. **scripts/dev.sh**
   - Otomatik venv tespiti eklendi
   - `get_python_path` fonksiyonu: venv yoksa sistem Python kullanır
   - `show_python` fonksiyonu: Python yapılandırmasını gösterir
   - `install_req` fonksiyonu: requirements.txt yükler
   - `run_trading` ve `run_scheduler`: `--venv-path` ve `--no-venv` parametreleri eklendi
   - `check_health`: Python version kontrolü eklendi

### ✅ Mevcut ve Çalışan Dosyalar

3. **monitoring/docker-compose.yml** - Değişiklik yapılmadı ✅
4. **monitoring/docker-compose.override.yml** - Değişiklik yapılmadı ✅
5. **monitoring/prometheus.yml** - Değişiklik yapılmadı ✅ (aibot hedefi zaten mevcut)
6. **monitoring/grafana/provisioning/datasources/prometheus.yml** - Değişiklik yapılmadı ✅
7. **monitoring/grafana/provisioning/dashboards/dashboard.yml** - Değişiklik yapılmadı ✅
8. **monitoring/grafana/provisioning/dashboards/aibot-dashboard.json** - Değişiklik yapılmadı ✅

### 📝 Oluşturulan Dosyalar

9. **docs/START_AND_MONITORING.md** - Bu dokuman (yeni) 📄

---

## 10. Ek Kaynaklar

- **Proje Dökümantasyonu:** `docs/README.md`
- **Çalıştırma Rehberi:** `docs/RUN_GUIDE_CURRENT.md`
- **Monitoring Detayları:** `docs/MONITORING.md`
- **Telegram Bot:** `docs/TELEGRAM.md`
- **Test Rehberi:** `docs/TESTING.md`

---

## 📞 Destek

Sorun yaşarsanız:

1. `Check-Health` / `check_health` komutunu çalıştırın
2. `Tail-Logs -Follow` / `tail_logs 100 --follow` ile logları kontrol edin
3. `docker compose logs -f` ile monitoring loglarını inceleyin
4. Bu dokümandaki sorun giderme bölümüne bakın

---

**Son Güncelleme:** 15 Ekim 2025, 18:25  
**Hazırlayan:** AI Agent  
**Doküman Versiyonu:** 1.0

